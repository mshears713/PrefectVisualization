"""
graph/module_graph_builder.py — Module overview graph builder for Phase 2 (PRD 07).

Overview
--------
PRD 06 produced a task-level data-flow graph where individual functions are
nodes and edges represent narrative pipeline progression.

PRD 07 introduces a second, coarser abstraction layer: the **module graph**.

Each node in the module graph represents a logical pipeline stage made up of
multiple tasks. Instead of showing every function, the user first sees:

    PDF Ingestion → Text Extraction → Text Processing →
    Chunking → LLM Analysis → Structured Output

This is the entry point for the Phase 2 visualization. Clicking a module
will later open the task-level graph for that module (PRD 08).

Architecture
------------
The builder is organized into four responsibilities:

1. Task grouping  (_group_tasks_by_module)
   Partitions task nodes from the PRD-06 graph by module_name. Alternate
   placeholder nodes are excluded — they belong to task-level rendering.

2. Metadata aggregation  (aggregate_module_metadata)
   Computes status, total_duration_ms, input_summary, output_summary, and
   branch_detected from the ordered set of tasks in each module.

3. Module node construction  (build_module_nodes)
   Creates one graph node per module with all aggregated metadata plus a
   list of task_ids for later drill-down navigation.

4. Module edge construction  (build_module_edges)
   Connects module nodes in stage_index order, producing a single linear
   progression edge between each consecutive pair of modules.

Module Node ID scheme
---------------------
Module IDs are stable and position-based:

    "module__{stage_index}"   e.g. "module__0", "module__1"

This keeps IDs independent of module name spelling and safe for graph
libraries that use string node IDs as dict keys.

Status aggregation rules
------------------------
    error   — at least one task in the module has status "error"
    warning — at least one task has status "warning" (and none are errors)
    success — all tasks have status "success"

Input / output summary rules
-----------------------------
    input_summary  — input_preview of the first task (by step_order)
    output_summary — output_preview of the last task (by step_order)

Branch awareness
----------------
If any task in the module carries a non-None branch_group, the module node
is flagged with branch_detected=True. This allows future UI enhancements to
indicate branching at the module level without expanding internal branches
in the overview graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _group_tasks_by_module(
    task_graph: nx.DiGraph,
) -> Dict[str, List[Tuple[str, dict]]]:
    """Partition task nodes into groups keyed by module_name.

    Alternate placeholder nodes (is_alternate=True) are excluded; they are
    only meaningful at the task-level graph layer.

    Tasks whose module_name is empty or None are grouped under the key
    "_unknown" so they are still represented rather than silently dropped.

    Returns
    -------
    Dict mapping module_name → list of (node_id, node_data) pairs.
    """
    groups: Dict[str, List[Tuple[str, dict]]] = {}
    for node_id, data in task_graph.nodes(data=True):
        if data.get("is_alternate"):
            continue
        module_name: str = data.get("module_name") or "_unknown"
        groups.setdefault(module_name, []).append((node_id, data))
    return groups


def _order_module_tasks(
    tasks: List[Tuple[str, dict]],
) -> List[Tuple[str, dict]]:
    """Sort tasks within a module in narrative pipeline order.

    Primary key: step_order (from the PRD-06 pipeline definition).
    Secondary key: trace_index (execution order, used as tiebreaker for
    tasks not in the pipeline definition).
    """
    return sorted(
        tasks,
        key=lambda item: (
            item[1].get("step_order", 999),
            item[1].get("trace_index", 999),
        ),
    )


# ---------------------------------------------------------------------------
# Metadata aggregation
# ---------------------------------------------------------------------------

def aggregate_module_metadata(tasks: List[Tuple[str, dict]]) -> dict:
    """Compute aggregated metadata for a list of task nodes.

    Parameters
    ----------
    tasks :
        List of (node_id, node_data) pairs for tasks in the same module.
        Need not be pre-sorted; this function sorts them internally.

    Returns
    -------
    dict with keys:
        stage_index       — lowest stage_index found across tasks
        status            — "error" | "warning" | "success"
        total_duration_ms — sum of all task durations
        input_summary     — input_preview from the first task
        output_summary    — output_preview from the last task
        branch_detected   — True if any task belongs to a branch group
        task_ids          — ordered list of node_id strings
        task_count        — len(task_ids)
    """
    ordered = _order_module_tasks(tasks)

    # Status: error beats warning beats success.
    status = "success"
    for _, data in ordered:
        task_status = data.get("status", "success")
        if task_status == "error":
            status = "error"
            break
        if task_status == "warning" and status == "success":
            status = "warning"

    total_duration = sum(data.get("duration_ms", 0.0) for _, data in ordered)

    # stage_index: use the minimum across the group.
    # Tasks in the same module should all share the same stage_index, but
    # taking the minimum is a safe fallback if decorators differ.
    stage_index = min(
        (data.get("stage_index", 999) for _, data in ordered),
        default=999,
    )

    # Input: from the first task in pipeline order.
    first_data = ordered[0][1]
    input_summary = first_data.get("input_preview", "")

    # Output: from the last task in pipeline order.
    last_data = ordered[-1][1]
    output_summary = last_data.get("output_preview", "")

    # Branch detection: any task has a non-None branch_group.
    branch_detected = any(
        data.get("branch_group") is not None for _, data in ordered
    )

    task_ids = [node_id for node_id, _ in ordered]

    return {
        "stage_index": stage_index,
        "status": status,
        "total_duration_ms": total_duration,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "branch_detected": branch_detected,
        "task_ids": task_ids,
        "task_count": len(task_ids),
    }


# ---------------------------------------------------------------------------
# Node construction
# ---------------------------------------------------------------------------

def _has_branch_edges(task_ids: List[str], task_graph: nx.DiGraph) -> bool:
    """Return True if any task in task_ids has an outgoing branch-annotated edge.

    Branch decision tasks (e.g. detect_language, choose_chunk_strategy) do not
    carry branch_group on their own node attributes — the branch_group lives on
    branch-option nodes and on edges. We therefore inspect outgoing edges to
    detect branching at the module level.
    """
    for node_id in task_ids:
        for _, _, edge_data in task_graph.out_edges(node_id, data=True):
            if edge_data.get("branch_group") is not None:
                return True
    return False


def build_module_nodes(task_graph: nx.DiGraph) -> nx.DiGraph:
    """Create a module graph with one node per module_name group.

    Consumes the PRD-06 task graph and produces a new DiGraph where each
    node represents an aggregated pipeline module.

    Parameters
    ----------
    task_graph :
        Data-flow task graph from build_dataflow_graph() (PRD 06).

    Returns
    -------
    nx.DiGraph with module nodes only — no edges yet. Call build_module_edges
    to connect them.
    """
    module_graph = nx.DiGraph()
    groups = _group_tasks_by_module(task_graph)

    for module_name, tasks in groups.items():
        meta = aggregate_module_metadata(tasks)
        module_id = f"module__{meta['stage_index']}"

        # Branch detection: check node attributes AND outgoing task edges.
        # Node-level branch_group is only set on branch-option tasks.
        # Decision tasks (e.g. detect_language) reveal branching via their edges.
        branch_detected = meta["branch_detected"] or _has_branch_edges(
            meta["task_ids"], task_graph
        )

        module_graph.add_node(
            module_id,
            # --- Identity ---
            module_id=module_id,
            module_name=module_name,
            module_description=f"{module_name} — {meta['task_count']} task(s)",
            # --- Ordering ---
            stage_index=meta["stage_index"],
            # --- Aggregated runtime metadata ---
            status=meta["status"],
            total_duration_ms=meta["total_duration_ms"],
            # --- Data summaries ---
            input_summary=meta["input_summary"],
            output_summary=meta["output_summary"],
            # --- Task references (enables drill-down in later PRDs) ---
            task_ids=meta["task_ids"],
            task_count=meta["task_count"],
            # --- Branch flag ---
            branch_detected=branch_detected,
        )

    return module_graph


# ---------------------------------------------------------------------------
# Edge construction
# ---------------------------------------------------------------------------

def build_module_edges(module_graph: nx.DiGraph) -> None:
    """Add pipeline-progression edges between module nodes.

    Edges are built by sorting module nodes on stage_index and connecting
    each consecutive pair. This produces the expected linear narrative:

        PDF Ingestion → Text Extraction → Text Processing → …

    For document size decision branching (Text Processing → Chunking):
    - Insert a conceptual "Document Size Decision" node
    - Create two outgoing edges: one to LLM Analysis (small doc), one to Chunking (large doc)
    - The large doc path (through Chunking) is marked as branch_taken=true

    Guarantees:
    - No duplicate edges (checked with has_edge before adding).
    - Deterministic ordering (sorted on stage_index, then module_name as
      tiebreaker so behavior is stable even if two stages share an index).
    - Branching structure is preserved for visualization.

    Parameters
    ----------
    module_graph :
        Module graph produced by build_module_nodes (modified in place).
    """
    ordered = sorted(
        module_graph.nodes(data=True),
        key=lambda item: (item[1].get("stage_index", 999), item[1].get("module_name", "")),
    )

    # Build initial edge list, detecting the Text Processing → Chunking transition
    edges_to_add = []
    text_processing_idx = None
    chunking_idx = None
    lllm_analysis_idx = None

    for i, (node_id, data) in enumerate(ordered):
        module_name = data.get("module_name", "")
        if module_name == "Text Processing":
            text_processing_idx = i
        elif module_name == "Chunking":
            chunking_idx = i
        elif module_name == "LLM Analysis":
            lllm_analysis_idx = i

    # If we have Text Processing → Chunking → LLM Analysis, inject decision node
    if (
        text_processing_idx is not None
        and chunking_idx is not None
        and text_processing_idx + 1 == chunking_idx
        and lllm_analysis_idx is not None
    ):
        # Add document size decision node
        decision_node_id = "decision__document_size"
        module_graph.add_node(
            decision_node_id,
            # --- Identity ---
            module_id=decision_node_id,
            module_name="Document Size Decision",
            module_description="Routing decision: document size",
            # --- Ordering (fractional between Text Processing and Chunking) ---
            stage_index=2.5,  # Between stage 2 (Text Processing) and stage 3 (Chunking)
            # --- Status/Metadata ---
            status="success",
            total_duration_ms=0.0,
            input_summary="",
            output_summary="",
            task_ids=[],
            task_count=0,
            # --- Decision node marker ---
            is_decision_node=True,
            branch_detected=True,
        )

        # Build edge list with branching
        for i in range(len(ordered) - 1):
            from_id = ordered[i][0]
            to_id = ordered[i + 1][0]
            from_data = ordered[i][1]
            to_data = ordered[i + 1][1]
            from_name = from_data.get("module_name", "")
            to_name = to_data.get("module_name", "")

            # Text Processing → Document Size Decision
            if from_name == "Text Processing" and to_name == "Chunking":
                edges_to_add.append({
                    "from_id": from_id,
                    "to_id": decision_node_id,
                    "edge_type": "pipeline",
                })
                # Document Size Decision → LLM Analysis (small doc, not taken)
                edges_to_add.append({
                    "from_id": decision_node_id,
                    "to_id": ordered[lllm_analysis_idx][0],
                    "edge_type": "branch",
                    "branch_type": "size_decision",
                    "branch_label": "small_doc",
                    "branch_taken": False,
                })
                # Document Size Decision → Chunking (large doc, taken)
                edges_to_add.append({
                    "from_id": decision_node_id,
                    "to_id": to_id,
                    "edge_type": "branch",
                    "branch_type": "size_decision",
                    "branch_label": "large_doc",
                    "branch_taken": True,
                })
            # Chunking → LLM Analysis (already routed via decision, skip in linear loop)
            elif from_name == "Chunking" and to_name == "LLM Analysis":
                # This edge will be added separately to maintain the large-doc path
                edges_to_add.append({
                    "from_id": from_id,
                    "to_id": to_id,
                    "edge_type": "branch",
                    "branch_type": "size_decision",
                    "branch_label": "large_doc",
                    "branch_taken": True,
                })
            # All other consecutive module pairs
            else:
                edges_to_add.append({
                    "from_id": from_id,
                    "to_id": to_id,
                    "edge_type": "pipeline",
                })

    else:
        # No branching detected; use original linear logic
        for i in range(len(ordered) - 1):
            from_id = ordered[i][0]
            to_id = ordered[i + 1][0]
            edges_to_add.append({
                "from_id": from_id,
                "to_id": to_id,
                "edge_type": "pipeline",
            })

    # Add all edges to the graph
    for edge_spec in edges_to_add:
        from_id = edge_spec.pop("from_id")
        to_id = edge_spec.pop("to_id")
        if not module_graph.has_edge(from_id, to_id):
            module_graph.add_edge(from_id, to_id, **edge_spec)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def create_module_graph(task_graph: nx.DiGraph) -> nx.DiGraph:
    """Build the module overview graph from a PRD-06 data-flow task graph.

    This is the primary public API for PRD 07.

    Parameters
    ----------
    task_graph :
        Data-flow task graph produced by build_dataflow_graph() in
        graph.dataflow_builder (PRD 06).

    Returns
    -------
    nx.DiGraph where:
        - each node represents one pipeline module (aggregated task group)
        - edges represent stage-to-stage progression
        - node attributes include status, duration, I/O summaries, task_ids
    """
    module_graph = build_module_nodes(task_graph)
    build_module_edges(module_graph)
    return module_graph


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------

def list_module_nodes(module_graph: nx.DiGraph) -> List[dict]:
    """Return module node attribute dicts sorted by stage_index."""
    return sorted(
        (data for _, data in module_graph.nodes(data=True)),
        key=lambda d: (d.get("stage_index", 999), d.get("module_name", "")),
    )


def module_graph_debug_summary(module_graph: nx.DiGraph) -> dict:
    """Return a structured summary of the module graph for inspection.

    Returns
    -------
    dict with keys:
        num_modules     — total module count
        num_edges       — total edge count
        modules         — list of condensed module summaries in stage order
        edges           — list of (from_module_name, to_module_name) pairs
        pipeline        — ordered list of module names (the high-level narrative)
        status_counts   — {status: count}
        total_duration_ms — sum across all modules
    """
    ordered_nodes = list_module_nodes(module_graph)

    module_summaries = []
    status_counts: Dict[str, int] = {}
    grand_total_ms = 0.0

    for data in ordered_nodes:
        sta = data.get("status", "unknown")
        status_counts[sta] = status_counts.get(sta, 0) + 1
        dur = data.get("total_duration_ms", 0.0)
        grand_total_ms += dur
        module_summaries.append({
            "module_id": data["module_id"],
            "module_name": data["module_name"],
            "stage_index": data["stage_index"],
            "status": sta,
            "total_duration_ms": round(dur, 4),
            "task_count": data.get("task_count", 0),
            "task_ids": data.get("task_ids", []),
            "input_summary": data.get("input_summary", ""),
            "output_summary": data.get("output_summary", ""),
            "branch_detected": data.get("branch_detected", False),
        })

    # Build edge list using module names for readability.
    id_to_name = {
        nid: data.get("module_name", nid)
        for nid, data in module_graph.nodes(data=True)
    }
    edges = [
        (id_to_name.get(u, u), id_to_name.get(v, v))
        for u, v in module_graph.edges()
    ]

    pipeline = [m["module_name"] for m in module_summaries]

    return {
        "num_modules": module_graph.number_of_nodes(),
        "num_edges": module_graph.number_of_edges(),
        "modules": module_summaries,
        "edges": edges,
        "pipeline": pipeline,
        "status_counts": status_counts,
        "total_duration_ms": round(grand_total_ms, 4),
    }
