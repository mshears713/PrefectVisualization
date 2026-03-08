# PRD 04 — Synthetic Demo Pipeline and Validation Scenarios

## Title

**Synthetic Demo Pipeline and Validation Scenarios for Runtime Visual Debugging**

## Document Purpose

This PRD defines the fourth implementation milestone for the Visual Debugging for AI-Generated Python Code project.

This milestone creates the first meaningful end-to-end specimen for the system: a synthetic, deterministic pipeline that exercises the instrumentation layer, graph builder, and visualization layer together.

If PRD 01 built the sensors, PRD 02 built the structure, and PRD 03 made the structure visible, PRD 04 gives the system something worth observing.

This milestone is deliberately not the final PDF workflow. It is the controlled proving ground that lets the team validate the architecture before introducing real file-processing dependencies and the inevitable nonsense those bring with them.

---

## Objective

Build a small but expressive synthetic pipeline that demonstrates the full concept end to end.

The pipeline should:

- include multiple modules
- include multiple tasks per module
- include both numeric and text data
- include nested execution relationships
- include at least one intentionally failing or invalid path for error visualization
- include lightweight validation signals
- generate a graph that is visually interesting, readable, and explanatory

The output of this milestone should make it possible to demonstrate the product without needing PDF extraction yet.

---

## Why This Milestone Comes Fourth

The first three milestones establish the machinery:

1. instrumentation
2. graph construction
3. graph visualization

But machinery without a specimen is not yet a convincing product.

This milestone exists to answer a critical question:

> Does the system actually produce a useful visual explanation when applied to a realistic mini-pipeline?

A synthetic pipeline is the correct next step because it is:

- deterministic
- easy to debug
- easy to reason about
- rich enough to exercise the architecture
- far less brittle than PDF parsing during early validation

This milestone should prove the concept before the project graduates into real file inputs.

---

## Scope

This milestone includes:

- creating a synthetic end-to-end demo pipeline
- defining multiple modules and tasks
- passing both numbers and strings through the system
- ensuring nested calls appear in the runtime trace
- adding basic validation scenarios
- adding at least one failure or clearly invalid case
- generating a graph artifact from the pipeline
- producing a demo script that runs the entire stack from task execution to HTML graph output

This milestone does **not** include:

- FastAPI routes
- upload UI
- real PDF extraction
- production persistence
- async execution
- live graph generation during execution
- LLM summaries
- advanced validation frameworks beyond what is useful for MVP
- true user-provided inputs beyond simple demo parameters

---

## Product Goal of This Milestone

A developer should be able to run one script and get the full workflow:

synthetic pipeline runs  
→ trace captured  
→ graph built  
→ HTML exported  

The resulting graph should clearly show:

- module grouping
- task flow
- numeric transformations
- text transformations
- durations
- success states
- at least one visible failure or invalid case

This is the first milestone where the product should feel demo-ready.

---

## Demo Pipeline Strategy

The synthetic pipeline must be easy to understand at a glance.

It should answer the question:

> Can the tool explain a mini program well enough that someone understands it without opening the source code?

To support that, the pipeline should use a small number of modules with clear semantic roles.

### Recommended module set

#### 1. Math Operations

Purpose:

Perform deterministic numeric transformations that are easy to verify.

Recommended tasks:

- add_numbers
- multiply_value
- compute_intermediate_score

This module creates simple numeric artifacts that later flow into text.

#### 2. Text Construction

Purpose:

Turn numeric results into human-readable text.

Recommended tasks:

- build_sentence_from_score
- build_status_phrase
- compose_report_line

This module ensures the graph carries string outputs and not only numbers.

#### 3. Text Transformation

Purpose:

Apply transformations to text so the graph shows multiple text-processing stages.

Recommended tasks:

- normalize_text
- emphasize_keywords
- create_final_message

This module provides multiple downstream string operations that are visible in the graph and easy to explain.

#### 4. Validation or Fault Injection

Purpose:

Introduce meaningful status variation into the graph.

Recommended tasks:

- validate_score_range
- validate_text_nonempty
- optional intentional_failure_task

This module should create either:
- an explicit error node, or
- a clearly invalid result that is captured in status metadata

At least one visible non-success scenario should exist in the demo.

---

## Pipeline Design Requirements

### Functional Requirement 1 — Multi-Module Pipeline

The synthetic demo must include at least three modules.

