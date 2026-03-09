# PRD 06 — Data-Flow Graph Builder Refactor

## Title

**Data-Flow Graph Builder Refactor for Narrative Pipeline Visualization**

## Document Purpose

This PRD defines the first implementation milestone of Phase 2 for the Visual Debugging for AI-Generated Python Code project.

Phase 1 proved that the system could collect runtime trace events and turn them into a graph.

Phase 2 changes the meaning of that graph.

This milestone refactors the graph builder so that the graph is no longer primarily a call-trace graph. Instead, it becomes a **data-flow graph** that tells the story of how artifacts move through a pipeline.

This is the structural foundation for every later Phase 2 improvement:
- module overview graph
- task drill-down
- left-to-right pipeline layout
- branching visibility
- PDF pipeline readability
- top-banner story summary

If this milestone is wrong, every later view will still look like a wiring diagram.

---

## Objective

Refactor the graph-building logic so that task nodes are connected according to **data flow and pipeline progression**, not just parent-child call relationships.

The graph builder must support a narrative like:

PDF Ingestion  
→ Text Extraction  
→ Text Processing  
→ Chunking  
→ LLM Analysis  
→ Structured Output  

At the task level, the same principle applies:

load_pdf  
→ extract_text  
→ detect_language  
→ clean_text  
→ choose_chunk_strategy  
→ split_into_chunks  
→ analyze_chunks  
→ generate_summary  

The resulting graph should communicate:
- what entered the system
- what each step produced
- what step used that output next
- where branching occurred

---

## Why This Milestone Comes First in Phase 2

The current prototype already has:
- instrumentation
- trace records
- graph rendering
- synthetic pipeline
- FastAPI delivery

But the current edges mostly reflect execution context.

That means the graph tells the user:
“which function ran inside which function”

instead of:
“what happened to the document”

That is the wrong semantic layer for the story we want.

Before modules, boxes, banners, PDF tasks, or drill-down interactions can work well, the edge logic must change.

This PRD therefore updates the most foundational meaning in the entire system.

---

## Scope

This milestone includes:

- refactoring graph construction semantics
- defining what counts as a producer and consumer step
- building graph edges based on pipeline progression / data handoff
- preserving trace metadata while changing edge semantics
- supporting linear narrative flows
- supporting explicit branch points
- supporting alternate, non-executed branches as metadata where needed
- adding tests and demo verification for the new semantics

This milestone does **not** include:

- module overview rendering
- task drill-down interaction
- square nodes
- width scaling
- PDF pipeline implementation
- top-banner summary
- click panels
- frontend work
- loop aggregation

This milestone only changes how graph structure is built.

---

## Key Conceptual Change

### Old model
Call-trace or parent-child graph.

Example:

pipeline → extract_text  
pipeline → clean_text  
pipeline → summarize_text  

Useful for debugging stack relationships, but poor for storytelling.

### New model
Data-flow / pipeline progression graph.

Example:

load_pdf → extract_text → clean_text → chunk_text → analyze_chunks → generate_summary  

Useful for understanding transformation and system behavior.

### Important clarification
This milestone does **not** discard runtime truth.

It uses trace order, task metadata, and pipeline structure to derive the most useful explanatory graph.

This is still grounded in actual execution.

---

## Core Design Decision

The graph builder must distinguish between two kinds of relationships:

### 1. Execution Context
Which function called which.

### 2. Narrative Data Flow
Which step produced the artifact consumed by the next meaningful step.

Phase 2 should prioritize **Narrative Data Flow** for visualization.

Execution context may still be preserved in metadata for debugging, but it should not drive the main graph edges.

---

## Expected Inputs

The graph builder consumes trace records created by the instrumentation system.

Each trace event already contains fields such as:

- task_name
- task_description
- module_name
- parent_task
- trace_index
- duration_ms
- status
- input_preview
- output_preview
- input_length
- output_length
- error_message

Phase 2 may require adding or standardizing additional metadata fields if necessary, such as:

- stage_index
- step_order
- branch_name
- branch_taken
- artifact_type
- output_kind
- source_file
- source_line_start
- source_line_end

Only add fields that are genuinely required for data-flow semantics.

Do not create decorative metadata that no component uses.

---

## Product Requirements

### Functional Requirement 1 — Introduce Pipeline-Aware Ordering

The system must support a stable, explicit notion of pipeline order.

This can be done with one of the following strategies:

