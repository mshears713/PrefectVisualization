# PRD 06 — Testing and Validation Framework

## Purpose

This document is the authoritative specification for the testing framework of the **Visual Debugging for AI-Generated Python Code** project. It defines the architecture of the test suite, the subsystems under test, the behaviors that must be validated, and how end-to-end testing works.

The test suite exists to:

- Verify that each subsystem fulfills its contract independently (unit tests).
- Verify that subsystems compose correctly into a working pipeline (integration tests).
- Prevent regressions as the prototype evolves.
- Provide a runnable confidence check before any demonstration or deployment.

---

## Architecture of the Testing System

### Location

All tests live in the `tests/` directory at the repository root:

```
tests/
├── __init__.py
├── test_instrumentation.py
├── test_graph_builder.py
├── test_visualization.py
├── test_demo_pipeline.py
├── test_api_endpoints.py
└── test_end_to_end_pipeline.py
```

### Test Runner

All tests are executed with **pytest**. The entire suite is invoked from the repository root:

```bash
pytest tests/ -v
```

### Test Isolation

Each test that touches the global trace state must call `reset_trace()` at the start or use a pytest fixture that ensures a clean state. This prevents test order from affecting results.

### No External Dependencies

Tests must not require a running server process, external network access, or a database. The FastAPI tests use `httpx.AsyncClient` via the ASGI interface (`httpx.AsyncClient(app=app, base_url="http://test")`), which runs completely in-process.

---

## Subsystems Under Test

The system contains five subsystems that must be tested individually and one end-to-end integration scenario:

| # | Subsystem | Module | Test File |
|---|-----------|--------|-----------|
| 1 | Instrumentation Layer | `instrumentation/` | `test_instrumentation.py` |
| 2 | Trace-to-Graph Builder | `graph/graph_builder.py` | `test_graph_builder.py` |
| 3 | Graph Visualization | `graph/graph_visualizer.py` | `test_visualization.py` |
| 4 | Synthetic Demo Pipeline | `pipeline/demo_pipeline.py` | `test_demo_pipeline.py` |
| 5 | FastAPI Delivery Layer | `api/server.py` | `test_api_endpoints.py` |
| 6 | End-to-End Pipeline | all subsystems combined | `test_end_to_end_pipeline.py` |

---

## Subsystem 1 — Instrumentation Layer

**Location:** `instrumentation/decorators.py`, `instrumentation/trace_collector.py`

**Behaviors to validate:**

### 1.1 Single decorated function produces a trace event

- A function decorated with `@task` must appear in the trace after execution.
- The trace event must contain the correct `task_name`, `task_description`, `status`, `duration_ms`, and `trace_index`.

### 1.2 Nested calls produce parent-child relationships

- When a decorated function calls another decorated function, the inner function's trace event must have `parent_task` set to the outer function's name.
- The outer function must have `parent_task` set to `None` (assuming it is the root call).

### 1.3 Execution order is preserved

- Multiple sequential calls must produce trace events with ascending `trace_index` values.
- The first call gets index 0, the second gets index 1, etc.

### 1.4 Error events are recorded with status="error"

- If a decorated function raises an exception, a trace event with `status="error"` must be recorded before the exception propagates.
- The `error_message` field must contain the exception string.
- The exception must still propagate to the caller.

### 1.5 Module name is preserved

- A function decorated with `@module` and `@task` must record the module name in the trace event.
- A function decorated with only `@task` must record an empty string for `module_name`.

### 1.6 Trace reset clears state

- After `reset_trace()`, `get_trace()` must return an empty list.
- After `reset_trace()`, the `execution_stack` must be empty.

### 1.7 Input and output previews are recorded

- The `input_preview`, `input_length`, `output_preview`, and `output_length` fields must be non-None for successful events.

---

## Subsystem 2 — Trace-to-Graph Builder

**Location:** `graph/graph_builder.py`

**Behaviors to validate:**

### 2.1 Sequential tasks produce the correct number of nodes

- A trace with N independent task events must produce a graph with exactly N nodes.

### 2.2 Sequential tasks produce no edges

- Tasks with no parent-child relationship must produce a graph with zero edges.

### 2.3 Parent-child trace events produce directed edges

- When task B is called inside task A, the graph must contain a directed edge from A's node to B's node.
- Edge direction: parent → child.

### 2.4 Node IDs follow the correct scheme

- Node IDs must follow the pattern `"{task_name}__{trace_index}"`.
- This guarantees uniqueness even when the same function is called multiple times.

### 2.5 Node attributes mirror trace event fields

- Each node must carry all trace event metadata: `task_name`, `task_description`, `module_name`, `status`, `duration_ms`, `input_preview`, `output_preview`, `error_message`.

### 2.6 Error events appear as nodes with status="error"

- A trace event with `status="error"` must produce a graph node with `status="error"` and the correct `error_message`.

### 2.7 Repeated calls to the same function produce distinct nodes

- Calling the same function twice must produce two distinct nodes with different `trace_index` suffixes.
- The same function called twice must not collapse into a single node.

### 2.8 Graph debug summary returns correct counts

- `graph_debug_summary()` must return correct values for `num_nodes`, `num_edges`, `root_nodes`, `module_counts`, and `status_counts`.

---

## Subsystem 3 — Graph Visualization

**Location:** `graph/graph_visualizer.py`

**Behaviors to validate:**

### 3.1 A graph can be exported to HTML

- `render_graph_html(graph, path)` must create an HTML file at the specified path.
- The function must not raise any exceptions for a valid graph.

