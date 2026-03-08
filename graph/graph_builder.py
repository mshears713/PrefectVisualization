"""
graph/graph_builder.py — Convert a runtime trace into a directed graph.

Overview
--------
This module takes the ordered list of TraceEvent dicts produced by the
instrumentation layer (PRD01) and builds a networkx.DiGraph where:

- every task execution becomes a unique node
- every parent-child execution relationship becomes a directed edge
- all trace metadata is preserved on nodes for downstream use

Node ID scheme
--------------
Node IDs follow the pattern  "<task_name>__<trace_index>",  e.g.:

    add_numbers__0
    multiply_numbers__1
    compute_pipeline__2

Using trace_index as the disambiguating suffix means:
- IDs are unique within a run even when the same function executes twice.
- IDs are deterministic for a given trace, so repeated calls with the same
  trace produce the same graph.

Edge strategy
-------------
Execution is synchronous, so parent-child relationships are fully captured
by the parent_task field on each TraceEvent.  The graph builder resolves a
parent task name to a specific node ID by locating the most recently *started*
(i.e. latest-indexed) node with that task name that has no outgoing edges to
the child yet.  Because synchronous children always complete before their
parent, the parent node is always the last node with the matching name whose
trace_index is *greater than* all its resolved children.

For MVP the simpler approach is used: build a name→node_id index as we
process events in trace_index order, and when a child needs its parent,
look up the node_id currently mapped to that parent name.  This works
correctly for all synchronous execution patterns tested in PRD01.

This module intentionally contains no visualization code.  It only constructs
and returns a graph object ready for PRD03.
"""

from __future__ import annotations

from typing import List, Optional

import networkx as nx

from schema import TraceEvent


# ---------------------------------------------------------------------------
# Node ID helpers
# ---------------------------------------------------------------------------

def make_node_id(task_name: str, trace_index: int) -> str:
    """Return a unique, human-readable node ID for a task execution.

    Parameters
    ----------
    task_name:
        The function name stored in the trace event.
    trace_index:
        The event's position in the runtime_trace list.
    """
    return f"{task_name}__{trace_index}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {
    "task_name",
    "task_description",
    "module_name",
    "parent_task",
    "trace_index",
    "start_time",
    "end_time",
    "duration_ms",
    "status",
    "input_preview",
    "output_preview",
    "input_length",
    "output_length",
    "error_message",
}


