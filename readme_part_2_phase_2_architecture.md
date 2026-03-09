# README Part 2 — Phase 2 Architecture: Narrative Pipeline View, Module Drill-Down, and PDF Workflow

## Purpose of This Document

This document extends the original README for the Visual Debugging for AI-Generated Python Code project.

README Part 1 defined the core MVP architecture:

- runtime instrumentation decorators
- in-memory trace collection
- trace-to-graph conversion
- HTML graph rendering
- synthetic demo pipeline
- FastAPI delivery surface

That first phase proved the basic concept:

> A Python program can generate a visual representation of its own execution.

Phase 2 exists because proving that the system works is not the same as making the visualization tell a useful story.

The early prototype behaves more like a raw trace graph:
- nodes appear
- colors change
- edges connect
- metadata exists

But the graph does not yet communicate the system in a clean narrative way.

Phase 2 upgrades the project from a raw execution graph into a structured explanation tool for AI-generated Python pipelines.

The central shift is this:

**Phase 1 was about observability. Phase 2 is about explainability.**

---

## Phase 2 Product Goal

Transform the prototype from a trace-oriented graph into a story-oriented pipeline view.

The system should answer two different questions depending on the level of detail:

### Module View
What major stages does this program perform?

### Task View
What exactly happened inside one stage?

The viewer should be able to start from a clean high-level pipeline, then drill into a stage to understand its internal operations, timing, branching, outputs, and source-code location.

---

## What Phase 2 Adds

Phase 2 introduces six major upgrades:

1. Data-flow graph semantics instead of call-stack semantics  
2. Two-level graph navigation: module overview and task drill-down  
3. Left-to-right pipeline layout  
4. Information-rich square nodes with duration-aware width  
5. Real PDF-oriented pipeline replacing the synthetic demo as the core story  
6. Hover, click, and top-banner narrative features that make the graph understandable without reading source code  

These upgrades are implemented through PRDs 6 through 11.

---

## Why the Current Graph Is Not Enough

The current graph can prove that instrumentation works, but it has several limitations:

- connections reflect execution context more than data transformation
- nodes are grouped only loosely by module metadata
- the graph layout is too free-form to read as a pipeline
- there is no clean module-level story
- there is no real drill-down interaction model
- the synthetic pipeline is useful for testing but not ideal for a compelling document-processing narrative

This means the current visualization behaves more like a wiring diagram than an explanation.

Phase 2 addresses this directly.

---

## Phase 2 Design Principles

Phase 2 should obey the following design principles.

### 1. Narrative First
The graph must tell the story of the document moving through the system.

### 2. Data Transformation Over Raw Trace
Edges should represent how data flows through the system, not merely who called whom.

### 3. Two Clear Levels of Abstraction
Users should not see all details at once.

### 4. Left-to-Right Readability
The graph should read like a pipeline, not like a particle simulation.

### 5. Visual Economy
The graph should show the most important information at a glance and reserve deeper detail for hover and click interactions.

### 6. Determinism
The Phase 2 demo should remain deterministic and stable enough for repeated conference demonstrations.

### 7. Minimal Dependence on LLMs
The system should not require LLM calls for its core explanation layer. Rule-based logic should be used for summaries and initial Phase 2 behavior.

---

## Phase 2 Architecture Overview

Phase 2 retains the original execution stack but changes what gets built and shown.

The updated conceptual flow is:

Python program runs  
→ decorators capture execution trace  
→ trace converted into data-aware execution records  
→ data-flow graph built  
→ module graph built  
→ user sees module overview  
→ user clicks module  
→ task graph for that module is rendered  
→ user hovers or clicks tasks for detailed metadata  

This means the system no longer revolves around a single graph artifact.

Instead, Phase 2 produces a family of related views:

- module overview graph
- task graph for a selected module
- top banner narrative summary
- task detail panel metadata

---

## Core Change: Data-Flow Graph Semantics

### Phase 1 Semantics
The first implementation mostly connected nodes based on execution context or parent-child task relationships.

That produces graphs like:

pipeline → task A  
pipeline → task B  
pipeline → task C  

This is technically valid as a trace, but it does not read like a story.

### Phase 2 Semantics
Phase 2 treats the graph primarily as a **data-flow graph**.

Edges should communicate:

- which step produced the output consumed by the next step
- how the document moves through the pipeline
- where branching occurs
- where outputs become inputs

