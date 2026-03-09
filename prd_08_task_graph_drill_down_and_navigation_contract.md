# PRD 08 — Task Graph Drill-Down and Navigation Contract

## Title

**Task Graph Drill-Down and Navigation Contract for Phase 2 Narrative Visualization**

## Document Purpose

This PRD defines the third implementation milestone of Phase 2 for the Visual Debugging for AI-Generated Python Code project.

PRD 06 refactored the graph semantics from call-trace to data-flow.

PRD 07 introduced the module overview graph, which gives the user a clean six-stage pipeline view.

PRD 08 defines the **task-level graph system** and the **navigation contract** between module overview and module task detail.

This milestone is where the two-layer architecture becomes real:

- the user starts at the module graph
- the user clicks a module
- the system renders the task graph for that module
- the user can inspect task-level execution within that module

This PRD does not yet implement every final UI flourish of Phase 2. It establishes the data model, rendering contract, and interaction flow needed so later PRDs can add square nodes, rich hover states, task panels, and styling without fighting ambiguity.

---

## Objective

Build the task graph generation and module-to-task drill-down mechanism that allows a user to move from the high-level module overview into a focused task graph for a selected module.

The task graph should:

- show only tasks that belong to the selected module
- preserve data-flow order between those tasks
- preserve branching where relevant inside the module
- preserve task metadata needed for hover and click interactions later
- support deterministic rendering and route-level navigation

This milestone should make the two-level architecture operational, even if the visual styling is still basic.

---

## Why This Milestone Comes After PRD 07

PRD 07 introduced aggregation.
PRD 08 introduces decomposition.

Once users can see the six-module overview, the next requirement is obvious:

> What happened inside one module?

Without drill-down, the module graph is only a summary.
Without the module graph, the task graph is too detailed.

The product depends on having both.

This PRD makes the relationship between those two layers explicit and stable.

---

## Scope

This milestone includes:

- building task graphs scoped to a selected module
- defining how task graphs are retrieved/generated
- preserving task data-flow semantics from PRD 06
- preserving task ordering inside the module
- preserving branch semantics inside the module
- defining the navigation contract from module view to task view
- defining how the selected module is represented in API or rendering calls
- adding tests that prove module drill-down works correctly

This milestone does **not** include:

- final square-node UI styling
- duration-based width scaling
- top banner summary
- rich task click detail panel
- PDF pipeline implementation
- frontend app polish
- IDE click-through
- loop aggregation
- advanced animation

This milestone is about making the two-level graph architecture functionally real.

---

## Core User Story

A user opens the Phase 2 module overview graph and sees:

PDF Ingestion → Text Extraction → Text Processing → Chunking → LLM Analysis → Structured Output

The user clicks **Text Extraction**.

The system renders a task graph for that module showing something like:

extract_text → merge_pages → detect_language

The user now understands what happened inside the selected stage.

This is the core interaction pattern this PRD must support.

---

## Product Requirements

### Functional Requirement 1 — Task Graph Generation by Module

The system must be able to generate a task graph for a selected module.

#### Requirements

Given a module identifier or module name, the graph builder must:

- filter tasks belonging to that module
- preserve only relevant nodes
- preserve edges between tasks inside that module
- retain task metadata

#### Input examples

- module_name = "Text Extraction"
- module_id = "text_extraction"

The exact parameter can vary, but it must be deterministic and consistent.

#### Output

A graph containing only tasks inside the selected module.

---

### Functional Requirement 2 — Preserve Intra-Module Data Flow

The task graph must preserve the data-flow semantics established in PRD 06.

This means task edges should represent narrative progression inside the module.

#### Example

For Text Extraction, the graph should read like:

extract_text  
→ merge_pages  
→ detect_language

Not like:

module_root → every task

And not like a parent-child trace unless that also matches the narrative data flow.

---

### Functional Requirement 3 — Preserve Branching Inside Task Graph

If a selected module contains branch logic, the task graph must preserve that structure.

#### Example

Inside Text Extraction:

