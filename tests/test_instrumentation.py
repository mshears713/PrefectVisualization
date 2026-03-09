"""
tests/test_instrumentation.py — Tests for the instrumentation layer.

Validates:
- @task decorator records trace events with correct metadata
- @module decorator attaches module names to trace events
- Nested calls produce parent-child relationships
- Execution order is preserved (trace_index ascends)
- Error events are recorded with status="error" before exception re-raises
- reset_trace() clears all state
- Input/output previews are populated
"""

from __future__ import annotations

import pytest

from instrumentation.decorators import module, task
from instrumentation.trace_collector import (
    execution_stack,
    get_trace,
    reset_trace,
)


# ---------------------------------------------------------------------------
# Helpers — define simple instrumented functions for testing
# ---------------------------------------------------------------------------

@module("Math Operations")
@task("Add two numbers")
def _add(a, b):
    return a + b


@task("Multiply two numbers")
def _multiply(a, b):
    return a * b


@module("Math Operations")
@task("Compute pipeline: add then multiply")
def _compute(a, b):
    s = _add(a, b)
    return _multiply(s, 2)


@module("Math Operations")
@task("A task that always raises")
def _failing_task(x):
    raise ValueError(f"Intentional error: {x}")


# ---------------------------------------------------------------------------
# Fixture — ensure clean trace for every test in this module
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    reset_trace()
    yield
    reset_trace()


# ---------------------------------------------------------------------------
# 1.1  Single decorated function produces a trace event
# ---------------------------------------------------------------------------

class TestSingleDecoratedFunction:

    def test_event_is_recorded_after_call(self):
        _add(3, 4)
        trace = get_trace()
        assert len(trace) == 1

    def test_task_name_matches_function_name(self):
        _add(3, 4)
        event = get_trace()[0]
        assert event["task_name"] == "_add"

    def test_task_description_is_stored(self):
        _add(3, 4)
        event = get_trace()[0]
        assert event["task_description"] == "Add two numbers"

    def test_status_is_success(self):
        _add(3, 4)
        event = get_trace()[0]
        assert event["status"] == "success"

    def test_duration_ms_is_non_negative(self):
        _add(3, 4)
        event = get_trace()[0]
        assert event["duration_ms"] >= 0

    def test_trace_index_is_zero_for_first_call(self):
        _add(3, 4)
        event = get_trace()[0]
        assert event["trace_index"] == 0


# ---------------------------------------------------------------------------
# 1.2  Module name is preserved
# ---------------------------------------------------------------------------

class TestModuleName:

    def test_module_name_recorded_when_decorator_present(self):
        _add(1, 2)
        event = get_trace()[0]
        assert event["module_name"] == "Math Operations"

    def test_module_name_is_empty_without_module_decorator(self):
        _multiply(3, 4)
        event = get_trace()[0]
        assert event["module_name"] == ""


# ---------------------------------------------------------------------------
# 1.3  Nested calls produce parent-child relationships
# ---------------------------------------------------------------------------

class TestNestedCalls:

    def test_children_have_parent_task_set(self):
        _compute(2, 3)
        trace = get_trace()
        # _add and _multiply are children; _compute is the root
        child_names = {e["task_name"] for e in trace if e["parent_task"] is not None}
        assert "_add" in child_names
        assert "_multiply" in child_names

    def test_root_has_no_parent(self):
        _compute(2, 3)
        trace = get_trace()
        root_events = [e for e in trace if e["task_name"] == "_compute"]
        assert len(root_events) == 1
        assert root_events[0]["parent_task"] is None

    def test_children_parent_task_points_to_compute(self):
        _compute(2, 3)
        trace = get_trace()
        for event in trace:
            if event["task_name"] in ("_add", "_multiply"):
                assert event["parent_task"] == "_compute"


# ---------------------------------------------------------------------------
# 1.4  Execution order is preserved
# ---------------------------------------------------------------------------

class TestExecutionOrder:

    def test_two_sequential_calls_have_ascending_trace_indices(self):
        _add(1, 2)
        _multiply(3, 4)
        trace = get_trace()
        assert trace[0]["trace_index"] == 0
        assert trace[1]["trace_index"] == 1

    def test_trace_indices_match_list_positions(self):
        _add(1, 2)
        _add(3, 4)
        _add(5, 6)
        trace = get_trace()
        for i, event in enumerate(trace):
            assert event["trace_index"] == i


# ---------------------------------------------------------------------------
# 1.5  Error events are recorded before re-raising
# ---------------------------------------------------------------------------

class TestErrorCapture:

    def test_exception_is_re_raised(self):
        with pytest.raises(ValueError):
            _failing_task("oops")

    def test_error_event_is_recorded(self):
        with pytest.raises(ValueError):
            _failing_task("oops")
        trace = get_trace()
        assert len(trace) == 1

    def test_error_event_has_error_status(self):
        with pytest.raises(ValueError):
            _failing_task("oops")
        event = get_trace()[0]
        assert event["status"] == "error"

    def test_error_message_contains_exception_text(self):
        with pytest.raises(ValueError):
            _failing_task("oops")
        event = get_trace()[0]
        assert "Intentional error" in event["error_message"]

    def test_error_output_preview_is_empty_string(self):
        with pytest.raises(ValueError):
            _failing_task("oops")
        event = get_trace()[0]
        assert event["output_preview"] == ""


# ---------------------------------------------------------------------------
# 1.6  reset_trace clears all state
# ---------------------------------------------------------------------------

class TestTraceReset:

    def test_trace_is_empty_after_reset(self):
        _add(1, 2)
        assert len(get_trace()) == 1
        reset_trace()
        assert get_trace() == []

    def test_execution_stack_is_empty_after_reset(self):
        reset_trace()
        assert execution_stack == []

    def test_trace_index_restarts_at_zero_after_reset(self):
        _add(1, 2)
        reset_trace()
        _add(3, 4)
        event = get_trace()[0]
        assert event["trace_index"] == 0


# ---------------------------------------------------------------------------
# 1.7  Input and output previews are populated
# ---------------------------------------------------------------------------

class TestInputOutputPreviews:

    def test_input_preview_is_non_empty(self):
        _add(10, 20)
        event = get_trace()[0]
        assert event["input_preview"] != ""

    def test_output_preview_is_non_empty(self):
        _add(10, 20)
        event = get_trace()[0]
        assert event["output_preview"] != ""

    def test_input_length_is_positive(self):
        _add(10, 20)
        event = get_trace()[0]
        assert event["input_length"] > 0

    def test_output_length_is_positive(self):
        _add(10, 20)
        event = get_trace()[0]
        assert event["output_length"] > 0

    def test_error_message_is_none_on_success(self):
        _add(1, 2)
        event = get_trace()[0]
        assert event["error_message"] is None
