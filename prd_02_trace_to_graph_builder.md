# PRD 02 — Trace-to-Graph Builder

## Title

**Trace-to-Graph Builder for Runtime Visual Debugging**

## Document Purpose

This PRD defines the second implementation milestone for the Visual Debugging for AI-Generated Python Code project.

This milestone takes the structured runtime trace produced by the instrumentation core and converts it into a directed graph representation that can later be visualized.

If PRD 01 creates the flight recorder, this PRD creates the map.

The goal is to transform execution records into a clean graph structure that preserves:

- task identity
- module grouping
- parent-child execution relationships
- durations
- validation and status metadata
- summarized data previews

This milestone should produce a graph object that is stable, inspectable, and ready for downstream visualization.

---

## Objective

Build a graph construction layer that consumes a structured in-memory runtime trace and produces a directed graph suitable for:

- module-aware visualization
- node inspection
- downstream HTML rendering
- future graph summarization and debugging workflows

The graph builder must turn runtime execution truth into a machine-readable topology without relying on any LLM inference.

---

## Why This Milestone Comes Second

Once the instrumentation layer works, the next question is:

> Can the recorded execution data be turned into a useful structural representation?

This must happen before visualization.

If the graph model is weak or inconsistent, the visual layer will become a cosmetic shell over bad structure. That would be software theater, and the gods of debugging despise theater without substance.

So this milestone focuses on correctness of structure first, appearance later.

---

## Scope

This milestone includes:

- consuming trace event records from PRD 01
- constructing a directed graph using NetworkX
- generating nodes for executed tasks
- generating edges for execution relationships
- attaching task metadata to graph nodes
- carrying module grouping metadata into the graph
- supporting multiple executed tasks in one run
- supporting nested synchronous parent-child task calls
- producing a graph object and graph inspection helpers
- basic graph summaries for development/debugging

This milestone does **not** include:

- HTML rendering
- PyVis configuration
- FastAPI endpoints
- PDF upload handling
- LLM summarization
- async concurrency modeling
- persistent run history
- visual clustering or subgraph rendering
- loop aggregation across repeated executions unless trivially easy

---

## Inputs and Outputs

### Input

The graph builder consumes a runtime trace from PRD 01.

Expected input shape:

- ordered list of trace event dictionaries
- each event corresponds to one completed task execution
- each event includes task metadata and execution metadata

The graph builder must assume the trace is already valid enough to process, but should fail clearly if required fields are missing.

### Output

The graph builder returns a directed graph object, preferably a `networkx.DiGraph`, where:

- each executed task becomes a node
- each parent-child execution relationship becomes an edge
- each node carries structured metadata
- the graph is inspectable programmatically before any rendering layer exists

---

## Product Requirements

### Functional Requirement 1 — Use NetworkX Directed Graph

The system must construct a directed graph using NetworkX.

#### Requirements

- Use `networkx.DiGraph` unless there is a compelling reason to use another graph type
- Direction must represent execution flow
- Graph must be easy to inspect from Python during development
- Graph must be straightforward to hand off to PyVis in the next milestone

#### Rationale

Directed edges align naturally with “task A triggered task B”.

---

### Functional Requirement 2 — Create Task Execution Nodes

Each trace event must produce one graph node representing a task execution instance.

#### Requirements

Each node should include, at minimum:

- unique node id
- task name
- task description
- module name
- parent task name, if any
- duration
- status
- input preview
- output preview
- input length
- output length
- error message if applicable

#### Important modeling decision

For MVP, **each task execution should become its own node**, not just each task definition.

This is the correct default because the graph is intended to reflect what happened during a specific run.

#### Example

If `add_numbers()` executes twice in one run, the graph may contain two distinct nodes, such as:

- `add_numbers__1`
- `add_numbers__2`

This preserves runtime truth.

---

### Functional Requirement 3 — Generate Stable Node IDs

Each graph node must have a unique identifier.

#### Recommended approach

Use a deterministic per-run node id based on trace order, such as:

- `task_name__0`
- `task_name__1`
- `task_name__2`

or an equivalent scheme.

#### Requirements

- Node ids must be unique within a run
- Node ids must be easy to inspect during debugging
- Node ids do not need to be globally unique across all future runs in MVP

---

### Functional Requirement 4 — Preserve Module Metadata

The graph must carry module metadata forward so the visualization layer can later group tasks by module.

#### Requirements

Every node must include:

- `module_name`

Optional helpful fields:

