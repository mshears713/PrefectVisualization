"""
graph/module_graph_visualizer.py — Module overview graph renderer (PRD 09).

Overview
--------
This module renders the Phase 2 module overview graph — produced by
create_module_graph() in PRD 07 — as a self-contained interactive HTML file.

Design goals
------------
- Left-to-right layout driven by stage_index (physics disabled).
- Rectangular boxes that read as "pipeline stages", not abstract graph nodes.
- Visible title, task count, status badge, and duration inside each node.
- Hover tooltip showing input summary, output summary, and duration.
- Status communicated via both color and badge text.
- Deterministic output: same module graph → same HTML structure.

Public API
----------
    render_module_graph_html(module_graph, output_path) -> str
        Full pipeline: position nodes, build PyVis network, write HTML,
        return absolute output path.

    make_module_node_label(node_data) -> str
        Format the visible in-node text (title, count, badge, duration).

    make_module_hover_text(node_data) -> str
        Format the HTML hover tooltip (input, output, duration).
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

import networkx as nx
from pyvis.network import Network


# ---------------------------------------------------------------------------
# Status colour and badge mapping
# ---------------------------------------------------------------------------

_STATUS_COLORS: Dict[str, str] = {
    "success":      "#4caf50",   # green
    "error":        "#f44336",   # red
    "warning":      "#ff9800",   # amber
    "not_executed": "#b0bec5",   # blue-grey (placeholder nodes)
}

_STATUS_BORDER_COLORS: Dict[str, str] = {
    "success":      "#388e3c",
    "error":        "#c62828",
    "warning":      "#e65100",
    "not_executed": "#90a4ae",
}

_STATUS_BADGES: Dict[str, str] = {
    "success":      "✓ success",
    "error":        "✖ error",
    "warning":      "⚠ warning",
    "not_executed": "— not executed",
}

_DEFAULT_COLOR  = "#90a4ae"
_DEFAULT_BORDER = "#607d8b"


def status_to_color(status: str) -> str:
    """Return the background hex colour for a given status value."""
    return _STATUS_COLORS.get(status, _DEFAULT_COLOR)


def status_to_border(status: str) -> str:
    """Return the border hex colour for a given status value."""
    return _STATUS_BORDER_COLORS.get(status, _DEFAULT_BORDER)


def status_badge(status: str) -> str:
    """Return a short badge string for a given status value."""
    return _STATUS_BADGES.get(status, status)


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_X_SPACING = 320    # horizontal pixels between module node centres
_Y_CENTER   = 0     # y coordinate for all module nodes (single row)


# ---------------------------------------------------------------------------
# Label and tooltip formatters
# ---------------------------------------------------------------------------

def make_module_node_label(node_data: dict) -> str:
    """Format the visible in-node text for a module box.

    Displays four lines:
        module name  (title)
        task count
        status badge
        total duration

    Parameters
    ----------
    node_data :
        Attribute dict of one module node as produced by create_module_graph().

    Returns
    -------
    str
        Newline-separated label displayed inside the node rectangle.
    """
    module_name  = node_data.get("module_name", "?")
    task_count   = node_data.get("task_count", 0)
    status       = node_data.get("status", "unknown")
    duration_ms  = node_data.get("total_duration_ms", 0.0)

    badge = status_badge(status)
    dur   = f"{duration_ms:.0f} ms"

    return f"{module_name}\n{task_count} task(s)\n{badge}\n{dur}"


def make_module_hover_text(node_data: dict) -> str:
    """Format the HTML hover tooltip for a module box.

    Shows: module name, input summary, output summary, duration.
    Branch flag and module ID are shown as supplementary details.

    Parameters
    ----------
    node_data :
        Attribute dict of one module node.

    Returns
    -------
    str
        HTML-formatted string rendered by vis.js on hover.
    """
    module_name    = node_data.get("module_name", "?")
    input_summary  = node_data.get("input_summary",  "") or "—"
    output_summary = node_data.get("output_summary", "") or "—"
    duration_ms    = node_data.get("total_duration_ms", 0.0)
    task_count     = node_data.get("task_count", 0)
    branch_flag    = node_data.get("branch_detected", False)
    module_id      = node_data.get("module_id", "")

    parts = [
        f"<b>{module_name}</b>",
        "<hr/>",
        f"<b>Input:</b>&nbsp;&nbsp;{input_summary}",
        f"<b>Output:</b>&nbsp;{output_summary}",
        f"<b>Duration:</b> {duration_ms:.0f} ms",
        f"<b>Tasks:</b>&nbsp;&nbsp;{task_count}",
    ]
    if branch_flag:
        parts.append("<br>⚡ <i>Branch point inside this module</i>")
    if module_id:
        parts.append(f"<small style='color:#888'>id: {module_id}</small>")

    return "<br>".join(parts)


# ---------------------------------------------------------------------------
# Position computation (left-to-right, deterministic)
# ---------------------------------------------------------------------------

def _sorted_module_nodes(
    module_graph: nx.DiGraph,
) -> List[Tuple[str, dict]]:
    """Return module nodes sorted by stage_index (then module_name as tiebreaker)."""
    return sorted(
        module_graph.nodes(data=True),
        key=lambda item: (
            item[1].get("stage_index", 999),
            item[1].get("module_name", ""),
        ),
    )


def _compute_module_positions(module_graph: nx.DiGraph) -> Dict[str, Dict[str, int]]:
    """Compute fixed (x, y) display positions for module nodes.

    Positions are assigned left-to-right in stage_index order.
    All modules share the same y coordinate so they appear in one horizontal row.

    Returns
    -------
    dict mapping node_id → {"x": int, "y": int}
    """
    ordered = _sorted_module_nodes(module_graph)
    positions: Dict[str, Dict[str, int]] = {}
    for i, (node_id, _) in enumerate(ordered):
        positions[node_id] = {"x": i * _X_SPACING, "y": _Y_CENTER}
    return positions


# ---------------------------------------------------------------------------
# PyVis options (physics off, left-to-right fixed layout)
# ---------------------------------------------------------------------------

_MODULE_VIS_OPTIONS = """{
  "physics": { "enabled": false },
  "layout": { "randomSeed": 42 },
  "edges": {
    "arrows": { "to": { "enabled": true, "scaleFactor": 1.0 } },
    "smooth": { "type": "straight" },
    "width": 2
  },
  "nodes": {
    "shape": "box",
    "borderWidth": 2,
    "shadow": { "enabled": true, "size": 5, "x": 2, "y": 2 },
    "margin": 10
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 80,
    "navigationButtons": true,
    "keyboard": false
  }
}"""


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_module_graph_html(
    module_graph: nx.DiGraph,
    output_path: str = "output/module_graph.html",
) -> str:
    """Render the module overview graph to a standalone HTML file.

    Produces a left-to-right process-map view of the pipeline's module stages.
    Each module is rendered as a coloured rectangular box showing its name,
    task count, status badge, and total duration. Hovering shows I/O summaries.

    Parameters
    ----------
    module_graph :
        Module overview graph from create_module_graph() (PRD 07).
    output_path :
        Destination file path. Created (with parent dirs) if it does not exist.

    Returns
    -------
    str
        Absolute path to the generated HTML file.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    positions = _compute_module_positions(module_graph)

    net = Network(
        height="420px",
        width="100%",
        directed=True,
        cdn_resources="in_line",
        bgcolor="#f0f4f8",
        heading="Module Overview — Phase 2 Pipeline",
    )
    net.set_options(_MODULE_VIS_OPTIONS)

    # --- Add module nodes ---
    for node_id, node_data in module_graph.nodes(data=True):
        pos    = positions.get(node_id, {"x": 0, "y": 0})
        status = node_data.get("status", "unknown")
        bg     = status_to_color(status)
        border = status_to_border(status)
        label  = make_module_node_label(node_data)
        title  = make_module_hover_text(node_data)

        # Add node with minimal positional args; patch everything else below.
        net.add_node(node_id, shape="box", label=label, title=title)

        n = net.node_map[node_id]
        n["x"]      = pos["x"]
        n["y"]      = pos["y"]
        n["physics"] = False     # pin this node so physics cannot move it
        n["color"]  = {
            "background": bg,
            "border":     border,
            "highlight":  {"background": bg, "border": "#212121"},
            "hover":      {"background": bg, "border": "#212121"},
        }
        n["font"] = {
            "color": "#ffffff",
            "size":  14,
            "face":  "Arial",
        }
        n["widthConstraint"] = {"minimum": 190, "maximum": 220}

    # --- Add pipeline edges ---
    for src, dst, _edge_data in module_graph.edges(data=True):
        net.add_edge(src, dst, color={"color": "#546e7a", "inherit": False}, width=2)

    html_content = net.generate_html(local=False, notebook=False)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    return os.path.abspath(output_path)
