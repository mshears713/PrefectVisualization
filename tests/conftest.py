"""
tests/conftest.py — Shared pytest fixtures for the test suite.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from instrumentation.trace_collector import reset_trace, record_event
from graph.graph_builder import build_graph


# ---------------------------------------------------------------------------
# Trace isolation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def clean_trace():
    """Reset the global trace before and after each test that uses it."""
    reset_trace()
    yield
    reset_trace()


# ---------------------------------------------------------------------------
# Minimal trace factories
# ---------------------------------------------------------------------------

def _make_event(
    task_name="sample_task",
    task_description="A sample task",
    module_name="Test Module",
    parent_task=None,
    trace_index=0,
    status="success",
    error_message=None,
    duration_ms=1.0,
):
    """Return a minimal, valid TraceEvent dict."""
    import time
    t = time.perf_counter()
    return {
        "task_name": task_name,
        "task_description": task_description,
        "module_name": module_name,
        "parent_task": parent_task,
        "trace_index": trace_index,
        "start_time": t,
        "end_time": t + duration_ms / 1000.0,
        "duration_ms": duration_ms,
        "status": status,
        "input_preview": "length=2, head='x'",
        "output_preview": "length=2, head='y'",
        "input_length": 2,
        "output_length": 2,
        "error_message": error_message,
    }


@pytest.fixture
def two_sequential_events():
    """Two independent trace events with no parent-child relationship."""
    return [
        _make_event(task_name="task_a", trace_index=0),
        _make_event(task_name="task_b", trace_index=1),
    ]


@pytest.fixture
def nested_events():
    """Three events: child_a and child_b nested inside parent_task."""
    return [
        _make_event(task_name="child_a", trace_index=0, parent_task="parent_task"),
        _make_event(task_name="child_b", trace_index=1, parent_task="parent_task"),
        _make_event(task_name="parent_task", trace_index=2, parent_task=None),
    ]


@pytest.fixture
def error_event():
    """A single trace event with status='error'."""
    return [
        _make_event(
            task_name="failing_task",
            trace_index=0,
            status="error",
            error_message="Something went wrong",
        )
    ]


@pytest.fixture
def simple_graph(two_sequential_events):
    """A small graph built from two sequential events."""
    return build_graph(two_sequential_events)


@pytest.fixture
def nested_graph(nested_events):
    """A graph with parent-child edges."""
    return build_graph(nested_events)


# ---------------------------------------------------------------------------
# Temporary output directory
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Return a temporary directory path for HTML output files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)
