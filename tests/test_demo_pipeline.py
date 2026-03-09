"""
tests/test_demo_pipeline.py — Tests for the synthetic demo pipeline.

Validates:
- Success path produces a non-empty trace with events from multiple modules
- Success path returns a non-empty string report
- Success path converts into a graph with nodes and edges
- Failure path raises ValueError
- Failure path records at least one error trace event
- Failure path still produces a usable partial graph
- All four expected modules appear in a successful trace
"""

from __future__ import annotations

import pytest

from graph.graph_builder import build_graph
from instrumentation.trace_collector import get_trace, reset_trace
from pipeline.demo_pipeline import run_demo_pipeline


# ---------------------------------------------------------------------------
# Fixture — clean trace before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    reset_trace()
    yield
    reset_trace()


# ---------------------------------------------------------------------------
# 4.1  Success path produces a non-empty trace
# ---------------------------------------------------------------------------

class TestSuccessPathTrace:

    def test_trace_is_non_empty_after_success_run(self):
        run_demo_pipeline(base=5, multiplier=3)
        assert len(get_trace()) > 0

    def test_trace_contains_multiple_events(self):
        run_demo_pipeline(base=5, multiplier=3)
        assert len(get_trace()) >= 5  # at minimum math + validation + report steps

    def test_all_events_have_required_fields(self):
        run_demo_pipeline(base=5, multiplier=3)
        required = {"task_name", "status", "trace_index", "module_name", "duration_ms"}
        for event in get_trace():
            assert required.issubset(event.keys())

    def test_trace_indices_are_sequential(self):
        run_demo_pipeline(base=5, multiplier=3)
        trace = get_trace()
        for i, event in enumerate(trace):
            assert event["trace_index"] == i


# ---------------------------------------------------------------------------
# 4.3  Success path does not raise
# ---------------------------------------------------------------------------

class TestSuccessPathNoException:

    def test_success_path_does_not_raise(self):
        run_demo_pipeline(base=5, multiplier=3)  # should not raise


# ---------------------------------------------------------------------------
# 4.4  Success path returns a non-empty string report
# ---------------------------------------------------------------------------

class TestSuccessPathReturnValue:

    def test_return_value_is_string(self):
        result = run_demo_pipeline(base=5, multiplier=3)
        assert isinstance(result, str)

    def test_return_value_is_non_empty(self):
        result = run_demo_pipeline(base=5, multiplier=3)
        assert len(result) > 0

    def test_return_value_contains_report_header(self):
        result = run_demo_pipeline(base=5, multiplier=3)
        assert "PIPELINE REPORT" in result.upper()


# ---------------------------------------------------------------------------
# 4.2  Success path produces graph nodes and edges
# ---------------------------------------------------------------------------

class TestSuccessPathGraph:

    def test_success_trace_converts_to_graph(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        assert graph.number_of_nodes() > 0

    def test_success_graph_has_edges(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        assert graph.number_of_edges() > 0


# ---------------------------------------------------------------------------
# 4.5 + 4.6  Failure path records error and raises ValueError
# ---------------------------------------------------------------------------

class TestFailurePath:

    def test_failure_path_raises_value_error(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)

    def test_failure_path_records_error_event(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        trace = get_trace()
        error_events = [e for e in trace if e["status"] == "error"]
        assert len(error_events) >= 1

    def test_failure_error_event_has_error_message(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        error_events = [e for e in get_trace() if e["status"] == "error"]
        assert error_events[0]["error_message"] is not None
        assert len(error_events[0]["error_message"]) > 0

    def test_failure_error_references_score_range(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        error_events = [e for e in get_trace() if e["status"] == "error"]
        # The error comes from validate_score_range
        assert any("range" in (e["error_message"] or "").lower()
                   or "score" in (e["error_message"] or "").lower()
                   for e in error_events)


# ---------------------------------------------------------------------------
# 4.7  Failure path still produces a partial graph
# ---------------------------------------------------------------------------

class TestFailureModePartialGraph:

    def test_partial_trace_converts_to_graph(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        assert graph.number_of_nodes() > 0

    def test_partial_graph_contains_error_node(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        error_nodes = [
            nid for nid, data in graph.nodes(data=True)
            if data["status"] == "error"
        ]
        assert len(error_nodes) >= 1


# ---------------------------------------------------------------------------
# 4.8  All expected modules appear in a successful trace
# ---------------------------------------------------------------------------

class TestModuleCoverage:

    def test_math_operations_module_present(self):
        run_demo_pipeline(base=5, multiplier=3)
        modules = {e["module_name"] for e in get_trace()}
        assert "Math Operations" in modules

    def test_text_construction_module_present(self):
        run_demo_pipeline(base=5, multiplier=3)
        modules = {e["module_name"] for e in get_trace()}
        assert "Text Construction" in modules

    def test_text_transformation_module_present(self):
        run_demo_pipeline(base=5, multiplier=3)
        modules = {e["module_name"] for e in get_trace()}
        assert "Text Transformation" in modules

    def test_validation_module_present(self):
        run_demo_pipeline(base=5, multiplier=3)
        modules = {e["module_name"] for e in get_trace()}
        assert "Validation" in modules

    def test_all_success_events_on_success_path(self):
        run_demo_pipeline(base=5, multiplier=3)
        statuses = {e["status"] for e in get_trace()}
        assert "error" not in statuses
        assert "success" in statuses
