"""
graph/module_graph_visualizer.py — Module overview graph renderer (PRD 09 / PRD 10 / PRD 11).

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
- PRD 10: clicking a module node navigates to its task graph HTML file.
- PRD 11: rule-based summary banner above the graph; single title; clean formatting.

Public API
----------
    render_module_graph_html(module_graph, output_path, task_graph_links) -> str
        Full pipeline: position nodes, build PyVis network, write HTML,
        return absolute output path. Injects click-to-navigate JS when
        task_graph_links are provided or auto-generated from module names.
        Also injects a rule-based summary banner.

    make_module_node_label(node_data) -> str
        Format the visible in-node text (title, count, badge, duration).

    make_module_hover_text(node_data) -> str
        Format the HTML hover tooltip (input, output, duration).

    build_pipeline_summary_banner(module_graph) -> str
        Generate HTML for the rule-based summary banner (PRD 11).
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Tuple

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


def make_module_hover_text(node_data: dict, has_task_link: bool = False) -> str:
    """Format the hover tooltip for a module box.

    Shows: module name, input summary, output summary, duration, task count.
    For decision nodes, shows placeholder values since they don't execute tasks.
    Uses plain text with newlines for reliable rendering across vis.js versions.

    Parameters
    ----------
    node_data :
        Attribute dict of one module node.
    has_task_link :
        If True, adds a hint that clicking opens the task graph.

    Returns
    -------
    str
        Plain text string with newlines (no HTML tags for maximum compatibility).
    """
    module_name    = node_data.get("module_name", "?")
    is_decision    = node_data.get("is_decision_node", False)
    
    # Decision nodes show placeholder values
    if is_decision:
        input_summary  = "[Decision point — no tasks]"
        output_summary = "[Routes pipeline based on logic]"
        duration_ms    = 0.0
        task_count     = 0
    else:
        input_summary  = node_data.get("input_summary",  "") or "[Coming from previous module]"
        output_summary = node_data.get("output_summary", "") or "[Passing to next module]"
        duration_ms    = node_data.get("total_duration_ms", 0.0)
        task_count     = node_data.get("task_count", 0)
    
    branch_flag    = node_data.get("branch_detected", False)

    parts = [
        module_name,
        "─" * 40,
        f"📥 INPUT:    {input_summary}",
        f"📤 OUTPUT:   {output_summary}",
        f"⏱  DURATION: {duration_ms:.0f} ms",
        f"📋 TASKS:    {task_count}",
    ]
    if branch_flag and not is_decision:
        parts.append("⚡ Branch point inside this module")
    if is_decision:
        parts.append("🔀 Routing decision node")
    if has_task_link and not is_decision:
        parts.append("→ Click to open task graph")

    return "\n".join(parts)


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
# Navigation injection helpers (PRD 10)
# ---------------------------------------------------------------------------

def _build_node_url_map(module_graph: nx.DiGraph) -> Dict[str, str]:
    """Build a mapping from vis.js node ID to task graph HTML filename.

    Uses module_name from each node to derive the stable slug filename
    (e.g. "Text Extraction" → "task_graph_text_extraction.html").
    
    Excludes decision nodes (is_decision_node=True) since they have no tasks.

    Returns
    -------
    dict mapping NetworkX node_id → relative HTML filename
    """
    from graph.task_graph_builder import module_name_to_id

    url_map: Dict[str, str] = {}
    for node_id, node_data in module_graph.nodes(data=True):
        # Skip decision nodes — they have no task graph to drill into
        if node_data.get("is_decision_node"):
            continue
            
        module_name = node_data.get("module_name", "")
        if module_name:
            slug = module_name_to_id(module_name)
            url_map[node_id] = f"task_graph_{slug}.html"
    return url_map


def _inject_navigation_js(html_content: str, node_url_map: Dict[str, str]) -> str:
    """Inject a click-handler into the module graph HTML for drill-down navigation.

    Appends JavaScript after the ``drawGraph()`` call so that clicking a
    module node opens the corresponding task graph HTML file.  The cursor
    changes to a pointer over nodes to signal that they are clickable.

    Parameters
    ----------
    html_content :
        Raw HTML string produced by PyVis.
    node_url_map :
        Mapping of vis.js node ID → relative URL for the task graph page.

    Returns
    -------
    str
        Modified HTML with click-navigation script injected.
    """
    mapping_json = json.dumps(node_url_map)

    nav_script = f"""
