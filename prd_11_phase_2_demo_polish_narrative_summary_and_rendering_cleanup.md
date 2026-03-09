# PRD 11 — Phase 2 Demo Polish, Narrative Summary, and Rendering Cleanup

## Title

**Phase 2 Demo Polish, Narrative Summary, and Rendering Cleanup for Visual Debugging**

## Document Purpose

This PRD defines the sixth and final implementation milestone of Phase 2 for the Visual Debugging for AI-Generated Python Code project.

PRD 06 established data-flow graph semantics.  
PRD 07 established the module overview graph.  
PRD 08 established the task graph drill-down contract.  
PRD 09 established readable Phase 2 graph rendering.  
PRD 10 established navigable drill-down from module view to task view.

PRD 11 completes the Phase 2 experience by focusing on polish, narrative readability, and demo reliability.

This milestone does not change the core architecture.
Instead, it improves the quality of presentation so the system feels intentional, understandable, and stable enough for real demonstrations.

This PRD is where the rough edges should be sanded down so the demo stops feeling like “a working prototype with visible seams” and starts feeling like “a coherent tool.”

---

## Objective

Improve the visual and narrative quality of the Phase 2 experience by:

- fixing rendering and formatting bugs
- improving label readability
- cleaning HTML output
- adding a rule-based pipeline summary banner
- improving hover formatting
- stabilizing layout and spacing
- making module and task graphs easier to read at a glance
- making the demo outputs suitable for presentation without apology

The goal is not to overbuild the UI.
The goal is to make the existing Phase 2 system feel polished, intentional, and legible.

---

## Why This Milestone Matters

The previous PRDs already built the machine:

Execution Trace  
→ Data-Flow Task Graph  
→ Module Overview Graph  
→ Task Graph Drill-Down  
→ Interactive Navigation

By PRD 10 the system should already be usable.

But a usable graph is not automatically a compelling demo.

A few rendering issues can ruin first impressions:
- duplicated titles
- malformed hover text
- inconsistent spacing
- cluttered labels
- weak visual hierarchy

PRD 11 focuses on those high-leverage improvements.

This milestone is the difference between:
“it works, if you explain it enough”
and
“it reads clearly on its own”

---

## Scope

This milestone includes:

- fixing duplicate title / repeated header issues
- fixing HTML escaping or raw `<br>` / formatting artifacts in hover text
- improving module node text layout
- improving task node text layout
- adding a rule-based pipeline summary banner
- improving module graph readability
- improving task graph readability
- ensuring navigation links remain clear and visible
- improving branch legibility where possible
- improving output consistency for demo generation

This milestone does **not** include:

- changing graph semantics again
- introducing a new rendering library unless absolutely necessary
- building a full frontend application
- implementing deep task click panels
- implementing real-time updates
- implementing timeline view
- implementing loop aggregation
- full PDF pipeline replacement if not already done
- LLM-based summaries

This milestone is about polish, not architectural reinvention.

---

## Product Goal of This Milestone

A first-time viewer should be able to open the generated module graph and understand the overall system within seconds.

Then they should be able to drill into one module and understand the internal task flow without confusion.

The graph should feel:

- clean
- intentional
- readable
- stable
- demo-ready

The product should no longer require a long technical preamble to be understandable.

---

## Core Problems This Milestone Should Solve

### Problem 1 — Duplicate or repeated page titles

The current rendering may produce repeated visible titles or duplicated heading elements.

This must be cleaned up.

Each graph page should have one clear main title only.

---

### Problem 2 — Broken hover formatting

The current rendering may show raw HTML-like text such as:
- `<br>`
- escaped formatting markers
- awkward tooltip layout

Hover text should render cleanly and read naturally.

---

### Problem 3 — Weak visual hierarchy

Nodes may technically contain the right information but still feel crowded or hard to scan.

This milestone should improve:
- text spacing
- line breaks
- ordering of fields
- visual separation between title, description, badge, and duration

---