This shifts the visualization from:
“which function invoked which”
to:
“what happened to the document”

### Important note
Instrumentation still captures runtime truth.
Phase 2 is not fabricating structure.
It is choosing the most useful semantic interpretation of that truth.

---

## Two-Level Graph System

Phase 2 introduces a two-level graph architecture.

### Level 1 — Module Overview Graph

This is the first graph the user sees.

It contains only major pipeline stages.

For the document pipeline, the top-level modules are:

- PDF Ingestion
- Text Extraction
- Text Processing
- Chunking
- LLM Analysis
- Structured Output

This graph answers:

- what major capabilities exist?
- where is the failure?
- how does the document move at a high level?

This view must remain simple and clean.

### Level 2 — Task Graph

Clicking a module opens a second graph showing the internal tasks for that module.

Example:

Text Extraction may contain:
- extract_text
- merge_pages
- detect_language

This graph answers:

- what exact steps happened inside this module?
- how long did each task take?
- what inputs and outputs did they use?
- what source code lines implement them?

### Interaction model

Module graph:
- hover → module summary
- click → open task graph

Task graph:
- hover → quick metadata preview
- click → open detailed task panel

This drill-down model is intentionally chosen instead of an in-place expanding graph because it is much more stable, easier to render, and easier to explain.

---

## Module Overview Design

The module overview graph should have exactly six nodes for the main Phase 2 pipeline.

### Selected modules

1. PDF Ingestion  
2. Text Extraction  
3. Text Processing  
4. Chunking  
5. LLM Analysis  
6. Structured Output  

This size is intentional:
- large enough to show real structure
- small enough to stay readable

### Module box content

Each module box should show:

- module title
- short description line
- status badge
- total runtime

Example conceptual layout:

Text Extraction  
Extract text from PDF  
✓ success  
120 ms  

### Module hover content

Hovering over a module should show:

- input summary
- output summary
- duration

Example:

Input: PDF document  
Output: 32,441 characters  
Duration: 120 ms  

Phase 2 intentionally excludes module-specific extras like page count or language in the module hover because those vary too much by module and would complicate the interface.

### Module click behavior

Clicking a module transitions to the task graph for that module.

This may be implemented through:
- a route change
- a separate HTML graph
- a server-side render of the selected module task graph

For MVP Phase 2, a route-based or separate-render approach is preferred over in-place dynamic expansion.

---

## Task Graph Design

Task graphs show the internal execution steps for a single module.

### Task node shape

Tasks should be rendered as square or rectangular nodes rather than circles.

Reason:
- circles communicate abstract graph data
- squares communicate process steps
- squares create more room for information

### Task node visible content

Task nodes should show:

- task name
- short description
- status badge
- duration

This should be visible at all times.

### Width scaling based on duration

Task node width should expand based on runtime.

Proposed formula:

width = 120 + duration_ms * 0.2

This is intentionally rough and can be tuned later.

The goal is not precision. The goal is visual intuition.

A slower task should look visibly “heavier” than a fast one.

### Task hover content

Hovering over a task should show a quick summary:

- input summary
- output summary
- duration
- status

Example:

Input: 32,441 chars  
Output: 28,990 chars  
Duration: 42 ms  

### Task click behavior

Clicking a task should open a detail panel or deeper inspection view.

The detail panel should include:

- task name
- task description
- module name
- duration
- status
- input summary
- output summary
- source file
- source line range
- library used, if available

Example:

extract_text

Module: Text Extraction  
Duration: 118 ms  
Input: PDF pages  
Output: 32,441 chars  

Source: pipeline.py:143–186  
Library: PyMuPDF  

### Deeper data preview

Within the task detail panel, the user should be able to inspect deeper preview information if desired.

This may be implemented as:
- an expand/collapse section
- a secondary click
- a nested details area

The deeper preview should show:

- total size
- HEAD preview
- TAIL preview

Example:

HEAD: "Introduction..."  
TAIL: "...Conclusion"  
Total characters: 32,441  

The exact UI pattern can be decided during implementation, but the information contract should remain the same.

---

## Top Banner Narrative Summary

Phase 2 adds a rule-based summary banner above the graph.

This banner is important because it helps non-technical users understand the system before they inspect the graph.

### Banner design goals

- summarize what happened
- stay deterministic
- avoid requiring an LLM
- remain short enough to scan quickly

### Example summary

Pipeline Summary