<script type="text/javascript">
  // PRD 10 — drill-down navigation: clicking a module node opens its task graph.
  (function() {{
    var nodeUrlMap = {mapping_json};

    // Wait until drawGraph() has run and the network object exists.
    function attachNavigation() {{
      if (typeof network === "undefined" || network === null) {{
        setTimeout(attachNavigation, 100);
        return;
      }}
      network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
          var nodeId = String(params.nodes[0]);
          var url = nodeUrlMap[nodeId];
          if (url) {{
            window.location.href = url;
          }}
        }}
      }});
      network.on("hoverNode", function() {{
        var canvas = document.querySelector("#mynetwork canvas");
        if (canvas) canvas.style.cursor = "pointer";
      }});
      network.on("blurNode", function() {{
        var canvas = document.querySelector("#mynetwork canvas");
        if (canvas) canvas.style.cursor = "default";
      }});
    }}

    attachNavigation();
  }})();
</script>
"""

    # Inject before the closing </body> tag so it runs after the page loads.
    if "</body>" in html_content:
        return html_content.replace("</body>", nav_script + "\n</body>", 1)
    return html_content + nav_script


# ---------------------------------------------------------------------------
# PRD 11 — Pipeline summary banner builders
# ---------------------------------------------------------------------------

def build_pipeline_summary_banner(module_graph: nx.DiGraph) -> str:
    """Build a rule-based summary banner HTML for the module overview.

    Displays high-level pipeline context:
    - total module count
    - total task count
    - success/failure/warning counts
    - total runtime
    - one-line narrative of execution

    Parameters
    ----------
    module_graph :
        The module overview graph.

    Returns
    -------
    str
        HTML string for the banner, ready to inject into the page.
    """
    # Collect module and task stats.
    module_nodes = list(module_graph.nodes(data=True))
    total_modules = len(module_nodes)
    total_tasks = 0
    total_duration_ms = 0.0
    success_count = 0
    error_count = 0
    warning_count = 0

    for _node_id, node_data in module_nodes:
        task_count = node_data.get("task_count", 0)
        total_tasks += task_count
        duration = node_data.get("total_duration_ms", 0.0)
        total_duration_ms += duration
        status = node_data.get("status", "unknown")
        if status == "success":
            success_count += 1
        elif status == "error":
            error_count += 1
        elif status == "warning":
            warning_count += 1

    # Build narrative line based on module sequence and status.
    ordered_modules = _sorted_module_nodes(module_graph)
    module_names = [data.get("module_name", "?") for _id, data in ordered_modules]
    narrative = " → ".join(module_names)

    # Abbreviate if too long.
    if len(narrative) > 100:
        narrative = narrative[:97] + "…"

    # Determine overall status emoji.
    if error_count > 0:
        status_emoji = "✖"
        status_text = "Errors encountered"
        status_color = "#f44336"
    elif warning_count > 0:
        status_emoji = "⚠"
        status_text = "Warnings present"
        status_color = "#ff9800"
    else:
        status_emoji = "✓"
        status_text = "All modules succeeded"
        status_color = "#4caf50"

    # Build banner HTML.
    banner_html = f"""
<div style="
  padding: 15px 20px;
  background: #263238;
  color: #eceff1;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 13px;
  line-height: 1.6;
  border-bottom: 1px solid #455a64;
">
  <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 8px;">
    <span style="color: {status_color}; font-size: 16px; font-weight: bold;">{status_emoji} {status_text}</span>
    <span style="color: #b0bec5;">
      <b>{total_modules}</b> modules &nbsp;| &nbsp; 
      <b>{total_tasks}</b> tasks &nbsp;| &nbsp; 
      <b>{total_duration_ms:.0f}</b> ms total
    </span>
  </div>
  <div style="color: #90a4ae; font-size: 12px; font-style: italic;">
    {narrative}
  </div>