detect_language  
→ english_processing_path  
→ non_english_processing_path

For the demo, the English path may be the executed one and Non-English the alternate one.

#### Requirements

The task graph must preserve the metadata needed for later rendering to distinguish:
- executed path
- alternate path

This milestone does not need to finalize the exact edge styling, but it must carry the semantics.

---

### Functional Requirement 4 — Stable Task Ordering

Tasks within a module must be presented in deterministic order.

Preferred ordering logic:
- explicit task_order or stage metadata if available
- otherwise trace index fallback

The resulting graph must be stable between runs for the same pipeline.

This is important because small differences in node order make narrative graphs feel unreliable.

---

### Functional Requirement 5 — Navigation Contract from Module Graph to Task Graph

The system must define a stable navigation contract.

This contract may later be implemented through FastAPI routes, generated HTML files, or server-side render calls.

#### Recommended approach

Support something like:

- module graph view
- selected module identifier
- task graph render request

Example conceptual routes or calls:

- /graph/modules
- /graph/tasks?module=text_extraction

The exact implementation may vary, but the contract must be clearly documented and internally consistent.

#### Requirements

- module nodes must include enough metadata to resolve their corresponding task graph
- task graph generation must accept that identifier without ambiguity
- later PRDs should not need to guess how navigation works

---

### Functional Requirement 6 — Back Navigation Contract

The task graph view must support a clear route or metadata contract for returning to the module overview.

This may be as simple as:
- a route back to module graph
- a metadata field
- a known “overview graph” identifier

The visual button or UI element may be implemented later, but the navigation logic must be planned now.

---

### Functional Requirement 7 — Task Graph Metadata Preservation

Each task node in the task graph must preserve metadata needed for later UI layers.

At minimum, preserve:

- task_name
- task_description
- module_name
- duration_ms
- status
- input_preview
- output_preview
- input_length
- output_length
- error_message
- source_file
- source_line_start
- source_line_end
- library_used if available

This PRD does not need to implement the final click panel, but it must ensure the data survives.

---

### Functional Requirement 8 — Module Summary Availability in Task View

When a user enters a task graph, the system should be able to provide module-level context for that view.

This context may include:

- module_name
- module_description
- total_duration_ms
- input_summary
- output_summary
- task_count

This information will be useful later for:
- task-view headers
- back-navigation breadcrumbs
- context panels

This does not need to be visually rendered yet, but the data contract should exist.

---

### Functional Requirement 9 — Isolation of Selected Module

The selected module task graph should not include unrelated tasks from other modules.

#### Example

Clicking Text Extraction should not show:
- clean_text
- split_into_chunks
- generate_summary

unless the selected module explicitly contains them.

This is important for cognitive clarity.

---

## Technical Design Guidance

### Recommended file structure

graph/
  module_graph_builder.py
  task_graph_builder.py

If the existing graph_builder.py remains the shared lower-level engine, that is acceptable, but the module and task graph builders should now have clearly separated responsibilities.

### Suggested responsibilities

#### module_graph_builder.py
- build module nodes
- build module edges
- expose module drill-down identifiers

#### task_graph_builder.py
- filter tasks by module
- construct module-scoped task graph
- preserve branch metadata
- provide selected-module context payload

### Suggested helper functions

Possible function shapes:

- build_task_graph_for_module(task_graph, module_name)
- get_module_context(task_graph, module_name)
- get_module_task_nodes(task_graph, module_name)
- get_module_task_edges(task_graph, module_name)
- make_task_graph_payload(module_name)

Exact names can vary, but the responsibilities must remain clear.

---

## Graph Payload Contract

It is strongly recommended that the task graph view be returned as a structured payload, not just as a raw graph object.

Example conceptual payload:

- module context
- selected module id
- task graph
- back-navigation reference

This payload does not need to be a Pydantic model yet unless that improves clarity.
A TypedDict, dataclass, or simple documented dictionary shape is sufficient.

This will make later FastAPI and rendering integration much easier.

---

## Interaction Model Contract

