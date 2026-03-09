"""
demo_prd9_visualization.py — Demo script for PRD 09 (Phase 2 Visualization Layer).

What this demonstrates
----------------------
PRD 09 turns the Phase 2 graph architecture into visually readable HTML outputs.

Two graphs are rendered:

    1. Module overview graph   → output/module_graph.html
       Shows the six-stage pipeline as a left-to-right process map.

    2. Task graph (Text Extraction) → output/task_graph_text_extraction.html
       Shows the internal tasks for the Text Extraction module, including
       the alternate language-branch path.

Run with:
    python demo_prd9_visualization.py

The script prints the absolute file paths of the generated HTML files
so they can be opened directly in a browser.
"""

from __future__ import annotations

import sys
from typing import Optional

from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph, module_graph_debug_summary
from graph.task_graph_builder import build_task_graph_for_module, task_graph_debug_summary
from graph.module_graph_visualizer import render_module_graph_html
from graph.task_graph_visualizer import render_task_graph_html


# ---------------------------------------------------------------------------
# Synthetic Phase 2 trace fixture
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
        "task_name":       task_name,
        "task_description": task_description or f"Task: {task_name}",
        "module_name":     module_name,
        "parent_task":     parent_task,
        "trace_index":     trace_index,
        "start_time":      float(trace_index),
        "end_time":        float(trace_index) + duration_ms / 1000,
        "duration_ms":     duration_ms,
        "status":          status,
        "input_preview":   input_preview,
        "output_preview":  output_preview if status == "success" else "",
        "input_length":    input_length,
        "output_length":   output_length if status == "success" else 0,
        "error_message":   error_message,
    }


def _build_phase2_trace():
    """Return a synthetic trace representing a full Phase 2 PDF pipeline run."""
    return [
        # PDF Ingestion
        _make_event(
            "load_pdf", 0, "PDF Ingestion",
            "Load and open the PDF file for processing",
            input_preview="file=report.pdf", output_preview="doc_obj",
            duration_ms=25.0,
        ),
        _make_event(
            "validate_pdf", 1, "PDF Ingestion",
            "Verify the PDF is readable and not corrupted",
            input_preview="doc_obj", output_preview="valid=True",
            duration_ms=5.0,
        ),
        _make_event(
            "count_pages", 2, "PDF Ingestion",
            "Count the total number of pages in the PDF",
            input_preview="doc_obj", output_preview="count=14",
            duration_ms=2.0,
        ),

        # Text Extraction (contains language branch)
        _make_event(
            "extract_text", 3, "Text Extraction",
            "Extract raw text content from each PDF page",
            input_preview="doc_obj", output_preview="chars=32441",
            duration_ms=118.0,
        ),
        _make_event(
            "merge_pages", 4, "Text Extraction",
            "Concatenate per-page text into a single string",
            input_preview="pages=[...]", output_preview="merged_text",
            duration_ms=3.0,
        ),
        _make_event(
            "detect_language", 5, "Text Extraction",
            "Detect the primary language of the extracted text",
            input_preview="merged_text", output_preview="lang=en",
            duration_ms=8.0,
        ),

        # Text Processing
        _make_event(
            "clean_text", 6, "Text Processing",
            "Remove noise, punctuation artifacts and OCR errors",
            input_preview="chars=32441", output_preview="chars=28990",
            duration_ms=42.0,
        ),
        _make_event(
            "normalize_whitespace", 7, "Text Processing",
            "Collapse redundant whitespace and line breaks",
            input_preview="chars=28990", output_preview="chars=27100",
            duration_ms=15.0,
        ),
        _make_event(
            "remove_headers", 8, "Text Processing",
            "Strip page headers and footers from the text",
            input_preview="chars=27100", output_preview="chars=25800",
            duration_ms=20.0,
        ),

        # Chunking (contains chunk-strategy branch)
        _make_event(
            "compute_text_length", 9, "Chunking",
            "Measure total character count of cleaned text",
            input_preview="chars=25800", output_preview="length=25800",
            duration_ms=1.0,
        ),
        _make_event(
            "choose_chunk_strategy", 10, "Chunking",
            "Select chunking strategy based on text length",
            input_preview="length=25800", output_preview="strategy=chunked",
            duration_ms=2.0,
        ),
        _make_event(
            "split_into_chunks", 11, "Chunking",
            "Divide text into overlapping chunks for LLM analysis",
            input_preview="chars=25800", output_preview="chunks=12",
            duration_ms=55.0,
        ),

        # LLM Analysis (slow tasks — shows width scaling)
        _make_event(
            "analyze_chunks", 12, "LLM Analysis",
            "Run LLM inference on each chunk to extract insights",
            input_preview="chunks=12", output_preview="analyses=[...]",
            duration_ms=820.0,
        ),
        _make_event(
            "aggregate_results", 13, "LLM Analysis",
            "Merge chunk-level results into a unified analysis",
            input_preview="analyses=[...]", output_preview="aggregated",
            duration_ms=12.0,
        ),
        _make_event(
            "generate_summary", 14, "LLM Analysis",
            "Generate a human-readable summary from aggregated results",
            input_preview="aggregated", output_preview="summary=...",
            duration_ms=340.0,
        ),

        # Structured Output
        _make_event(
            "build_structured_result", 15, "Structured Output",
            "Assemble the final structured result object",
            input_preview="summary=...", output_preview="result_obj",
            duration_ms=4.0,
        ),
        _make_event(
            "validate_schema", 16, "Structured Output",
            "Validate result conforms to the expected JSON schema",
            input_preview="result_obj", output_preview="valid=True",
            duration_ms=2.0,
        ),
        _make_event(
            "export_result", 17, "Structured Output",
            "Serialize and write the result to output.json",
            input_preview="result_obj", output_preview="output.json",
            duration_ms=8.0,
        ),
    ]


