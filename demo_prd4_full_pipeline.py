"""
demo_prd4_full_pipeline.py — End-to-end demo runner for Milestone 4.

Usage
-----
    # Run both success and failure modes (default):
    python demo_prd4_full_pipeline.py

    # Run only the success (happy-path) mode:
    python demo_prd4_full_pipeline.py --success-only

    # Run only the failure mode (shows red error node in graph):
    python demo_prd4_full_pipeline.py --fail-only

What this script does
---------------------
For each requested mode:

    1. Reset the runtime trace to a clean state.
    2. Execute the synthetic demo pipeline.
    3. Retrieve the accumulated runtime trace.
    4. Build an execution graph from the trace.
    5. Render the graph to a standalone interactive HTML file.
    6. Print a summary including node/edge counts and the HTML path.

By default both modes run sequentially so the user gets two HTML files that
can be compared side by side: one showing a fully green graph and one showing
a red failure node at the validation step.

Output files
------------
    output/prd4_demo_success.html   — happy-path run
    output/prd4_demo_failure.html   — failure-mode run
"""

from __future__ import annotations

import os
import sys

from instrumentation.trace_collector import get_trace, reset_trace
from graph.graph_builder import build_graph, graph_debug_summary
from graph.graph_visualizer import render_graph_html
from pipeline.demo_pipeline import run_demo_pipeline


# ---------------------------------------------------------------------------
# Single-mode runner
# ---------------------------------------------------------------------------

def run_mode(fail_mode: bool) -> None:
    """Execute one full pipeline run and render the graph to HTML.

    Parameters
    ----------
    fail_mode:
        When True, the pipeline uses parameters that trigger a deterministic
        validation failure, producing a red error node in the graph.
    """
    mode_label = "FAILURE" if fail_mode else "SUCCESS"
    separator = "=" * 62
    print(f"\n{separator}")
    print(f"  Synthetic Demo Pipeline  —  {mode_label} MODE")
    print(f"{separator}")

    # Step 1 — reset trace
    reset_trace()
    print("\n[1/5] Trace reset.")

    # Step 2 — run the pipeline
    pipeline_output: str | None = None
    pipeline_error: Exception | None = None

    print(f"[2/5] Running pipeline (fail_mode={fail_mode}) ...")
    try:
        pipeline_output = run_demo_pipeline(base=5, multiplier=3, fail_mode=fail_mode)
        print(f"      Pipeline completed successfully.")
        preview = repr(pipeline_output[:80]) if pipeline_output else "—"
        print(f"      Output preview : {preview}")
    except Exception as exc:
        pipeline_error = exc
        print(f"      Pipeline raised : {type(exc).__name__}: {exc}")
        print(f"      (Expected in failure mode — trace events are still recorded.)")

    # Step 3 — retrieve trace
    trace = get_trace()
    print(f"[3/5] Trace retrieved: {len(trace)} event(s).")

    if not trace:
        print("      No trace events found — cannot build graph. Stopping.")
        return

    # Step 4 — build graph
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)

    print(f"[4/5] Graph built:")
    print(f"      Nodes   : {summary['num_nodes']}")
    print(f"      Edges   : {summary['num_edges']}")
    print(f"      Modules : {sorted(summary['module_counts'].keys())}")
    print(f"      Status  : {summary['status_counts']}")

    # Step 5 — render HTML
    suffix = "failure" if fail_mode else "success"
    output_path = f"output/prd4_demo_{suffix}.html"
    abs_path = render_graph_html(graph, output_path)

    print(f"[5/5] HTML written to: {abs_path}")
    print(f"      File size : {os.path.getsize(abs_path):,} bytes")

    # Summary banner
    print()
    run_ok = pipeline_error is None
    print(f"  Run status   : {'SUCCEEDED' if run_ok else 'FAILED (intentional)'}")
    print(f"  Trace events : {len(trace)}")
    print(f"  Graph nodes  : {summary['num_nodes']}")
    print(f"  Graph edges  : {summary['num_edges']}")
    print(f"  HTML output  : {abs_path}")
    if not run_ok:
        print(f"  Tip: open the HTML and look for the red node — that is where")
        print(f"       the pipeline failed (validate_score_range).")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = set(sys.argv[1:])

    success_only = "--success-only" in args
    fail_only = "--fail-only" in args

    if success_only and fail_only:
        print("Error: --success-only and --fail-only are mutually exclusive.")
        sys.exit(1)

    if fail_only:
        run_mode(fail_mode=True)
    elif success_only:
        run_mode(fail_mode=False)
    else:
        # Default: run both modes so the user gets two comparable graphs.
        run_mode(fail_mode=False)
        run_mode(fail_mode=True)

    print("Done. Open the HTML files above in a browser to explore the graphs.")
    print()
