"""
tests/test_graph_builder.py — Tests for the trace-to-graph builder.

Validates:
- Sequential trace events produce correct node count with no edges
- Parent-child trace events produce directed edges
- Node IDs follow the task_name__trace_index scheme
- All trace metadata is preserved on nodes
- Error events appear as nodes with status="error"
- Repeated calls to the same function produce distinct nodes
- graph_debug_summary returns correct counts and structure
"""

from __future__ import annotations

import pytest

from graph.graph_builder import (
    build_graph,
    graph_debug_summary,
    list_graph_edges,
    list_graph_nodes,
    make_node_id,
    validate_trace_event,
)
from tests.conftest import _make_event


# ---------------------------------------------------------------------------
# 2.1 + 2.2  Sequential tasks — node count and no edges
# ---------------------------------------------------------------------------

class TestSequentialTrace:

    def test_two_sequential_events_produce_two_nodes(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        assert graph.number_of_nodes() == 2

    def test_two_sequential_events_produce_zero_edges(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        assert graph.number_of_edges() == 0

    def test_empty_trace_produces_empty_graph(self):
        graph = build_graph([])
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_single_event_produces_one_node(self):
        event = _make_event(task_name="solo_task", trace_index=0)
        graph = build_graph([event])
        assert graph.number_of_nodes() == 1


# ---------------------------------------------------------------------------
# 2.3  Parent-child events produce directed edges
# ---------------------------------------------------------------------------

class TestNestedTrace:

    def test_nested_events_produce_edges(self, nested_events):
        graph = build_graph(nested_events)
        assert graph.number_of_edges() == 2

    def test_edge_direction_is_parent_to_child(self, nested_events):
        graph = build_graph(nested_events)
        # parent_task__2 → child_a__0 and parent_task__2 → child_b__1
        assert graph.has_edge("parent_task__2", "child_a__0")
        assert graph.has_edge("parent_task__2", "child_b__1")

    def test_no_edge_from_child_to_parent(self, nested_events):
        graph = build_graph(nested_events)
        assert not graph.has_edge("child_a__0", "parent_task__2")
        assert not graph.has_edge("child_b__1", "parent_task__2")

    def test_nested_events_produce_three_nodes(self, nested_events):
        graph = build_graph(nested_events)
        assert graph.number_of_nodes() == 3


# ---------------------------------------------------------------------------
# 2.4  Node IDs follow the correct scheme
# ---------------------------------------------------------------------------

class TestNodeIdScheme:

    def test_make_node_id_format(self):
        assert make_node_id("my_function", 5) == "my_function__5"

    def test_make_node_id_zero_index(self):
        assert make_node_id("foo", 0) == "foo__0"

    def test_node_ids_in_graph_follow_scheme(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        assert "task_a__0" in graph.nodes
        assert "task_b__1" in graph.nodes

    def test_node_id_attribute_matches_graph_key(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        for node_id, data in graph.nodes(data=True):
            assert data["node_id"] == node_id


# ---------------------------------------------------------------------------
# 2.5  Node attributes mirror trace event fields
# ---------------------------------------------------------------------------

class TestNodeAttributes:

    def test_task_name_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["task_name"] == "task_a"

    def test_task_description_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["task_description"] == "A sample task"

    def test_module_name_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["module_name"] == "Test Module"

    def test_status_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["status"] == "success"

    def test_trace_index_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["trace_index"] == 0

    def test_input_preview_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["input_preview"] is not None

    def test_output_preview_preserved(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["output_preview"] is not None

    def test_error_message_is_none_for_success_node(self, two_sequential_events):
        graph = build_graph(two_sequential_events)
        node_data = graph.nodes["task_a__0"]
        assert node_data["error_message"] is None


# ---------------------------------------------------------------------------
# 2.6  Error events appear as nodes with status="error"
# ---------------------------------------------------------------------------

class TestErrorNode:

    def test_error_event_produces_node(self, error_event):
        graph = build_graph(error_event)
        assert graph.number_of_nodes() == 1

    def test_error_node_has_error_status(self, error_event):
        graph = build_graph(error_event)
        node_data = graph.nodes["failing_task__0"]
        assert node_data["status"] == "error"

    def test_error_node_has_error_message(self, error_event):
        graph = build_graph(error_event)
        node_data = graph.nodes["failing_task__0"]
        assert node_data["error_message"] == "Something went wrong"


# ---------------------------------------------------------------------------
# 2.7  Repeated calls produce distinct nodes
# ---------------------------------------------------------------------------

class TestRepeatedCalls:

    def test_two_calls_to_same_function_produce_two_nodes(self):
        events = [
            _make_event(task_name="repeated_func", trace_index=0),
            _make_event(task_name="repeated_func", trace_index=1),
        ]
        graph = build_graph(events)
        assert graph.number_of_nodes() == 2

    def test_repeated_call_node_ids_are_distinct(self):
        events = [
            _make_event(task_name="repeated_func", trace_index=0),
            _make_event(task_name="repeated_func", trace_index=1),
        ]
        graph = build_graph(events)
        assert "repeated_func__0" in graph.nodes
        assert "repeated_func__1" in graph.nodes

    def test_repeated_calls_have_no_edges_when_sequential(self):
        events = [
            _make_event(task_name="repeated_func", trace_index=0),
            _make_event(task_name="repeated_func", trace_index=1),
        ]
        graph = build_graph(events)
        assert graph.number_of_edges() == 0


# ---------------------------------------------------------------------------
# 2.8  graph_debug_summary returns correct structure
# ---------------------------------------------------------------------------

class TestDebugSummary:

    def test_summary_num_nodes(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        assert summary["num_nodes"] == 3

    def test_summary_num_edges(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        assert summary["num_edges"] == 2

    def test_summary_root_nodes_contains_parent(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        assert "parent_task__2" in summary["root_nodes"]

    def test_summary_status_counts_all_success(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        assert summary["status_counts"].get("success", 0) == 3

    def test_summary_module_counts_correct(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        assert summary["module_counts"].get("Test Module", 0) == 3

    def test_summary_keys_present(self, nested_events):
        graph = build_graph(nested_events)
        summary = graph_debug_summary(graph)
        required_keys = {"num_nodes", "num_edges", "root_nodes", "nodes", "edges",
                         "module_counts", "status_counts"}
        assert required_keys.issubset(summary.keys())


# ---------------------------------------------------------------------------
# validate_trace_event
# ---------------------------------------------------------------------------

class TestValidateTraceEvent:

    def test_valid_event_does_not_raise(self):
        event = _make_event()
        validate_trace_event(event)  # should not raise

    def test_missing_field_raises_value_error(self):
        event = _make_event()
        del event["task_name"]
        with pytest.raises(ValueError, match="missing required fields"):
            validate_trace_event(event)


# ---------------------------------------------------------------------------
# list_graph_nodes and list_graph_edges helpers
# ---------------------------------------------------------------------------

class TestListHelpers:

    def test_list_graph_nodes_sorted_by_trace_index(self, nested_events):
        graph = build_graph(nested_events)
        nodes = list_graph_nodes(graph)
        indices = [n["trace_index"] for n in nodes]
        assert indices == sorted(indices)

    def test_list_graph_edges_returns_from_and_to(self, nested_events):
        graph = build_graph(nested_events)
        edges = list_graph_edges(graph)
        assert len(edges) == 2
        for edge in edges:
            assert "from_node" in edge
            assert "to_node" in edge
            assert "relationship" in edge

    def test_list_graph_edges_relationship_is_calls(self, nested_events):
        graph = build_graph(nested_events)
        edges = list_graph_edges(graph)
        for edge in edges:
            assert edge["relationship"] == "calls"