PDF loaded  
Text extracted  
Text cleaned  
Language detected: English  
Document chunked  
Summary generated  

### Rule-based implementation

The top banner should be built from graph metadata and pipeline outcomes, not from a model call.

Possible inputs:
- module completion status
- output sizes
- chosen branch
- final output generated

Future versions may optionally support LLM-generated summaries, but Phase 2 should stay rule-based.

---

## Left-to-Right Layout

Both graphs should use a left-to-right layout.

This is critical.

### Why left-to-right?

- matches how most people read process diagrams
- supports pipeline storytelling
- avoids the “random node cloud” problem
- aligns with data transformation semantics

### Layout rule

Both the module graph and task graphs should be arranged left to right.

The x-axis represents progression through the pipeline.
Not necessarily precise wall-clock time, but process order.

### Time as a secondary signal

A full timeline graph is explicitly deferred.
Phase 2 uses box width as a lightweight proxy for duration.

---

## Branching Design

Phase 2 includes two branching opportunities.

### Branch 1 — Language Branch

During text extraction, the pipeline should detect language.

The graph should display both potential branches:
- English
- Non-English

For the demo, execution should always take the English path.

The non-English path should still be visible as a non-executed or dotted alternative so viewers understand branching exists.

### Branch 2 — Chunk Strategy Branch

This is the main operational branch.

After text length is computed:
- if the text is small, a simpler path can be shown
- if the text is large, the pipeline follows chunking + aggregation

This is useful because:
- it reflects a real decision point
- it is easy to explain
- it creates a meaningful narrative in the graph

### Branch rendering

Suggested visual conventions:
- solid edge = executed path
- dotted or muted edge = alternate path

The exact rendering is implementation-dependent, but the graph must make branching visible.

---

## Phase 2 PDF Pipeline

Phase 2 upgrades the demo from a synthetic pipeline to a real PDF-oriented flow.

### Recommended PDF library

Use **PyMuPDF**.

Rationale:
- fast
- mature
- good text extraction support
- practical for PDF demo workflows

### Phase 2 module pipeline

#### 1. PDF Ingestion
Purpose:
Load and validate the document.

Suggested tasks:
- load_pdf
- validate_pdf
- count_pages

#### 2. Text Extraction
Purpose:
Extract raw text and determine language.

Suggested tasks:
- extract_text
- merge_pages
- detect_language

#### 3. Text Processing
Purpose:
Normalize and clean extracted text.

Suggested tasks:
- clean_text
- normalize_whitespace
- remove_headers

#### 4. Chunking
Purpose:
Choose chunk strategy and split large text if needed.

Suggested tasks:
- compute_text_length
- choose_chunk_strategy
- split_into_chunks

#### 5. LLM Analysis
Purpose:
Analyze chunks or full text and generate semantic output.

Suggested tasks:
- analyze_chunks
- aggregate_results
- generate_summary

#### 6. Structured Output
Purpose:
Build final structured result and validate it.

Suggested tasks:
- build_structured_result
- validate_schema
- export_result

### Narrative the graph should tell

PDF loaded  
→ text extracted  
→ language detected  
→ text cleaned  
→ chunk strategy selected  
→ document analyzed  
→ summary generated  
→ structured result returned  

This should be understandable from the graph alone.

---

## Data Summarization Strategy

Phase 2 must support different data types cleanly.

The system cannot assume everything is a string.

### Type-aware summarization

#### Strings
Show:
- char count
- head
- tail
- optional delta if compared to prior step

#### Lists
Show:
- item count
- optional item type

#### Dict / JSON
Show:
- key count
- notable top-level keys if simple

#### Numbers
Show:
- value
- transformed value where useful

#### Enums / Models / Unknown objects
Show:
- type name
- minimal safe summary
- size if available

### Transformation indicators

Only compute transformation deltas where the comparison makes sense.

Examples:
- text length changed
- list item count changed
- score value changed

Do not force meaningless deltas across unrelated data types.

---

## Source Code Location Metadata

Phase 2 adds source-code awareness to task details.

### Why it matters

This feature creates a direct bridge between the graph and the implementation.

The user should be able to answer:

“Where in the code is this step implemented?”

### Required metadata

For each task:
- source file path
- line start
- line end

This can be collected using Python introspection.

The task panel should display it in a form like:

pipeline.py:143–186

Later versions may make this clickable in an IDE or editor integration.
Phase 2 only needs to display it.

---

