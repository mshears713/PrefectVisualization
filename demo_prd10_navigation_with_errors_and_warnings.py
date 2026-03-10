"""
demo_prd10_navigation_with_errors_and_warnings.py — Demo with failures & warnings.

What this demonstrates
----------------------
This is an alternate scenario showing how the visualization system represents
execution failures and warnings:

    • Yellow warning on Text Extraction module (extract_text task took longer)
    • Red failure on Chunking module (split_into_chunks failed)
    • Red downstream modules (LLM Analysis, Structured Output failed as a result)

This demonstrates the visual cascade of failures through dependent modules.

Generated files (alternate names from the success demo):
    output/module_graph_with_errors.html        — Module overview with warnings/errors
    output/task_graph_text_extraction_warned.html
    output/task_graph_chunking_error.html
    output/task_graph_llm_analysis_error.html
    output/task_graph_structured_output_error.html

Run with:
    python demo_prd10_navigation_with_errors_and_warnings.py
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
# Synthetic trace with errors and warnings
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


def _build_error_warning_trace() -> list:
    """
    Synthetic trace with:
      • Text Extraction: warning on extract_text (took longer than expected)
      • Chunking: error on split_into_chunks
      • LLM Analysis: errors (cascading from chunking failure)
      • Structured Output: errors (cascading from LLM failure)
    """
    return [
        # PDF Ingestion — all succeed
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

        # Text Extraction — extract_text has WARNING (took too long)
        _make_event(
            "extract_text", 3, "Text Extraction",
            "Extract raw text content from each PDF page",
            input_preview="doc_obj", output_preview="chars=32441",
            duration_ms=250.0,  # Much longer than expected (~118ms normally)
            status="warning",
            error_message="Performance warning: Task completed but took longer than expected (250ms vs 118ms threshold)",
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

        # Text Processing — all succeed (not affected by warning)
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

        # Chunking — split_into_chunks FAILS
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
            input_preview="chars=25800", output_preview="",
            duration_ms=55.0,
            status="error",
            error_message="Chunking strategy failed: overlap factor out of range. Expected 0.2-0.5, got 0.8",
        ),

        # LLM Analysis — all tasks fail (cascading from chunking failure)
        _make_event(
            "analyze_chunks", 12, "LLM Analysis",
            "Run LLM inference on each chunk to extract insights",
            input_preview="chunks=[]", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Input validation failed: no chunks provided (upstream failure)",
        ),
        _make_event(
            "aggregate_results", 13, "LLM Analysis",
            "Merge chunk-level results into a unified analysis",
            input_preview="analyses=[]", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Dependency failed: analyze_chunks did not complete",
        ),
        _make_event(
            "generate_summary", 14, "LLM Analysis",
            "Generate a human-readable summary from aggregated results",
            input_preview="aggregated=None", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Dependency failed: aggregate_results did not complete",
        ),

        # Structured Output — all tasks fail (cascading from LLM failure)
        _make_event(
            "build_structured_result", 15, "Structured Output",
            "Assemble the final structured result object",
            input_preview="summary=None", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Dependency failed: generate_summary did not complete",
        ),
        _make_event(
            "validate_schema", 16, "Structured Output",
            "Validate result conforms to the expected JSON schema",
            input_preview="result_obj=None", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Dependency failed: build_structured_result did not complete",
        ),
        _make_event(
            "export_result", 17, "Structured Output",
            "Serialize and write the result to output.json",
            input_preview="result_obj=None", output_preview="",
            duration_ms=0.0,
            status="error",
            error_message="Dependency failed: validate_schema did not complete",
        ),
    ]


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------

def generate_error_warning_graphs(output_dir: str = "output") -> list[str]:
    """Generate HTML graph files showing failures and warnings scenario.

    Builds the Phase 2 graph stack from a synthetic error trace, then renders:

    - module_graph_with_errors.html       (overview showing warnings/errors)
    - task_graph_*_error.html files       (task details with affected modules)

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
    print("  PRD 10 — Errors & Warnings Demo — Batch Generation")
    print(sep)

    # -----------------------------------------------------------------------
    # Step 1 — Build data-flow task graph
    # -----------------------------------------------------------------------
    print("\n[1] Building data-flow task graph from error trace...")
    trace      = _build_error_warning_trace()
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

    # Count status for summary
    status_counts = {}
    for m in mod_summary["modules"]:
        s = m["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    status_msg = ", ".join(
        f"{count} {status}" for status, count in sorted(status_counts.items())
    )
    print(f"\n    Status summary: {status_msg}")

    # -----------------------------------------------------------------------
    # Step 3 — Prepare module nodes and build task graph links
    # -----------------------------------------------------------------------
    print(f"\n[3] Preparing module nodes and task graph links...")
    
    module_nodes = list_module_nodes(module_graph)
    
    # Build custom task graph links for error scenario with appropriate suffixes
    # Map from NetworkX node_id to task graph HTML filename
    task_graph_links = {}
    for node_id, node_data in module_graph.nodes(data=True):
        # Skip decision nodes
        if node_data.get("is_decision_node"):
            continue
        
        module_name = node_data.get("module_name", "")
        status = node_data.get("status", "success")
        
        if module_name:
            module_id = module_name_to_id(module_name)
            
            if status == "error":
                link = f"task_graph_{module_id}_error.html"
            elif status == "warning":
                link = f"task_graph_{module_id}_warned.html"
            else:
                link = f"task_graph_{module_id}.html"
            
            task_graph_links[node_id] = link
            print(f"    {module_name:<25} → {link}")

    # -----------------------------------------------------------------------
    # Step 4 — Render module overview HTML
    # -----------------------------------------------------------------------
    print(f"\n[4] Rendering module overview graph with error highlighting...")
    module_html_path = render_module_graph_html(
        module_graph,
        output_path=f"{output_dir}/module_graph_with_errors.html",
        task_graph_links=task_graph_links,
    )
    print(f"    Generated : {module_html_path}")

    generated_paths = [module_html_path]

    # -----------------------------------------------------------------------
    # Step 5 — Render task graph HTML for each module
    # -----------------------------------------------------------------------
    print(f"\n[5] Rendering task graphs for all {mod_summary['num_modules']} modules...")
    print(sep2)

    for mod in module_nodes:
        # Skip decision nodes
        if mod.get("is_decision_node"):
            continue

        module_name = mod["module_name"]
        module_slug = module_name_to_id(module_name)
        
        # Add suffix to indicate error/warning status
        status = mod.get("status", "success")
        if status == "error":
            out_path = f"{output_dir}/task_graph_{module_slug}_error.html"
        elif status == "warning":
            out_path = f"{output_dir}/task_graph_{module_slug}_warned.html"
        else:
            out_path = f"{output_dir}/task_graph_{module_slug}.html"

        print(f"\n    [{module_slug:<25}] Building task graph...")
        task_payload = build_task_graph_for_module(task_graph, module_name)
        task_summary = task_graph_debug_summary(task_payload)

        print(f"        Tasks : {len(task_summary['task_flow'])}")
        print(f"        Status: {status}")
        
        # Calculate total duration from tasks
        total_dur = sum(n.get("duration_ms", 0) for n in task_summary["nodes"] if not n["is_alternate"])
        print(f"        Dur   : {total_dur:.0f} ms")

        print(f"        Rendering to: {out_path}")
        task_html_path = render_task_graph_html(
            task_payload,
            output_path=out_path,
            back_link="module_graph_with_errors.html",
        )
        generated_paths.append(task_html_path)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(sep)
    print(f"\n✓ Generated {len(generated_paths)} HTML files:")
    for path in generated_paths:
        print(f"  • {path}")
    print()
    print("Next steps:")
    print("  1. Open the first file in a browser:")
    print(f"     {generated_paths[0]}")
    print("  2. Click on module nodes to drill into task details")
    print("  3. Use the 'Back' link to return to module overview")
    print()
    print(sep)

    return generated_paths


if __name__ == "__main__":
    generate_error_warning_graphs()
