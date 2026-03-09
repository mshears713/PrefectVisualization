"""
demo_prd6_test.py — Verification script for PRD 06 (Data-Flow Graph Builder Refactor).

Run with:
    python demo_prd6_test.py

What this script demonstrates
------------------------------
PRD 06 shifts graph semantics from call-trace (parent→child) to data-flow
(step N → step N+1 in pipeline narrative order). This test file verifies
all five acceptance criteria from the PRD test plan:

Test 1 — Linear pipeline ordering
    A simple linear trace produces edges in exact narrative progression:
    load_pdf → extract_text → clean_text → generate_summary

Test 2 — Existing metadata preservation
    All Phase 1 metadata fields survive the refactor intact on graph nodes:
    task_name, task_description, module_name, duration_ms, status,
    input_preview, output_preview, input_length, output_length, error_message

Test 3 — Language branch structure
    When detect_language runs, the graph shows both:
    - English path (taken)  → solid edge, branch_taken=True
    - Non-English path (not taken) → placeholder node, branch_taken=False

Test 4 — Chunk strategy branch structure
    When choose_chunk_strategy runs, the graph shows both:
    - Chunked path (taken)     → split_into_chunks node, branch_taken=True
    - Single-pass path (not taken) → placeholder node, branch_taken=False

Test 5 — Deterministic graph
    Running build_dataflow_graph on the same trace twice produces
    identical node IDs, edge lists, and branch metadata.

The final section prints a sample pipeline narrative so the graph structure
can be verified visually.
"""

from __future__ import annotations

import pprint
import sys
from typing import Optional

