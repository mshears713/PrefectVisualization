"""
demo_prd3_visualization_test.py — Verification script for PRD 03 (Visualization).

Run with:
    python demo_prd3_visualization_test.py

What this script demonstrates
------------------------------
1. Full pipeline render    — decorated program → trace → graph → HTML file.
2. Error node render       — a failed task produces a red node in the graph.
3. Multi-module render     — tasks from different modules are grouped
                              separately in the visualization.
4. Repeated task render    — the same function called twice produces two
                              distinct nodes.
5. Output file exists      — all tests verify that the HTML file was written.

After running this script, open the generated HTML files in a browser to
inspect the interactive graphs visually.
"""

import os
import sys

from instrumentation.decorators import module, task
from instrumentation.trace_collector import get_trace, reset_trace
from graph.graph_builder import build_graph
from graph.graph_visualizer import (
    render_graph_html,
    build_pyvis_network,
    make_node_title,
    status_to_color,
)


# ---------------------------------------------------------------------------
# Decorated demo functions
# ---------------------------------------------------------------------------

@module("Math Operations")
@task("Add two numbers to compute an intermediate value")
def add_numbers(a, b):
    return a + b


@module("Math Operations")
@task("Multiply two numbers to scale a result")
def multiply_numbers(a, b):
    return a * b


@module("Math Operations")
@task("Compute a combined math result by adding then multiplying")
def compute_pipeline(a, b):
    added = add_numbers(a, b)
    return multiply_numbers(added, 10)


@module("Text Construction")
@task("Convert a number into a descriptive sentence")
def build_sentence(number):
    return f"The computed result is {number}."


@module("Math Operations")
@task("Divide two numbers — raises ZeroDivisionError when divisor is zero")
def divide_numbers(a, b):
    return a / b


# ---------------------------------------------------------------------------
# Test 1 — Full pipeline: program → trace → graph → HTML
# ---------------------------------------------------------------------------

def test_full_pipeline_render():
    print("\n>>> Test 1: Full pipeline render")
    reset_trace()

    result = compute_pipeline(5, 7)
    sentence = build_sentence(result)
    try:
        divide_numbers(result, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    graph = build_graph(trace)
    out_path = render_graph_html(graph, "output/test1_full_pipeline.html")

    assert os.path.exists(out_path), f"HTML file not found: {out_path}"
    with open(out_path, encoding="utf-8") as f:
        html = f.read()
    assert len(html) > 1000, "HTML output looks suspiciously small"
    assert "compute_pipeline" in html
    assert "add_numbers" in html
    assert "multiply_numbers" in html
    assert "build_sentence" in html
    assert "divide_numbers" in html

    print(f"  HTML written to: {out_path}")
    print(f"  File size      : {os.path.getsize(out_path):,} bytes")
    print(f"  Final sentence : {sentence!r}")
    print(f"  Nodes in graph : {graph.number_of_nodes()}")
    print(f"  Edges in graph : {graph.number_of_edges()}")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Error node renders as red node
# ---------------------------------------------------------------------------

def test_error_node_render():
    print("\n>>> Test 2: Error node render")
    reset_trace()

    try:
        divide_numbers(10, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    graph = build_graph(trace)
    out_path = render_graph_html(graph, "output/test2_error_node.html")

    assert os.path.exists(out_path)
    with open(out_path, encoding="utf-8") as f:
        html = f.read()
    # The error colour hex should appear in the rendered HTML
    assert "#f44336" in html, "Expected error colour #f44336 not found in HTML"
    assert "divide_numbers" in html
    assert "division by zero" in html

    print(f"  HTML written to: {out_path}")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — Multi-module graph shows distinct module groups
# ---------------------------------------------------------------------------

def test_multi_module_render():
    print("\n>>> Test 3: Multi-module render")
    reset_trace()

    add_numbers(1, 2)
    build_sentence(42)
    multiply_numbers(3, 4)

    trace = get_trace()
    graph = build_graph(trace)
    out_path = render_graph_html(graph, "output/test3_multi_module.html")

    assert os.path.exists(out_path)
    with open(out_path, encoding="utf-8") as f:
        html = f.read()
    assert "Math Operations" in html
    assert "Text Construction" in html

    print(f"  HTML written to: {out_path}")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Repeated task execution → two distinct nodes
# ---------------------------------------------------------------------------

def test_repeated_task_render():
    print("\n>>> Test 4: Repeated task render")
    reset_trace()

    add_numbers(1, 2)
    add_numbers(10, 20)

    trace = get_trace()
    graph = build_graph(trace)
    out_path = render_graph_html(graph, "output/test4_repeated_task.html")

    assert os.path.exists(out_path)
    with open(out_path, encoding="utf-8") as f:
        html = f.read()
    # Both node IDs should appear in the serialized graph data
    assert "add_numbers__0" in html
    assert "add_numbers__1" in html

    print(f"  HTML written to: {out_path}")
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Helper unit tests
# ---------------------------------------------------------------------------

def test_helpers():
    print("\n>>> Test 5: Helper function unit tests")

    # status_to_color
    assert status_to_color("success") == "#4caf50"
    assert status_to_color("error")   == "#f44336"
    assert status_to_color("unknown") == "#90a4ae"   # neutral fallback

    # make_node_title
    node_data = {
        "task_name": "add_numbers",
        "task_description": "Add two numbers",
        "module_name": "Math Operations",
        "status": "success",
        "duration_ms": 0.0128,
        "input_length": 4,
        "input_preview": "length=4, head='3, 4'",
        "output_length": 1,
        "output_preview": "length=1, head='7'",
        "error_message": None,
    }
    title = make_node_title(node_data)
    assert "add_numbers" in title
    assert "Add two numbers" in title
    assert "Math Operations" in title
    assert "success" in title

    # error message included only when present
    assert "Error" not in title

    error_data = {**node_data, "status": "error", "error_message": "division by zero"}
    error_title = make_node_title(error_data)
    assert "division by zero" in error_title

    # build_pyvis_network returns a Network object
    reset_trace()
    add_numbers(2, 3)
    trace = get_trace()
    graph = build_graph(trace)
    net = build_pyvis_network(graph)
    assert len(net.get_nodes()) == 1
    assert len(net.get_edges()) == 0

    print("  PASSED")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_full_pipeline_render,
        test_error_node_render,
        test_multi_module_render,
        test_repeated_task_render,
        test_helpers,
    ]
    for test_fn in tests:
        try:
            test_fn()
        except AssertionError as exc:
            print(f"  FAILED: {exc}")
            all_passed = False
        except Exception as exc:
            import traceback
            print(f"  ERROR (unexpected):")
            traceback.print_exc()
            all_passed = False

    print()
    if all_passed:
        print("All tests passed.")
        print()
        print("Open these files in a browser to inspect the visualizations:")
        for f in sorted(os.listdir("output")):
            if f.endswith(".html"):
                print(f"  output/{f}")
    else:
        print("Some tests FAILED.")
        sys.exit(1)