### 3.2 The generated HTML file is non-empty

- The output file must exist after rendering and have a non-zero size.

### 3.3 HTML content contains task names

- Each task name from the graph must appear somewhere in the rendered HTML content.

### 3.4 Status colors are correctly mapped

- `status_to_color("success")` must return the green hex value `#4caf50`.
- `status_to_color("error")` must return the red hex value `#f44336`.
- `status_to_color("unknown_value")` must return the fallback grey `#90a4ae`.

### 3.5 Node tooltips contain task metadata

- `make_node_title(node_data)` must return an HTML string containing the task name, module name, status, and duration.

### 3.6 PyVis network contains the correct number of nodes and edges

- `build_pyvis_network(graph)` must return a PyVis Network whose node list and edge list match the input graph.

---

## Subsystem 4 — Synthetic Demo Pipeline

**Location:** `pipeline/demo_pipeline.py`

**Behaviors to validate:**

### 4.1 Success path produces a non-empty trace

- `run_demo_pipeline(base=5, multiplier=3)` must produce at least one trace event.
- The trace must contain events from multiple modules.

### 4.2 Success path produces graph nodes and edges

- The trace from a successful run must convert into a graph with nodes and edges.

### 4.3 Success path does not raise exceptions

- The success path must complete without raising any exception.

### 4.4 Success path returns a non-empty string report

- The return value must be a non-empty string.

### 4.5 Failure path records an error trace event

- With `fail_mode=True`, at least one trace event must have `status="error"`.

### 4.6 Failure path raises a ValueError

- With `fail_mode=True`, the pipeline must raise `ValueError`.

### 4.7 Failure path still produces a partial graph

- Even after failure, the partial trace must be convertible into a graph with at least one node.

### 4.8 All expected modules appear in a success trace

- A successful run must produce events for all four modules: Math Operations, Text Construction, Text Transformation, and Validation.

---

## Subsystem 5 — FastAPI Delivery Layer

**Location:** `api/server.py`

**Test approach:** Use `httpx.AsyncClient` with the ASGI transport to make in-process HTTP requests without a running server.

**Behaviors to validate:**

### 5.1 Health endpoint returns status=ok

- `GET /health` must return HTTP 200.
- The response body must be `{"status": "ok"}`.

### 5.2 Root endpoint returns service description

- `GET /` must return HTTP 200.
- The response body must contain a `"service"` key and a `"routes"` key.

### 5.3 Run-demo success endpoint executes the pipeline

- `GET /run-demo` (default mode=success) must return HTTP 200.
- The response must include `"pipeline_status": "success"`.
- The response must include `"node_count"` greater than zero.
- The response must include `"trace_event_count"` greater than zero.

### 5.4 Run-demo failure endpoint records error

- `GET /run-demo?mode=failure` must return HTTP 200.
- The response must include `"pipeline_status": "error"`.
- The response must include a non-null `"pipeline_error"`.

### 5.5 Graph endpoint returns HTML after demo run

- After calling `GET /run-demo`, calling `GET /graph` must return HTTP 200.
- The response content-type must be `text/html`.

### 5.6 Graph endpoint returns 404 before any demo run

- If `GET /graph` is called and no graph has been generated, it must return HTTP 404.
  - Note: test isolation must ensure the graph file does not exist.

### 5.7 Run-demo with invalid mode returns 400

- `GET /run-demo?mode=invalid` must return HTTP 400.

---

## Subsystem 6 — End-to-End Pipeline Integration

**Location:** `tests/test_end_to_end_pipeline.py`

This test exercises the full stack from instrumentation through to HTML artifact generation.

### Full integration scenario

1. Reset the trace.
2. Execute the demo pipeline in success mode.
3. Retrieve the trace with `get_trace()`.
4. Build a graph with `build_graph(trace)`.
5. Render the graph to an HTML file with `render_graph_html(graph, path)`.
6. Verify that the HTML file exists.
7. Verify that the HTML file is non-empty.
8. Verify that the graph has nodes and edges.
9. Verify that node names from the pipeline appear in the HTML content.

### Failure mode integration scenario

1. Reset the trace.
2. Execute the demo pipeline in failure mode (catching the ValueError).
3. Retrieve the partial trace.
4. Build a graph from the partial trace.
5. Render the graph to HTML.
6. Verify that at least one node has `status="error"`.
7. Verify that the HTML file contains the error color (`#f44336`).

---

## Test Organization Conventions

### Fixtures

A `conftest.py` file at the `tests/` level may define shared fixtures such as:

- `clean_trace` — calls `reset_trace()` before each test using `autouse=True` for instrumentation tests.
- `sample_trace` — returns a minimal valid trace list for graph builder tests.
- `simple_graph` — returns a built graph for visualization tests.
- `test_output_dir` — returns a temporary directory path for HTML output tests.

### Naming Conventions

- All test functions are prefixed with `test_`.
- Test module names match the subsystem: `test_<subsystem>.py`.
- Test functions describe the behavior being verified: `test_nested_calls_produce_parent_child_relationship`.

### Assertions

- Use plain `assert` statements rather than custom assertion helpers.
- Keep assertions specific: check exact values, not just truthiness where values are known.

---

## Expected Outcome

After implementing and running the full test suite:

- All tests in `tests/` pass with `pytest tests/ -v`.
- The test suite acts as a regression harness for future changes.
- Each subsystem's contract is documented via executable specifications.
- The prototype is validated end-to-end: from decorated functions to rendered HTML.