#### Preferred strategy
Each task carries a pipeline stage or step ordering value through metadata.

Examples:
- stage_index
- task_order
- pipeline_order

This metadata may be attached through decorators, helper configuration, or centralized pipeline definitions.

#### Requirements

- the ordering must be deterministic
- the ordering must be readable and inspectable
- the graph builder must use this ordering when constructing edges
- ordering should support both module-level and task-level views later

#### Important note

Do not rely only on incidental trace order if a stronger ordering mechanism can be cleanly established.
Trace order can help, but explicit ordering is safer for narrative graphs.

---

### Functional Requirement 2 — Build Edges Based on Narrative Progression

The graph builder must connect steps based on the intended flow of artifacts through the pipeline.

#### Requirements

For linear flows:
- step N should connect to step N+1

For branch points:
- the decision node should connect to the relevant downstream options
- the executed branch should be marked as taken
- alternate branch(es) should remain visible as potential routes if the graph model supports them

#### Example

detect_language  
→ english_processing_path  (taken)  
→ non_english_processing_path  (not taken / alternate)

or

choose_chunk_strategy  
→ single_pass_analysis  
→ chunked_analysis  

This milestone only needs to define graph structure clearly enough that later rendering can distinguish executed vs alternate routes.

---

### Functional Requirement 3 — Preserve Existing Node Metadata

Changing the edge model must not destroy the useful metadata already attached to nodes.

Each graph node should still preserve fields such as:

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

Later Phase 2 features depend on this metadata.

---

### Functional Requirement 4 — Support Explicit Branch Metadata

The data-flow graph must support branch nodes.

At minimum, branch-aware metadata should make it possible later to render:

- executed branch as solid
- alternate branch as dotted or muted

#### Recommended fields

Possible fields include:

- is_branch_node
- branch_group
- branch_option
- branch_taken

These names can vary, but the semantics must be clear and documented.

#### Requirements

- a branch decision must be representable in the graph
- branch options must be distinguishable
- the graph builder must not require UI code to infer branch semantics later

---

### Functional Requirement 5 — Support Both Executed and Potential Paths

For the demo pipeline, some branches will not actually execute, but they should still appear in the narrative graph as alternate paths.

#### Example

Language branch:
- English path is taken
- Non-English path is not taken, but should still exist visually

#### Requirements

The graph builder should support one of the following approaches:

Option A:
Include alternate-path nodes/edges with metadata marking them as not executed

Option B:
Include alternate-path edges only, if the nodes already exist in pipeline structure definitions

#### Preferred outcome

Later visualization should be able to show alternate branches, so the graph model should preserve that information now.

---

### Functional Requirement 6 — Introduce Graph-Building Separation of Concerns

The graph-building system should now be explicitly split into layers if needed.

Recommended separation:

- trace normalization
- pipeline ordering / narrative mapping
- node creation
- edge creation
- branch annotation
- debug summary helpers

Do not cram all logic into one monolithic function if it reduces clarity.

---

### Functional Requirement 7 — Keep a Debuggable Transition Path

Because this is a refactor of a working system, developers must be able to compare old and new behavior during debugging.

#### Recommended approach

Keep either:
- a legacy edge-building helper
or
- a debug mode that can print old vs new edge interpretations

This is optional if it adds too much clutter, but some comparison mechanism is very helpful during refactor validation.

---

## Suggested Architecture

### Recommended file structure

graph/
  graph_builder.py
  dataflow_builder.py   (optional if helpful)

If the existing graph builder is still clean, the refactor may remain in graph_builder.py.
If clarity improves significantly, split the data-flow logic into a dedicated module.

### Suggested internal functions

Examples of useful responsibilities:

- normalize_trace(trace)
- derive_pipeline_steps(trace)
- assign_stage_order(trace)
- build_dataflow_nodes(trace)
- build_dataflow_edges(steps)
- annotate_branch_edges(graph)
- graph_debug_summary(graph)

Function names can vary, but the architecture should remain easy to reason about.

---

## Pipeline Structure Strategy

This milestone must answer a subtle but important question:

How does the graph builder know the intended order of tasks?

### Recommended strategy

Introduce an explicit pipeline structure definition for the Phase 2 demo pipeline.

This can be a small configuration object or ordered mapping describing:
- module sequence
- task sequence
- branch points
- alternate paths

Example conceptual structure:

