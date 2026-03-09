"""
demo_prd8_test.py — Verification script for PRD 08 (Task Graph Drill-Down).

Run with:
    python demo_prd8_test.py

What this demonstrates
----------------------
PRD 08 implements the drill-down layer: selecting a module from the overview
graph and generating a focused task graph for that module.

Two-layer navigation contract:

    Module Overview (PRD 07)
        PDF Ingestion → Text Extraction → Text Processing → …
                                │
                         user selects module
                                │
    Task Graph (PRD 08)         ▼
        extract_text → merge_pages → detect_language
                                   ↘ non_english_processing  [alternate]

Test 1 — Task filtering
    Selecting "Text Extraction" returns only that module's tasks.
    Tasks from other modules must not appear.

Test 2 — Intra-module edge preservation
    Edges between tasks inside the module are preserved intact.

Test 3 — External edge removal
    Edges to tasks in other modules are dropped.

Test 4 — Module context payload
    The returned payload carries module-level metadata for headers/breadcrumbs.

Test 5 — Deterministic navigation
    Selecting the same module twice returns identical graph structure.

The bonus walkthrough shows the full two-layer navigation for the Phase 2
PDF pipeline, drilling into Text Extraction, Chunking, and LLM Analysis.
"""

from __future__ import annotations

import sys
from typing import Optional

from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph, module_graph_debug_summary
from graph.task_graph_builder import (
    MODULE_OVERVIEW_REF,
    TaskGraphPayload,
    build_task_graph_for_module,
    module_name_to_id,
    task_graph_debug_summary,
)


# ---------------------------------------------------------------------------
# Helpers
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


def _print_payload(payload: TaskGraphPayload, title: str = "") -> None:
    summary = task_graph_debug_summary(payload)
    sep = "=" * 72
    heading = title or f"Task Graph — {payload.module_name}"
    print(f"\n{sep}")
    print(f"  {heading}")
    print(sep)
    print(f"  Module       : {summary['module_name']}")
    print(f"  Module ID    : {summary['module_id']}")
    print(f"  Back to      : {summary['back_ref']}")
    print(f"  Nodes        : {summary['num_nodes']}")
    print(f"  Edges        : {summary['num_edges']}")
    print(f"  Task flow    : {' → '.join(summary['task_flow'])}")
    ctx = summary["context"]
    print(f"  Duration     : {ctx['total_duration_ms']:.1f} ms")
    print(f"  Input        : {ctx['input_summary']}")
    print(f"  Output       : {ctx['output_summary']}")
    print()

    for node in summary["nodes"]:
        alt = "  [ALT]" if node["is_alternate"] else f"  [{node['trace_index']:2d}]"
        branch_tag = ""
        if node["branch_group"]:
            branch_tag = f"  branch={node['branch_group']}/{node['branch_option']}"
        print(
            f"{alt} {node['node_id']:<45}"
            f"  status={node['status']:<12}"
            f"  dur={node['duration_ms']:.1f}ms"
            f"{branch_tag}"
        )

    print()
    for u, v in summary["edges"]:
        be = next(
            (e for e in summary["branch_edges"] if e["from_node"] == u and e["to_node"] == v),
            None,
        )
        tag = ""
        if be:
            taken = "TAKEN" if be["branch_taken"] else "alternate"
            tag = f"  [{be['branch_group']} → {be['branch_option']} ({taken})]"
        print(f"  EDGE  {u}  →  {v}{tag}")
    print(sep)


# ---------------------------------------------------------------------------
# Full-pipeline trace fixture (reused across multiple tests)
# ---------------------------------------------------------------------------

