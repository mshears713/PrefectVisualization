# PRD 09 — Phase 2 Visualization Layer: Module View, Task View, and Narrative Node Design

## Title

**Phase 2 Visualization Layer for Module Overview, Task Drill-Down, and Narrative Node Design**

## Document Purpose

This PRD defines the fourth implementation milestone of Phase 2 for the Visual Debugging for AI-Generated Python Code project.

PRD 06 changed the graph semantics from call-trace to data-flow.

PRD 07 introduced the module overview graph.

PRD 08 established the task drill-down architecture and navigation contract.

PRD 09 is where the system becomes visually meaningful.

This milestone is responsible for rendering the Phase 2 graphs in a way that communicates the pipeline clearly and immediately.

The goal is no longer merely to show that a graph exists.
The goal is to make the graph readable as a story.

This PRD introduces:

- left-to-right rendering
- module boxes
- task boxes
- visible descriptions
- visible status badges
- visible duration
- duration-aware width scaling
- module hover summaries
- task hover summaries
- HTML output for module and task views
- stable rendering behavior suitable for demo use

This is the first Phase 2 milestone that should produce a graph you can open and inspect as a narrative artifact.

---

## Objective

Implement the Phase 2 visualization layer so that the system can render:

1. a module overview graph
2. a task graph for a selected module

Both views must be understandable at a glance and compatible with the interaction model established in README Part 2.

This milestone should produce actual HTML outputs for visual inspection.

These outputs do not need full polish, but they must communicate the intended hierarchy and flow.

---

## Why This Milestone Comes Now

The previous PRDs established structure:

- correct data-flow edges
- module aggregation
- module-to-task drill-down

But structure in memory is not enough.
The project only becomes useful when the output looks like a pipeline instead of a random network.

PRD 09 turns graph objects into an explanation interface.

This is the point where the team should start opening generated HTML and asking:

“Does this tell the story I want?”

---

## Scope

This milestone includes:

- rendering the module graph as HTML
- rendering the task graph as HTML
- enforcing left-to-right visual layout
- replacing circles with square/rectangular boxes
- showing title, description, status, and duration directly inside nodes
- scaling task node width based on duration
- showing rule-based module hover summaries
- showing task hover summaries
- preserving branch-aware edge metadata for future styling
- making outputs stable enough to inspect in a browser

This milestone does **not** include:

- final PDF pipeline implementation
- top banner summary
- task click detail panel
- deep input/output preview expansion
- real-time graph updates
- timeline view
- loop aggregation
- IDE integration
- full frontend app polish

This milestone is primarily about graph rendering and visual language.

---

## Core Visual Goals

The rendered graph should feel like a process map, not a graph toy.

A viewer should be able to answer these questions without reading code:

- What major stages exist?
- What stage comes next?
- Which stage failed?
- What happened inside one module?
- Which steps were slow?
- What flowed in and out of the step?

The rendering should communicate hierarchy, progression, and status.

---

## View 1 — Module Overview Graph

### Purpose

Show the full pipeline at the module level.

The expected module sequence is:

PDF Ingestion  
→ Text Extraction  
→ Text Processing  
→ Chunking  
→ LLM Analysis  
→ Structured Output

### Requirements

Each module should appear as a box, not a circle.

Each module node must show directly inside the node:

- module title
- description line
- status badge
- total duration

### Example conceptual layout

Text Extraction  
Extract text from PDF  
✓ success  
120 ms

### Hover behavior

Hovering over a module should show:

- input summary
- output summary
- duration

Example:

Input: PDF document  
Output: 32,441 characters  
Duration: 120 ms

Do not include page count or language in module hover at this stage.
Keep it consistent across modules.

### Click behavior

This PRD should prepare the module nodes for drill-down.
If easy, module nodes may include clickable links or data attributes that later support task graph navigation.

At minimum, the rendered module graph must preserve a deterministic module identifier for later drill-down.

---

## View 2 — Task Graph

### Purpose

Show the internal task pipeline for a selected module.

Example for Text Extraction:

extract_text  
→ merge_pages  
→ detect_language

### Requirements

Task nodes must be square or rectangular.

Each task node must show directly inside the node:

- task name
- short description
- status badge
- duration

### Example conceptual layout

extract_text  
Extract text from PDF pages  
✓ success  
42 ms

### Hover behavior

Hovering over a task should show:

- input summary
- output summary
- duration
- status

Example:

Input: PDF pages  
Output: 32,441 chars  
Duration: 42 ms  
Status: success

The richer task click detail panel comes later.
This PRD should only ensure hover content is ready and readable.

---

## Left-to-Right Layout

### Requirement

Both module and task graphs must render left-to-right.

This is non-negotiable for Phase 2.

The graph should not use a random force-directed layout.

### Reason

The whole narrative depends on process order being readable.

The x-axis should communicate progression through the pipeline.

A user should be able to visually scan from left to right and understand what happened.

### Implementation expectation

Use rendering options or node position strategy that enforces a left-to-right hierarchical layout.

If the existing rendering library resists this, prefer deterministic manual positioning over chaotic physics.

Readable and boring is better than dynamic and confusing.

---

## Node Shape and Visual Style

### Requirement

Use square or rectangular node shapes instead of circles.

### Reason

Rectangular nodes support readable embedded text.
They visually communicate “step in a process” better than circular nodes.

### Visual language

Module boxes and task boxes may differ slightly in size, but the overall style should remain coherent.

The graph should look like one system, not two unrelated widgets.

---

## Node Width Scaling by Duration

### Requirement

Task node width should roughly scale based on duration.

Use the agreed formula:

width = 120 + duration_ms * 0.2

This is intentionally approximate and can be tuned later.

### Goals

- make slower steps feel visually heavier
- provide immediate performance intuition
- avoid absurdly large nodes for long tasks