### Problem 4 — Lack of immediate narrative framing

A graph without context can still feel abstract.

The summary banner solves this by giving the viewer a top-level interpretation of the run.

---

## Product Requirements

### Functional Requirement 1 — Add Rule-Based Pipeline Summary Banner

Each generated graph page should include a summary banner at the top.

This should be especially visible on the module overview graph, and optionally repeated in task graph pages in module-specific form.

#### Goals of the banner

- give immediate context
- summarize the run
- remain deterministic
- avoid requiring any model call

#### Recommended banner contents for module overview

Possible fields include:

- total modules
- total tasks
- success/failure count
- total runtime
- selected branch information if relevant
- one-line pipeline narrative

#### Example conceptual summary

Pipeline Summary

6 modules  
18 tasks  
0 failures  
Total runtime: 520 ms  

PDF loaded, text extracted, text cleaned, chunk strategy selected, analysis completed, structured result generated.

This should be built using existing graph and pipeline metadata.

Do not use an LLM.

---

### Functional Requirement 2 — Clean Up Page Titles and Headers

Each generated HTML page should contain exactly one visible title/header block.

#### Requirements

- module overview page has one clear heading
- task graph page has one clear heading
- task graph page should identify the selected module
- header text should not appear duplicated

#### Suggested titles

Module Overview — Phase 2 Pipeline

Task Graph — Text Extraction

or equivalent clean wording.

---

### Functional Requirement 3 — Fix Hover Text Formatting

Hover content for both module and task nodes must render cleanly.

#### Requirements

- line breaks should appear as real line breaks
- no raw HTML artifacts should appear visibly
- no escaped formatting markers should leak into the tooltip
- hover text should remain concise and readable

#### Suggested module hover format

Input: PDF document  
Output: 32,441 characters  
Duration: 120 ms

#### Suggested task hover format

Input: PDF pages  
Output: 32,441 chars  
Duration: 42 ms  
Status: success

Keep hover useful but not overloaded.

---

### Functional Requirement 4 — Improve Module Node Text Layout

Module nodes should present information in a cleaner hierarchy.

#### Required visible fields

- module title
- description line
- status badge
- total duration

#### Design guidance

These should not appear as a dense block of text.

Preferred layout order:

1. title  
2. description  
3. status line  
4. duration line

Spacing should make the node easy to scan quickly.

---

### Functional Requirement 5 — Improve Task Node Text Layout

Task nodes should follow the same readability principle.

#### Required visible fields

- task name
- short description
- status badge
- duration

#### Requirements

- text should wrap or break in a controlled way
- labels should remain readable without major zooming
- duration should not visually dominate the title
- status badge should be obvious but not noisy

This milestone should improve readability without overcomplicating the renderer.

---

### Functional Requirement 6 — Keep Branch Paths Legible

If task graphs contain alternate paths, the rendering should make them understandable.

#### Requirements

- executed branch must remain clearly visible
- alternate branch should remain visible but less prominent
- branch styling should not introduce confusion or clutter

This is not the milestone for advanced branch UX.
It is the milestone for basic legibility.

---

### Functional Requirement 7 — Improve Navigation Clarity

Task graph pages already support back navigation from PRD 10.

This milestone should make that navigation visually clear and demo-friendly.

#### Requirements

- back link or button should be easy to find
- task graph page should clearly indicate what module is being shown
- module overview should feel like the “home” view

This avoids the viewer feeling lost inside the drill-down.

---

### Functional Requirement 8 — Stabilize HTML Output for Demo Use

The generated HTML should be clean enough that opening it during a demo does not require explanation like:

“ignore the duplicate heading”
or
“that hover formatting bug doesn’t matter”

#### Requirements

- generated pages must look stable
- visible formatting defects should be removed
- output paths should remain predictable
- regeneration should not break page naming conventions

---

## Summary Banner Rules

The summary banner should remain simple and deterministic.

### Recommended data sources

- module graph metadata
- task graph metadata
- runtime totals
- success/failure counts
- selected module context for task pages