def _build_full_trace():
    return [
        # PDF Ingestion
        _make_event("load_pdf",              0,  "PDF Ingestion",
                    input_preview="file=report.pdf", output_preview="doc_obj",   duration_ms=25.0),
        _make_event("validate_pdf",          1,  "PDF Ingestion",
                    input_preview="doc_obj",         output_preview="valid=True", duration_ms=5.0),
        _make_event("count_pages",           2,  "PDF Ingestion",
                    input_preview="doc_obj",         output_preview="count=14",   duration_ms=2.0),
        # Text Extraction (contains language branch)
        _make_event("extract_text",          3,  "Text Extraction",
                    input_preview="doc_obj",         output_preview="chars=32441", duration_ms=118.0),
        _make_event("merge_pages",           4,  "Text Extraction",
                    input_preview="pages=[…]",       output_preview="merged_text", duration_ms=3.0),
        _make_event("detect_language",       5,  "Text Extraction",
                    input_preview="merged_text",     output_preview="lang=en",     duration_ms=8.0),
        # Text Processing
        _make_event("clean_text",            6,  "Text Processing",
                    input_preview="chars=32441",     output_preview="chars=28990", duration_ms=42.0),
        _make_event("normalize_whitespace",  7,  "Text Processing",
                    input_preview="chars=28990",     output_preview="chars=27100", duration_ms=15.0),
        _make_event("remove_headers",        8,  "Text Processing",
                    input_preview="chars=27100",     output_preview="chars=25800", duration_ms=20.0),
        # Chunking (contains chunk-strategy branch)
        _make_event("compute_text_length",   9,  "Chunking",
                    input_preview="chars=25800",     output_preview="length=25800", duration_ms=1.0),
        _make_event("choose_chunk_strategy", 10, "Chunking",
                    input_preview="length=25800",    output_preview="strategy=chunked", duration_ms=2.0),
        _make_event("split_into_chunks",     11, "Chunking",
                    input_preview="chars=25800",     output_preview="chunks=12",   duration_ms=55.0),
        # LLM Analysis
        _make_event("analyze_chunks",        12, "LLM Analysis",
                    input_preview="chunks=12",       output_preview="analyses=[…]", duration_ms=820.0),
        _make_event("aggregate_results",     13, "LLM Analysis",
                    input_preview="analyses=[…]",    output_preview="aggregated",  duration_ms=12.0),
        _make_event("generate_summary",      14, "LLM Analysis",
                    input_preview="aggregated",      output_preview="summary=…",   duration_ms=340.0),
        # Structured Output
        _make_event("build_structured_result", 15, "Structured Output",
                    input_preview="summary=…",       output_preview="result_obj",  duration_ms=4.0),
        _make_event("validate_schema",       16, "Structured Output",
                    input_preview="result_obj",      output_preview="valid=True",  duration_ms=2.0),
        _make_event("export_result",         17, "Structured Output",
                    input_preview="result_obj",      output_preview="output.json", duration_ms=8.0),
    ]


# ---------------------------------------------------------------------------
# Test 1 — Task filtering
# ---------------------------------------------------------------------------

def test_task_filtering() -> None:
    """Selecting a module returns only its tasks; nothing from other modules."""
    print("\n\n>>> Test 1: Task filtering")

    task_graph = build_dataflow_graph(_build_full_trace())
    payload = build_task_graph_for_module(task_graph, "Text Extraction")
    summary = task_graph_debug_summary(payload)
    _print_payload(payload, "Test 1 — Task filtering (Text Extraction)")

    # Exactly the three executed tasks + alternate placeholder from detect_language.
    executed_tasks = {n["task_name"] for n in summary["nodes"] if not n["is_alternate"]}
    assert executed_tasks == {"extract_text", "merge_pages", "detect_language"}, (
        f"Wrong executed tasks: {executed_tasks}"
    )

    # No tasks from other modules.
    other_module_tasks = {"clean_text", "normalize_whitespace", "remove_headers",
                          "load_pdf", "analyze_chunks", "export_result"}
    overlap = executed_tasks & other_module_tasks
    assert not overlap, f"Found tasks from other modules: {overlap}"

    # Alternate node for the language branch is included.
    alt_tasks = {n["task_name"] for n in summary["nodes"] if n["is_alternate"]}
    assert "non_english_processing" in alt_tasks, (
        "Alternate branch node non_english_processing missing from task graph"
    )

    # Navigation identifiers are correct.
    assert payload.module_id == "text_extraction"
    assert payload.back_ref == MODULE_OVERVIEW_REF

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Intra-module edge preservation
# ---------------------------------------------------------------------------

def test_intra_module_edges() -> None:
    """Edges between tasks inside the module must be preserved in full."""
    print("\n\n>>> Test 2: Intra-module edge preservation")

    task_graph = build_dataflow_graph(_build_full_trace())
    payload = build_task_graph_for_module(task_graph, "Text Extraction")
    summary = task_graph_debug_summary(payload)
    _print_payload(payload, "Test 2 — Intra-module edge preservation")

    edge_pairs = summary["edges"]

    # extract_text → merge_pages must exist.
    assert ("extract_text__3", "merge_pages__4") in edge_pairs, (
        "Edge extract_text → merge_pages missing"
    )

    # merge_pages → detect_language must exist.
    assert ("merge_pages__4", "detect_language__5") in edge_pairs, (
        "Edge merge_pages → detect_language missing"
    )

    # detect_language → non_english_processing (alternate) must exist with branch metadata.
    alt_node = "non_english_processing__alt"
    branch_edge = next(
        (e for e in summary["branch_edges"] if e["to_node"] == alt_node),
        None,
    )
    assert branch_edge is not None, "Branch edge to non_english_processing__alt missing"
    assert branch_edge["branch_taken"] is False
    assert branch_edge["branch_group"] == "language_branch"

    # All edge attributes are preserved (relationship field present).
    for u, v, data in payload.graph.edges(data=True):
        assert "relationship" in data, (
            f"Edge {u}→{v} missing 'relationship' attribute"
        )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — External edge removal
