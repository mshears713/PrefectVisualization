# PRD 01 — Instrumentation Core

## Title

**Instrumentation Core for Runtime Visual Debugging**

## Document Purpose

This PRD defines the first implementation milestone for the Visual Debugging for AI-Generated Python Code project.

This milestone builds the **instrumentation core**: the decorators and runtime trace system that observe Python function execution without changing business logic.

This is the foundation of the entire product. If this layer is not reliable, every downstream layer—graph generation, visualization, API delivery, and demo pipeline—will become difficult to debug.

---

## Objective

Build a lightweight instrumentation layer that allows decorated Python functions to automatically record structured runtime execution events into a global in-memory trace.

The instrumentation system must:

- preserve the original behavior of decorated functions
- record execution metadata consistently
- track parent-child task relationships
- measure duration
- summarize inputs and outputs
- store trace data in a simple in-memory structure
- be easy to test with tiny deterministic functions before any real pipeline is added

---

## Why This Milestone Comes First

The product depends on one core claim:

> Decorated Python code can explain itself through runtime-generated structure.

That claim cannot be tested until function execution can be observed reliably.

Building the instrumentation layer first reduces ambiguity. It separates “does the tracing work?” from later questions like:

- does the graph render properly?
- is the demo pipeline correct?
- is the API serving the right artifact?
- is PDF extraction behaving?

This milestone creates the raw truth that every later stage will consume.

---

## Scope

This milestone includes:

- `@module(...)` decorator
- `@task(...)` decorator
- runtime trace storage
- execution context tracking
- duration measurement
- input/output preview summarization
- basic error capture
- support for deterministic synchronous execution only
- tiny demo/test functions for verification

This milestone does **not** include:

- graph generation
- HTML visualization
- FastAPI
- PDF processing
- LLM summaries
- async support
- persistent storage
- nested module hierarchies beyond module → task

---

## Product Requirements

### Functional Requirement 1 — Module Decorator

The system must provide a module decorator:

```python
@module("Math Operations")
```

This decorator attaches a human-readable module name to a function.

#### Requirements

- Must store module metadata in a way that the task decorator can access later
- Must not alter the function’s return value
- Must not break function invocation semantics
- Must work with any function used in the MVP demo pipeline

---

### Functional Requirement 2 — Task Decorator

The system must provide a task decorator:

```python
@task("Add two numbers to compute an intermediate value")
```

This decorator wraps the function and records runtime execution information.

#### Requirements

When a decorated task runs, the system must capture:

- function name
- task description
- module name
- parent task name, if any
- start timestamp
- end timestamp
- duration
- summarized input preview
- summarized output preview
- approximate input/output data length where practical
- execution status (`success` or `error`)
- error message, if raised

#### Behavior Requirements

- The decorator must preserve the original function return value on success
- The decorator must re-raise exceptions after capturing error metadata
- The decorator must support stacking with `@module(...)`
- The decorator must use `functools.wraps` so function metadata remains sane

---

### Functional Requirement 3 — Runtime Trace Storage

The system must maintain an in-memory runtime trace for a single execution session.

#### Requirements

- Trace storage should be simple and inspectable
- A global list-based structure is acceptable for MVP
- Each executed task should append a structured event record to the trace
- A reset function must exist so each demo run starts cleanly

#### Recommended shape

A trace event should be stored as a dictionary with fields similar to:

```python
{
    "task_name": "add_numbers",
    "task_description": "Add two numbers to compute an intermediate value",
    "module_name": "Math Operations",
    "parent_task": None,
    "start_time": 123.45,
    "end_time": 123.47,
    "duration_ms": 20.1,
    "input_preview": "...",
    "output_preview": "...",
    "input_length": 18,
    "output_length": 2,
    "status": "success",
    "error_message": None,
}
```

Exact field names may vary slightly, but the structure must be consistent.

---

### Functional Requirement 4 — Execution Context Tracking

The system must identify parent-child execution relationships for synchronous nested calls.

#### Example

If:

```python
main_task()
  -> add_numbers()
  -> multiply_numbers()
```

then the trace should reflect that `multiply_numbers` was called from within the active task context.

#### Recommended implementation

Use a simple global stack:

- push current task when entering wrapped function
- inspect previous stack item as parent
- pop on exit

#### Requirements

- Must work for standard synchronous nested calls
- Must not attempt async context propagation in this milestone
- Must clean up stack state even if exceptions occur

---

### Functional Requirement 5 — Duration Measurement

Each task execution must record duration.

#### Requirements

- Measure execution time per call
- Prefer `time.perf_counter()` for precision
- Store duration in milliseconds or seconds consistently
- Duration should be metadata only in this milestone

---

### Functional Requirement 6 — Input / Output Summarization

The system must summarize input and output values without storing full payloads by default.

#### Requirements

For each task call, generate compact summaries for:

- inputs
- outputs

#### Summary format

The summary should aim to include:

- approximate total character length
- first 50 characters
- last 50 characters

Examples:

- `"length=124, head='The quick brown fox...', tail='...jumps over the fence'"`