### For module overview pages

Suggested content:

- total modules
- total tasks
- total runtime
- failure count
- one short narrative line

### For task graph pages

Suggested content:

- module name
- task count
- module runtime
- input summary
- output summary

The exact formatting can vary, but the hierarchy should remain clean.

---

## Technical Design Guidance

### Recommended files likely involved

graph/
  graph_visualizer.py

Optional helper files if clarity improves:

graph/
  summary_formatter.py
  hover_formatter.py

Do not create extra files unless they improve maintainability.

A small helper for summary formatting is acceptable if the visualizer is becoming too cluttered.

### Suggested responsibilities

Possible functions or helpers:

- make_module_page_header(...)
- make_task_page_header(...)
- build_pipeline_summary(...)
- format_module_hover(...)
- format_task_hover(...)
- clean_label_text(...)
- sanitize_rendered_html(...)

Exact names can vary.

The key is to keep formatting logic centralized enough that it does not become scattered and brittle.

---

## Data Contract Expectations

This PRD assumes the graph builders already provide clean metadata.

The visualizer should not need to infer semantics from scratch.

It should use:
- module context
- task metadata
- branch metadata
- duration values
- status values

Keep semantics in the data layer.
Keep presentation in the visual layer.

---

## Non-Functional Requirements

### Readability
The graph should be understandable from across a room, not only when stared at from six inches away.

### Determinism
Repeated renders of the same graph should not randomly change visible wording or structure.

### Minimalism
Do not bloat the UI with too many metrics.
Keep the summary and hover content concise.

### Demo Suitability
A developer should be able to open the generated HTML and feel comfortable showing it to another person.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. Duplicate or repeated visible titles are removed
2. Hover text renders cleanly without raw formatting artifacts
3. Module node labels read clearly and consistently
4. Task node labels read clearly and consistently
5. A rule-based summary banner appears on the module overview page
6. Task graph pages include clear header context and visible back navigation
7. Branch styling remains understandable
8. The generated HTML feels stable and presentation-ready
9. A developer can open the graph and explain it without apologizing for visible formatting issues

---

## Test Plan

### Test 1 — Header cleanup

Render the module overview page.

#### Expected result

Only one visible page title/header appears.

---

### Test 2 — Hover cleanup

Hover over several module and task nodes.

#### Expected result

Hover text uses readable line breaks and does not show raw formatting artifacts.

---

### Test 3 — Summary banner

Open the module overview page.

#### Expected result

A rule-based pipeline summary banner appears above the graph and shows key run metrics.

---

### Test 4 — Task graph header and navigation

Open a task graph page.

#### Expected result

The page clearly identifies the selected module and includes a visible back link.

---

### Test 5 — Visual readability

Open both module and task pages and scan them quickly.

#### Expected result

The labels, hierarchy, and spacing are clearer than before and suitable for demo use.

---

## Deliverables

At the end of this milestone, the repo should contain:

- cleaned-up HTML rendering for module and task graphs
- fixed hover formatting
- single-title page headers
- a rule-based module overview summary banner
- improved task graph context headers
- stable, demo-ready HTML outputs

---

## Definition of Done

This milestone is done when the Phase 2 graphs feel polished enough that the system can be shown to another person without distracting visual defects.

A developer should be able to:

1. open the module overview graph
2. understand the summary banner
3. drill into a task graph
4. read the labels and hover data cleanly
5. navigate back without confusion

At that point, Phase 2 is no longer just technically correct.
It is communicatively effective.

That is the purpose of PRD 11.

---

## Implementation Cautions

Avoid these traps:

- overloading the summary banner with too much data
- moving too much hover information into visible node labels
- making the layout prettier at the expense of readability
- introducing new rendering bugs while fixing the current ones
- attempting to solve future deep-click detail panels in this milestone
- changing graph semantics again

Stay focused on one thing:

Polish the existing Phase 2 experience until it reads like an intentional tool rather than a clever prototype.