#### Minimum required modules

- Math Operations
- Text Construction
- Text Transformation

A fourth validation or error-focused module is strongly recommended.

#### Requirements

- Each module must contain at least two tasks
- Modules must be named clearly
- Task descriptions must be explicit and human-readable
- Module membership must be known ahead of time and encoded directly in decorators

The graph should not look like a flat bag of functions.

---

### Functional Requirement 2 — Mixed Data Types

The pipeline must pass both numeric and string values through different tasks.

#### Requirements

- numeric values should be created and transformed in early stages
- numeric results should feed into string-building functions
- string results should be transformed downstream

#### Rationale

This validates that input/output preview handling works across different data types and that the graph remains readable.

---

### Functional Requirement 3 — Nested Task Relationships

The demo pipeline must include nested task calls, not only sequential top-level calls.

#### Requirements

At least one higher-level task should call multiple lower-level tasks.

Example conceptual shape:

- compute_pipeline
  - add_numbers
  - multiply_value
  - compute_intermediate_score

and later:

- build_report
  - build_sentence_from_score
  - compose_report_line
  - normalize_text

#### Rationale

This ensures parent-child relationships appear in the graph and that the structure is interesting enough to demonstrate the system's value.

---

### Functional Requirement 4 — Validation Signal

The pipeline must include lightweight validation logic.

#### Recommended approach

Use simple, deterministic validation checks.

Examples:

- score must be within a specific range
- text must be non-empty
- string length must exceed a minimum threshold

#### Requirements

- validation results must be reflected in task status or node metadata
- success path should be visible
- invalid or failing path should also be demonstrable

#### Important note

This does not need to become a full validation framework. The goal is simply to make graph status meaningful.

---

### Functional Requirement 5 — Intentional Error or Failure Case

The demo must include one intentionally broken or invalid scenario.

This is important because a debugging product with no visible failure mode is a bit like a fire extinguisher demo where nothing is on fire.

#### Acceptable strategies

- provide one demo run where a task raises an exception
- provide one alternate parameter set that produces an invalid result
- provide a task that fails when input is outside a simple threshold

#### Requirements

- the failure should be deterministic
- the failure should be easy to trigger intentionally
- the graph should make the failing node obvious
- the demo should still remain understandable

#### Recommendation

Use a parameterized demo script with:

- a normal run
- an optional failure run

This keeps the happy path available while still proving the product's debugging value.

---

### Functional Requirement 6 — End-to-End Demo Runner

Create a single script that exercises the full workflow.

#### Recommended file name

demo_prd4_full_pipeline.py

#### Responsibilities

This script should:

- reset trace state
- run the synthetic demo pipeline
- collect the runtime trace
- build the graph
- export HTML visualization
- print useful console output indicating what happened
- show where the HTML was saved

#### Recommended output

The script should print:

- whether run succeeded or failed
- number of trace events
- number of graph nodes
- number of graph edges
- output HTML path

#### Optional

It may optionally support a simple parameter or flag to run a failure scenario.

---

## Validation Design Guidance

The validation model in this milestone should remain lightweight and practical.

### Recommended status model

At minimum support:

- success
- error

If the existing architecture already supports or can easily support:

- warning
- suspicious
- invalid

then that is acceptable, but not required.

### Suggested checks

For numeric stages:

- score range validation

For text stages:

- non-empty text validation
- minimum length validation

### Design rule

Validation should enrich the demo, not hijack it.

Do not spend half the project inventing a validation taxonomy worthy of a medieval bureaucracy.

---

## Technical Design Guidance

### Recommended file structure additions

repo/
  pipeline/
    demo_pipeline.py
    validation_models.py   (optional)
    demo_inputs.py         (optional)

  scripts/
    demo_prd4_full_pipeline.py

The exact file layout can vary, but responsibilities should remain clear.

### Likely responsibilities of pipeline/demo_pipeline.py

Should include:

- synthetic pipeline task definitions
- orchestrating functions for demo runs
- normal path logic
- optional failure path logic

### Optional validation_models.py

If helpful, define simple validation helpers or lightweight Pydantic models.

Only do this if it genuinely clarifies the code.

If plain functions are cleaner, use plain functions.

---

## Parameterization Guidance

The demo should be deterministic.

Recommended approach:

Expose one or two simple inputs such as:

- base number
- multiplier
- failure mode toggle