# ---------------------------------------------------------------------------

def test_external_edge_removal() -> None:
    """Edges to tasks outside the module must not appear in the task graph."""
    print("\n\n>>> Test 3: External edge removal")

    task_graph = build_dataflow_graph(_build_full_trace())
    payload = build_task_graph_for_module(task_graph, "Text Extraction")
    summary = task_graph_debug_summary(payload)
    _print_payload(payload, "Test 3 — External edge removal")

    # The global graph has detect_language → clean_text (cross-module).
    # That edge must not appear in the scoped graph.
    edge_pairs = summary["edges"]
    cross_module_targets = {
        "clean_text", "normalize_whitespace", "remove_headers",
        "load_pdf", "validate_pdf", "count_pages",
        "analyze_chunks", "generate_summary",
    }

    for u, v in edge_pairs:
        # Extract task_name from node_id (format: task_name__trace_index or task_name__alt)
        target_task = v.rsplit("__", 1)[0]
        assert target_task not in cross_module_targets, (
            f"Cross-module edge found: {u} → {v}  (target '{target_task}' is in another module)"
        )

    # Confirm the number of edges is bounded: at most 3 intra + 1 alternate edge.
    assert summary["num_edges"] <= 4, (
        f"Too many edges ({summary['num_edges']}); cross-module edges may have leaked"
    )

    # Confirm the scoped graph has no reference to tasks from Text Processing.
    scoped_node_names = {n["task_name"] for n in summary["nodes"]}
    assert "clean_text" not in scoped_node_names
    assert "remove_headers" not in scoped_node_names

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Module context payload
# ---------------------------------------------------------------------------

def test_module_context_payload() -> None:
    """The returned payload must contain complete module-level metadata."""
    print("\n\n>>> Test 4: Module context payload")

    task_graph = build_dataflow_graph(_build_full_trace())
    payload = build_task_graph_for_module(task_graph, "Text Extraction")
    _print_payload(payload, "Test 4 — Module context payload")
    ctx = payload.context

    # Required keys.
    required_keys = {
        "module_name", "module_id", "module_description",
        "task_count", "total_duration_ms", "input_summary", "output_summary",
        "back_ref",
    }
    missing = required_keys - set(ctx.keys())
    assert not missing, f"Context missing keys: {missing}"

    assert ctx["module_name"] == "Text Extraction"
    assert ctx["module_id"] == "text_extraction"
    assert ctx["task_count"] == 3  # extract_text, merge_pages, detect_language
    assert abs(ctx["total_duration_ms"] - (118.0 + 3.0 + 8.0)) < 0.01, (
        f"Wrong duration: {ctx['total_duration_ms']}"
    )

    # input_summary = first task's input_preview
    assert ctx["input_summary"] == "doc_obj", (
        f"Wrong input_summary: {ctx['input_summary']!r}"
    )

    # output_summary = last task's output_preview
    assert ctx["output_summary"] == "lang=en", (
        f"Wrong output_summary: {ctx['output_summary']!r}"
    )

    # back_ref allows return navigation to the module overview.
    assert ctx["back_ref"] == MODULE_OVERVIEW_REF

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Deterministic navigation
# ---------------------------------------------------------------------------

def test_deterministic_navigation() -> None:
    """Selecting the same module twice must produce identical results."""
    print("\n\n>>> Test 5: Deterministic navigation")

    task_graph = build_dataflow_graph(_build_full_trace())

    payload_a = build_task_graph_for_module(task_graph, "Chunking")
    payload_b = build_task_graph_for_module(task_graph, "Chunking")

    sum_a = task_graph_debug_summary(payload_a)
    sum_b = task_graph_debug_summary(payload_b)

    _print_payload(payload_a, "Test 5 — Deterministic navigation (Chunking, run 1)")

    # Node sets must be identical.
    nodes_a = sorted(n["node_id"] for n in sum_a["nodes"])
    nodes_b = sorted(n["node_id"] for n in sum_b["nodes"])
    assert nodes_a == nodes_b, f"Node sets differ:\n  {nodes_a}\n  {nodes_b}"

    # Edge sets must be identical.
    edges_a = sorted(sum_a["edges"])
    edges_b = sorted(sum_b["edges"])
    assert edges_a == edges_b, f"Edge sets differ:\n  {edges_a}\n  {edges_b}"

    # Context must be identical.
    assert sum_a["context"] == sum_b["context"], "Context differs between runs"

    # Module IDs must be identical.
    assert payload_a.module_id == payload_b.module_id == "chunking"

    print(f"  Run 1 nodes : {nodes_a}")
    print(f"  Run 2 nodes : {nodes_b}")
    print(f"  Identical   : YES")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Bonus: full two-layer navigation walkthrough