PRD 08 should define the behavior, even if some presentation details are implemented later.

### Module View
- hover = module summary
- click = request task graph for module

### Task View
- hover = quick task metadata
- click = later task detail panel
- back action = return to module view

This contract should be documented in code comments or payload structures so later UI PRDs do not drift.

---

## Branch Semantics in Task View

Task graphs must support both:
- executed branch edges
- alternate branch edges

The graph data model should provide enough information for later rendering to style them differently.

Recommended metadata examples:

- edge_taken: true/false
- edge_type: normal / alternate / branch
- branch_group
- branch_option

Exact names are flexible, but they must be consistent.

Do not leave this to visualization-only heuristics.

---

## Deterministic IDs and References

Selected modules and tasks should have stable identifiers.

### Module IDs
Recommended:
- normalized slug from module name

Examples:
- PDF Ingestion → pdf_ingestion
- Text Extraction → text_extraction

### Task IDs
Continue using deterministic task IDs from existing graph logic.

The navigation system should not rely on labels alone.

---

## Backward Compatibility

This PRD should extend the current architecture, not destabilize it.

The system should remain compatible with:
- existing trace collection
- data-flow graph builder
- existing tests where relevant
- future visualization PRDs

Avoid changing fundamental schema names unless necessary.

---

## Non-Functional Requirements

### Clarity
The implementation should make the two-layer design obvious in code.

### Separation of Concerns
Do not mix navigation logic with rendering logic unless absolutely necessary.

### Determinism
Selecting a given module should always yield the same task graph structure for the same run.

### Extensibility
This PRD should make it easy later to add:
- square node styling
- detail panels
- top-banner summaries
- route-based graph switching

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. A selected module can be used to generate a task-only graph
2. The task graph preserves data-flow edges inside that module
3. Unrelated tasks are excluded
4. Branch-aware metadata is preserved where applicable
5. The system exposes a stable contract for moving from module graph to task graph
6. The system exposes enough context to support returning back to the module graph
7. Task metadata needed for later hover/click UI is preserved
8. The task graph is deterministic and inspectable

---

## Test Plan

### Test 1 — Task graph filtering

Select the Text Extraction module.

#### Expected result

The graph contains only:
- extract_text
- merge_pages
- detect_language
- branch-related extraction tasks if defined

No tasks from Text Processing, Chunking, LLM Analysis, or Structured Output should appear.

---

### Test 2 — Intra-module edge preservation

Select a module with multiple ordered tasks.

#### Expected result

Task edges preserve the narrative progression inside that module.

---

### Test 3 — Branch preservation

Select a module containing a branch.

#### Expected result

Task graph preserves both:
- taken path
- alternate path metadata

---

### Test 4 — Module context payload

Request a task graph for a module.

#### Expected result

The returned structure includes:
- module name
- module description
- duration
- input summary
- output summary
- task count

---

### Test 5 — Deterministic navigation identifier

Select the same module twice.

#### Expected result

The same identifier yields the same task graph structure and context.

---

## Deliverables

At the end of this milestone, the repo should contain:

- task_graph_builder implementation
- navigation-aware payload or contract
- module-scoped graph generation logic
- tests validating task graph filtering and branch preservation
- at least one example task graph generated from the demo pipeline

---

## Definition of Done

This milestone is done when the two-layer architecture actually works in structure, even before the visual polish is added.

A developer should be able to:

1. generate a module overview graph
2. select one module
3. generate a task graph for that module
4. inspect that graph and see only the relevant internal steps

At that point, the product has crossed from “one graph with too much going on” into a real drill-down architecture.

That is a major usability threshold.

---

## Implementation Cautions

Avoid these traps:

- making task graph generation depend on UI code
- leaking unrelated tasks into module views
- hiding branch semantics only in visualization
- changing identifiers between module view and task view
- tightly coupling rendering and graph building
- overengineering a generic navigation framework

Stay focused on the narrow goal:

Create a clean, deterministic, module-to-task drill-down contract that future UI layers can build on confidently.
