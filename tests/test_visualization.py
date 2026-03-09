"""
tests/test_visualization.py — Tests for the graph visualization layer.

Validates:
- render_graph_html produces a non-empty HTML file
- HTML content contains task names from the graph
- status_to_color maps status strings to correct hex values
- make_node_title includes required metadata fields
- build_pyvis_network produces a network with the correct node/edge counts
"""

from __future__ import annotations

import os

import pytest

from graph.graph_builder import build_graph
from graph.graph_visualizer import (
    build_pyvis_network,
    make_node_title,
    render_graph_html,
    status_to_color,
)
from tests.conftest import _make_event


# ---------------------------------------------------------------------------
# 3.4  Status color mapping
# ---------------------------------------------------------------------------

class TestStatusToColor:

    def test_success_maps_to_green(self):
        assert status_to_color("success") == "#4caf50"

    def test_error_maps_to_red(self):
        assert status_to_color("error") == "#f44336"

    def test_warning_maps_to_amber(self):
        assert status_to_color("warning") == "#ff9800"

    def test_unknown_maps_to_fallback_grey(self):
        assert status_to_color("unknown_value") == "#90a4ae"

    def test_empty_string_maps_to_fallback_grey(self):
        assert status_to_color("") == "#90a4ae"


# ---------------------------------------------------------------------------
# 3.5  Node tooltip contains task metadata
# ---------------------------------------------------------------------------

class TestMakeNodeTitle:

    @pytest.fixture
    def sample_node_data(self):
        return {
            "task_name": "my_function",
            "task_description": "Does something useful",
            "module_name": "My Module",
            "status": "success",
            "duration_ms": 12.3456,
            "input_length": 10,
            "input_preview": "length=10, head='abc'",
            "output_length": 5,
            "output_preview": "length=5, head='xyz'",
            "error_message": None,
        }

    def test_tooltip_contains_task_name(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "my_function" in title

    def test_tooltip_contains_module_name(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "My Module" in title

    def test_tooltip_contains_status(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "success" in title

    def test_tooltip_contains_duration(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "12.3456" in title

    def test_tooltip_contains_description(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "Does something useful" in title

    def test_tooltip_does_not_include_error_section_on_success(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert "Error:" not in title

    def test_tooltip_includes_error_section_on_failure(self, sample_node_data):
        sample_node_data["error_message"] = "Something went wrong"
        title = make_node_title(sample_node_data)
        assert "Error:" in title
        assert "Something went wrong" in title

    def test_tooltip_is_html_string(self, sample_node_data):
        title = make_node_title(sample_node_data)
        assert isinstance(title, str)
        assert "<b>" in title


# ---------------------------------------------------------------------------
# 3.6  build_pyvis_network produces correct node/edge counts
# ---------------------------------------------------------------------------

class TestBuildPyvisNetwork:

    def test_network_has_correct_node_count(self, simple_graph):
        net = build_pyvis_network(simple_graph)
        assert len(net.nodes) == 2

    def test_network_has_correct_edge_count(self, nested_graph):
        net = build_pyvis_network(nested_graph)
        assert len(net.edges) == 2

    def test_network_node_labels_match_task_names(self, simple_graph):
        net = build_pyvis_network(simple_graph)
        labels = {node["label"] for node in net.nodes}
        assert "task_a" in labels
        assert "task_b" in labels

    def test_network_nodes_have_color(self, simple_graph):
        net = build_pyvis_network(simple_graph)
        for node in net.nodes:
            assert "color" in node

    def test_empty_graph_produces_empty_network(self):
        graph = build_graph([])
        net = build_pyvis_network(graph)
        assert len(net.nodes) == 0


# ---------------------------------------------------------------------------
# 3.1 + 3.2  render_graph_html creates a non-empty HTML file
# ---------------------------------------------------------------------------

class TestRenderGraphHtml:

    def test_html_file_is_created(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "test_graph.html")
        render_graph_html(simple_graph, out_path)
        assert os.path.exists(out_path)

    def test_html_file_is_non_empty(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "test_graph.html")
        render_graph_html(simple_graph, out_path)
        assert os.path.getsize(out_path) > 0

    def test_render_does_not_raise(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "test_graph.html")
        render_graph_html(simple_graph, out_path)  # should not raise

    def test_render_returns_absolute_path(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "test_graph.html")
        result = render_graph_html(simple_graph, out_path)
        assert os.path.isabs(result)


# ---------------------------------------------------------------------------
# 3.3  HTML content contains task names
# ---------------------------------------------------------------------------

class TestHtmlContent:

    def test_html_contains_task_names(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "content_test.html")
        render_graph_html(simple_graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "task_a" in content
        assert "task_b" in content

    def test_html_contains_error_color_for_error_graph(self, tmp_output_dir):
        events = [
            _make_event(task_name="broken_task", trace_index=0,
                        status="error", error_message="failure")
        ]
        graph = build_graph(events)
        out_path = os.path.join(tmp_output_dir, "error_graph.html")
        render_graph_html(graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "#f44336" in content

    def test_html_contains_success_color_for_success_graph(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "success_graph.html")
        render_graph_html(simple_graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "#4caf50" in content

    def test_html_is_valid_html_document(self, simple_graph, tmp_output_dir):
        out_path = os.path.join(tmp_output_dir, "valid_html.html")
        render_graph_html(simple_graph, out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        # PyVis produces a full HTML document
        assert "<html" in content.lower()

    def test_render_creates_output_directory_if_missing(self, tmp_path, simple_graph):
        nested_dir = str(tmp_path / "deeply" / "nested" / "output")
        out_path = os.path.join(nested_dir, "graph.html")
        render_graph_html(simple_graph, out_path)
        assert os.path.exists(out_path)
