"""
demo_prd7_test.py — Verification script for PRD 07 (Module Overview Graph Builder).

Run with:
    python demo_prd7_test.py

What this script demonstrates
------------------------------
PRD 07 introduces the module overview graph: a coarser abstraction above the
task-level data-flow graph from PRD 06.

Instead of showing every function, the module graph shows:

    PDF Ingestion → Text Extraction → Text Processing →
    Chunking → LLM Analysis → Structured Output

Each node aggregates the tasks that belong to that pipeline stage.

Test 1 — Module Aggregation
    Tasks with the same module_name produce exactly one module node.

Test 2 — Module Ordering
    Modules appear in stage_index (pipeline) order, not insertion order.

Test 3 — Duration Aggregation
    Module total_duration_ms equals the sum of its task durations.

Test 4 — Input / Output Summary
    input_summary  = input_preview of the first task in the module
    output_summary = output_preview of the last task in the module

Test 5 — Edge Construction
    Module edges match stage order with no duplicates.

The final section prints the full module graph for the Phase 2 demo pipeline,
confirming the narrative overview is correct.
"""

from __future__ import annotations

import sys
from typing import Optional

from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import (
    aggregate_module_metadata,
    build_module_edges,
    build_module_nodes,
    create_module_graph,
    list_module_nodes,
    module_graph_debug_summary,
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


def _print_summary(summary: dict, title: str = "Module Graph") -> None:
    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    print(f"  Modules           : {summary['num_modules']}")
    print(f"  Edges             : {summary['num_edges']}")
    print(f"  Total duration    : {summary['total_duration_ms']:.1f} ms")
    print(f"  Pipeline          : {' → '.join(summary['pipeline'])}")
    print()

    for mod in summary["modules"]:
        branch_tag = "  [branch]" if mod["branch_detected"] else ""
        print(
            f"  [{mod['stage_index']}] {mod['module_name']:<28}"
            f"  status={mod['status']:<9}"
            f"  dur={mod['total_duration_ms']:.1f}ms"
            f"  tasks={mod['task_count']}"
            f"{branch_tag}"
        )
        if mod["input_summary"]:
            print(f"       in : {mod['input_summary'][:60]}")
        if mod["output_summary"]:
            print(f"       out: {mod['output_summary'][:60]}")
        print(f"       ids: {mod['task_ids']}")

    print()
    for src, dst in summary["edges"]:
        print(f"  EDGE  {src}  →  {dst}")
    print(sep)


# ---------------------------------------------------------------------------
# Test 1 — Module Aggregation
# ---------------------------------------------------------------------------

def test_module_aggregation() -> None:
    """Tasks sharing module_name must produce exactly one module node."""
    print("\n\n>>> Test 1: Module Aggregation")

    trace = [
        # Two tasks in PDF Ingestion → one module node
        _make_event("load_pdf",     trace_index=0, module_name="PDF Ingestion",
                    input_preview="report.pdf", output_preview="doc_object"),
        _make_event("validate_pdf", trace_index=1, module_name="PDF Ingestion",
                    input_preview="doc_object", output_preview="valid=True"),
        # Two tasks in Text Extraction → one module node
        _make_event("extract_text", trace_index=2, module_name="Text Extraction",
                    input_preview="doc_object", output_preview="raw_text"),
        _make_event("merge_pages",  trace_index=3, module_name="Text Extraction",
                    input_preview="raw_text", output_preview="merged_text"),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Test 1 — Module Aggregation")

    # Four tasks → two module nodes (PDF Ingestion and Text Extraction).
    assert summary["num_modules"] == 2, (
        f"Expected 2 modules, got {summary['num_modules']}"
    )

    module_names = {m["module_name"] for m in summary["modules"]}
    assert "PDF Ingestion" in module_names, "PDF Ingestion module missing"
    assert "Text Extraction" in module_names, "Text Extraction module missing"

    # Each module must reference exactly the tasks that belong to it.
    pdf_mod = next(m for m in summary["modules"] if m["module_name"] == "PDF Ingestion")
    txt_mod = next(m for m in summary["modules"] if m["module_name"] == "Text Extraction")

    assert pdf_mod["task_count"] == 2, (
        f"PDF Ingestion should have 2 tasks, got {pdf_mod['task_count']}"
    )
    assert txt_mod["task_count"] == 2, (
        f"Text Extraction should have 2 tasks, got {txt_mod['task_count']}"
    )

    # task_ids must reference real node IDs in the task graph.
    task_graph_node_ids = set(task_graph.nodes())
    for task_id in pdf_mod["task_ids"] + txt_mod["task_ids"]:
        assert task_id in task_graph_node_ids, (
            f"task_id {task_id!r} not found in task graph"
        )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Module Ordering
# ---------------------------------------------------------------------------

def test_module_ordering() -> None:
    """Modules must appear in pipeline stage order (stage_index), not insertion order."""
    print("\n\n>>> Test 2: Module Ordering")

    # Provide tasks in reverse stage order to confirm ordering is by
    # stage_index, not by the order tasks appear in the trace.
    trace = [
        _make_event("generate_summary",     trace_index=0, module_name="LLM Analysis"),
        _make_event("analyze_chunks",       trace_index=1, module_name="LLM Analysis"),
        _make_event("choose_chunk_strategy",trace_index=2, module_name="Chunking"),
        _make_event("compute_text_length",  trace_index=3, module_name="Chunking"),
        _make_event("clean_text",           trace_index=4, module_name="Text Processing"),
        _make_event("extract_text",         trace_index=5, module_name="Text Extraction"),
        _make_event("load_pdf",             trace_index=6, module_name="PDF Ingestion"),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Test 2 — Module Ordering")

    pipeline = summary["pipeline"]
    expected_order = [
        "PDF Ingestion",
        "Text Extraction",
        "Text Processing",
        "Chunking",
        "LLM Analysis",
    ]
    assert pipeline == expected_order, (
        f"Unexpected module order:\n  Got     : {pipeline}\n  Expected: {expected_order}"
    )

    # Stage indices must be strictly increasing along the pipeline.
    stage_indices = [m["stage_index"] for m in summary["modules"]]
    assert stage_indices == sorted(stage_indices), (
        f"Stage indices not sorted: {stage_indices}"
    )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — Duration Aggregation
# ---------------------------------------------------------------------------

def test_duration_aggregation() -> None:
    """Module total_duration_ms must equal the sum of its task durations."""
    print("\n\n>>> Test 3: Duration Aggregation")

    trace = [
        _make_event("load_pdf",    trace_index=0, module_name="PDF Ingestion", duration_ms=25.0),
        _make_event("validate_pdf",trace_index=1, module_name="PDF Ingestion", duration_ms=5.0),
        _make_event("count_pages", trace_index=2, module_name="PDF Ingestion", duration_ms=2.0),
        _make_event("extract_text",trace_index=3, module_name="Text Extraction", duration_ms=118.0),
        _make_event("merge_pages", trace_index=4, module_name="Text Extraction", duration_ms=3.0),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Test 3 — Duration Aggregation")

    pdf_mod = next(m for m in summary["modules"] if m["module_name"] == "PDF Ingestion")
    txt_mod = next(m for m in summary["modules"] if m["module_name"] == "Text Extraction")

    assert abs(pdf_mod["total_duration_ms"] - 32.0) < 0.01, (
        f"PDF Ingestion: expected 32.0 ms, got {pdf_mod['total_duration_ms']}"
    )
    assert abs(txt_mod["total_duration_ms"] - 121.0) < 0.01, (
        f"Text Extraction: expected 121.0 ms, got {txt_mod['total_duration_ms']}"
    )

    # Grand total must equal sum of all module durations.
    expected_grand_total = 25.0 + 5.0 + 2.0 + 118.0 + 3.0
    assert abs(summary["total_duration_ms"] - expected_grand_total) < 0.01, (
        f"Grand total: expected {expected_grand_total}, got {summary['total_duration_ms']}"
    )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Input / Output Summary
# ---------------------------------------------------------------------------

def test_input_output_summary() -> None:
    """input_summary = first task's input_preview; output_summary = last task's output_preview."""
    print("\n\n>>> Test 4: Input / Output Summary")

    trace = [
        _make_event(
            "load_pdf", trace_index=0, module_name="PDF Ingestion",
            input_preview="file=report.pdf (2.3 MB)",
            output_preview="pages=14",
        ),
        _make_event(
            "validate_pdf", trace_index=1, module_name="PDF Ingestion",
            input_preview="pages=14",
            output_preview="valid=True",
        ),
        _make_event(
            "count_pages", trace_index=2, module_name="PDF Ingestion",
            input_preview="doc_object",
            output_preview="count=14",
        ),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Test 4 — Input / Output Summary")

    pdf_mod = next(m for m in summary["modules"] if m["module_name"] == "PDF Ingestion")

    # input_summary comes from load_pdf (first in pipeline order).
    assert pdf_mod["input_summary"] == "file=report.pdf (2.3 MB)", (
        f"Wrong input_summary: {pdf_mod['input_summary']!r}"
    )

    # output_summary comes from count_pages (last in pipeline order).
    assert pdf_mod["output_summary"] == "count=14", (
        f"Wrong output_summary: {pdf_mod['output_summary']!r}"
    )

    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Edge Construction
# ---------------------------------------------------------------------------

def test_edge_construction() -> None:
    """Module edges must exactly match consecutive stage order with no duplicates."""
    print("\n\n>>> Test 5: Edge Construction")

    trace = [
        _make_event("load_pdf",              trace_index=0,  module_name="PDF Ingestion"),
        _make_event("extract_text",          trace_index=1,  module_name="Text Extraction"),
        _make_event("clean_text",            trace_index=2,  module_name="Text Processing"),
        _make_event("choose_chunk_strategy", trace_index=3,  module_name="Chunking"),
        _make_event("analyze_chunks",        trace_index=4,  module_name="LLM Analysis"),
        _make_event("export_result",         trace_index=5,  module_name="Structured Output"),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Test 5 — Edge Construction")

    expected_edges = [
        ("PDF Ingestion",    "Text Extraction"),
        ("Text Extraction",  "Text Processing"),
        ("Text Processing",  "Chunking"),
        ("Chunking",         "LLM Analysis"),
        ("LLM Analysis",     "Structured Output"),
    ]

    assert summary["edges"] == expected_edges, (
        f"Edge mismatch:\n  Got     : {summary['edges']}\n  Expected: {expected_edges}"
    )

    # Six modules → exactly five edges.
    assert summary["num_edges"] == 5, (
        f"Expected 5 edges, got {summary['num_edges']}"
    )

    # All edges must have edge_type="pipeline".
    for u, v, data in module_graph.edges(data=True):
        assert data.get("edge_type") == "pipeline", (
            f"Edge {u}→{v} has wrong edge_type: {data.get('edge_type')!r}"
        )

    # No duplicate edges.
    edge_list = list(module_graph.edges())
    assert len(edge_list) == len(set(edge_list)), "Duplicate edges found"

    print("  PASSED")


# ---------------------------------------------------------------------------
# Bonus: Full Phase 2 pipeline module overview
# ---------------------------------------------------------------------------

def run_full_pipeline_walkthrough() -> None:
    """Show the module overview graph for the complete Phase 2 PDF pipeline."""
    print("\n\n>>> Bonus: Full Phase 2 pipeline module overview")

    trace = [
        # PDF Ingestion
        _make_event("load_pdf",              trace_index=0,  module_name="PDF Ingestion",
                    duration_ms=25.0,  input_preview="file=report.pdf",   output_preview="pages=14"),
        _make_event("validate_pdf",          trace_index=1,  module_name="PDF Ingestion",
                    duration_ms=5.0,   input_preview="pages=14",           output_preview="valid=True"),
        _make_event("count_pages",           trace_index=2,  module_name="PDF Ingestion",
                    duration_ms=2.0,   input_preview="doc_object",         output_preview="count=14"),
        # Text Extraction (contains language branch)
        _make_event("extract_text",          trace_index=3,  module_name="Text Extraction",
                    duration_ms=118.0, input_preview="doc_object",         output_preview="chars=32441"),
        _make_event("merge_pages",           trace_index=4,  module_name="Text Extraction",
                    duration_ms=3.0,   input_preview="pages=[...]",        output_preview="merged_text"),
        _make_event("detect_language",       trace_index=5,  module_name="Text Extraction",
                    duration_ms=8.0,   input_preview="merged_text",        output_preview="lang=en"),
        # Text Processing
        _make_event("clean_text",            trace_index=6,  module_name="Text Processing",
                    duration_ms=42.0,  input_preview="chars=32441",        output_preview="chars=28990"),
        _make_event("normalize_whitespace",  trace_index=7,  module_name="Text Processing",
                    duration_ms=15.0,  input_preview="chars=28990",        output_preview="chars=27100"),
        _make_event("remove_headers",        trace_index=8,  module_name="Text Processing",
                    duration_ms=20.0,  input_preview="chars=27100",        output_preview="chars=25800"),
        # Chunking (contains chunk strategy branch)
        _make_event("compute_text_length",   trace_index=9,  module_name="Chunking",
                    duration_ms=1.0,   input_preview="chars=25800",        output_preview="length=25800"),
        _make_event("choose_chunk_strategy", trace_index=10, module_name="Chunking",
                    duration_ms=2.0,   input_preview="length=25800",       output_preview="strategy=chunked"),
        _make_event("split_into_chunks",     trace_index=11, module_name="Chunking",
                    duration_ms=55.0,  input_preview="chars=25800",        output_preview="chunks=12"),
        # LLM Analysis
        _make_event("analyze_chunks",        trace_index=12, module_name="LLM Analysis",
                    duration_ms=820.0, input_preview="chunks=12",          output_preview="analyses=[...]"),
        _make_event("aggregate_results",     trace_index=13, module_name="LLM Analysis",
                    duration_ms=12.0,  input_preview="analyses=[...]",     output_preview="aggregated"),
        _make_event("generate_summary",      trace_index=14, module_name="LLM Analysis",
                    duration_ms=340.0, input_preview="aggregated",         output_preview="summary=..."),
        # Structured Output
        _make_event("build_structured_result",trace_index=15,module_name="Structured Output",
                    duration_ms=4.0,   input_preview="summary=...",        output_preview="result_obj"),
        _make_event("validate_schema",       trace_index=16, module_name="Structured Output",
                    duration_ms=2.0,   input_preview="result_obj",         output_preview="valid=True"),
        _make_event("export_result",         trace_index=17, module_name="Structured Output",
                    duration_ms=8.0,   input_preview="result_obj",         output_preview="output.json"),
    ]

    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    summary = module_graph_debug_summary(module_graph)
    _print_summary(summary, "Full Phase 2 PDF Pipeline — Module Overview")

    print("\n  === MODULE OVERVIEW NARRATIVE ===")
    print(f"  {' → '.join(summary['pipeline'])}")

    print("\n  === STAGE DETAILS ===")
    for mod in summary["modules"]:
        branch_note = " (contains branch)" if mod["branch_detected"] else ""
        print(
            f"  Stage {mod['stage_index']}  {mod['module_name']:<28}"
            f"  {mod['total_duration_ms']:6.0f} ms"
            f"  {mod['task_count']} tasks"
            f"{branch_note}"
        )

    # Verify branch_detected propagates correctly.
    txt_mod = next(m for m in summary["modules"] if m["module_name"] == "Text Extraction")
    chunk_mod = next(m for m in summary["modules"] if m["module_name"] == "Chunking")
    assert txt_mod["branch_detected"], "Text Extraction should report branch_detected=True"
    assert chunk_mod["branch_detected"], "Chunking should report branch_detected=True"

    pdf_mod = next(m for m in summary["modules"] if m["module_name"] == "PDF Ingestion")
    assert not pdf_mod["branch_detected"], "PDF Ingestion should report branch_detected=False"

    # Verify task_ids enable drill-down (all reference real task graph nodes).
    task_node_ids = set(task_graph.nodes())
    for mod in summary["modules"]:
        for tid in mod["task_ids"]:
            assert tid in task_node_ids, (
                f"Module {mod['module_name']!r} references unknown task_id {tid!r}"
            )

    print(f"\n  Total pipeline duration : {summary['total_duration_ms']:.0f} ms")
    print(f"  Statuses                : {summary['status_counts']}")
    print("\n  Task drill-down references verified (all task_ids found in task graph).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_module_aggregation,
        test_module_ordering,
        test_duration_aggregation,
        test_input_output_summary,
        test_edge_construction,
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
        print("\n\nAll PRD 07 tests passed.")
    else:
        print("\n\nSome tests FAILED.")
        sys.exit(1)