### Suggested constraints

Implement reasonable min/max bounds so a very long-running task does not dominate the screen.

Module node widths may remain stable for now unless dynamic scaling is easy and clearly beneficial.

---

## Status Representation

### Requirement

Continue to use both color and badge text.

Supported states should include at least:

- success
- error
- warning or suspicious if present

### Examples

✓ success  
✖ error  
⚠ warning

### Design rule

Color alone is not enough.
Badges should make state explicit.

### Color mapping

Use deterministic status-to-color logic.

Do not infer status from output values in the visualization layer.

Use status already provided in node metadata.

---

## Branch Visualization

PRD 06 and PRD 08 preserve branch semantics.
This PRD should carry those semantics into rendering in a basic but visible way.

### Requirement

The graph should distinguish between:

- executed path
- alternate path

### Suggested rendering strategy

- solid edge = executed path
- dotted or muted edge = alternate path

### Important note

This does not need to become a fancy animation system.
It only needs to be obvious enough that branching exists.

---

## Rendering Library Expectations

The existing project likely already uses PyVis or related graph rendering infrastructure.

This PRD should extend that system rather than replace it unless replacement is absolutely necessary.

If the current renderer makes Phase 2 layout impossible, document the issue clearly before introducing a new dependency.

The implementation should remain pragmatic.

---

## HTML Output Requirements

### Requirement

This milestone must produce HTML outputs that can be opened in a browser for inspection.

At minimum support:

- module overview HTML
- task graph HTML for a selected module

### Suggested output files

output/module_graph.html  
output/task_graph_<module_id>.html

If a different structure is cleaner, that is acceptable, but output naming should remain obvious.

### Goal

A developer should be able to generate the HTML and open it directly to visually inspect the result.

---

## Suggested File Structure

Likely files involved:

graph/
  graph_visualizer.py
  module_graph_visualizer.py   (optional)
  task_graph_visualizer.py     (optional)

Do not create unnecessary files if a clean extension of the existing visualizer is sufficient.

However, separate responsibilities if that improves readability.

---

## Suggested Internal Responsibilities

Possible functions include:

- render_module_graph_html(module_graph, output_path)
- render_task_graph_html(task_graph_payload, output_path)
- make_module_node_label(node_data)
- make_task_node_label(node_data)
- make_module_hover_text(node_data)
- make_task_hover_text(node_data)
- status_to_color(status)
- compute_node_width(duration_ms)
- apply_left_to_right_layout(graph)

Exact names can vary, but the responsibilities should remain clear and testable.

---

## Data Contract Requirements

This visualization layer must assume the graph builders already provide clean metadata.

The renderer should not perform heavy semantic inference.

Its job is to:

- format
- style
- position
- expose metadata clearly

Do not bury graph meaning inside rendering hacks.

Keep semantics in the graph builder layers.

---

## Non-Functional Requirements

### Readability

Text inside nodes must be readable without zoom gymnastics.

### Determinism

The same graph input should produce stable visual structure.

### Separation of Concerns

Rendering code should not redefine graph semantics.

### Demo Suitability

The output should be clear enough for conference demo inspection.

### Incremental Improvement

This PRD should improve the graph immediately, even if later PRDs add additional polish.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. The module overview graph renders as HTML
2. The task graph renders as HTML
3. Both graphs are laid out left-to-right
4. Nodes are square or rectangular rather than circles
5. Node labels show title, description, status, and duration directly
6. Task node width scales with runtime using the agreed formula
7. Module hover shows input, output, and duration
8. Task hover shows input, output, duration, and status
9. Branch paths can be visually distinguished at least in a basic way
10. A developer can open the generated HTML and understand the story more clearly than before

---

## Test Plan

### Test 1 — Module graph rendering

Render the module overview graph.

#### Expected result

- six modules appear
- left-to-right ordering is obvious
- each module shows title, description, badge, duration
- hover shows input, output, duration

---

### Test 2 — Task graph rendering

Render a task graph for a selected module such as Text Extraction.

#### Expected result

- only relevant tasks appear
- left-to-right ordering is obvious
- tasks show title, description, badge, duration
- hover shows quick metadata

---

### Test 3 — Duration width scaling

Use tasks with visibly different durations.

#### Expected result

- slower tasks render wider than faster ones
- widths remain reasonable and readable

---

### Test 4 — Branch edge rendering

Render a graph containing both executed and alternate branch paths.

#### Expected result

- the taken branch is visibly distinct from the alternate path
- the graph remains understandable

---

### Test 5 — Visual sanity check

Open generated HTML in a browser.

#### Expected result

The graph feels like a process map rather than a random network.
A viewer should be able to follow the story.

---

## Deliverables

At the end of this milestone, the repo should contain:

- updated visualization code
- HTML rendering for module graphs
- HTML rendering for task graphs
- left-to-right layout support
- square/rectangular node rendering
- duration-aware width scaling
- hover formatting for modules and tasks
- example HTML outputs for inspection

---

## Definition of Done

This milestone is done when the Phase 2 graphs are visually understandable.

A developer should be able to open the module graph, see the six-stage pipeline, and immediately understand the overall process.

Then they should be able to open a task graph for one module and understand the internal task progression.

At that point, the project has moved beyond structural correctness into narrative clarity.

That is the main job of PRD 09.

---

## Implementation Cautions

Avoid these traps:

- letting the renderer fall back to random physics-driven layouts
- overloading nodes with too much text
- moving hover information into visible labels where it causes clutter
- implementing click panels prematurely
- overcomplicating branch rendering
- rewriting graph semantics in the visualizer
- sacrificing readability for flashy movement

Stay focused on one goal:

Render the existing Phase 2 graph architecture in a way that finally looks like the story you want to tell.
