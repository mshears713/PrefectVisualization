"""
graph/task_graph_visualizer.py — Task graph renderer for Phase 2 (PRD 09 / PRD 10).

Overview
--------
This module renders the task-level drill-down graph produced by
build_task_graph_for_module() in PRD 08 as a self-contained interactive
HTML file.

Design goals
------------
- Left-to-right layout: main pipeline tasks advance along the x-axis.
- Alternate (non-executed) branch nodes appear below the main row at a fixed
  y offset so the "road not taken" is visible without cluttering the spine.
- Rectangular box nodes with visible title, description, status badge, and
  duration inside each box.
- Duration-aware width scaling: width = max(140, min(380, 120 + ms * 0.2)).
  Slower tasks appear wider to communicate relative cost at a glance.
- Executed path uses solid edges; alternate branch edges are dashed and muted.
- Status communicated by both fill colour and badge text.
- Deterministic output: same TaskGraphPayload → same HTML structure.
- PRD 10: each task graph page includes a back-navigation bar linking to
  the module overview graph.

Public API
----------
    render_task_graph_html(payload, output_path, back_link) -> str
        Full pipeline: position nodes, build PyVis network, write HTML,
        return absolute output path.

    compute_node_width(duration_ms) -> int
        Apply the duration scaling formula with min/max clamp.

    make_task_node_label(node_data) -> str
        Format the visible in-node text (name, description, badge, duration).

    make_task_hover_text(node_data) -> str
        Format the HTML hover tooltip (input, output, duration, status).
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import networkx as nx
from pyvis.network import Network

from graph.task_graph_builder import TaskGraphPayload


# ---------------------------------------------------------------------------
# Status colour and badge mapping
# ---------------------------------------------------------------------------

_STATUS_COLORS: Dict[str, str] = {
    "success":      "#4caf50",
    "error":        "#f44336",
    "warning":      "#ff9800",
    "not_executed": "#b0bec5",
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

# Alternate node style (dimmed — road not taken)
_ALT_BG     = "#cfd8dc"
_ALT_BORDER = "#90a4ae"
_ALT_FONT   = "#546e7a"   # darker text because background is light

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
# Width scaling
# ---------------------------------------------------------------------------

_WIDTH_BASE  = 120
_WIDTH_SCALE = 0.2
_WIDTH_MIN   = 140
_WIDTH_MAX   = 380


def compute_node_width(duration_ms: float) -> int:
    """Compute display width for a task node based on duration.

    Formula (from PRD 09):
        width = 120 + duration_ms * 0.2

    Clamped to [_WIDTH_MIN, _WIDTH_MAX] so that very fast or very slow tasks
    remain readable rather than vanishingly narrow or screen-filling.

    Parameters
    ----------
    duration_ms :
        Task execution duration in milliseconds.

    Returns
    -------
    int
        Width in pixels to apply as widthConstraint.minimum/maximum.
    """
    raw = _WIDTH_BASE + duration_ms * _WIDTH_SCALE
    return int(max(_WIDTH_MIN, min(_WIDTH_MAX, raw)))


# ---------------------------------------------------------------------------
# Label and tooltip formatters
# ---------------------------------------------------------------------------

def make_task_node_label(node_data: dict) -> str:
    """Format the visible in-node text for a task box.

    For executed tasks, displays four lines:
        task name
        description  (truncated at 48 chars)
        status badge
        duration

    For alternate (not-executed) placeholder tasks, displays three lines:
        task name
        [alternate path — not executed]
        status badge

    Parameters
    ----------
    node_data :
        Attribute dict of one task node as produced by the graph builders.

    Returns
    -------
    str
        Newline-separated label displayed inside the node rectangle.
    """
    task_name   = node_data.get("task_name", "?")
    description = node_data.get("task_description", "")
    status      = node_data.get("status", "unknown")
    duration_ms = node_data.get("duration_ms", 0.0)
    is_alt      = node_data.get("is_alternate", False)

    badge = status_badge(status)

    if is_alt:
        return f"{task_name}\n[alternate — not executed]\n{badge}"

    # Truncate long descriptions so the label stays compact.
    if len(description) > 48:
        description = description[:45] + "..."

    dur = f"{duration_ms:.0f} ms"
    return f"{task_name}\n{description}\n{badge}\n{dur}"


def make_task_hover_text(node_data: dict) -> str:
    """Format the HTML hover tooltip for a task box.

    Shows: task name, description, input summary, output summary, duration,
    status. Error message is appended when present. Alternate path nodes
    include a note that they were not executed.

    Parameters
    ----------
    node_data :
        Attribute dict of one task node.

    Returns
    -------
    str
        HTML-formatted string rendered by vis.js on hover.
    """
    task_name   = node_data.get("task_name", "?")
    description = node_data.get("task_description", "")
    status      = node_data.get("status", "unknown")
    duration_ms = node_data.get("duration_ms", 0.0)
    input_prev  = node_data.get("input_preview",  "") or "—"
    output_prev = node_data.get("output_preview", "") or "—"
    error_msg   = node_data.get("error_message")
    is_alt      = node_data.get("is_alternate", False)

    badge = status_badge(status)

    parts = [
        f"<b>{task_name}</b>",
        f"<i>{description}</i>",
        "<hr/>",
        f"<b>Input:</b>&nbsp;&nbsp;{input_prev}",
        f"<b>Output:</b>&nbsp;{output_prev}",
        f"<b>Duration:</b> {duration_ms:.0f} ms",
        f"<b>Status:</b>&nbsp;&nbsp;{badge}",
    ]
    if error_msg:
        parts.append(
            f"<b style='color:#f44336'>Error:</b> {error_msg}"
        )
    if is_alt:
        parts.append("<br><i style='color:#90a4ae'>This path was not taken in this run.</i>")

    return "<br>".join(parts)


# ---------------------------------------------------------------------------
# Position computation (left-to-right, deterministic)
# ---------------------------------------------------------------------------

_X_SPACING_MAIN = 360    # horizontal gap between main-path nodes
_Y_MAIN         = 0      # y for main pipeline row
_Y_ALT          = 280    # y for alternate-path nodes (below main row)


def _sort_main_nodes(task_graph: nx.DiGraph) -> List[Tuple[str, dict]]:
    """Return executed (non-alternate) nodes sorted by pipeline order."""
    main = [
        (nid, data)
        for nid, data in task_graph.nodes(data=True)
        if not data.get("is_alternate")
    ]
    return sorted(
        main,
        key=lambda item: (
            item[1].get("step_order", 999),
            item[1].get("trace_index", 999),
        ),
    )


def _compute_task_positions(
    task_graph: nx.DiGraph,
) -> Dict[str, Dict[str, int]]:
    """Compute fixed (x, y) display positions for all task nodes.

    Main path nodes are evenly spaced left-to-right at y = _Y_MAIN.

    Alternate (non-executed) nodes are placed below their predecessor
    (the branch decision task) at y = _Y_ALT, offset slightly right so
    the edge arrow is clearly visible.

    Returns
    -------
    dict mapping node_id → {"x": int, "y": int}
    """
    main_nodes = _sort_main_nodes(task_graph)
    alt_nodes  = [
        (nid, data)
        for nid, data in task_graph.nodes(data=True)
        if data.get("is_alternate")
    ]

    positions: Dict[str, Dict[str, int]] = {}

    # Place main-path nodes.
    for i, (nid, _) in enumerate(main_nodes):
        positions[nid] = {"x": i * _X_SPACING_MAIN, "y": _Y_MAIN}

    # Place alternate nodes below their predecessor.
    for nid, _ in alt_nodes:
        predecessors = list(task_graph.predecessors(nid))
        if predecessors and predecessors[0] in positions:
            pred_x = positions[predecessors[0]]["x"]
        else:
            # Fallback: place after all main nodes.
            pred_x = len(main_nodes) * _X_SPACING_MAIN
        # Offset right by a third of the spacing to keep arrow visible.
        positions[nid] = {"x": pred_x + _X_SPACING_MAIN // 3, "y": _Y_ALT}

    return positions


# ---------------------------------------------------------------------------
# PyVis options (physics off, left-to-right fixed layout)
# ---------------------------------------------------------------------------

_TASK_VIS_OPTIONS = """{
  "physics": { "enabled": false },
  "layout": { "randomSeed": 42 },
  "edges": {
    "arrows": { "to": { "enabled": true, "scaleFactor": 0.9 } },
    "smooth": { "type": "curvedCW", "roundness": 0.15 }
  },
  "nodes": {
    "shape": "box",
    "borderWidth": 2,
    "shadow": { "enabled": true, "size": 4, "x": 2, "y": 2 },
    "margin": 8
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 80,
    "navigationButtons": true,
    "keyboard": false
  }
}"""


# ---------------------------------------------------------------------------
# Back navigation injection (PRD 10)
# ---------------------------------------------------------------------------

def _inject_back_nav(
    html_content: str,
    back_link: str,
    module_name: str,
    task_count: int,
    total_duration_ms: float,
) -> str:
    """Inject a back-navigation header bar into the task graph HTML.

    Inserts a styled navigation row above the vis.js graph container.
    The bar contains a "Back to Module Overview" link on the left and a
    breadcrumb label on the right showing the current module name.

    Parameters
    ----------
    html_content :
        Raw HTML string produced by PyVis.
    back_link :
        Relative URL of the module overview page (e.g. "module_graph.html").
    module_name :
        Human-readable module name displayed in the breadcrumb.
    task_count :
        Number of executed tasks (shown in the breadcrumb).
    total_duration_ms :
        Total module duration (shown in the breadcrumb).

    Returns
    -------
    str
        Modified HTML with the navigation bar injected.
    """
    nav_html = (
        '<div style="'
        "padding: 10px 20px;"
        "background: #37474f;"
        "font-family: Arial, sans-serif;"
        "display: flex;"
        "align-items: center;"
        "gap: 20px;"
        '">'
        f'<a href="{back_link}" style="'
        "color: #80cbc4;"
        "text-decoration: none;"
        "font-size: 14px;"
        "font-weight: 600;"
        '">'
        "&#8592; Back to Module Overview"
        "</a>"
        '<span style="'
        "color: #b0bec5;"
        "font-size: 14px;"
        '">'
        f"Task Graph &mdash; {module_name}"
        f" &nbsp;|&nbsp; {task_count} task(s)"
        f" &nbsp;|&nbsp; {total_duration_ms:.0f}&thinsp;ms total"
        "</span>"
        "</div>\n"
    )

    # Insert before the graph container div.
    target = '<div id="mynetwork"'
    if target in html_content:
        return html_content.replace(target, nav_html + target, 1)
    # Fallback: insert at the start of <body>.
    if "<body>" in html_content:
        return html_content.replace("<body>", "<body>\n" + nav_html, 1)
    return nav_html + html_content


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_task_graph_html(
    payload: TaskGraphPayload,
    output_path: Optional[str] = None,
    back_link: str = "module_graph.html",
) -> str:
    """Render a module task graph to a standalone HTML file.

    Produces a left-to-right process-map view of the tasks inside one
    pipeline module. Each task is a coloured rectangle scaled by duration.
    Alternate branch paths are shown below the main row with dashed edges.

    PRD 10: a navigation bar is injected above the graph with a back link
    to the module overview page.

    Parameters
    ----------
    payload :
        TaskGraphPayload from build_task_graph_for_module() (PRD 08).
    output_path :
        Destination file path. Defaults to
        "output/task_graph_<module_id>.html".
        Parent directories are created if they do not exist.
    back_link :
        Relative URL for the "Back to Module Overview" link.
        Defaults to "module_graph.html".

    Returns
    -------
    str
        Absolute path to the generated HTML file.
    """
    if output_path is None:
        output_path = f"output/task_graph_{payload.module_id}.html"

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    task_graph = payload.graph
    ctx        = payload.context
    positions  = _compute_task_positions(task_graph)

    heading = (
        f"Task Graph — {payload.module_name} "
        f"({ctx.get('task_count', 0)} tasks, "
        f"{ctx.get('total_duration_ms', 0.0):.0f} ms total)"
    )

    net = Network(
        height="500px",
        width="100%",
        directed=True,
        cdn_resources="in_line",
        bgcolor="#f0f4f8",
        heading=heading,
    )
    net.set_options(_TASK_VIS_OPTIONS)

    # --- Add task nodes ---
    for node_id, node_data in task_graph.nodes(data=True):
        pos    = positions.get(node_id, {"x": 0, "y": 0})
        is_alt = node_data.get("is_alternate", False)
        status = node_data.get("status", "unknown")
        dur_ms = node_data.get("duration_ms", 0.0)

        # Width scales with duration for executed nodes; fixed min for alternates.
        width = compute_node_width(dur_ms) if not is_alt else _WIDTH_MIN

        if is_alt:
            bg     = _ALT_BG
            border = _ALT_BORDER
            font_c = _ALT_FONT
        else:
            bg     = status_to_color(status)
            border = status_to_border(status)
            font_c = "#ffffff"

        label = make_task_node_label(node_data)
        title = make_task_hover_text(node_data)

        net.add_node(node_id, shape="box", label=label, title=title)

        n = net.node_map[node_id]
        n["x"]       = pos["x"]
        n["y"]       = pos["y"]
        n["physics"] = False
        n["color"]   = {
            "background": bg,
            "border":     border,
            "highlight":  {"background": bg, "border": "#212121"},
            "hover":      {"background": bg, "border": "#212121"},
        }
        n["font"]    = {"color": font_c, "size": 12, "face": "Arial"}
        n["widthConstraint"] = {"minimum": width, "maximum": width}

    # --- Add edges with branch-aware styling ---
    for src, dst, edge_data in task_graph.edges(data=True):
        branch_taken = edge_data.get("branch_taken")
        # branch_taken is explicitly False only for alternate-path edges.
        is_alt_edge  = branch_taken is False

        if is_alt_edge:
            edge_color = "#b0bec5"
            edge_width = 1.5
            dashes     = True
        else:
            edge_color = "#546e7a"
            edge_width = 2.5
            dashes     = False

        net.add_edge(
            src, dst,
            color={"color": edge_color, "inherit": False},
            width=edge_width,
            dashes=dashes,
        )

    html_content = net.generate_html(local=False, notebook=False)

    # Inject back-navigation bar (PRD 10).
    html_content = _inject_back_nav(
        html_content,
        back_link=back_link,
        module_name=payload.module_name,
        task_count=ctx.get("task_count", 0),
        total_duration_ms=ctx.get("total_duration_ms", 0.0),
    )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    return os.path.abspath(output_path)