#### Design constraints

- Avoid massive raw payloads in trace records
- Be resilient to non-string values by converting via `repr()` or similar
- Handle `None`, numbers, dicts, and lists sensibly
- Exact formatting can be simple, but must be consistent

---

### Functional Requirement 7 — Error Capture

If a decorated task raises an exception, the trace must still capture the failed execution.

#### Requirements

- Record status as `error`
- Store string form of exception
- Record start time and end time
- Capture input summary if available
- Re-raise the original exception after logging

This ensures later graphing and debugging layers can highlight failure locations.

---

## Non-Functional Requirements

### Reliability

- Decorators must not silently change program logic
- Trace data must be deterministic for deterministic function calls
- State cleanup must occur even when exceptions happen

### Simplicity

- Code should favor readability over abstraction
- Avoid premature framework design
- Avoid introducing classes unless clearly useful

### Extensibility

The implementation should be simple now but not paint the project into a corner later. In particular:

- trace event structure should be easy to feed into a graph builder
- module/task metadata should be easy to reuse later
- context tracking should be isolated enough that async support could be added later without rewriting everything

---

## Technical Design Guidance

### Recommended file structure for this milestone

```text
instrumentation/
  decorators.py
  trace_collector.py
```

### `trace_collector.py` responsibilities

Should likely contain:

- global runtime trace list
- global execution stack list
- helper functions:
  - `reset_trace()`
  - `get_trace()`
  - `record_event(...)`
  - optional preview helpers

### `decorators.py` responsibilities

Should likely contain:

- `module(name: str)` decorator
- `task(description: str)` decorator
- wrapping logic
- duration timing
- push/pop execution stack handling
- exception capture
- summary generation via helper functions or imports

---

## Suggested Implementation Notes

### Decorator stacking order

The implementation must work with this style:

```python
@module("Math Operations")
@task("Add two numbers to compute an intermediate value")
def add_numbers(a, b):
    return a + b
```

If the chosen implementation prefers the reverse stacking order, that must be clearly documented and used consistently across the codebase. But the preferred outcome is to support the human-readable order above.

### Metadata storage

A pragmatic MVP approach is to attach metadata directly to the function object, for example:

- `_viz_module_name`
- `_viz_task_description`

This is acceptable if implemented cleanly.

### Preview helper

Implement a helper that safely converts values into preview strings. It should:

- handle primitives cleanly
- use `repr()` for non-trivial structures
- truncate very long strings
- include length metadata

### Input representation

For inputs, it is acceptable to summarize:

- positional args together
- keyword args together

The exact formatting can be simple. The goal is legibility, not perfect serialization.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. A tiny synchronous test script with several decorated functions runs successfully
2. Each decorated function produces a corresponding trace event
3. Trace events include module name, task description, parent task, duration, input preview, output preview, and status
4. Nested decorated calls correctly capture parent-child relationships
5. A failing decorated function records an error event before re-raising
6. `reset_trace()` clears prior run state
7. The original function return values remain unchanged
8. Code is clean enough that the next milestone can consume the trace without refactoring

---

## Test Plan

### Test 1 — Basic success path

Create two simple functions:

- `add_numbers(a, b)`
- `multiply_numbers(a, b)`

Call them sequentially.

#### Expected result

- two trace events recorded
- both marked `success`
- durations present
- input/output previews present

---

### Test 2 — Nested call path

Create a function such as:

```python
@module("Math Operations")
@task("Compute a combined math result")
def compute_pipeline(a, b):
    added = add_numbers(a, b)
    return multiply_numbers(added, 10)
```

#### Expected result

- `compute_pipeline`, `add_numbers`, and `multiply_numbers` all appear in trace
- child calls record `compute_pipeline` as parent where appropriate

---

### Test 3 — Mixed data types

Create a text-focused task such as:

- `build_sentence(number)`

that converts a numeric result into a string.

#### Expected result

- previews handle int and str types without breaking
- output preview includes character count

---

### Test 4 — Error case

Create a task that intentionally raises an exception.

#### Expected result

- error event appears in trace
- status is `error`
- exception message captured
- exception is still raised to caller

---

### Test 5 — Trace reset

Run one test, call `reset_trace()`, then run another.

#### Expected result

- only the new run appears after reset

---

## Deliverables

At the end of this milestone, the repo should contain:

- working decorators
- working trace collector
- tiny deterministic test/demo functions
- documented trace event shape
- evidence that nested calls, durations, previews, and errors are captured correctly

---

## Definition of Done

This milestone is done when a developer can run a tiny Python script and inspect a clean runtime trace that makes it obvious:

- what functions ran
- what module each belonged to
- who called whom
- how long each took
- what data roughly flowed through them
- whether anything failed

When that works, the project has a real spine instead of just a cool idea.

---

## Out of Scope Reminders

Do not add any of the following in this milestone unless absolutely required for correctness:

- NetworkX
- PyVis
- FastAPI routes
- file upload handling
- PDF parsing
- LLM calls
- live graph updates
- async execution

Those shiny objects can wait their turn like civilized software components.
