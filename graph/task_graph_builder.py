"""
graph/task_graph_builder.py — Task-level drill-down graph builder (PRD 08).

Overview
--------
PRD 06 built a full data-flow task graph for an entire pipeline run.
PRD 07 aggregated that graph into a module overview.

PRD 08 adds the other direction: **decomposition**.

When a user selects a module in the overview, the system generates a
task graph containing only the tasks that belong to that module, with all
intra-module data-flow edges, branch metadata, and task details preserved.

This creates the two-layer navigation architecture:

    Module Overview         (PRD 07)
        │
        │  user selects "Text Extraction"
        ▼
    Task Graph              (PRD 08)
        extract_text → merge_pages → detect_language
                                   ↘ non_english_processing  [alternate]

Architecture
------------
Four responsibilities:

1. ID normalisation  (module_name_to_id)
   Converts a human-readable module name ("Text Extraction") to a stable
   slug ("text_extraction") used as a navigation identifier. Slugs are
   lower-case and use underscores, matching the convention in PRD 08.

2. Task filtering  (get_module_task_nodes)
   Extracts all task nodes — both executed and alternate placeholders —
   whose module_name (or branch membership) belongs to the requested module.

3. Edge extraction  (get_module_task_edges)
   Copies every edge whose source AND target both belong to the filtered
   node set. Edges crossing into other modules are dropped. All edge
   attributes (including branch_group, branch_option, branch_taken) are
   preserved intact.

4. Context payload  (get_module_context)
   Returns a lightweight dict describing the module — used later for
   view headers, breadcrumbs, and back-navigation.

Navigation contract
-------------------
The canonical drill-down call is:

    result = build_task_graph_for_module(task_graph, module_name)

result is a TaskGraphPayload dataclass containing:

    result.graph          — nx.DiGraph, tasks for the selected module only
    result.context        — dict with module-level summary metadata
    result.module_id      — stable slug for routing ("text_extraction")
    result.back_ref       — identifier for returning to module overview ("module_overview")

Slugs are derived deterministically from module names so route-based
navigation never has to guess identifiers.

Alternate (non-executed) branch nodes
--------------------------------------
Alternate placeholder nodes are included in the task graph when their
branch_group belongs to a decision task inside the selected module.
For example, selecting "Text Extraction" includes non_english_processing__alt
because detect_language (the decision task) lives in that module.

This ensures the task view can render "roads not taken" without fetching
additional data.

Module isolation
----------------
Tasks from other modules are never included, even if they are reachable via
edges from tasks inside the selected module. Cross-module edges are dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import networkx as nx


# ---------------------------------------------------------------------------
# Navigation identifier helpers
# ---------------------------------------------------------------------------

def module_name_to_id(module_name: str) -> str:
    """Convert a module name to a stable navigation slug.

    Examples
    --------
    "Text Extraction" → "text_extraction"
    "LLM Analysis"    → "llm_analysis"
    "PDF Ingestion"   → "pdf_ingestion"

    Rules: lower-case, spaces and hyphens replaced with underscores,
    non-alphanumeric characters stripped.
    """
    slug = module_name.lower()
    slug = re.sub(r"[\s\-]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug


# The stable identifier for the module overview layer, used as back_ref.
MODULE_OVERVIEW_REF = "module_overview"


# ---------------------------------------------------------------------------
# Task filtering
# ---------------------------------------------------------------------------

def get_module_task_nodes(
    task_graph: nx.DiGraph,
    module_name: str,
) -> Dict[str, dict]:
    """Return all task nodes that belong to the given module.

    Includes:
    - Executed tasks whose module_name matches exactly.
    - Alternate placeholder nodes whose branch_group connects them to a
      decision task inside this module (so the task view can render
      alternate paths without needing to look outside the module).

    Excludes:
    - Tasks from other modules.

    Parameters
    ----------
    task_graph :
        Full data-flow task graph from PRD 06.
    module_name :
        Human-readable module name, e.g. "Text Extraction".

    Returns
    -------
    Dict mapping node_id → node_data for every task in the module.
    """
    # First pass: collect all executed task node IDs for this module.
    executed_ids: set[str] = set()
    for node_id, data in task_graph.nodes(data=True):
        if data.get("is_alternate"):
            continue
        if data.get("module_name") == module_name:
            executed_ids.add(node_id)

    # Second pass: find alternate placeholder nodes that are reached via
    # a branch edge from a decision task inside this module.
    alternate_ids: set[str] = set()
    for node_id in executed_ids:
        for _, target, edge_data in task_graph.out_edges(node_id, data=True):
            target_data = task_graph.nodes[target]
            if target_data.get("is_alternate") and edge_data.get("branch_group"):
                alternate_ids.add(target)

    # Build the combined result dict.
    all_ids = executed_ids | alternate_ids
    return {
        nid: dict(task_graph.nodes[nid])
        for nid in all_ids
    }


def get_module_task_edges(
    task_graph: nx.DiGraph,
    node_ids: set[str],
) -> List[tuple]:
    """Return edges whose source AND target are both inside node_ids.

    Edges that cross into other modules are dropped. All edge attributes
    (relationship, branch_group, branch_option, branch_taken) are preserved.

    Parameters
    ----------
    task_graph :
        Full data-flow task graph from PRD 06.
    node_ids :
        Set of node IDs belonging to the selected module.

    Returns
    -------
    List of (source, target, attrs_dict) triples.
    """
    return [
        (u, v, dict(data))
        for u, v, data in task_graph.edges(data=True)
        if u in node_ids and v in node_ids
    ]


# ---------------------------------------------------------------------------
# Module context payload
# ---------------------------------------------------------------------------

def get_module_context(
    task_graph: nx.DiGraph,
    module_name: str,
) -> dict:
    """Build the module-level context dict for a task graph view.

    This information is used later for view headers, breadcrumb navigation,
    and context panels. It does not depend on the module graph (PRD 07) so
    it can be computed from the task graph alone.

    Parameters
    ----------
    task_graph :
        Full data-flow task graph from PRD 06.
    module_name :
        Human-readable module name.

    Returns
    -------
    dict with keys:
        module_name        — human-readable name
        module_id          — stable slug for routing
        module_description — brief auto-generated description
        task_count         — number of executed tasks in the module
        total_duration_ms  — sum of task durations
        input_summary      — input_preview of the first task (by step_order)
        output_summary     — output_preview of the last task (by step_order)
        back_ref           — identifier to return to module overview
    """
    # Collect executed tasks for this module, sorted by pipeline position.
    tasks = sorted(
        [
            data
            for _, data in task_graph.nodes(data=True)
            if not data.get("is_alternate") and data.get("module_name") == module_name
        ],
        key=lambda d: (d.get("step_order", 999), d.get("trace_index", 999)),
    )

    if not tasks:
        return {
            "module_name": module_name,
            "module_id": module_name_to_id(module_name),
            "module_description": module_name,
            "task_count": 0,
            "total_duration_ms": 0.0,
            "input_summary": "",
            "output_summary": "",
            "back_ref": MODULE_OVERVIEW_REF,
        }

    total_duration = sum(t.get("duration_ms", 0.0) for t in tasks)
    input_summary = tasks[0].get("input_preview", "")
    output_summary = tasks[-1].get("output_preview", "")
    task_count = len(tasks)

    return {
        "module_name": module_name,
        "module_id": module_name_to_id(module_name),
        "module_description": f"{module_name} — {task_count} task(s)",
        "task_count": task_count,
        "total_duration_ms": total_duration,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "back_ref": MODULE_OVERVIEW_REF,
    }


# ---------------------------------------------------------------------------
# Task graph payload
# ---------------------------------------------------------------------------

@dataclass
class TaskGraphPayload:
    """The complete result of a module drill-down request.

    This is the stable navigation contract between the module view (PRD 07)
    and the task view (PRD 08 and later).

    Attributes
    ----------
    graph : nx.DiGraph
        Task graph scoped to the selected module. Contains only the tasks
        and intra-module edges for that module, plus any alternate branch
        placeholder nodes reachable from a decision task inside the module.
    context : dict
        Module-level summary metadata for headers, breadcrumbs, and panels.
        Keys: module_name, module_id, module_description, task_count,
              total_duration_ms, input_summary, output_summary, back_ref.
    module_name : str
        Human-readable module name ("Text Extraction").
    module_id : str
        Stable navigation slug ("text_extraction"). Safe for use in routes
        like /graph/tasks?module=text_extraction.
    back_ref : str
        Identifier for returning to the module overview. Currently always
        MODULE_OVERVIEW_REF = "module_overview".
    """
    graph: nx.DiGraph
    context: dict
    module_name: str
    module_id: str
    back_ref: str = MODULE_OVERVIEW_REF


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_task_graph_for_module(
    task_graph: nx.DiGraph,
    module_name: str,
) -> TaskGraphPayload:
    """Generate a task graph scoped to a single pipeline module.

    This is the primary public API for PRD 08. It implements the navigation
    step: user selects a module → system returns the focused task graph.

    Parameters
    ----------
    task_graph :
        Full data-flow task graph from build_dataflow_graph() (PRD 06).
    module_name :
        Human-readable module name to drill into, e.g. "Text Extraction".

    Returns
    -------
    TaskGraphPayload containing:
        .graph      — module-scoped nx.DiGraph
        .context    — module summary dict (for headers and back-navigation)
        .module_name — the requested module name
        .module_id  — stable slug for routing
        .back_ref   — reference to return to module overview

    Raises
    ------
    ValueError
        If module_name does not match any task in the task graph.
    """
    # Validate module_name exists in the graph.
    known_modules = {
        data.get("module_name")
        for _, data in task_graph.nodes(data=True)
        if not data.get("is_alternate") and data.get("module_name")
    }
    if module_name not in known_modules:
        raise ValueError(
            f"Module {module_name!r} not found in task graph. "
            f"Available modules: {sorted(known_modules)}"
        )

    # Step 1 — filter nodes.
    node_data = get_module_task_nodes(task_graph, module_name)
    node_ids = set(node_data.keys())

    # Step 2 — filter edges.
    edges = get_module_task_edges(task_graph, node_ids)

    # Step 3 — build the scoped graph.
    scoped_graph = nx.DiGraph()
    for node_id, attrs in node_data.items():
        scoped_graph.add_node(node_id, **attrs)
    for u, v, attrs in edges:
        scoped_graph.add_edge(u, v, **attrs)

    # Step 4 — build the context payload.
    context = get_module_context(task_graph, module_name)
    module_id = module_name_to_id(module_name)

    return TaskGraphPayload(
        graph=scoped_graph,
        context=context,
        module_name=module_name,
        module_id=module_id,
    )


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------

def list_task_graph_nodes(scoped_graph: nx.DiGraph) -> List[dict]:
    """Return node attribute dicts sorted by (step_order, trace_index).

    Alternate nodes appear after executed nodes.
    """
    return sorted(
        (data for _, data in scoped_graph.nodes(data=True)),
        key=lambda d: (
            1 if d.get("is_alternate") else 0,
            d.get("step_order", 999),
            d.get("trace_index", 999),
        ),
    )


def task_graph_debug_summary(payload: TaskGraphPayload) -> dict:
    """Return a structured, human-readable summary of a TaskGraphPayload.

    Useful for debugging, testing, and printing demo output without
    touching any rendering code.

    Returns
    -------
    dict with keys:
        module_name      — selected module
        module_id        — stable slug
        back_ref         — how to return to overview
        context          — full module context dict
        num_nodes        — total node count (executed + alternates)
        num_edges        — total edge count
        task_flow        — ordered list of executed task names
        nodes            — condensed per-node summaries
        edges            — list of (from_node, to_node) pairs
        branch_edges     — list of branch-annotated edge dicts
    """
    g = payload.graph
    ordered_nodes = list_task_graph_nodes(g)

    node_summaries = []
    for data in ordered_nodes:
        node_summaries.append({
            "node_id": data["node_id"],
            "task_name": data["task_name"],
            "status": data.get("status", "unknown"),
            "duration_ms": round(data.get("duration_ms", 0.0), 4),
            "trace_index": data.get("trace_index", -1),
            "step_order": data.get("step_order", -1),
            "branch_group": data.get("branch_group"),
            "branch_option": data.get("branch_option"),
            "is_alternate": data.get("is_alternate", False),
            "input_preview": data.get("input_preview", ""),
            "output_preview": data.get("output_preview", ""),
        })

    edge_pairs = []
    branch_edges = []
    for u, v, data in g.edges(data=True):
        edge_pairs.append((u, v))
        if data.get("branch_group") is not None:
            branch_edges.append({
                "from_node": u,
                "to_node": v,
                "branch_group": data["branch_group"],
                "branch_option": data["branch_option"],
                "branch_taken": data.get("branch_taken"),
            })

    task_flow = [
        n["task_name"] for n in node_summaries if not n["is_alternate"]
    ]

    return {
        "module_name": payload.module_name,
        "module_id": payload.module_id,
        "back_ref": payload.back_ref,
        "context": payload.context,
        "num_nodes": g.number_of_nodes(),
        "num_edges": g.number_of_edges(),
        "task_flow": task_flow,
        "nodes": node_summaries,
        "edges": edge_pairs,
        "branch_edges": branch_edges,
    }
