"""
demo_prd10_navigation.py — Batch generation script for PRD 10.

What this demonstrates
----------------------
PRD 10 makes the Phase 2 visualization navigable.

This script generates the complete set of HTML graph files in one run:

    output/module_graph.html               — clickable module overview
    output/task_graph_pdf_ingestion.html
    output/task_graph_text_extraction.html  — includes language branch
    output/task_graph_text_processing.html
    output/task_graph_chunking.html         — includes chunk-strategy branch
    output/task_graph_llm_analysis.html
    output/task_graph_structured_output.html

Navigation flow
---------------
    module_graph.html
        Click "Text Extraction" node
    → task_graph_text_extraction.html
        Click "← Back to Module Overview"
    → module_graph.html

Run with:
    python demo_prd10_navigation.py

The script prints the absolute file paths of all generated HTML files.
"""

from __future__ import annotations

import sys
from typing import Optional

from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import (
    create_module_graph,
    list_module_nodes,
    module_graph_debug_summary,
)
from graph.task_graph_builder import (
    build_task_graph_for_module,
    module_name_to_id,
    task_graph_debug_summary,
)
from graph.module_graph_visualizer import render_module_graph_html
from graph.task_graph_visualizer import render_task_graph_html


# ---------------------------------------------------------------------------
# Synthetic Phase 2 trace fixture (same as PRD 09 demo)
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
        "task_name":        task_name,
        "task_description": task_description or f"Task: {task_name}",
        "module_name":      module_name,
        "parent_task":      parent_task,
        "trace_index":      trace_index,
        "start_time":       float(trace_index),
        "end_time":         float(trace_index) + duration_ms / 1000,
        "duration_ms":      duration_ms,
        "status":           status,
        "input_preview":    input_preview,
        "output_preview":   output_preview if status == "success" else "",
        "input_length":     input_length,
        "output_length":    output_length if status == "success" else 0,
        "error_message":    error_message,
    }


def _build_phase2_trace() -> list:
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
# Batch generation
# ---------------------------------------------------------------------------

def generate_all_graphs(output_dir: str = "output") -> list[str]:
    """Generate the full set of navigable HTML graph files.

    Builds the Phase 2 graph stack from a synthetic trace, then renders:

    - module_graph.html         (overview with clickable module nodes)
    - task_graph_<slug>.html    (one file per module, with back link)

    Parameters
    ----------
    output_dir :
        Directory to write HTML files into. Created if it does not exist.

    Returns
    -------
    list[str]
        Absolute paths of all generated HTML files, module graph first.
    """
    sep  = "=" * 72
    sep2 = "-" * 72

    print(sep)
    print("  PRD 10 — Interactive Drill-Down Navigation — Batch Generation")
    print(sep)

    # -----------------------------------------------------------------------
    # Step 1 — Build data-flow task graph
    # -----------------------------------------------------------------------
    print("\n[1] Building data-flow task graph from synthetic trace...")
    trace      = _build_phase2_trace()
    task_graph = build_dataflow_graph(trace)
    print(f"    Nodes : {task_graph.number_of_nodes()}  (executed + alternate branch placeholders)")
    print(f"    Edges : {task_graph.number_of_edges()}")

    # -----------------------------------------------------------------------
    # Step 2 — Build module overview graph
    # -----------------------------------------------------------------------
    print("\n[2] Building module overview graph...")
    module_graph = create_module_graph(task_graph)
    mod_summary  = module_graph_debug_summary(module_graph)

    print(f"    Modules   : {mod_summary['num_modules']}")
    pipeline_str = ' -> '.join(mod_summary['pipeline'])
    print(f"    Pipeline  : {pipeline_str}")
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
    # Step 3 — Render module overview HTML (with click navigation)
    # -----------------------------------------------------------------------
    print(f"\n[3] Rendering module overview graph with navigation links...")
    module_html_path = render_module_graph_html(
        module_graph,
        output_path=f"{output_dir}/module_graph.html",
        # task_graph_links=None  → auto-generated from module names
    )
    print(f"    Generated : {module_html_path}")

    generated_paths = [module_html_path]

    # -----------------------------------------------------------------------
    # Step 4 — Render task graph HTML for each module
    # -----------------------------------------------------------------------
    print(f"\n[4] Rendering task graphs for all {mod_summary['num_modules']} modules...")
    print(sep2)

    module_nodes = list_module_nodes(module_graph)

    for mod in module_nodes:
        # Skip decision nodes they have no tasks to drill into
        if mod.get("is_decision_node"):
            continue

        module_name = mod["module_name"]
        module_slug = module_name_to_id(module_name)
        out_path    = f"{output_dir}/task_graph_{module_slug}.html"

        print(f"\n    Module : {module_name!r}")

        payload = build_task_graph_for_module(task_graph, module_name)
        summary = task_graph_debug_summary(payload)
        ctx     = payload.context

        print(f"    Tasks  : {' -> '.join(summary['task_flow'])}")
        print(f"    Dur    : {ctx['total_duration_ms']:.0f} ms")

        if summary["branch_edges"]:
            for be in summary["branch_edges"]:
                taken = "TAKEN" if be["branch_taken"] else "alternate"
                print(
                    f"    Branch : {be['from_node']} -> {be['to_node']}"
                    f"  [{be['branch_group']} / {be['branch_option']} ({taken})]"
                )

        task_html_path = render_task_graph_html(
            payload,
            output_path=out_path,
            back_link="module_graph.html",
        )
        generated_paths.append(task_html_path)
        print(f"    Output : {task_html_path}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print()
    print(sep)
    print("  Generated HTML Files")
    print(sep)
    for path in generated_paths:
        print(f"  {path}")
    print()
    print("  Navigation:")
    print("    1. Open module_graph.html in your browser")
    print("    2. Click any module node to open its task graph")
    print("    3. Click '< Back to Module Overview' to return")
    print(sep)

    return generated_paths


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        generate_all_graphs()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