from graph.dataflow_builder import (
    build_dataflow_graph,
    graph_debug_summary,
    list_graph_edges,
    list_graph_nodes,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal valid TraceEvent dict for testing
# ---------------------------------------------------------------------------

def _make_event(
    task_name: str,
    trace_index: int,
    module_name: str = "",
    task_description: str = "",
    duration_ms: float = 10.0,
    status: str = "success",
    parent_task: Optional[str] = None,
    input_preview: str = "input",
    output_preview: str = "output",
    input_length: int = 5,
    output_length: int = 6,
    error_message: Optional[str] = None,
) -> dict:
    """Construct a minimal TraceEvent dict for use in tests.

    Supplies default values for every required field so test cases can stay
    focused on only the fields that matter for that test.
    """
    return {
        "task_name": task_name,
        "task_description": task_description or f"Task: {task_name}",
        "module_name": module_name,
        "parent_task": parent_task,
        "trace_index": trace_index,
        "start_time": float(trace_index),
        "end_time": float(trace_index) + duration_ms / 1000,
        "duration_ms": duration_ms,
        "status": status,
        "input_preview": input_preview,
        "output_preview": output_preview if status == "success" else "",
        "input_length": input_length,
        "output_length": output_length if status == "success" else 0,
        "error_message": error_message,
    }


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_summary(summary: dict, title: str = "Graph Summary") -> None:
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    print(f"  Nodes            : {summary['num_nodes']}")
    print(f"  Edges            : {summary['num_edges']}")
    print(f"  Pipeline flow    : {' → '.join(summary['pipeline_flow'])}")
    print()

    for node in summary["nodes"]:
        prefix = "  [ALT]" if node["is_alternate"] else f"  [{node['trace_index']:2d}]"
        branch_tag = ""
        if node["branch_group"]:
            branch_tag = f"  branch={node['branch_group']}/{node['branch_option']}"
        print(
            f"{prefix} {node['node_id']:<45}"
            f"  status={node['status']:<12}"
            f"  dur={node['duration_ms']:.1f}ms"
            f"{branch_tag}"
        )
    print()

    for src, dst in summary["edges"]:
        edge_data = next(
            (e for e in summary["branch_edges"] if e["from_node"] == src and e["to_node"] == dst),
            None,
        )
        if edge_data:
            taken = "TAKEN" if edge_data["branch_taken"] else "alternate"
            tag = f"  [{edge_data['branch_group']} → {edge_data['branch_option']} ({taken})]"
        else:
            tag = ""
        print(f"  EDGE  {src}  →  {dst}{tag}")
    print(sep)


# ---------------------------------------------------------------------------
# Test 1 — Linear pipeline ordering
# ---------------------------------------------------------------------------

def test_linear_pipeline_ordering() -> None:
    """Edges must reflect narrative order, not call-stack order.

    A trace containing only four tasks from different pipeline stages should
    produce exactly three edges in the correct narrative sequence:
        load_pdf → extract_text → clean_text → generate_summary
    """
    print("\n\n>>> Test 1: Linear pipeline ordering")
    trace = [
        _make_event("load_pdf",        trace_index=0, module_name="PDF Ingestion"),
        _make_event("extract_text",    trace_index=1, module_name="Text Extraction"),
        _make_event("clean_text",      trace_index=2, module_name="Text Processing"),
        _make_event("generate_summary", trace_index=3, module_name="LLM Analysis"),
    ]

    graph = build_dataflow_graph(trace)
    summary = graph_debug_summary(graph)
    _print_summary(summary, "Test 1 — Linear pipeline ordering")

    # Exactly 4 executed nodes plus any alternate placeholders for branches
    # not triggered (detect_language and choose_chunk_strategy didn't run,
    # so no alternate branches are attached — 0 alternates expected).
    executed_nodes = [n for n in summary["nodes"] if not n["is_alternate"]]
    assert len(executed_nodes) == 4, (
        f"Expected 4 executed nodes, got {len(executed_nodes)}"
    )

    # Edges must follow narrative progression, not call hierarchy.
    # load_pdf is first in the pipeline; generate_summary is last of these four.
    edge_pairs = summary["edges"]
    assert len(edge_pairs) == 3, f"Expected 3 edges, got {len(edge_pairs)}"

    # Verify the exact narrative sequence by checking node ordering.
    pipeline_flow = summary["pipeline_flow"]
    assert pipeline_flow == [
        "load_pdf", "extract_text", "clean_text", "generate_summary"
    ], f"Unexpected pipeline flow: {pipeline_flow}"

    # Verify each edge follows pipeline order (step N → step N+1).
    from_nodes = [src for src, _ in edge_pairs]
    to_nodes   = [dst for _, dst in edge_pairs]
    assert any("load_pdf" in n for n in from_nodes), "load_pdf should be an edge source"
    assert any("generate_summary" in n for n in to_nodes), "generate_summary should be an edge target"

    # Confirm this is pipeline-flow edges, not call-trace edges.
    for u, v, data in graph.edges(data=True):
        assert data.get("relationship") == "pipeline_flow", (
            f"Expected 'pipeline_flow' relationship, got {data.get('relationship')!r}"
        )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Existing metadata preservation
# ---------------------------------------------------------------------------

def test_metadata_preservation() -> None:
    """All Phase 1 metadata fields must survive the Phase 2 refactor.

    Each field listed here is required by later PRDs. Losing any of them
    during the graph-builder refactor would break downstream consumers.
    """
    print("\n\n>>> Test 2: Metadata preservation")
    trace = [
        _make_event(
            task_name="extract_text",
            trace_index=0,
            module_name="Text Extraction",
            task_description="Extract raw text from PDF pages",
            duration_ms=118.5,
            status="success",
            parent_task=None,
            input_preview="length=5, head='page1', tail='page1'",
            output_preview="length=32441, head='Intro...', tail='...End'",
            input_length=5,
            output_length=32441,
            error_message=None,
        )
    ]

    graph = build_dataflow_graph(trace)

    # The node was added under the id "extract_text__0"
    assert "extract_text__0" in graph.nodes, "Node 'extract_text__0' not found in graph"
    node = graph.nodes["extract_text__0"]

    # Phase 1 required metadata
    assert node["task_name"] == "extract_text"
    assert node["task_description"] == "Extract raw text from PDF pages"
    assert node["module_name"] == "Text Extraction"
    assert node["duration_ms"] == 118.5
    assert node["status"] == "success"
    assert node["input_preview"] == "length=5, head='page1', tail='page1'"
    assert node["output_preview"] == "length=32441, head='Intro...', tail='...End'"
    assert node["input_length"] == 5
    assert node["output_length"] == 32441
    assert node["error_message"] is None
    assert node["parent_task"] is None
    assert node["trace_index"] == 0

    # Phase 2 additional metadata
    assert node["is_alternate"] is False
    assert "stage_index" in node
    assert "step_order" in node

    # Summary node must also carry metadata
    summary = graph_debug_summary(graph)
    node_summary = next(n for n in summary["nodes"] if n["task_name"] == "extract_text")
    assert node_summary["status"] == "success"
    assert node_summary["duration_ms"] == 118.5
    assert node_summary["module_name"] == "Text Extraction"

    _print_summary(summary, "Test 2 — Metadata preservation")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — Language branch structure
# ---------------------------------------------------------------------------

def test_language_branch() -> None:
    """The graph must represent both English and Non-English branch paths.

    When detect_language executes:
    - A pipeline-flow edge to clean_text must exist and be marked branch_taken=True.
    - A placeholder node for non_english_processing must exist (is_alternate=True).
    - An edge from detect_language to non_english_processing must exist and be
      marked branch_taken=False.

    The visualization layer later uses these metadata flags to render executed
    branches as solid lines and alternate branches as dotted/muted.
    """
    print("\n\n>>> Test 3: Language branch structure")
    trace = [
        _make_event("extract_text",    trace_index=0, module_name="Text Extraction"),
        _make_event("merge_pages",     trace_index=1, module_name="Text Extraction"),
        _make_event("detect_language", trace_index=2, module_name="Text Extraction"),
        _make_event("clean_text",      trace_index=3, module_name="Text Processing"),
    ]

    graph = build_dataflow_graph(trace)
    summary = graph_debug_summary(graph)
    _print_summary(summary, "Test 3 — Language branch")

    # --- Verify alternate placeholder exists ---
    node_names = {d["task_name"] for _, d in graph.nodes(data=True)}
    assert "non_english_processing" in node_names, (
        "Placeholder node for non_english_processing not found"
    )
    alt_node = next(
        d for _, d in graph.nodes(data=True)
        if d["task_name"] == "non_english_processing"
    )
    assert alt_node["is_alternate"] is True, (
        "non_english_processing node should be marked is_alternate=True"
    )
    assert alt_node["status"] == "not_executed"

    # --- Verify taken branch edge (detect_language → clean_text) ---
    detect_lang_node_id = "detect_language__2"
    clean_text_node_id = "clean_text__3"
    assert graph.has_edge(detect_lang_node_id, clean_text_node_id), (
        f"Expected edge {detect_lang_node_id} → {clean_text_node_id} (english branch taken)"
    )
    taken_edge = graph.edges[detect_lang_node_id, clean_text_node_id]
    assert taken_edge.get("branch_taken") is True
    assert taken_edge.get("branch_group") == "language_branch"
    assert taken_edge.get("branch_option") == "english"

    # --- Verify alternate branch edge (detect_language → non_english_processing) ---
    alt_node_id = "non_english_processing__alt"
    assert graph.has_edge(detect_lang_node_id, alt_node_id), (
        f"Expected edge {detect_lang_node_id} → {alt_node_id} (non_english branch alternate)"
    )
    alt_edge = graph.edges[detect_lang_node_id, alt_node_id]
    assert alt_edge.get("branch_taken") is False
    assert alt_edge.get("branch_group") == "language_branch"
    assert alt_edge.get("branch_option") == "non_english"

    # --- Branch edge summary contains both ---
    branch_groups = {e["branch_group"] for e in summary["branch_edges"]}
    assert "language_branch" in branch_groups

    taken_count = sum(
        1 for e in summary["branch_edges"]
        if e["branch_group"] == "language_branch" and e["branch_taken"] is True
    )
    alternate_count = sum(
        1 for e in summary["branch_edges"]
        if e["branch_group"] == "language_branch" and e["branch_taken"] is False
    )
    assert taken_count >= 1, "Expected at least one taken language_branch edge"
    assert alternate_count >= 1, "Expected at least one alternate language_branch edge"

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Chunk strategy branch structure
# ---------------------------------------------------------------------------

def test_chunk_strategy_branch() -> None:
    """The graph must represent both the chunked and single-pass paths.

    When choose_chunk_strategy executes:
    - An edge to split_into_chunks must exist and be marked branch_taken=True.
    - A placeholder node for single_pass_analysis must exist (is_alternate=True).
    - An edge from choose_chunk_strategy to single_pass_analysis must exist and
      be marked branch_taken=False.
    """
    print("\n\n>>> Test 4: Chunk strategy branch structure")
    trace = [
        _make_event("compute_text_length",    trace_index=0, module_name="Chunking"),
        _make_event("choose_chunk_strategy",  trace_index=1, module_name="Chunking"),
        _make_event("split_into_chunks",      trace_index=2, module_name="Chunking"),
        _make_event("analyze_chunks",         trace_index=3, module_name="LLM Analysis"),
    ]

    graph = build_dataflow_graph(trace)
    summary = graph_debug_summary(graph)
    _print_summary(summary, "Test 4 — Chunk strategy branch")

    # --- Verify alternate placeholder exists ---
    node_names = {d["task_name"] for _, d in graph.nodes(data=True)}
    assert "single_pass_analysis" in node_names, (
        "Placeholder node for single_pass_analysis not found"
    )
    alt_node = next(
        d for _, d in graph.nodes(data=True)
        if d["task_name"] == "single_pass_analysis"
    )
    assert alt_node["is_alternate"] is True
    assert alt_node["status"] == "not_executed"

    # --- Verify taken branch edge (choose_chunk_strategy → split_into_chunks) ---
    decide_node_id = "choose_chunk_strategy__1"
    split_node_id = "split_into_chunks__2"
    assert graph.has_edge(decide_node_id, split_node_id), (
        f"Expected edge {decide_node_id} → {split_node_id} (chunked branch taken)"
    )
    taken_edge = graph.edges[decide_node_id, split_node_id]
    assert taken_edge.get("branch_taken") is True
    assert taken_edge.get("branch_group") == "chunk_strategy"
    assert taken_edge.get("branch_option") == "chunked"

    # --- Verify alternate branch edge ---
    alt_node_id = "single_pass_analysis__alt"
    assert graph.has_edge(decide_node_id, alt_node_id), (
        f"Expected edge {decide_node_id} → {alt_node_id} (single_pass branch alternate)"
    )
    alt_edge = graph.edges[decide_node_id, alt_node_id]
    assert alt_edge.get("branch_taken") is False
    assert alt_edge.get("branch_group") == "chunk_strategy"
    assert alt_edge.get("branch_option") == "single_pass"

    # --- Verify narrative flow continues after the branch ---
    assert graph.has_edge(split_node_id, "analyze_chunks__3"), (
        "Pipeline should continue split_into_chunks → analyze_chunks"
    )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Deterministic graph
# ---------------------------------------------------------------------------

def test_deterministic_graph() -> None:
    """Same trace must produce identical graph structure on every run.

    This is critical for debugging stability and conference demonstration
    repeatability. The test builds the graph twice and compares node IDs,
    edge tuples, and branch metadata dictionaries.
    """
    print("\n\n>>> Test 5: Deterministic graph")
    trace = [
        _make_event("load_pdf",              trace_index=0,  module_name="PDF Ingestion"),
        _make_event("validate_pdf",          trace_index=1,  module_name="PDF Ingestion"),
        _make_event("count_pages",           trace_index=2,  module_name="PDF Ingestion"),
        _make_event("extract_text",          trace_index=3,  module_name="Text Extraction"),
        _make_event("merge_pages",           trace_index=4,  module_name="Text Extraction"),
        _make_event("detect_language",       trace_index=5,  module_name="Text Extraction"),
        _make_event("clean_text",            trace_index=6,  module_name="Text Processing"),
        _make_event("normalize_whitespace",  trace_index=7,  module_name="Text Processing"),
        _make_event("remove_headers",        trace_index=8,  module_name="Text Processing"),
        _make_event("compute_text_length",   trace_index=9,  module_name="Chunking"),
        _make_event("choose_chunk_strategy", trace_index=10, module_name="Chunking"),
        _make_event("split_into_chunks",     trace_index=11, module_name="Chunking"),
        _make_event("analyze_chunks",        trace_index=12, module_name="LLM Analysis"),
        _make_event("aggregate_results",     trace_index=13, module_name="LLM Analysis"),
        _make_event("generate_summary",      trace_index=14, module_name="LLM Analysis"),
        _make_event("build_structured_result", trace_index=15, module_name="Structured Output"),
        _make_event("validate_schema",       trace_index=16, module_name="Structured Output"),
        _make_event("export_result",         trace_index=17, module_name="Structured Output"),
    ]

    graph_a = build_dataflow_graph(trace)
    graph_b = build_dataflow_graph(trace)

    summary_a = graph_debug_summary(graph_a)
    summary_b = graph_debug_summary(graph_b)

    # Node sets must be identical.
    nodes_a = sorted(n["node_id"] for n in summary_a["nodes"])
    nodes_b = sorted(n["node_id"] for n in summary_b["nodes"])
    assert nodes_a == nodes_b, (
        f"Node sets differ:\n  Run 1: {nodes_a}\n  Run 2: {nodes_b}"
    )

    # Edge lists must be identical.
    edges_a = sorted(summary_a["edges"])
    edges_b = sorted(summary_b["edges"])
    assert edges_a == edges_b, (
        f"Edge lists differ:\n  Run 1: {edges_a}\n  Run 2: {edges_b}"
    )

    # Pipeline narrative flow must be identical.
    assert summary_a["pipeline_flow"] == summary_b["pipeline_flow"], (
        "Pipeline flow order differs between runs"
    )

    # Branch edge metadata must be identical.
    def _normalize_branch_edges(branch_edges):
        return sorted(
            (e["from_node"], e["to_node"], e["branch_group"], e["branch_option"], e["branch_taken"])
            for e in branch_edges
        )

    branch_a = _normalize_branch_edges(summary_a["branch_edges"])
    branch_b = _normalize_branch_edges(summary_b["branch_edges"])
    assert branch_a == branch_b, (
        f"Branch edge metadata differs between runs:\n  Run 1: {branch_a}\n  Run 2: {branch_b}"
    )

    _print_summary(summary_a, "Test 5 — Deterministic graph (run 1)")
    print(f"  Run 1 nodes : {nodes_a}")
    print(f"  Run 2 nodes : {nodes_b}")
    print(f"  Both runs identical: YES")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Bonus: full pipeline narrative walkthrough
# ---------------------------------------------------------------------------

def run_full_pipeline_walkthrough() -> None:
    """Print a complete narrative of the Phase 2 PDF pipeline graph.

    This shows the data-flow graph for the full 18-task pipeline (plus two
    alternate branch placeholders), demonstrating the 'story' the graph tells:

    PDF loaded → text extracted → language detected → text cleaned →
    chunk strategy chosen → document split → chunks analyzed →
    summary generated → structured result exported
    """
    print("\n\n>>> Bonus: Full Phase 2 pipeline narrative walkthrough")
    trace = [
        # PDF Ingestion
        _make_event("load_pdf",              trace_index=0,  module_name="PDF Ingestion",
                    task_description="Load the PDF file from disk",
                    input_preview="length=22, head='report.pdf'", input_length=22,
                    output_preview="length=4, head='[doc]'", output_length=4, duration_ms=25.0),
        _make_event("validate_pdf",          trace_index=1,  module_name="PDF Ingestion",
                    task_description="Validate PDF structure and page count",
                    duration_ms=5.0),
        _make_event("count_pages",           trace_index=2,  module_name="PDF Ingestion",
                    task_description="Count total pages in the document",
                    duration_ms=2.0),
        # Text Extraction (with language branch)
        _make_event("extract_text",          trace_index=3,  module_name="Text Extraction",
                    task_description="Extract raw text from all PDF pages",
                    output_length=32441, duration_ms=118.0),
        _make_event("merge_pages",           trace_index=4,  module_name="Text Extraction",
                    task_description="Merge per-page text into a single document",
                    duration_ms=3.0),
        _make_event("detect_language",       trace_index=5,  module_name="Text Extraction",
                    task_description="Detect the primary language of the document",
                    duration_ms=8.0),
        # Text Processing (english branch was taken)
        _make_event("clean_text",            trace_index=6,  module_name="Text Processing",
                    task_description="Remove noise characters and fix encoding",
                    output_length=28990, duration_ms=42.0),
        _make_event("normalize_whitespace",  trace_index=7,  module_name="Text Processing",
                    task_description="Collapse multiple spaces and normalize newlines",
                    duration_ms=15.0),
        _make_event("remove_headers",        trace_index=8,  module_name="Text Processing",
                    task_description="Strip repeated header and footer text",
                    duration_ms=20.0),
        # Chunking (chunked branch is taken)
        _make_event("compute_text_length",   trace_index=9,  module_name="Chunking",
                    task_description="Compute character length of cleaned text",
                    duration_ms=1.0),
        _make_event("choose_chunk_strategy", trace_index=10, module_name="Chunking",
                    task_description="Select chunking strategy based on text length",
                    duration_ms=2.0),
        _make_event("split_into_chunks",     trace_index=11, module_name="Chunking",
                    task_description="Split text into overlapping semantic chunks",
                    duration_ms=55.0),
        # LLM Analysis
        _make_event("analyze_chunks",        trace_index=12, module_name="LLM Analysis",
                    task_description="Run LLM analysis on each chunk",
                    duration_ms=820.0),
        _make_event("aggregate_results",     trace_index=13, module_name="LLM Analysis",
                    task_description="Aggregate per-chunk LLM results",
                    duration_ms=12.0),
        _make_event("generate_summary",      trace_index=14, module_name="LLM Analysis",
                    task_description="Generate the final document summary",
                    duration_ms=340.0),
        # Structured Output
        _make_event("build_structured_result", trace_index=15, module_name="Structured Output",
                    task_description="Build the Pydantic structured result object",
                    duration_ms=4.0),
        _make_event("validate_schema",       trace_index=16, module_name="Structured Output",
                    task_description="Validate output conforms to result schema",
                    duration_ms=2.0),
        _make_event("export_result",         trace_index=17, module_name="Structured Output",
                    task_description="Serialize and export the final result",
                    duration_ms=8.0),
    ]

    graph = build_dataflow_graph(trace)
    summary = graph_debug_summary(graph)
    _print_summary(summary, "Full Phase 2 PDF Pipeline")

    print("\n  === NARRATIVE ===")
    print(f"  {' → '.join(summary['pipeline_flow'])}")

    print("\n  === BRANCH POINTS ===")
    for edge in summary["branch_edges"]:
        taken_str = "TAKEN" if edge["branch_taken"] else "alternate"
        print(
            f"  [{edge['branch_group']}]  "
            f"{edge['from_node']} → {edge['to_node']}  "
            f"option={edge['branch_option']} ({taken_str})"
        )

    print(f"\n  Total nodes   : {summary['num_nodes']} "
          f"({summary['num_nodes'] - 2} executed + 2 alternate placeholders)")
    print(f"  Total edges   : {summary['num_edges']}")
    print(f"  Modules       : {list(summary['stage_counts'].keys())}")
    print(f"  Statuses      : {summary['status_counts']}")

    # Verify the graph reads as a pipeline, not a stack trace.
    # There must be no "pipeline → every_task" hub pattern (old Phase 1 shape).
    # Instead, each node has at most one pipeline_flow predecessor on the spine.
    spine_nodes = [n["node_id"] for n in summary["nodes"] if not n["is_alternate"]]
    for node_id in spine_nodes:
        pipeline_predecessors = [
            u for u, v, d in graph.in_edges(node_id, data=True)
            if d.get("relationship") == "pipeline_flow" and d.get("branch_taken") is not False
        ]
        assert len(pipeline_predecessors) <= 1, (
            f"Node {node_id} has {len(pipeline_predecessors)} pipeline predecessors; "
            f"expected at most 1 (this would indicate a hub, not a pipeline)"
        )

    print("\n  Pipeline shape verified: no hub-and-spoke pattern detected.")
    print("  This graph tells a story, not a stack trace.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_linear_pipeline_ordering,
        test_metadata_preservation,
        test_language_branch,
        test_chunk_strategy_branch,
        test_deterministic_graph,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except AssertionError as exc:
            print(f"  FAILED: {exc}")
            all_passed = False
        except Exception:
            import traceback
            print("  ERROR (unexpected):")
            traceback.print_exc()
            all_passed = False

    try:
        run_full_pipeline_walkthrough()
    except Exception:
        import traceback
        print("  ERROR in walkthrough:")
        traceback.print_exc()
        all_passed = False

    if all_passed:
        print("\n\nAll PRD 06 tests passed.")
    else:
        print("\n\nSome tests FAILED.")
        sys.exit(1)