- `module_slug`
- `module_group`
- `module_color_hint` (future-facing only if convenient)

#### Important note

This milestone does **not** need to visually group nodes yet. It only needs to preserve the metadata required for grouping later.

---

### Functional Requirement 5 — Build Execution Edges

The graph builder must create directed edges that reflect parent-child execution relationships captured in the runtime trace.

#### Requirements

If a trace event includes a parent task relationship, the graph should create an edge:

```text
parent_task_execution -> child_task_execution
```

#### Caveat

Because the runtime trace records task names and not necessarily unique parent execution ids unless added in PRD 01, the graph builder must choose a practical MVP strategy for mapping parent relationships.

#### Recommended approach

Prefer one of the following:

1. If PRD 01 already records a parent execution id, use it directly  
2. Otherwise, infer parent node based on active execution order and nearest matching parent in the trace

Option 1 is better if available.

#### Requirements

- Edge direction must reflect the flow of execution
- Nested synchronous calls must produce correct parent-child edges
- Root tasks with no parent should have no incoming execution edge unless a synthetic root node is later introduced

---

### Functional Requirement 6 — Preserve Execution Order

The graph builder must preserve execution order in a way that is inspectable.

#### Recommended options

At minimum, store one of:

- `trace_index`
- `execution_index`

as node metadata.

This will help later with:

- debugging graph correctness
- generating ordered summaries
- rendering tooltips
- future LLM summarization

---

### Functional Requirement 7 — Support Success and Error States

The graph must carry task status cleanly into node metadata.

#### Requirements

Status values should remain explicit:

- `success`
- `error`

If later validation layers introduce:

- `warning`
- `invalid`
- `suspicious`

the graph model should not prevent that extension.

#### Error handling

Error nodes must preserve:

- status
- error message
- duration if available
- input preview

This allows later visual layers to highlight broken steps.

---

### Functional Requirement 8 — Graph Inspection Helpers

The system should provide simple helper functions for inspecting the graph during development.

#### Recommended helpers

- `build_graph(trace) -> nx.DiGraph`
- `graph_to_debug_summary(graph) -> dict | str`
- `list_graph_nodes(graph)`
- `list_graph_edges(graph)`

These helpers do not need to be fancy. They exist to make milestone testing easy.

---

## Data Model Guidance

### Recommended node attributes

Each node should carry fields like:

```python
{
    "node_id": "add_numbers__0",
    "task_name": "add_numbers",
    "task_description": "Add two numbers to compute an intermediate value",
    "module_name": "Math Operations",
    "parent_task": "compute_pipeline",
    "trace_index": 1,
    "duration_ms": 4.2,
    "status": "success",
    "input_preview": "length=7, head='(2, 3)', tail='(2, 3)'",
    "output_preview": "length=1, head='5', tail='5'",
    "input_length": 7,
    "output_length": 1,
    "error_message": None,
}
```

The exact schema may vary, but it must be consistent and visualization-friendly.

### Recommended edge attributes

Edges can start simple.

At minimum:

```python
{
    "relationship": "calls"
}
```

Optional future-facing fields if convenient:

- `parent_task_name`
- `child_task_name`
- `edge_type`
- `trace_index_from`
- `trace_index_to`

Do not over-engineer edges in this milestone.

---

## Graph Modeling Decisions

### Decision 1 — Runtime truth over static compression

The graph should represent **executions**, not merely function definitions.

Why:

- the tool is about what happened during a run
- repeated execution may matter
- failures can happen on one execution but not another
- durations may differ across calls

### Decision 2 — Two-level semantic model remains intact

Even though the graph contains only task execution nodes at this stage, the conceptual structure remains:

- modules as grouping metadata
- tasks as executable steps

Actual visual module containers will come later.

### Decision 3 — No synthetic module nodes yet

Do **not** create separate module nodes in this milestone unless absolutely necessary.

Why:

- they are not needed to prove graph correctness
- they complicate the graph model early
- visualization can group by metadata later

### Decision 4 — No synthetic root node yet

Do not add a root node unless testing clearly benefits from it.

A plain set of root task nodes with no incoming edges is acceptable.

---

## Technical Design Guidance

### Recommended file structure for this milestone

```text
graph/
  graph_builder.py
```

### Likely responsibilities of `graph_builder.py`

Should include:

- validation of trace shape
- node id assignment
- graph construction
- edge construction
- helper functions for debugging/inspection

### Suggested primary functions

Likely candidates:

