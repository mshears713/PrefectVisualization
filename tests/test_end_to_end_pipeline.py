"""
tests/test_end_to_end_pipeline.py — Full integration tests for the entire pipeline.

Exercises the complete stack:
    instrumentation → trace collection → graph building → HTML rendering

Validates:
- Full success pipeline produces a valid HTML artifact with nodes and edges
- Failure pipeline still produces a partial graph with an error node
- HTML artifact contains node names from the original pipeline
- End-to-end run is deterministic for the same inputs
"""

from __future__ import annotations

import os

import pytest

from graph.graph_builder import build_graph, graph_debug_summary
from graph.graph_visualizer import render_graph_html
from instrumentation.trace_collector import get_trace, reset_trace
from pipeline.demo_pipeline import run_demo_pipeline


# ---------------------------------------------------------------------------
# Fixture — clean trace and temp output directory
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    reset_trace()
    yield
    reset_trace()


# ---------------------------------------------------------------------------
# Full success integration scenario
# ---------------------------------------------------------------------------

class TestEndToEndSuccess:

    def test_full_pipeline_produces_html_file(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        trace = get_trace()
        graph = build_graph(trace)
        out_path = os.path.join(tmp_output_dir, "e2e_success.html")
        render_graph_html(graph, out_path)
        assert os.path.exists(out_path)

    def test_html_file_is_non_empty(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        out_path = os.path.join(tmp_output_dir, "e2e_success.html")
        render_graph_html(graph, out_path)
        assert os.path.getsize(out_path) > 0

    def test_graph_has_nodes(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        assert graph.number_of_nodes() > 0

    def test_graph_has_edges(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        assert graph.number_of_edges() > 0

    def test_all_trace_events_are_success(self):
        run_demo_pipeline(base=5, multiplier=3)
        trace = get_trace()
        statuses = {e["status"] for e in trace}
        assert "error" not in statuses

    def test_html_contains_run_demo_pipeline_node(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        out_path = os.path.join(tmp_output_dir, "e2e_nodes.html")
        render_graph_html(graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        # The top-level pipeline task should appear in the HTML
        assert "run_demo_pipeline" in content

    def test_html_contains_math_task(self, tmp_output_dir):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        out_path = os.path.join(tmp_output_dir, "e2e_math.html")
        render_graph_html(graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "add_numbers" in content

    def test_debug_summary_has_correct_structure(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        summary = graph_debug_summary(graph)
        assert summary["num_nodes"] > 0
        assert summary["num_edges"] > 0
        assert len(summary["module_counts"]) >= 4  # all four modules


# ---------------------------------------------------------------------------
# End-to-end determinism
# ---------------------------------------------------------------------------

class TestEndToEndDeterminism:

    def test_same_inputs_produce_same_node_count(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph1 = build_graph(get_trace())
        node_count1 = graph1.number_of_nodes()

        reset_trace()

        run_demo_pipeline(base=5, multiplier=3)
        graph2 = build_graph(get_trace())
        node_count2 = graph2.number_of_nodes()

        assert node_count1 == node_count2

    def test_same_inputs_produce_same_edge_count(self):
        run_demo_pipeline(base=5, multiplier=3)
        edge_count1 = build_graph(get_trace()).number_of_edges()

        reset_trace()

        run_demo_pipeline(base=5, multiplier=3)
        edge_count2 = build_graph(get_trace()).number_of_edges()

        assert edge_count1 == edge_count2


# ---------------------------------------------------------------------------
# Failure mode integration scenario
# ---------------------------------------------------------------------------

class TestEndToEndFailure:

    def test_failure_pipeline_html_file_is_created(self, tmp_output_dir):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        out_path = os.path.join(tmp_output_dir, "e2e_failure.html")
        render_graph_html(graph, out_path)
        assert os.path.exists(out_path)

    def test_failure_graph_has_at_least_one_node(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        assert graph.number_of_nodes() > 0

    def test_failure_graph_has_error_node(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        error_nodes = [
            nid for nid, data in graph.nodes(data=True)
            if data.get("status") == "error"
        ]
        assert len(error_nodes) >= 1

    def test_failure_html_contains_error_color(self, tmp_output_dir):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        graph = build_graph(get_trace())
        out_path = os.path.join(tmp_output_dir, "e2e_failure_color.html")
        render_graph_html(graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Error nodes should be red
        assert "#f44336" in content

    def test_failure_trace_contains_both_success_and_error_events(self):
        with pytest.raises(ValueError):
            run_demo_pipeline(fail_mode=True)
        trace = get_trace()
        statuses = {e["status"] for e in trace}
        assert "success" in statuses
        assert "error" in statuses


# ---------------------------------------------------------------------------
# Multi-module coverage check
# ---------------------------------------------------------------------------

class TestEndToEndModuleCoverage:

    def test_all_four_modules_represented_in_graph(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        summary = graph_debug_summary(graph)
        modules = set(summary["module_counts"].keys())
        assert "Math Operations" in modules
        assert "Text Construction" in modules
        assert "Text Transformation" in modules
        assert "Validation" in modules

    def test_pipeline_module_is_in_graph(self):
        run_demo_pipeline(base=5, multiplier=3)
        graph = build_graph(get_trace())
        summary = graph_debug_summary(graph)
        modules = set(summary["module_counts"].keys())
        assert "Pipeline" in modules