# ---------------------------------------------------------------------------
# Demo pipeline
# ---------------------------------------------------------------------------

def run_demo() -> tuple:
    """Run the PRD 09 visualization demo.

    Builds the Phase 2 graph stack, renders module and task graph HTML,
    and prints the file paths to generated outputs.

    Returns
    -------
    tuple (module_html_path, task_html_path)
        Absolute paths to the two generated HTML files.
    """
    sep  = "=" * 72
    sep2 = "-" * 72

    print(sep)
    print("  PRD 09 — Phase 2 Visualization Layer Demo")
    print(sep)

    # -----------------------------------------------------------------------
    # Step 1 — Build data-flow task graph
    # -----------------------------------------------------------------------
    print("\n[1] Building data-flow task graph...")
    trace      = _build_phase2_trace()
    task_graph = build_dataflow_graph(trace)
    print(f"    Nodes : {task_graph.number_of_nodes()}  "
          f"(executed + alternate branch placeholders)")
    print(f"    Edges : {task_graph.number_of_edges()}")

    # -----------------------------------------------------------------------
    # Step 2 — Build module overview graph
    # -----------------------------------------------------------------------
    print("\n[2] Building module overview graph...")
    module_graph = create_module_graph(task_graph)
    mod_summary  = module_graph_debug_summary(module_graph)

    print(f"    Modules   : {mod_summary['num_modules']}")
    print(f"    Pipeline  : {' → '.join(mod_summary['pipeline'])}")
    print(f"    Total dur : {mod_summary['total_duration_ms']:.0f} ms")
    print()
    print("    Module breakdown:")
    for m in mod_summary["modules"]:
        branch_note = " [branch]" if m["branch_detected"] else ""
        print(
            f"      [{m['stage_index']}] {m['module_name']:<26} "
            f"  {m['status']:<9}  {m['total_duration_ms']:6.0f} ms"
            f"  ({m['task_count']} tasks){branch_note}"
        )

    # -----------------------------------------------------------------------
    # Step 3 — Render module overview HTML
    # -----------------------------------------------------------------------
    print(f"\n[3] Rendering module overview graph...")
    module_html_path = render_module_graph_html(
        module_graph,
        output_path="output/module_graph.html",
    )
    print(f"    Generated : {module_html_path}")

    # -----------------------------------------------------------------------
    # Step 4 — Drill into Text Extraction and render its task graph
    # -----------------------------------------------------------------------
    selected_module = "Text Extraction"
    print(f"\n[4] Drilling into module: {selected_module!r}")
    te_payload = build_task_graph_for_module(task_graph, selected_module)
    te_summary = task_graph_debug_summary(te_payload)
    ctx        = te_payload.context

    print(f"    Module ID   : {te_payload.module_id}")
    print(f"    Task flow   : {' → '.join(te_summary['task_flow'])}")
    print(f"    Duration    : {ctx['total_duration_ms']:.0f} ms")
    print(f"    Nodes total : {te_summary['num_nodes']}  (executed + alternate)")
    print(f"    Edges total : {te_summary['num_edges']}")

    if te_summary["branch_edges"]:
        print("    Branch edges:")
        for be in te_summary["branch_edges"]:
            taken = "TAKEN" if be["branch_taken"] else "alternate"
            print(
                f"      {be['from_node']} → {be['to_node']}"
                f"  [{be['branch_group']} / {be['branch_option']} ({taken})]"
            )

    task_html_path = render_task_graph_html(
        te_payload,
        output_path=f"output/task_graph_{te_payload.module_id}.html",
    )
    print(f"\n    Generated : {task_html_path}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print()
    print(sep)
    print("  HTML Output Files")
    print(sep)
    print(f"  Module overview  :  {module_html_path}")
    print(f"  Task graph       :  {task_html_path}")
    print()
    print("  Open these files in your browser to inspect the visualizations.")
    print(sep)

    return module_html_path, task_html_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        run_demo()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
