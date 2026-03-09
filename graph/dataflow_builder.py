"""
graph/dataflow_builder.py — Data-flow graph builder for Phase 2 (PRD 06).

Overview
--------
Phase 1 connected nodes based on execution parent-child relationships
(which function called which). This produced call-stack-style graphs.

Phase 2 changes the edge semantics: edges now represent **narrative pipeline
progression** — how an artifact moves through the system step by step.

Old model (Phase 1):
    pipeline → extract_text
    pipeline → clean_text
    pipeline → generate_summary

New model (Phase 2):
    load_pdf → extract_text → clean_text → generate_summary

Architecture
------------
The builder is organized into five clearly separated concerns:

1. Pipeline structure definition
   DEMO_PIPELINE_STAGES holds the explicit ordering of modules, tasks, and
   branch points for the Phase 2 PDF pipeline. This drives edge construction
   and is the authoritative source of narrative order.

2. Trace normalization  (normalize_trace)
   Validates incoming trace events and enriches them with Phase 2 fields
   (source_file, source_line_start, source_line_end) using None defaults
   when not present.

3. Pipeline ordering  (assign_pipeline_order)
   Maps each trace event to a (stage_index, step_order) position from the
   pipeline definition. Tasks not in the definition fall back to trace_index
   ordering so they are still included.

4. Node and edge construction
   build_dataflow_nodes — creates executed-task nodes preserving all Phase 1
       metadata, plus pipeline ordering and branch metadata.
   build_dataflow_edges — connects nodes in narrative pipeline order, adding
       branch metadata to transitions that cross a branch point.
   _add_alternate_nodes — creates lightweight placeholder nodes for branch
       options that did not execute, so visualizers can show "roads not taken".

5. Debug inspection  (graph_debug_summary)
   Returns a structured, human-readable dict for inspecting node ordering,
   edge list, and branch metadata without touching rendering code.

Edge metadata
-------------
Every edge carries at minimum:
    relationship: "pipeline_flow"

Edges that cross a branch point additionally carry:
    branch_group:   str  — e.g. "language_branch"
    branch_option:  str  — e.g. "english" or "non_english"
    branch_taken:   bool — True for the executed path, False for alternates

This means visualization layers never need to infer branch semantics from
graph topology — the information is explicit in edge attributes.

Node ID scheme
--------------
Executed tasks:    "<task_name>__<trace_index>"   e.g. "load_pdf__0"
Alternate tasks:   "<task_name>__alt"             e.g. "non_english_processing__alt"

The __trace_index suffix keeps IDs unique when the same function executes
multiple times. The __alt suffix marks placeholder nodes for alternate paths.

Determinism guarantee
---------------------
Given the same trace and the same DEMO_PIPELINE_STAGES definition, this
builder always produces the same graph structure. Ordering is driven by
explicit stage_index/step_order values, not by incidental dict iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

from schema import TraceEvent


# ---------------------------------------------------------------------------
# Pipeline structure data types
# ---------------------------------------------------------------------------

@dataclass
class BranchOption:
    """One option within a branch point.

    Attributes
    ----------
    name : str
        Short identifier, e.g. "english", "non_english", "chunked".
    tasks : list of str
        Task names that belong exclusively to this branch option. May be
        empty when the option immediately continues the main spine (e.g. the
        "english" option continues directly to the Text Processing stage).
    is_main_path : bool
        True  — this option is taken in the Phase 2 demo (executed path).
        False — this is an alternate path shown for narrative completeness.
    """
    name: str
    tasks: List[str]
    is_main_path: bool


@dataclass
class BranchPoint:
    """A decision step that splits the pipeline into multiple paths.

    Attributes
    ----------
    group : str
        Identifies the branch family, e.g. "language_branch".
    decision_task : str
        The task whose output drives the branching decision.
    options : list of BranchOption
        All possible paths from this decision point.
    taken_option : str
        The option name that is executed in the Phase 2 demo.
    """
    group: str
    decision_task: str
    options: List[BranchOption]
    taken_option: str


@dataclass
class PipelineStage:
    """One module/stage in the pipeline.

    Attributes
    ----------
    name : str
        Module name — should match the @module decorator value in the pipeline.
    stage_index : int
        Ordering position of this module (0 = first module in the pipeline).
    tasks : list of str
        Task names executed in this stage, in narrative order.
    branch : BranchPoint or None
        Optional branch point that occurs after this stage's tasks complete.
        The decision_task is always the last task in the tasks list that
        triggers the branching.
    """
    name: str
    stage_index: int
    tasks: List[str]
    branch: Optional[BranchPoint] = None


# ---------------------------------------------------------------------------
# Phase 2 Demo Pipeline Definition
#
# This is the explicit pipeline structure for the Phase 2 PDF processing demo.
# It drives all pipeline ordering and branch semantics in this builder.
# When a task's name appears here, it gets a deterministic position in the
# narrative graph. Tasks not listed here fall back to trace_index ordering.
# ---------------------------------------------------------------------------

DEMO_PIPELINE_STAGES: List[PipelineStage] = [
    PipelineStage(
        name="PDF Ingestion",
        stage_index=0,
        tasks=["load_pdf", "validate_pdf", "count_pages"],
    ),
    PipelineStage(
        name="Text Extraction",
        stage_index=1,
        tasks=["extract_text", "merge_pages", "detect_language"],
        # detect_language decides language; "english" continues to Text Processing.
        # "non_english" is the alternate path shown visually but not executed.
        branch=BranchPoint(
            group="language_branch",
            decision_task="detect_language",
            options=[
                BranchOption(
                    name="english",
                    tasks=[],           # Empty: english path continues directly on the spine
                    is_main_path=True,
                ),
                BranchOption(
                    name="non_english",
                    tasks=["non_english_processing"],
                    is_main_path=False,
                ),
            ],
            taken_option="english",
        ),
    ),
    PipelineStage(
        name="Text Processing",
        stage_index=2,
        tasks=["clean_text", "normalize_whitespace", "remove_headers"],
    ),
    PipelineStage(
        name="Chunking",
        stage_index=3,
        tasks=["compute_text_length", "choose_chunk_strategy"],
        # choose_chunk_strategy decides chunk path.
        # "chunked" leads to split_into_chunks then continues.
        # "single_pass" is the alternate shown visually but not executed.
        branch=BranchPoint(
            group="chunk_strategy",
            decision_task="choose_chunk_strategy",
            options=[
                BranchOption(
                    name="single_pass",
                    tasks=["single_pass_analysis"],
                    is_main_path=False,
                ),
                BranchOption(
                    name="chunked",
                    tasks=["split_into_chunks"],
                    is_main_path=True,
                ),
            ],
            taken_option="chunked",
        ),
    ),
    PipelineStage(
        name="LLM Analysis",
        stage_index=4,
        tasks=["analyze_chunks", "aggregate_results", "generate_summary"],
    ),
    PipelineStage(
        name="Structured Output",
        stage_index=5,
        tasks=["build_structured_result", "validate_schema", "export_result"],
    ),
]


# ---------------------------------------------------------------------------
# Derived lookup structures (computed once from DEMO_PIPELINE_STAGES)
#
# These are private to this module. Callers should use the public functions.
# ---------------------------------------------------------------------------

def _build_pipeline_index() -> Dict[str, Tuple[int, int, str, Optional[str], Optional[str]]]:
    """Map task_name → (stage_index, step_order, module_name, branch_group, branch_option).

    step_order is a global integer starting at 0 for load_pdf and incrementing
    with each task entry in the pipeline definition. It drives deterministic
    edge ordering within the graph.
    """
    index: Dict[str, Tuple[int, int, str, Optional[str], Optional[str]]] = {}
    step = 0
    for stage in DEMO_PIPELINE_STAGES:
        for task_name in stage.tasks:
            index[task_name] = (stage.stage_index, step, stage.name, None, None)
            step += 1
        if stage.branch:
            for option in stage.branch.options:
                for task_name in option.tasks:
                    index[task_name] = (
                        stage.stage_index,
                        step,
                        stage.name,
                        stage.branch.group,
                        option.name,
                    )
                    step += 1
    return index


def _build_main_spine() -> List[str]:
    """Return the ordered flat list of task names on the main narrative path.

    The main spine is the sequence of tasks in the Phase 2 demo's happy path:
    all stage tasks, plus main-path branch option tasks, in order.
    """
    spine: List[str] = []
    for stage in DEMO_PIPELINE_STAGES:
        spine.extend(stage.tasks)
        if stage.branch:
            for option in stage.branch.options:
                if option.is_main_path:
                    spine.extend(option.tasks)
    return spine


def _build_branch_transitions() -> Dict[str, BranchPoint]:
    """Return {decision_task_name: BranchPoint} for all branch decision tasks."""
    return {
        stage.branch.decision_task: stage.branch
        for stage in DEMO_PIPELINE_STAGES
        if stage.branch
    }


def _build_alternate_tasks() -> Dict[str, Tuple[str, str]]:
    """Return {task_name: (branch_group, branch_option)} for all alternate-path tasks."""
    alternates: Dict[str, Tuple[str, str]] = {}
    for stage in DEMO_PIPELINE_STAGES:
        if stage.branch:
            for option in stage.branch.options:
                if not option.is_main_path:
                    for task_name in option.tasks:
                        alternates[task_name] = (stage.branch.group, option.name)
    return alternates


def _build_spine_transition_map() -> Dict[Tuple[str, str], Tuple[str, str]]:
    """Map (from_task, to_task) → (branch_group, taken_option_name) for branch transitions.

    A branch transition is any consecutive spine pair where the source task
    is a branch decision task. These edges need branch metadata so visualizers
    can distinguish them from plain pipeline-flow edges.
    """
    transitions: Dict[Tuple[str, str], Tuple[str, str]] = {}
    branch_lookup = _build_branch_transitions()
    spine = _build_main_spine()
    for i in range(len(spine) - 1):
        from_task = spine[i]
        to_task = spine[i + 1]
        if from_task in branch_lookup:
            branch = branch_lookup[from_task]
            transitions[(from_task, to_task)] = (branch.group, branch.taken_option)
    return transitions


# Pre-compute once. These are read-only lookup structures.
_PIPELINE_INDEX = _build_pipeline_index()
_MAIN_SPINE = _build_main_spine()
_BRANCH_TRANSITIONS = _build_branch_transitions()
_ALTERNATE_TASKS = _build_alternate_tasks()
_SPINE_TRANSITION_MAP = _build_spine_transition_map()

# Sentinel stage index for tasks not in the pipeline definition.
# High value so unknown tasks sort after all known pipeline tasks.
_FALLBACK_STAGE = 999


# ---------------------------------------------------------------------------
# Node ID helpers
# ---------------------------------------------------------------------------

def _make_executed_node_id(task_name: str, trace_index: int) -> str:
    """Node ID for a task that ran in the trace. Matches Phase 1 scheme."""
    return f"{task_name}__{trace_index}"


def _make_alternate_node_id(task_name: str) -> str:
    """Node ID for a placeholder node representing a non-executed branch path."""
    return f"{task_name}__alt"


# ---------------------------------------------------------------------------
# Required trace fields (same set validated by Phase 1 graph_builder)
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


# ---------------------------------------------------------------------------
# Layer 1 — Trace normalization
# ---------------------------------------------------------------------------

def normalize_trace(trace: List[TraceEvent]) -> List[dict]:
    """Validate and enrich trace events for Phase 2 graph building.

    Parameters
    ----------
    trace :
        Raw list of TraceEvent dicts from the instrumentation layer.

    Returns
    -------
    List of enriched dicts that include Phase 2 fields with None defaults
    when not captured by the instrumentation layer:
        source_file, source_line_start, source_line_end

    Raises
    ------
    ValueError
        If any event is missing a required Phase 1 field.
    """
    normalized = []
    for event in trace:
        missing = _REQUIRED_FIELDS - set(event.keys())
        if missing:
            raise ValueError(
                f"Trace event for '{event.get('task_name', '?')}' is missing "
                f"required fields: {sorted(missing)}"
            )
        enriched = dict(event)
        # Add Phase 2 source-location fields with None defaults.
        # These are populated when the decorator captures inspect data.
        enriched.setdefault("source_file", None)
        enriched.setdefault("source_line_start", None)
        enriched.setdefault("source_line_end", None)
        normalized.append(enriched)
    return normalized


# ---------------------------------------------------------------------------
# Layer 2 — Pipeline ordering
# ---------------------------------------------------------------------------

def assign_pipeline_order(trace: List[dict]) -> List[dict]:
    """Augment each event with pipeline ordering metadata.

    Events whose task_name appears in DEMO_PIPELINE_STAGES receive an
    explicit (stage_index, step_order) from the pipeline definition.
    Unrecognized tasks fall back to trace_index-based ordering after all
    known pipeline tasks.

    The returned list is sorted by (stage_index, step_order, trace_index)
    so the ordering is fully deterministic.

    Parameters
    ----------
    trace :
        Normalized trace events (output of normalize_trace).

    Returns
    -------
    List of dicts, each extended with private keys:
        _stage_index, _step_order, _pipeline_module,
        _branch_group, _branch_option
    """
    enriched = []
    for event in trace:
        name = event["task_name"]
        if name in _PIPELINE_INDEX:
            stage_index, step_order, pipeline_module, branch_group, branch_option = (
                _PIPELINE_INDEX[name]
            )
        else:
            # Unknown task: place after all known pipeline steps.
            stage_index = _FALLBACK_STAGE
            step_order = event["trace_index"]
            pipeline_module = event.get("module_name", "")
            branch_group = None
            branch_option = None

        e = dict(event)
        e["_stage_index"] = stage_index
        e["_step_order"] = step_order
        e["_pipeline_module"] = pipeline_module
        e["_branch_group"] = branch_group
        e["_branch_option"] = branch_option
        enriched.append(e)

    # Sort deterministically: primary by pipeline position, secondary by
    # trace_index so repeated executions of the same task are stable.
    enriched.sort(key=lambda e: (e["_stage_index"], e["_step_order"], e["trace_index"]))
    return enriched


# ---------------------------------------------------------------------------
# Layer 3a — Node construction (executed tasks)
# ---------------------------------------------------------------------------

def build_dataflow_nodes(
    trace: List[dict],
    graph: nx.DiGraph,
) -> Dict[str, str]:
    """Add nodes to the graph for each executed trace event.

    All Phase 1 metadata fields are preserved exactly. Phase 2 ordering
    and branch fields are added as additional node attributes.

    Parameters
    ----------
    trace :
        Normalized events from normalize_trace.
    graph :
        The DiGraph to add nodes to (modified in place).

    Returns
    -------
    Dict mapping task_name → node_id for the *primary* (first pipeline-order)
    execution of each task. Used by build_dataflow_edges to resolve node IDs
    when constructing edges.
    """
    ordered = assign_pipeline_order(trace)
    task_to_node: Dict[str, str] = {}

    for event in ordered:
        task_name = event["task_name"]
        node_id = _make_executed_node_id(task_name, event["trace_index"])

        graph.add_node(
            node_id,
            # --- Identity ---
            node_id=node_id,
            task_name=task_name,
            # --- Phase 1 metadata (preserved) ---
            task_description=event.get("task_description", ""),
            module_name=event.get("module_name", ""),
            parent_task=event.get("parent_task"),
            trace_index=event["trace_index"],
            start_time=event.get("start_time", 0.0),
            end_time=event.get("end_time", 0.0),
            duration_ms=event.get("duration_ms", 0.0),
            status=event.get("status", "unknown"),
            input_preview=event.get("input_preview", ""),
            output_preview=event.get("output_preview", ""),
            input_length=event.get("input_length", 0),
            output_length=event.get("output_length", 0),
            error_message=event.get("error_message"),
            # --- Phase 2 metadata ---
            stage_index=event["_stage_index"],
            step_order=event["_step_order"],
            pipeline_module=event["_pipeline_module"],
            branch_group=event["_branch_group"],
            branch_option=event["_branch_option"],
            source_file=event.get("source_file"),
            source_line_start=event.get("source_line_start"),
            source_line_end=event.get("source_line_end"),
            is_alternate=False,
        )

        # Track the first (primary) node for each task name. Because events
        # are sorted by (stage_index, step_order, trace_index), the first
        # occurrence is the canonical pipeline execution of that task.
        if task_name not in task_to_node:
            task_to_node[task_name] = node_id

    return task_to_node


# ---------------------------------------------------------------------------
# Layer 3b — Node construction (alternate branch placeholders)
# ---------------------------------------------------------------------------

def _add_alternate_nodes(
    graph: nx.DiGraph,
    task_to_node: Dict[str, str],
) -> Dict[str, str]:
    """Add placeholder nodes for branch options that did not execute.

    These nodes represent "roads not taken" in the pipeline. They allow
    visualization layers to render alternate paths (e.g. as dotted edges)
    without requiring UI code to know the pipeline structure.

    A placeholder is only created when the alternate task did NOT appear
    in the executed trace (i.e. is not already in task_to_node).

    Parameters
    ----------
    graph :
        The DiGraph to add placeholder nodes to (modified in place).
    task_to_node :
        Map of task names already added as executed nodes.

    Returns
    -------
    Dict mapping task_name → node_id for the created alternate nodes.
    """
    alt_task_to_node: Dict[str, str] = {}

    for task_name, (branch_group, branch_option) in _ALTERNATE_TASKS.items():
        if task_name in task_to_node:
            # Task actually ran — no placeholder needed.
            continue

        node_id = _make_alternate_node_id(task_name)
        graph.add_node(
            node_id,
            node_id=node_id,
            task_name=task_name,
            # Minimal metadata — this task did not actually run.
            task_description=f"[Alternate path — not executed]",
            module_name="",
            parent_task=None,
            trace_index=-1,
            start_time=0.0,
            end_time=0.0,
            duration_ms=0.0,
            status="not_executed",
            input_preview="",
            output_preview="",
            input_length=0,
            output_length=0,
            error_message=None,
            stage_index=0,
            step_order=0,
            pipeline_module="",
            branch_group=branch_group,
            branch_option=branch_option,
            source_file=None,
            source_line_start=None,
            source_line_end=None,
            is_alternate=True,
        )
        alt_task_to_node[task_name] = node_id

    return alt_task_to_node


# ---------------------------------------------------------------------------
# Layer 4 — Edge construction
# ---------------------------------------------------------------------------

def build_dataflow_edges(
    graph: nx.DiGraph,
    task_to_node: Dict[str, str],
    alt_task_to_node: Dict[str, str],
) -> None:
    """Add pipeline-progression edges to the graph.

    Two kinds of edges are created:

    1. Main spine edges
       Connect consecutive *executed* tasks in pipeline narrative order.
       When the transition crosses a branch decision point, the edge is
       annotated with branch_group, branch_option, and branch_taken=True.

    2. Alternate branch edges
       Connect each branch decision task to the start of every non-executed
       branch option. These edges are annotated with branch_taken=False.

    Parameters
    ----------
    graph :
        The DiGraph to add edges to (modified in place).
    task_to_node :
        {task_name: node_id} for executed tasks.
    alt_task_to_node :
        {task_name: node_id} for alternate-path placeholder nodes.
    """
    all_nodes = {**task_to_node, **alt_task_to_node}

    # --- Main spine edges ---
    # Walk the canonical spine in order. Skip any spine tasks that were not
    # executed (not in task_to_node). Connect consecutive executed spine tasks.
    executed_spine = [t for t in _MAIN_SPINE if t in task_to_node]

    for i in range(len(executed_spine) - 1):
        from_task = executed_spine[i]
        to_task = executed_spine[i + 1]
        from_node = task_to_node[from_task]
        to_node = task_to_node[to_task]

        edge_attrs: dict = {"relationship": "pipeline_flow"}

        # Annotate transitions that cross a branch decision point.
        branch_info = _SPINE_TRANSITION_MAP.get((from_task, to_task))
        if branch_info:
            branch_group, taken_option = branch_info
            edge_attrs.update({
                "branch_group": branch_group,
                "branch_option": taken_option,
                "branch_taken": True,
            })

        graph.add_edge(from_node, to_node, **edge_attrs)

    # --- Alternate branch edges ---
    # For each branch point whose decision task executed, add edges to all
    # non-main-path options (whether they ran or not).
    for stage in DEMO_PIPELINE_STAGES:
        if not stage.branch:
            continue

        branch = stage.branch
        decision_task = branch.decision_task

        if decision_task not in task_to_node:
            # Decision task did not run; skip alternate edges for this branch.
            continue

        decision_node = task_to_node[decision_task]

        for option in branch.options:
            if option.is_main_path:
                # Main path edge is already included in the spine walk above.
                continue

            if not option.tasks:
                # Empty option list — no alternate node to connect to.
                continue

            # Connect decision node to the first task of each alternate option.
            first_alt_task = option.tasks[0]
            if first_alt_task in all_nodes:
                alt_node = all_nodes[first_alt_task]
                graph.add_edge(
                    decision_node,
                    alt_node,
                    relationship="pipeline_flow",
                    branch_group=branch.group,
                    branch_option=option.name,
                    branch_taken=False,
                )

            # If the alternate option has multiple tasks, connect them linearly.
            for j in range(1, len(option.tasks)):
                prev_task = option.tasks[j - 1]
                curr_task = option.tasks[j]
                if prev_task in all_nodes and curr_task in all_nodes:
                    graph.add_edge(
                        all_nodes[prev_task],
                        all_nodes[curr_task],
                        relationship="pipeline_flow",
                        branch_group=branch.group,
                        branch_option=option.name,
                        branch_taken=False,
                    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_dataflow_graph(trace: List[TraceEvent]) -> nx.DiGraph:
    """Build a data-flow narrative graph from a runtime trace.

    This is the primary public API for Phase 2 graph construction.

    Parameters
    ----------
    trace :
        Ordered list of TraceEvent dicts from instrumentation.trace_collector.

    Returns
    -------
    nx.DiGraph where:
        - each node represents one task execution (or alternate placeholder)
        - edges represent narrative pipeline progression, not call hierarchy
        - branch transitions carry explicit branch_group/branch_option/branch_taken
        - all Phase 1 node metadata is preserved
        - alternate (non-executed) branch paths appear as placeholder nodes
    """
    # Step 1 — Validate and enrich trace events.
    normalized = normalize_trace(trace)

    # Step 2 — Create the graph.
    graph = nx.DiGraph()

    # Step 3 — Add executed-task nodes.
    task_to_node = build_dataflow_nodes(normalized, graph)

    # Step 4 — Add alternate branch placeholder nodes.
    alt_task_to_node = _add_alternate_nodes(graph, task_to_node)

    # Step 5 — Add pipeline-progression edges.
    build_dataflow_edges(graph, task_to_node, alt_task_to_node)

    return graph


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------

def list_graph_nodes(graph: nx.DiGraph) -> List[dict]:
    """Return node attribute dicts sorted by (stage_index, step_order, trace_index).

    Alternate nodes (is_alternate=True) appear after executed nodes.
    """
    nodes = [data for _, data in graph.nodes(data=True)]
    return sorted(
        nodes,
        key=lambda d: (
            1 if d.get("is_alternate") else 0,
            d.get("stage_index", 999),
            d.get("step_order", 999),
            d.get("trace_index", 999),
        ),
    )


def list_graph_edges(graph: nx.DiGraph) -> List[dict]:
    """Return edge descriptor dicts with all edge attributes."""
    return [
        {
            "from_node": u,
            "to_node": v,
            "relationship": data.get("relationship", "pipeline_flow"),
            "branch_group": data.get("branch_group"),
            "branch_option": data.get("branch_option"),
            "branch_taken": data.get("branch_taken"),
        }
        for u, v, data in graph.edges(data=True)
    ]


def graph_debug_summary(graph: nx.DiGraph) -> dict:
    """Return a structured summary of a data-flow graph for quick inspection.

    Useful for debugging and for Test 5 (determinism check). A developer
    should be able to read this output and say:
    "The PDF was loaded, text was extracted, language was detected, the text
    was cleaned, chunking strategy was chosen, analysis ran, and a structured
    result was produced."

    Returns
    -------
    dict with keys:
        num_nodes       — total node count (executed + alternate placeholders)
        num_edges       — total edge count
        nodes           — list of condensed node summaries in pipeline order
        edges           — list of (from_node, to_node) pairs
        branch_edges    — list of branch-annotated edge dicts
        pipeline_flow   — ordered list of executed task names (the narrative)
        stage_counts    — {module_name: node_count}
        status_counts   — {status: node_count}
    """
    nodes = list_graph_nodes(graph)
    edges = list_graph_edges(graph)

    node_summaries = []
    stage_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}

    for node_data in nodes:
        mod = node_data.get("module_name") or node_data.get("pipeline_module", "")
        sta = node_data.get("status", "unknown")
        stage_counts[mod] = stage_counts.get(mod, 0) + 1
        status_counts[sta] = status_counts.get(sta, 0) + 1
        node_summaries.append({
            "node_id": node_data["node_id"],
            "task_name": node_data["task_name"],
            "module_name": node_data.get("module_name", ""),
            "stage_index": node_data.get("stage_index", -1),
            "step_order": node_data.get("step_order", -1),
            "status": node_data.get("status", "unknown"),
            "duration_ms": round(node_data.get("duration_ms", 0.0), 4),
            "trace_index": node_data.get("trace_index", -1),
            "branch_group": node_data.get("branch_group"),
            "branch_option": node_data.get("branch_option"),
            "is_alternate": node_data.get("is_alternate", False),
        })

    branch_edges = [e for e in edges if e.get("branch_group") is not None]

    # The narrative flow: only executed (non-alternate) nodes in pipeline order.
    pipeline_flow = [
        n["task_name"] for n in node_summaries if not n["is_alternate"]
    ]

    return {
        "num_nodes": graph.number_of_nodes(),
        "num_edges": graph.number_of_edges(),
        "nodes": node_summaries,
        "edges": [(e["from_node"], e["to_node"]) for e in edges],
        "branch_edges": branch_edges,
        "pipeline_flow": pipeline_flow,
        "stage_counts": stage_counts,
        "status_counts": status_counts,
    }