This lets the team trigger:

- a normal successful graph
- an error graph

without changing code manually every time.

The script should remain trivial to run.

---

## Graph Expectations for This Milestone

The synthetic pipeline should produce a graph with enough shape to be worth showing.

### Desired graph qualities

- at least 8 to 12 nodes in the happy path
- at least 3 module groupings
- at least one branching or nested structure
- visible movement from numbers to text
- clear tooltip metadata
- at least one red or non-success node in a failure demo

The graph should not be so large that it becomes visually chaotic.

This is a showcase specimen, not a stress test.

---

## Non-Functional Requirements

### Readability

The demo pipeline should be understandable without reading a novel.

Use simple function names and clear task descriptions.

### Determinism

Runs should be predictable.

Avoid randomness unless seeded and clearly justified.

### Debuggability

When something fails, the console output and graph should make the failure understandable.

### Demo Friendliness

A developer should be able to open the generated HTML and explain the system to another person in under two minutes.

That is a brutally useful quality bar.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. A synthetic pipeline exists with at least three modules
2. The pipeline exercises numeric and string transformations
3. The runtime trace captures meaningful nested execution
4. The graph builder produces a structured graph from the run
5. The visualization layer exports a readable HTML artifact
6. A happy-path run succeeds and produces a useful graph
7. At least one deterministic failure or invalid scenario exists
8. The failure scenario is visible in the graph or clearly represented in console output
9. A single demo script can run the end-to-end flow without manual glue code

---

## Test Plan

### Test 1 — Happy path end-to-end

Run the full synthetic pipeline with valid inputs.

#### Expected result

- trace generated
- graph generated
- HTML exported
- all main tasks appear successful
- numeric and text previews visible

---

### Test 2 — Failure path end-to-end

Run the full synthetic pipeline with a parameter set that triggers an intentional failure or invalid state.

#### Expected result

- failure is deterministic
- trace captures the failure
- graph includes the failed node or clearly reflects the failure state
- HTML still exports if architecture allows
- user can identify where the failure occurred

---

### Test 3 — Module grouping sanity check

Inspect the HTML graph.

#### Expected result

- Math Operations tasks visibly belong together
- Text Construction tasks visibly belong together
- Text Transformation tasks visibly belong together

---

### Test 4 — Mixed preview data check

Inspect tooltip metadata for numeric and text tasks.

#### Expected result

- numeric stages show concise previews
- text stages show head/tail previews and lengths
- metadata remains readable

---

### Test 5 — Narrative explainability check

Open the final HTML and attempt to verbally explain the pipeline from the graph alone.

#### Expected result

A reasonable viewer should be able to infer something like:

“This pipeline computes a score, turns it into text, transforms the text, validates it, and shows where something failed if the data is bad.”

If that is not possible, the demo pipeline is not doing its job.

---

## Deliverables

At the end of this milestone, the repo should contain:

- a synthetic demo pipeline module
- one or more simple validation or fault-injection helpers
- an end-to-end runner script
- at least one generated HTML graph artifact from the synthetic pipeline
- evidence that both happy-path and failure-path runs are supported

---

## Definition of Done

This milestone is done when a developer can run one command and get a graph that clearly demonstrates the product idea.

That graph should show a mini-program transforming data through named modules and tasks, with enough metadata and status information to make the runtime behavior intelligible at a glance.

At that point, the project has crossed from “technical prototype pieces” into “actual demoable product concept.”

That matters because after this milestone, the remaining work is about delivery and realism, not whether the core idea exists.

---

## Future Bridge to PRD 05

This milestone intentionally stops short of full API delivery and real PDF input.

That is the next step.

Once this synthetic pipeline is working, the team will be in a strong position to:

- expose the demo through FastAPI
- let a frontend trigger runs
- later swap in a real PDF-based flow
- possibly add LLM-generated summaries after the graph is produced

PRD 04 is the proving ground.

If it works, the project has a heartbeat.

---

## Implementation Cautions

Avoid the following traps:

- making the synthetic pipeline too trivial to be interesting
- making it too complex to debug in the available time
- introducing PDF dependencies before the synthetic demo is working
- turning validation into a giant side project
- building multiple competing demo runners
- adding frontend concerns before the backend demo loop is stable

Stay focused on one thing:

Create the clearest possible controlled demo of the concept.

That is the shortest path to a working conference-worthy prototype.
