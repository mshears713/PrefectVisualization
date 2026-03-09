# PRD 10 — Interactive Drill-Down, Task Graph Rendering, and Branch-Aware Navigation

## Title

**Interactive Drill-Down, Task Graph Rendering, and Branch-Aware Navigation for Phase 2**

## Document Purpose

This PRD defines the fifth implementation milestone of Phase 2 for the Visual Debugging for AI-Generated Python Code project.

PRD 06 introduced data-flow graph semantics.  
PRD 07 introduced the module overview graph.  
PRD 08 introduced the task graph drill-down contract.  
PRD 09 introduced the Phase 2 visualization layer and produced the first readable HTML pipeline view.

PRD 10 makes the Phase 2 system **interactive**.

This milestone connects the module overview graph to its corresponding task graphs, renders those task graphs as actual HTML artifacts, and makes branch-aware internal execution visible inside modules.

This is the milestone where the product stops being “a graph you can open” and becomes “a graph you can navigate.”

---

## Objective

Implement the interactive navigation flow between:

- module overview graph
- task graph for a selected module

The user should be able to:

1. open the module overview graph  
2. click a module  
3. open the corresponding task graph  
4. inspect task-level execution and branch behavior  
5. return to the module overview graph  

This milestone should also make branch visualization meaningfully visible inside task graphs.

---

## Why This Milestone Matters

The architecture already supports:

Execution Trace  
→ Data-Flow Task Graph  
→ Module Overview Graph  
→ Task Graph by Module

But until a user can actually move between those views, the system is still only structurally correct, not experientially useful.

PRD 10 is the bridge between architecture and demonstration.

It should make the drill-down behavior obvious enough that someone seeing the tool for the first time can understand the product concept in seconds:

“Click the stage, see what happened inside it.”

---

## Scope

This milestone includes:

- making module nodes navigable
- generating task graph HTML files for selected modules
- linking module graph to task graph outputs
- rendering task graphs as browsable outputs
- rendering branch-aware paths in the task graph
- enabling return navigation from task graph back to module overview
- improving task hover content enough for practical use
- producing a development-friendly interaction flow that works locally and can later be exposed through FastAPI

This milestone does **not** include:

- final visual polish fixes like duplicate titles and HTML escaping bugs
- final pipeline summary banner
- deep task detail panel with source location click-through
- real PDF pipeline replacement unless trivial and already safe
- timeline view
- live graph updates
- loop aggregation
- full app shell / frontend framework

This milestone is about interactive graph navigation and meaningful task graph visibility.

---

## Primary User Story

A user opens the module overview graph and sees:

PDF Ingestion → Text Extraction → Text Processing → Chunking → LLM Analysis → Structured Output

The user clicks **Text Extraction**.

A task graph opens showing:

extract_text → merge_pages → detect_language

The user can see:

- internal task progression
- status of each task
- branch behavior if present
- quick input/output hover summaries

Then the user clicks a back link and returns to the module overview graph.

This is the core user experience PRD 10 must deliver.

---

## Product Requirements

### Functional Requirement 1 — Module Nodes Must Be Navigable

Each module node in the module overview graph must contain enough information to open its corresponding task graph.

#### Requirements

- each module must have a stable module identifier
- the rendered module graph must embed or reference that identifier
- clicking a module should open the task graph HTML for that module

#### Acceptable implementations

Option A:
Generate distinct HTML files and link each module node directly to its task graph HTML

Option B:
Generate one interactive shell that switches task graph views dynamically

#### Recommendation

Use Option A for now.

It is simpler, deterministic, and fits the current architecture well.

Examples:

- module_graph.html
- task_graph_pdf_ingestion.html
- task_graph_text_extraction.html
- task_graph_text_processing.html
- task_graph_chunking.html
- task_graph_llm_analysis.html
- task_graph_structured_output.html

This is the most practical conference-demo path.

---

### Functional Requirement 2 — Generate Task Graph HTML for Each Module

The system must render HTML task graphs for at least the key pipeline modules.

#### Requirements

- task graph HTML should be generated using the module-scoped graphs from PRD 08
- graphs must preserve left-to-right layout
- graphs must preserve branch metadata
- graphs must include visible title, description, badge, and duration inside task nodes
- hover should show quick task metadata

#### Naming

Use stable output naming conventions based on module id.

Examples:

- output/task_graph_text_extraction.html
- output/task_graph_chunking.html

---

### Functional Requirement 3 — Back Navigation from Task Graph to Module Graph

The task graph view must provide a clear path back to the module overview graph.

#### Requirements

- task graph HTML must include a visible back action or link
- the destination should be the module overview graph HTML
- the back behavior should not require extra application state

#### Acceptable implementations

- a plain HTML back link above the graph
- a button-like link
- a small header navigation row

#### Recommendation

Use a simple explicit link such as:

Back to Module Overview

This is enough for the current stage.

---

### Functional Requirement 4 — Branch Visualization in Task Graph

Task graphs must visually distinguish executed and alternate paths.

#### Requirements

If branch metadata is present:
- executed edges should be rendered as normal/solid
- alternate edges should be rendered as dotted, muted, or otherwise visibly distinct

#### Required demo branches

This milestone should support the two agreed branch concepts:

1. Language branch
   - English path
   - Non-English path
   - English path may be the one taken for demo runs
   - Non-English path should still be visible as alternate

2. Chunk strategy branch
   - small / single-pass path
   - large / chunked path

The exact degree of implementation depends on what is already represented in the pipeline data, but the rendering layer must be able to show branches where metadata exists.