## Libraries Used Metadata

Where practical, the task detail panel should also show the primary library associated with the task.

Examples:
- PyMuPDF
- regex
- OpenAI client
- Pydantic

This is useful for debugging and explaining dependencies.

This does not need to be perfect or fully automatic in Phase 2.
A lightweight metadata association is acceptable.

---

## Status and Badges

Phase 2 continues to use color for status:
- green = success
- red = error
- yellow = warning or suspicious

In addition, visible badges should make status explicit.

Examples:
- ✓ success
- ⚠ warning
- ✖ error

This makes the graph easier to read without relying on color alone.

---

## Interaction Model Summary

### Module graph
- hover → module summary
- click → open task graph

### Task graph
- hover → quick task metadata
- click → open task detail panel

### Task detail panel
- show code location, runtime, input/output summary, and library
- allow deeper input/output preview inspection

This interaction model should remain consistent across the entire Phase 2 system.

---

## What Phase 2 Defers

Phase 2 intentionally does not implement the following:

- real-time graph updates during execution
- a full timeline graph
- in-place expanding nodes
- loop or repeated-operation aggregation
- nested module trees deeper than module → task
- LLM-generated pipeline summaries
- full IDE click-through source navigation
- a full frontend application beyond what is necessary to support the graphs and panels

These are future directions, not Phase 2 requirements.

---

## About Loops and Repeated Operations

Loops are a known visualization problem.

If repeated operations are rendered as separate nodes for every iteration, the graph becomes unreadable.

Future versions should support **loop collapsing**, where repeated operations are aggregated into a single node like:

analyze_chunks  
(48 iterations)

with metadata such as:
- iteration count
- average duration
- total duration

This is intentionally deferred for the Phase 2 demo.

---

## Relationship to Existing Tool Categories

Phase 2 should be built with a clear understanding of what this system is and is not.

This project is not trying to replace:
- Jaeger or Zipkin for distributed tracing
- Airflow or Prefect for workflow orchestration
- LangGraph for explicit graph-authored agent programs

Instead, it combines ideas from those categories into something different:

**a runtime-generated, data-flow-oriented explanation layer for AI-generated Python programs**

That positioning should guide future design choices.

---

## Best Engineering Practices for Phase 2

### Preserve clear separation of concerns

Do not collapse everything into one renderer or one graph builder.

Prefer separate modules for:
- data-flow graph building
- module graph construction
- task graph construction
- visualization rendering
- summary generation
- detail panel metadata formatting

### Keep graph semantics explicit

Do not hide graph meaning inside UI code.

Clearly define:
- what a node represents
- what an edge represents
- what a module summary represents
- what a task summary represents

### Use deterministic rendering defaults

Avoid highly dynamic layouts that make the graph jump unpredictably.

### Minimize unnecessary refactors

Phase 2 should extend the working prototype rather than rewrite the entire system unless necessary.

### Reuse existing metadata

Phase 1 already captures valuable trace data.
Phase 2 should build on it, not discard it.

### Maintain testability

Each new Phase 2 component should be small enough to validate visually and programmatically.

---

## Suggested Implementation Order

Phase 2 should be implemented incrementally.

Recommended order:

1. Convert graph semantics from call-trace to data-flow where needed  
2. Build module-level graph builder  
3. Build task-level graph builder  
4. Redesign nodes and layout  
5. Implement PDF-oriented pipeline  
6. Add top banner summary, hover behavior, and task detail panels  

This sequence allows visual inspection after each stage.

---

## Phase 2 Deliverable Definition

Phase 2 is successful when the following are true:

- the main graph shows six modules in a left-to-right pipeline
- hovering a module shows input, output, and duration
- clicking a module reveals a task graph for that stage
- task nodes are squares with visible title, description, status, and duration
- task width roughly reflects runtime
- task hover gives quick metadata
- task click opens detailed metadata including source file and line range
- the graph visually shows both language branching and chunking branching
- the pipeline uses a real PDF flow powered by PyMuPDF
- the top banner summary explains the pipeline in rule-based language
- the overall experience tells a clear story about what happened to the document

---

## Final Framing

Phase 1 proved that a Python program could generate a graph of its execution.

Phase 2 aims higher.

Phase 2 should make that graph useful enough that a viewer can understand the behavior of an AI-generated document-processing pipeline without reading the code.

That is the product direction.

The system should not merely show activity.

It should show meaning.