# ---------------------------------------------------------------------------

def run_full_navigation_walkthrough() -> None:
    """Demo the complete two-layer drill-down for the Phase 2 pipeline."""
    print("\n\n>>> Bonus: Full two-layer navigation walkthrough")

    task_graph = build_dataflow_graph(_build_full_trace())

    # --- Layer 1: Module overview ---
    module_graph = create_module_graph(task_graph)
    mod_summary = module_graph_debug_summary(module_graph)

    sep = "=" * 72
    print(f"\n{sep}")
    print("  LAYER 1 — Module Overview")
    print(sep)
    print(f"  {' → '.join(mod_summary['pipeline'])}")
    print(f"  {mod_summary['num_modules']} modules, {mod_summary['num_edges']} edges")
    for m in mod_summary["modules"]:
        branch_note = " [branch]" if m["branch_detected"] else ""
        print(f"    [{m['stage_index']}] {m['module_name']:<28}  {m['total_duration_ms']:6.0f} ms{branch_note}")
    print(sep)

    # --- Layer 2: Drill into three representative modules ---
    drill_targets = ["Text Extraction", "Chunking", "LLM Analysis"]

    for module_name in drill_targets:
        payload = build_task_graph_for_module(task_graph, module_name)
        _print_payload(payload, f"LAYER 2 — {module_name}")

        summary = task_graph_debug_summary(payload)

        # Verify isolation: no tasks from other modules.
        other_modules = {
            m["module_name"] for m in mod_summary["modules"]
            if m["module_name"] != module_name
        }
        for node_data in summary["nodes"]:
            if node_data["is_alternate"]:
                continue
            # The node's module should match the selected module only.
            node_module = payload.graph.nodes[node_data["node_id"]].get("module_name", "")
            assert node_module == module_name, (
                f"Task {node_data['task_name']!r} has module_name={node_module!r}, "
                f"expected {module_name!r}"
            )

    # --- slug correctness ---
    slug_cases = [
        ("PDF Ingestion",    "pdf_ingestion"),
        ("Text Extraction",  "text_extraction"),
        ("Text Processing",  "text_processing"),
        ("Chunking",         "chunking"),
        ("LLM Analysis",     "llm_analysis"),
        ("Structured Output","structured_output"),
    ]
    print("\n  Navigation slug table:")
    for name, expected_slug in slug_cases:
        slug = module_name_to_id(name)
        assert slug == expected_slug, f"Bad slug for {name!r}: {slug!r}"
        print(f"    {name:<28} → {slug}")

    # --- unknown module raises ValueError ---
    try:
        build_task_graph_for_module(task_graph, "Nonexistent Module")
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        print(f"\n  Unknown module correctly raises ValueError: {exc}")

    # --- task metadata preserved in drill-down ---
    txt_payload = build_task_graph_for_module(task_graph, "Text Extraction")
    extract_node = txt_payload.graph.nodes.get("extract_text__3")
    assert extract_node is not None, "extract_text__3 node not found"
    for field in ("task_name", "task_description", "module_name", "duration_ms",
                  "status", "input_preview", "output_preview",
                  "input_length", "output_length", "error_message"):
        assert field in extract_node, f"Node missing field: {field!r}"
    print("\n  All required task metadata fields preserved in drill-down nodes.")

    print(f"\n  back_ref for every module task graph : {txt_payload.back_ref!r}")
    print("  This is the stable reference for returning to the module overview.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_task_filtering,
        test_intra_module_edges,
        test_external_edge_removal,
        test_module_context_payload,
        test_deterministic_navigation,
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
        run_full_navigation_walkthrough()
    except Exception:
        import traceback
        print("  ERROR in walkthrough:")
        traceback.print_exc()
        all_passed = False

    if all_passed:
        print("\n\nAll PRD 08 tests passed.")
    else:
        print("\n\nSome tests FAILED.")
        sys.exit(1)