---

### Functional Requirement 5 — Task Graph Hover Summaries Must Be Useful

Hovering over a task must show enough information to make the task graph useful, even before the full detail panel exists.

#### Required hover fields

- input summary
- output summary
- duration
- status

#### Optional if already available

- branch marker
- source file reference
- library used

Do not overload the hover content.
Keep it readable.

---

### Functional Requirement 6 — Module Graph Must Link Only to Relevant Task Graphs

Only module nodes should be clickable for drill-down.

Task nodes in the task graph do not yet need to open deeper task detail panels in this milestone.

This keeps the interaction model simple and consistent:

- module click = go deeper
- task click = reserved for future detail panel

---

### Functional Requirement 7 — Task Graph Titles and Context Headers

Each task graph HTML page should clearly identify what module it represents.

#### Requirements

Include a readable title or header such as:

Task Graph — Text Extraction

Optional supporting context:

- module description
- task count
- total duration

This helps the user remain oriented after drill-down.

---

### Functional Requirement 8 — Batch Generation Helper

Provide a helper function or script that can generate:

- module overview graph
- all module task graphs

in one run.

#### Why this matters

For demos and debugging, it should be easy to regenerate the entire graph set after running the pipeline.

#### Suggested behavior

A single script should output:

- module_graph.html
- task_graph_<module>.html for all main modules

Then print the generated file paths.

---

## Architecture Guidance

### Recommended file structure

graph/
  module_graph_builder.py
  task_graph_builder.py
  graph_visualizer.py

scripts/
  generate_phase2_graphs.py   (or similarly named helper)

The exact structure can vary, but responsibilities should stay clear.

### Recommended responsibilities

#### graph_visualizer.py
- render module graph HTML
- render task graph HTML
- support links/back navigation
- support edge styling for branch paths

#### task_graph_builder.py
- provide module-scoped task graph payloads
- preserve branch metadata
- provide module context for headers

#### generation script
- run end-to-end graph generation
- write all HTML outputs
- report paths

---

## Navigation Strategy

### Recommended approach: static HTML linking

For the current stage, favor simple static linking between generated HTML files.

Reasons:
- minimal moving parts
- no dependency on app state
- easy to inspect locally
- works well for conference demos
- easy to later serve through FastAPI

#### Example workflow

Open:
output/module_graph.html

Click:
Text Extraction node

Open:
output/task_graph_text_extraction.html

Click:
Back to Module Overview

Return to:
output/module_graph.html

This is simple and robust.

---

## Data Contract Requirements

This milestone assumes the graph builders already provide:

- stable module ids
- task graph payloads
- preserved branch metadata
- task metadata
- module context

Do not re-derive semantics inside the visualizer if the builder already knows them.

Rendering and linking should consume existing graph contracts cleanly.

---

## Non-Functional Requirements

### Simplicity
Favor the simplest interaction model that works reliably.

### Determinism
The same selected module should always render the same task graph HTML for the same run.

### Compatibility
The output should remain compatible with later FastAPI serving.

### Demo Readability
A first-time viewer should understand within seconds:
- that the module graph is the overview
- that clicking reveals the internal tasks
- that the alternate path is visible where branching exists

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. The module overview graph renders as HTML
2. The module nodes are clickable or linked to corresponding task graph HTML files
3. Task graph HTML files are generated for relevant modules
4. Task graph pages clearly indicate which module is being shown
5. Each task graph includes a visible back link to the module overview graph
6. Task graph hover summaries are readable and useful
7. Branch paths are visually distinguishable where branch metadata exists
8. A developer can regenerate the full set of HTML graph files in one run
9. The system now feels navigable rather than static

---

## Test Plan

### Test 1 — Module click navigation

Generate the module overview graph and click a module node such as Text Extraction.

#### Expected result

The corresponding task graph HTML opens.

---

### Test 2 — Back navigation

Open a task graph and click the back action.

#### Expected result

The module overview graph opens.

---

### Test 3 — Task graph filtering

Open a specific task graph such as task_graph_text_extraction.html.

#### Expected result

Only tasks from the Text Extraction module are shown.

---

### Test 4 — Branch edge rendering

Open a task graph containing a branch.

#### Expected result

Executed and alternate paths are visually distinct.

---

### Test 5 — Batch generation

Run the generation helper.

#### Expected result

The full set of HTML outputs is generated and the file paths are printed.

---

## Deliverables

At the end of this milestone, the repo should contain:

- module overview graph HTML with navigation links
- task graph HTML outputs for relevant modules
- a back-navigation mechanism from task graph to module overview
- branch-aware task graph rendering
- a graph generation helper script
- tests or verification scripts covering the navigation flow

---

## Definition of Done

This milestone is done when the graph system is no longer just a static visualization.

A developer should be able to:

1. open the module overview graph
2. click a module
3. inspect the task graph for that module
4. see branch behavior where relevant
5. return back to the module overview graph

At that point, the product has crossed into a real explorable interface.

That is the essential job of PRD 10.

---

## Implementation Cautions

Avoid these traps:

- building a heavy client-side application when static HTML linking is enough
- mixing navigation logic with graph semantics
- making task nodes clickable before the deeper task detail model exists
- overcomplicating branch rendering
- introducing PDF pipeline changes in the same milestone unless already trivial and safe
- forgetting to generate all task graph HTML files automatically

Stay focused on the main outcome:

Make the Phase 2 graph navigable, inspectable, and demo-ready at the module-to-task level.