</div>
"""
    return banner_html


def _inject_summary_banner(html_content: str, banner_html: str) -> str:
    """Inject the summary banner into the HTML output.

    Inserts before the mynetwork div.

    Parameters
    ----------
    html_content :
        Raw HTML from PyVis.
    banner_html :
        The banner HTML to inject.

    Returns
    -------
    str
        Modified HTML with banner injected.
    """
    target = '<div id="mynetwork"'
    if target in html_content:
        return html_content.replace(target, banner_html + "\n" + target, 1)
    # Fallback: insert at the start of <body>.
    if "<body>" in html_content:
        return html_content.replace("<body>", "<body>\n" + banner_html, 1)
    return banner_html + html_content


# ---------------------------------------------------------------------------
# PRD 11 — HTML cleanup and title normalization
# ---------------------------------------------------------------------------

def _clean_duplicate_titles(html_content: str) -> str:
    """Remove PyVis-generated heading tags and keep only the primary title we set.

    This ensures only one visible page title.

    Parameters
    ----------
    html_content :
        Raw HTML from PyVis.

    Returns
    -------
    str
        HTML with duplicate titles removed.
    """
    # PyVis generates an <h1> or similar from the "heading" parameter.
    # We want to remove any extra title markup to ensure a single title only.
    # Remove the auto-generated h1 or h2 that PyVis might create separately.
    html_content = re.sub(r'<h1[^>]*>.*?</h1>', '', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<h2[^>]*>.*?</h2>', '', html_content, flags=re.DOTALL)
    return html_content


def render_module_graph_html(
    module_graph: nx.DiGraph,
    output_path: str = "output/module_graph.html",
    task_graph_links: Optional[Dict[str, str]] = None,
) -> str:
    """Render the module overview graph to a standalone HTML file.

    Produces a left-to-right process-map view of the pipeline's module stages.
    Each module is rendered as a coloured rectangular box showing its name,
    task count, status badge, and total duration. Hovering shows I/O summaries.

    PRD 10: clicking a module node navigates to its task graph HTML page.
    Navigation links are auto-generated from module names unless overridden
    via the ``task_graph_links`` parameter.

    PRD 11: injects a rule-based summary banner above the graph; cleans up
    titles to ensure a single visible heading.

    Parameters
    ----------
    module_graph :
        Module overview graph from create_module_graph() (PRD 07).
    output_path :
        Destination file path. Created (with parent dirs) if it does not exist.
    task_graph_links :
        Optional mapping of NetworkX node_id → relative HTML filename for the
        task graph. When None (default), links are auto-generated from module
        names using the standard slug convention.  Pass an empty dict to
        disable navigation entirely.

    Returns
    -------
    str
        Absolute path to the generated HTML file.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Build node → URL mapping for click navigation.
    if task_graph_links is None:
        node_url_map = _build_node_url_map(module_graph)
    else:
        node_url_map = task_graph_links

    positions = _compute_module_positions(module_graph)

    net = Network(
        height="420px",
        width="100%",
        directed=True,
        cdn_resources="in_line",
        bgcolor="#f0f4f8",
        heading="",  # Empty heading; we'll inject our own below
    )
    net.set_options(_MODULE_VIS_OPTIONS)

    # --- Add module nodes ---
    for node_id, node_data in module_graph.nodes(data=True):
        pos         = positions.get(node_id, {"x": 0, "y": 0})
        status      = node_data.get("status", "unknown")
        bg          = status_to_color(status)
        border      = status_to_border(status)
        label       = make_module_node_label(node_data)
        
        # Decision nodes should not be clickable (no task graph)
        is_decision = node_data.get("is_decision_node", False)
        has_link    = (node_id in node_url_map) and (not is_decision)
        title       = make_module_hover_text(node_data, has_task_link=has_link)
        
        # Decision nodes get a slightly different visual treatment (diamond-like or lighter)
        shape = "diamond" if is_decision else "box"

        # Add node with minimal positional args; patch everything else below.
        net.add_node(node_id, shape=shape, label=label, title=title)

        n = net.node_map[node_id]
        n["x"]      = pos["x"]
        n["y"]      = pos["y"]
        n["physics"] = False     # pin this node so physics cannot move it
        
        # Decision nodes get a different visual appearance
        if is_decision:
            decision_color = "#ffc107"  # amber/yellow
            decision_border = "#f57f17"
            n["color"] = {
                "background": decision_color,
                "border":     decision_border,
                "highlight":  {"background": decision_color, "border": "#212121"},
                "hover":      {"background": decision_color, "border": "#212121"},
            }
            n["font"] = {
                "color": "#000000",  # Black text for decision nodes (yellow background)
                "size":  14,
                "face":  "Arial",
            }
        else:
            n["color"] = {
                "background": bg,
                "border":     border,
                "highlight":  {"background": bg, "border": "#212121"},
                "hover":      {"background": bg, "border": "#212121"},
            }
            n["font"] = {
                "color": "#ffffff",  # White text for other nodes
                "size":  14,
                "face":  "Arial",
            }
        n["widthConstraint"] = {"minimum": 190, "maximum": 220}

    # --- Add pipeline edges with data flow labels ---
    for src, dst, edge_data in module_graph.edges(data=True):
        # Get source module's output to show data flow.
        src_node = module_graph.nodes[src]
        output_label = src_node.get("output_summary", "")
        if output_label and len(output_label) > 35:
            output_label = output_label[:32] + "…"

        edge_label = output_label if output_label else ""
        
        # Check if this is a branch edge
        edge_type = edge_data.get("edge_type", "pipeline")
        is_branch = edge_type == "branch"
        branch_taken = edge_data.get("branch_taken", False)
        branch_label = edge_data.get("branch_label", "")
        
        # Style edges based on type and whether they were taken
        if is_branch:
            if branch_taken:
                # Taken branch: solid, visible color
                edge_color = "#2e7d32"  # darker green
                edge_width = 3
                edge_style = "solid"
                smooth_type = "curvedCW"  # Curve clockwise for taken path
                # Add branch label to edge
                if branch_label:
                    edge_label = branch_label + " (taken)"
            else:
                # Alternate branch: dotted, faded color
                edge_color = "#b0bec5"  # light grey-blue
                edge_width = 2
                edge_style = "dotted"
                smooth_type = "curvedCCW"  # Curve counter-clockwise for alternate path
                # Add branch label to edge
                if branch_label:
                    edge_label = branch_label + " (alternate)"
        else:
            # Pipeline edges: standard style
            edge_color = "#546e7a"  # standard blue-grey
            edge_width = 2
            edge_style = "solid"
            smooth_type = "straight"

        net.add_edge(
            src, dst,
            color={"color": edge_color, "inherit": False},
            width=edge_width,
            label=edge_label,
            font={"size": 11, "color": edge_color, "align": "middle"},
            dashes=True if edge_style == "dotted" else False,
            smooth={"type": smooth_type},
        )

    html_content = net.generate_html(local=False, notebook=False)

    # PRD 11 — Clean up duplicate titles and add page title.
    html_content = _clean_duplicate_titles(html_content)
    # Inject our own clean title into <head> if needed.
    if "<title>" not in html_content:
        if "</head>" in html_content:
            html_content = html_content.replace(
                "</head>",
                "<title>Module Overview — Phase 2 Pipeline</title>\n</head>",
                1
            )

    # PRD 11 — Inject summary banner.
    banner_html = build_pipeline_summary_banner(module_graph)
    html_content = _inject_summary_banner(html_content, banner_html)

    # Inject click-navigation if we have any links to add.
    if node_url_map:
        html_content = _inject_navigation_js(html_content, node_url_map)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)

    return os.path.abspath(output_path)
