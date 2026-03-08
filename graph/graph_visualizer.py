"""
graph/graph_visualizer.py — Render a NetworkX execution graph as interactive HTML.

Overview
--------
This module is the rendering layer (PRD03).  It takes the directed graph
produced by graph_builder.build_graph() and converts it into a standalone
HTML file using PyVis.

The HTML file is self-contained (all JS/CSS inlined) and can be opened
directly in any browser without a server.

Design principles
-----------------
- Node labels are minimal (task name only) so the canvas stays readable.
- All detail lives in the node tooltip (title attribute rendered on hover).
- Color encodes status:  green = success, red = error, grey = unknown.
- Module grouping is expressed via PyVis group= so the physics engine
  clusters related nodes; no custom containers are required.
- Edge arrows show execution direction:  parent → child.
- Physics is configured conservatively (repulsion solver) to avoid chaotic
  layouts; the graph stabilizes quickly and then movement stops.

Public API
----------
    render_graph_html(graph, output_path="output/graph.html") -> str
        Full pipeline: build PyVis network, write HTML, return output_path.

    build_pyvis_network(graph) -> pyvis.network.Network
        Convert a networkx.DiGraph to a configured PyVis Network.
        Useful for testing or for callers that want the network object.

    make_node_title(node_data) -> str
        Format a tooltip string from a node attribute dict.

    status_to_color(status) -> str
        Map status string to a CSS colour value.
"""

from __future__ import annotations

import os
from typing import Optional

import networkx as nx
from pyvis.network import Network


# ---------------------------------------------------------------------------
# Colour mapping
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "success": "#4caf50",   # medium green — readable on white background
    "error":   "#f44336",   # medium red
    "warning": "#ff9800",   # amber — for future use
}
_DEFAULT_COLOR = "#90a4ae"  # blue-grey — neutral fallback


def status_to_color(status: str) -> str:
    """Return a CSS hex colour for the given task status.

    Parameters
    ----------
    status:
        One of "success", "error", "warning", or any future value.
        Unknown values fall back to a neutral grey.
    """
    return _STATUS_COLORS.get(status, _DEFAULT_COLOR)


# ---------------------------------------------------------------------------
# Tooltip formatter
# ---------------------------------------------------------------------------

def make_node_title(node_data: dict) -> str:
    """Format an HTML tooltip string for a graph node.

    The tooltip is rendered by PyVis when the user hovers a node.
    HTML tags are supported by vis.js / PyVis title attributes.

    Parameters
    ----------
    node_data:
        The attribute dict for one graph node, as produced by
        graph_builder.build_graph().

    Returns
    -------
    str
        An HTML-formatted multi-line tooltip.
    """
    lines = [
        f"<b>{node_data.get('task_name', '?')}</b>",
        f"<i>{node_data.get('task_description', '')}</i>",
        "─────────────────────",
        f"<b>Module:</b> {node_data.get('module_name', '—')}",
        f"<b>Status:</b> {node_data.get('status', '—')}",
        f"<b>Duration:</b> {node_data.get('duration_ms', 0):.4f} ms",
        "─────────────────────",
        f"<b>Input length:</b> {node_data.get('input_length', 0)}",
        f"<b>Input preview:</b> {node_data.get('input_preview', '—')}",
        f"<b>Output length:</b> {node_data.get('output_length', 0)}",
        f"<b>Output preview:</b> {node_data.get('output_preview', '—')}",
    ]

    error_msg = node_data.get("error_message")
    if error_msg:
        lines += [
            "─────────────────────",
            f"<b>Error:</b> {error_msg}",
        ]

    return "<br>".join(lines)


# ---------------------------------------------------------------------------
# PyVis network construction
# ---------------------------------------------------------------------------

# Physics options as a JSON string passed to set_options().
# Repulsion solver with conservative settings keeps the graph stable and
# readable without excessive tuning.
_PHYSICS_OPTIONS = """
{
  "physics": {
    "enabled": true,
    "solver": "repulsion",
    "repulsion": {
      "nodeDistance": 150,
      "centralGravity": 0.15,
      "springLength": 200,
      "springStrength": 0.04,
      "damping": 0.12
    },
    "stabilization": {
      "enabled": true,
      "iterations": 200,
      "updateInterval": 50,
      "fit": true
    }
  },
  "edges": {
    "arrows": {
      "to": { "enabled": true, "scaleFactor": 0.8 }
    },
    "smooth": { "type": "dynamic" },
    "color": { "color": "#78909c", "inherit": false }
  },
  "nodes": {
    "shape": "dot",
    "size": 20,
    "font": { "size": 14, "face": "arial" },
    "borderWidth": 2,
    "shadow": true
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 150,
    "navigationButtons": false,
    "keyboard": false
  }
}
"""


def build_pyvis_network(graph: nx.DiGraph) -> Network:
    """Convert a NetworkX directed graph to a configured PyVis Network.

    Parameters
    ----------
    graph:
        A directed graph produced by graph_builder.build_graph().

    Returns
    -------
    pyvis.network.Network
        A fully configured network with styled nodes and edges, ready for
        HTML export.
    """
    net = Network(
        height="750px",
        width="100%",
        directed=True,
        cdn_resources="in_line",   # single self-contained HTML file
        bgcolor="#f5f5f5",
        font_color="#212121",
        heading="Execution Graph",
    )

    net.set_options(_PHYSICS_OPTIONS)

    # Add nodes.
    # PyVis quirk: when `group=` is supplied, PyVis's add_node() drops the
    # `color=` named argument entirely (the two code-paths in PyVis's
    # add_node are mutually exclusive for color vs group).  Work around this
    # by adding the node with group (for module clustering) and then writing
    # the color directly into the node's options dict afterward.
    for node_id, node_data in graph.nodes(data=True):
        task_name = node_data.get("task_name", node_id)
        status = node_data.get("status", "")
        module_name = node_data.get("module_name", "")

        net.add_node(
            node_id,
            label=task_name,
            title=make_node_title(node_data),
            group=module_name,      # clusters nodes from the same module
        )
        # Patch color onto the node after the fact so both group and color
        # are present in the serialized HTML.
        net.node_map[node_id]["color"] = status_to_color(status)

    # Add edges
    for src, dst, edge_data in graph.edges(data=True):
        net.add_edge(src, dst)

    return net


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------

def render_graph_html(
    graph: nx.DiGraph,
    output_path: str = "output/graph.html",
) -> str:
    """Render an execution graph to a standalone interactive HTML file.

    Creates the output directory if it does not exist.

    Parameters
    ----------
    graph:
        A directed graph produced by graph_builder.build_graph().
    output_path:
        Destination file path for the HTML output.
        Defaults to "output/graph.html".

    Returns
    -------
    str
        The absolute path to the generated HTML file.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    net = build_pyvis_network(graph)
    net.write_html(output_path, local=False, notebook=False, open_browser=False)

    return os.path.abspath(output_path)
