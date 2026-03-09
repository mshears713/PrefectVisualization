"""
api/server.py — FastAPI delivery layer for the Runtime Visual Debugger.

This module is the thin orchestration layer that exposes the prototype
through HTTP.  It does not duplicate business logic from earlier milestones;
it only wires existing components together.

Routes
------
GET  /              — service description and available routes
GET  /health        — health check (used by Render deployment checks)
GET  /run-demo      — execute the synthetic demo pipeline, generate graph HTML
GET  /graph         — serve the most recently generated graph HTML in a browser
POST /analyze-pdf   — placeholder bridge route for future PDF-based analysis

Starting the server
-------------------
    uvicorn api.server:app --host 0.0.0.0 --port 8000

    # Render deployment (port picked up from environment):
    uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-10000}

Typical demo workflow
---------------------
1. GET /run-demo              — runs the pipeline, returns JSON summary
2. GET /run-demo?mode=failure — reruns in failure mode (red error nodes)
3. GET /graph                 — opens the graph in a browser
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from graph.graph_builder import build_graph, graph_debug_summary
from graph.graph_visualizer import render_graph_html
from instrumentation.trace_collector import get_trace, reset_trace
from pipeline.demo_pipeline import run_demo_pipeline


# ---------------------------------------------------------------------------
# Paths — resolved relative to the repo root so the server works correctly
# regardless of which directory uvicorn is invoked from.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_DIR = _REPO_ROOT / "output"
_LATEST_GRAPH = _OUTPUT_DIR / "latest_graph.html"


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Runtime Visual Debugger",
    description=(
        "Instruments Python function calls, converts the runtime trace into a "
        "directed execution graph, and renders it as an interactive HTML visualization."
    ),
    version="0.5.0",
)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@app.get("/", response_class=JSONResponse)
def root() -> dict:
    """Return a description of the service and the available routes."""
    return {
        "service": "Runtime Visual Debugger",
        "description": (
            "Triggers a synthetic demo pipeline, captures its execution trace, "
            "builds a directed graph, and serves the result as interactive HTML."
        ),
        "routes": {
            "GET /health": "Health check — confirms the service is running.",
            "GET /run-demo": (
                "Run the demo pipeline and generate a graph. "
                "Optional query param: mode=success (default) or mode=failure."
            ),
            "GET /graph": (
                "Serve the most recently generated graph HTML. "
                "Open in a browser to inspect the interactive visualization."
            ),
            "POST /analyze-pdf": (
                "[Coming soon] Upload a PDF to analyse its execution trace. "
                "Returns a placeholder response for now."
            ),
        },
        "usage_example": {
            "step_1": "GET /run-demo",
            "step_2": "GET /graph  ← open this in a browser",
            "failure_demo": "GET /run-demo?mode=failure",
        },
    }


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", response_class=JSONResponse)
def health() -> dict:
    """Return a simple health status, suitable for Render deployment checks."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /run-demo
# ---------------------------------------------------------------------------

@app.get("/run-demo", response_class=JSONResponse)
def run_demo(
    mode: str = Query(
        default="success",
        description="Demo mode: 'success' for the happy path, 'failure' to trigger a deterministic validation error.",
    ),
) -> dict:
    """Execute the synthetic demo pipeline and render the result as a graph.

    Steps performed:
    1. Reset the runtime trace.
    2. Run the synthetic pipeline (success or failure mode).
    3. Retrieve the recorded trace events.
    4. Build an execution graph from the trace.
    5. Render the graph to ``output/latest_graph.html``.
    6. Return a JSON summary with counts and the graph URL.

    Parameters
    ----------
    mode:
        ``"success"`` — runs the normal pipeline (all tasks succeed, green graph).
        ``"failure"`` — uses inputs that cause ``validate_score_range`` to raise,
        producing red error nodes in the graph.
    """
    if mode not in ("success", "failure"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Use 'success' or 'failure'.",
        )

    fail_mode = mode == "failure"

    # --- Step 1: reset trace ---
    reset_trace()

    # --- Step 2: run pipeline ---
    pipeline_output: Optional[str] = None
    pipeline_error: Optional[str] = None

    try:
        pipeline_output = run_demo_pipeline(base=5, multiplier=3, fail_mode=fail_mode)
    except Exception as exc:
        # Expected in failure mode.  The decorator has already recorded the
        # error event, so the trace still contains the partial execution.
        pipeline_error = f"{type(exc).__name__}: {exc}"

    # --- Step 3: retrieve trace ---
    trace = get_trace()
    if not trace:
        raise HTTPException(
            status_code=500,
            detail="No trace events were recorded. The pipeline may not be instrumented correctly.",
        )

    # --- Step 4: build graph ---
    try:
        graph = build_graph(trace)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Graph construction failed: {exc}",
        )

    summary = graph_debug_summary(graph)

    # --- Step 5: render graph ---
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        abs_path = render_graph_html(graph, str(_LATEST_GRAPH))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Graph rendering failed: {exc}",
        )

    # --- Step 6: return summary ---
    return {
        "mode": mode,
        "pipeline_status": "error" if pipeline_error else "success",
        "pipeline_error": pipeline_error,
        "pipeline_output_preview": (
            pipeline_output[:120] if pipeline_output else None
        ),
        "trace_event_count": len(trace),
        "node_count": summary["num_nodes"],
        "edge_count": summary["num_edges"],
        "modules": sorted(summary["module_counts"].keys()),
        "status_counts": summary["status_counts"],
        "graph_url": "/graph",
        "graph_file": abs_path,
        "next_step": "Open /graph in a browser to inspect the interactive visualization.",
    }


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------

@app.get("/graph")
def serve_graph() -> FileResponse:
    """Serve the most recently generated graph HTML so it renders in a browser.

    Returns the contents of ``output/latest_graph.html``.  Call ``GET /run-demo``
    first to generate the graph if this endpoint returns 404.
    """
    if not _LATEST_GRAPH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No graph has been generated yet. "
                "Call GET /run-demo first to produce a graph."
            ),
        )
    return FileResponse(str(_LATEST_GRAPH), media_type="text/html")


# ---------------------------------------------------------------------------
# POST /analyze-pdf  — placeholder bridge for future PDF analysis
# ---------------------------------------------------------------------------

@app.post("/analyze-pdf", response_class=JSONResponse)
async def analyze_pdf(
    file: UploadFile = File(
        ...,
        description="PDF file to analyse (full pipeline coming in a future milestone).",
    ),
) -> dict:
    """Accept a PDF upload and return a placeholder response.

    This route establishes the upload contract for the real PDF analysis
    pipeline, which will be implemented in a future milestone.  The file is
    received and its metadata is echoed back, but no processing is performed.
    """
    # Read a small header just to confirm the file is accessible.
    header = await file.read(8)
    is_pdf = header.startswith(b"%PDF")
    await file.seek(0)

    return {
        "status": "not_implemented",
        "message": (
            "PDF analysis pipeline is coming in the next milestone. "
            "The route contract is established — the real pipeline will be "
            "wired in here once PDF extraction is ready."
        ),
        "received_filename": file.filename,
        "content_type": file.content_type,
        "looks_like_pdf": is_pdf,
    }