- `build_graph(trace: list[dict]) -> nx.DiGraph`
- `validate_trace_event(event: dict) -> None`
- `make_node_id(event: dict, index: int) -> str`
- `graph_debug_summary(graph: nx.DiGraph) -> dict`

These exact names can vary, but the separation of concerns should remain clean.

---

## Parent-Child Mapping Strategy

This is the trickiest part of the milestone and deserves explicit treatment.

### Preferred approach

If the instrumentation layer can provide a unique parent execution reference, use it.

If not, use trace order plus parent task name to infer the most likely parent node in a deterministic way.

### MVP assumption

Because execution is synchronous in MVP, trace order should make parent mapping manageable.

#### Example

Trace order:

1. `compute_pipeline`
2. `add_numbers` (parent: compute_pipeline)
3. `multiply_numbers` (parent: compute_pipeline)

This should create edges:

- `compute_pipeline__0 -> add_numbers__1`
- `compute_pipeline__0 -> multiply_numbers__2`

### Important requirement

The implementation must document the chosen strategy clearly so later milestones do not have to reverse-engineer edge semantics.

---

## Non-Functional Requirements

### Correctness

- graph structure must accurately reflect trace relationships
- repeated runs with same trace should produce same graph structure
- node metadata must be preserved faithfully

### Readability

- implementation should be straightforward to inspect
- helper outputs should make debugging easy
- avoid unnecessary abstractions

### Extensibility

The graph model should leave room for future work such as:

- module grouping in visualization
- validation color mapping
- loop aggregation
- run history
- summary generation

But do not implement those features here unless they are trivial and do not increase risk.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. A valid runtime trace can be converted into a `networkx.DiGraph`
2. Every trace event becomes a node with consistent metadata
3. Parent-child relationships become directed edges
4. Root tasks appear as nodes with no incoming execution edge
5. Repeated task executions in one run produce distinct node ids
6. Error executions remain in the graph with error metadata
7. Module metadata is preserved on nodes for future grouping
8. A developer can inspect the graph in Python and understand the flow without visualization

---

## Test Plan

### Test 1 — Sequential trace becomes graph

Use a simple trace corresponding to:

- `add_numbers`
- `multiply_numbers`

#### Expected result

- two nodes
- zero or one edge depending on whether one calls the other
- metadata preserved
- node ids unique

---

### Test 2 — Nested execution graph

Use a trace corresponding to:

- `compute_pipeline`
- `add_numbers`
- `multiply_numbers`

where `compute_pipeline` is parent to both child tasks.

#### Expected result

- three nodes
- two edges from `compute_pipeline` to each child
- trace order visible in metadata

---

### Test 3 — Mixed data metadata preserved

Use a trace where one node outputs a number and another outputs a string.

#### Expected result

- both nodes present
- previews and lengths preserved correctly as metadata
- no graph construction errors from mixed types

---

### Test 4 — Error node appears correctly

Use a trace where one task status is `error`.

#### Expected result

- node still exists
- status is `error`
- error message present
- graph still builds without crashing

---

### Test 5 — Repeated task execution

Use a trace where the same task name appears twice in one run.

#### Expected result

- two distinct nodes created
- node ids unique
- metadata tied to the correct execution order

---

### Test 6 — Debug summary helper

Run graph builder and debug summary helper on a known trace.

#### Expected result

Developer can quickly inspect:

- number of nodes
- number of edges
- node list
- edge list
- module distribution if helpful

---

## Deliverables

At the end of this milestone, the repo should contain:

- a graph builder module
- a primary function that converts a trace into a directed graph
- unique node ids for executed tasks
- preserved metadata on nodes
- constructed execution edges
- helper functions for graph inspection/debugging
- small test data or deterministic demo traces proving correctness

---

## Definition of Done

This milestone is done when a developer can:

1. run a small decorated Python program,
2. inspect the runtime trace,
3. pass that trace into the graph builder,
4. receive a directed graph object,
5. and clearly understand the execution structure from nodes and edges alone.

At that point, the system has crossed an important threshold:

it no longer merely records events; it understands them structurally.

---

## Implementation Cautions

Do not drift into the visualization milestone prematurely.

Avoid:

- styling decisions
- HTML generation
- color mapping logic beyond carrying status metadata
- frontend-oriented hacks
- premature “module box” rendering logic

This milestone is about **graph correctness**, not graph beauty.

Beauty can arrive later after correctness has stopped tripping over its own shoelaces.