def validate_trace_event(event: TraceEvent) -> None:
    """Raise ValueError if a trace event is missing required fields.

    Parameters
    ----------
    event:
        A dict expected to conform to the TraceEvent schema.

    Raises
    ------
    ValueError
        If any required field is absent.
    """
    missing = _REQUIRED_FIELDS - set(event.keys())
    if missing:
        raise ValueError(
            f"Trace event for '{event.get('task_name', '?')}' is missing "
            f"required fields: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_graph(trace: List[TraceEvent]) -> nx.DiGraph:
    """Convert a runtime trace into a directed execution graph.

    Parameters
    ----------
    trace:
        Ordered list of TraceEvent dicts as returned by
        instrumentation.trace_collector.get_trace().

    Returns
    -------
    nx.DiGraph
        A directed graph where each node represents one task execution and
        each edge represents a parent → child execution relationship.

    Node attributes mirror all TraceEvent fields plus a ``node_id`` key for
    convenient reference.

    Raises
    ------
    ValueError
        If any event fails validation.
    """
    graph = nx.DiGraph()

    # Map task_name → node_id for the *active* (most recent) invocation seen
    # so far.  Because the trace is in completion order (children before
    # parents), we build this index while iterating and resolve parent edges
    # using a secondary pass.  To handle multiple invocations of the same
    # function we keep a list of node_ids per name and pick the right one.
    #
    # Two-pass approach:
    #   Pass 1 — add all nodes.
    #   Pass 2 — add edges using parent_task name → node_id resolution.

    # Pass 1: validate and add nodes
    for event in trace:
        validate_trace_event(event)
        node_id = make_node_id(event["task_name"], event["trace_index"])
        graph.add_node(
            node_id,
            node_id=node_id,
            task_name=event["task_name"],
            task_description=event["task_description"],
            module_name=event["module_name"],
            parent_task=event["parent_task"],
            trace_index=event["trace_index"],
            start_time=event["start_time"],
            end_time=event["end_time"],
            duration_ms=event["duration_ms"],
            status=event["status"],
            input_preview=event["input_preview"],
            output_preview=event["output_preview"],
            input_length=event["input_length"],
            output_length=event["output_length"],
            error_message=event["error_message"],
        )

    # Pass 2: build edges
    # For each child node that has a parent_task name, we need to find the
    # correct parent node_id.  In synchronous execution the parent is always
    # the node whose task_name matches parent_task AND whose trace_index is
    # *higher* than the child's (the parent completes after its children).
    # Among multiple candidates, the one with the *lowest* trace_index that
    # is still greater than the child's trace_index is the direct parent.
    for event in trace:
        if event["parent_task"] is None:
            continue

        child_id = make_node_id(event["task_name"], event["trace_index"])
        child_index = event["trace_index"]
        parent_name = event["parent_task"]

        # Collect all nodes with the matching parent task name.
        candidates = [
            (data["trace_index"], nid)
            for nid, data in graph.nodes(data=True)
            if data["task_name"] == parent_name
            and data["trace_index"] > child_index
        ]

        if not candidates:
            # Fallback: take any node with the matching name (handles edge
            # cases where trace ordering differs from expectations).
            candidates = [
                (data["trace_index"], nid)
                for nid, data in graph.nodes(data=True)
                if data["task_name"] == parent_name
            ]

        if candidates:
            # Pick the candidate with the smallest qualifying trace_index —
            # that is the innermost (closest) enclosing parent.
            _, parent_id = min(candidates, key=lambda x: x[0])
            graph.add_edge(parent_id, child_id, relationship="calls")

    return graph


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------

def list_graph_nodes(graph: nx.DiGraph) -> List[dict]:
    """Return a list of node attribute dicts, sorted by trace_index.

    Parameters
    ----------
    graph:
        A directed graph produced by build_graph().

    Returns
    -------
    List of node attribute dicts, each containing all metadata stored on
    the node, plus an implicit ordering by execution completion time.
    """
    nodes = [data for _, data in graph.nodes(data=True)]
    return sorted(nodes, key=lambda d: d.get("trace_index", 0))


def list_graph_edges(graph: nx.DiGraph) -> List[dict]:
    """Return a list of edge descriptor dicts.

    Each dict contains:
        from_node:  source node_id
        to_node:    target node_id
        relationship: edge attribute (always "calls" for now)

    Parameters
    ----------
    graph:
        A directed graph produced by build_graph().
    """
    return [
        {
            "from_node": u,
            "to_node": v,
            "relationship": data.get("relationship", "calls"),
        }
        for u, v, data in graph.edges(data=True)
    ]


def graph_debug_summary(graph: nx.DiGraph) -> dict:
    """Return a structured summary of the graph for quick inspection.

    Parameters
    ----------
    graph:
        A directed graph produced by build_graph().

    Returns
    -------
    dict with keys:
        num_nodes:      total node count
        num_edges:      total edge count
        root_nodes:     node_ids with no incoming edges (root tasks)
        nodes:          list of condensed per-node summaries
        edges:          list of (from_node, to_node) pairs
        module_counts:  {module_name: count} breakdown
        status_counts:  {status: count} breakdown
    """
    nodes = list_graph_nodes(graph)
    edges = list_graph_edges(graph)

    root_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]

    module_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    node_summaries = []

    for node_data in nodes:
        mod = node_data.get("module_name", "")
        sta = node_data.get("status", "")
        module_counts[mod] = module_counts.get(mod, 0) + 1
        status_counts[sta] = status_counts.get(sta, 0) + 1
        node_summaries.append(
            {
                "node_id": node_data["node_id"],
                "task_name": node_data["task_name"],
                "module_name": node_data["module_name"],
                "parent_task": node_data["parent_task"],
                "status": node_data["status"],
                "duration_ms": round(node_data["duration_ms"], 4),
                "trace_index": node_data["trace_index"],
            }
        )

    return {
        "num_nodes": graph.number_of_nodes(),
        "num_edges": graph.number_of_edges(),
        "root_nodes": sorted(root_nodes),
        "nodes": node_summaries,
        "edges": [(e["from_node"], e["to_node"]) for e in edges],
        "module_counts": module_counts,
        "status_counts": status_counts,
    }