PDF Ingestion
  load_pdf
  validate_pdf
  count_pages

Text Extraction
  extract_text
  merge_pages
  detect_language
  branch: english / non_english

Text Processing
  clean_text
  normalize_whitespace
  remove_headers

Chunking
  compute_text_length
  choose_chunk_strategy
  branch: single_pass / chunked
  split_into_chunks

This does not need to be a giant framework.
A clean, explicit structure for the Phase 2 demo is enough.

#### Why this matters

Trying to infer the entire narrative pipeline from only incidental runtime trace data is fragile.
A small explicit pipeline description will make the graph more stable and much easier to extend.

---

## Data-Flow vs Data Artifact Granularity

Phase 2 should build a graph of **task steps**, not yet a full artifact graph.

That means:

Nodes = task steps  
Edges = progression / handoff between task steps  

Do not yet create separate nodes for:
- raw_text
- cleaned_text
- chunk_list
- summary_output

Those data artifacts can be surfaced through metadata and summaries for now.

This avoids graph bloat.

---

## Backward Compatibility Guidance

The refactor should avoid breaking the rest of the Phase 1 system unnecessarily.

The resulting graph must still be compatible enough with:
- existing visualization code
- existing tests where relevant
- metadata assumptions in later PRDs

If graph node IDs or fields must change, the change should be documented clearly and consistently.

Avoid ad-hoc breakage.

---

## Non-Functional Requirements

### Readability
The graph-building logic must be easier to reason about after this change, not harder.

### Determinism
The same trace and same pipeline definition should always yield the same graph.

### Extensibility
The system should support future additions such as:
- module overview graphs
- task graphs
- alternate branch rendering
- top-banner summary generation

### Minimalism
Do not build a giant generalized graph-DSL unless clearly necessary.
The goal is to support the real Phase 2 pipeline cleanly.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. The graph builder produces edges that reflect narrative progression instead of only parent-child execution
2. A simple pipeline trace produces a clear left-to-right logical flow when rendered
3. Existing node metadata is preserved
4. Branch points can be represented in graph structure
5. Executed and non-executed branch options can be distinguished in metadata
6. The graph builder is deterministic and inspectable
7. The resulting graph is a better foundation for the module overview and task drill-down views

---

## Test Plan

### Test 1 — Linear pipeline ordering

Use a simple known pipeline:
load_pdf → extract_text → clean_text → generate_summary

#### Expected result

The graph edges reflect that exact progression.

Not:
pipeline → every task

But:
load_pdf → extract_text → clean_text → generate_summary

---

### Test 2 — Existing metadata preservation

Use a trace with task descriptions, durations, and previews.

#### Expected result

Graph nodes still retain all expected metadata.

---

### Test 3 — Language branch structure

Use the PDF extraction stage with a language branch definition.

#### Expected result

The graph contains both:
- English path
- Non-English path

One path is marked as taken and the other as alternate/not taken.

---

### Test 4 — Chunk strategy branch structure

Use a chunking stage with:
- single-pass path
- chunked-analysis path

#### Expected result

Both paths exist in graph structure and the taken path is marked clearly in metadata.

---

### Test 5 — Debug summary readability

Run a graph debug summary on the refactored graph.

#### Expected result

A developer can inspect:
- ordered node list
- edge list
- branch metadata
- stage ordering

and immediately understand the pipeline structure.

---

## Deliverables

At the end of this milestone, the repo should contain:

- refactored graph-building logic
- support for explicit narrative ordering
- support for branch-aware edge metadata
- preserved node metadata compatibility
- updated tests or new tests validating data-flow semantics
- at least one demo script or graph output showing the new behavior clearly

---

## Definition of Done

This milestone is done when the graph stops feeling like a stack trace and starts feeling like a pipeline.

A developer should be able to inspect the graph and say:

“The PDF was loaded, text was extracted, language was detected, the text was cleaned, chunking strategy was chosen, analysis ran, and a structured result was produced.”

If the graph communicates that, this milestone succeeded.

---

## Implementation Cautions

Avoid these traps:

- overfitting the graph builder to one exact rendering library
- inferring too much from noisy trace order
- creating branch semantics that only make sense in UI code
- losing existing metadata during refactor
- building a giant abstraction layer that slows implementation
- trying to solve loop aggregation in this milestone

Keep the goal narrow and decisive:

Turn the graph into a data-flow narrative foundation for the Phase 2 UI.
