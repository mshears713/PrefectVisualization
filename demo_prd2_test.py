"""
demo_prd2_test.py — Verification script for PRD 02 (Trace-to-Graph Builder).

Run with:
    python demo_prd2_test.py

What this script demonstrates
------------------------------
1. Sequential trace → graph   — two independent tasks produce two nodes and
                                 no execution edges (they are siblings, not
                                 parent-child).
2. Nested execution graph     — compute_pipeline + its two children produce
                                 three nodes and two directed edges.
3. Mixed metadata preserved   — numeric and string outputs survive as node
                                 attribute strings.
4. Error node in graph        — a failed task still appears as a node with
                                 status="error" and an error_message.
5. Repeated task execution    — the same function called twice produces two
                                 distinct nodes with unique IDs.
6. Debug summary helper       — graph_debug_summary() returns a sensible dict.

Each test resets the trace, runs decorated functions via PRD1 decorators,
captures the trace, builds the graph, and asserts structural properties.
"""

import sys
import pprint

from instrumentation.decorators import module, task
from instrumentation.trace_collector import get_trace, reset_trace
from graph.graph_builder import (
    build_graph,
    list_graph_nodes,
    list_graph_edges,
    graph_debug_summary,
)


# ---------------------------------------------------------------------------
# Decorated demo functions (reused from PRD1, defined locally for clarity)
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
# Display helpers
# ---------------------------------------------------------------------------

def print_graph_summary(summary: dict, title: str = "Graph Summary") -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    print(f"  Nodes      : {summary['num_nodes']}")
    print(f"  Edges      : {summary['num_edges']}")
    print(f"  Root nodes : {summary['root_nodes']}")
    print(f"  Modules    : {summary['module_counts']}")
    print(f"  Statuses   : {summary['status_counts']}")
    print()
    for node in summary["nodes"]:
        print(
            f"  [{node['trace_index']}] {node['node_id']}"
            f"  module={node['module_name']!r}"
            f"  parent={node['parent_task']!r}"
            f"  status={node['status']}"
            f"  dur={node['duration_ms']} ms"
        )
    print()
    for src, dst in summary["edges"]:
        print(f"  EDGE  {src}  →  {dst}")
    print(sep)


# ---------------------------------------------------------------------------
# Test 1 — Sequential trace → two nodes, no edges between them
# ---------------------------------------------------------------------------

def test_sequential_graph():
    print("\n\n>>> Test 1: Sequential trace → graph")
    reset_trace()

    add_numbers(3, 4)
    multiply_numbers(5, 6)

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 1 — Sequential")

    assert summary["num_nodes"] == 2, f"Expected 2 nodes, got {summary['num_nodes']}"
    # These two tasks are independent siblings — no edges expected.
    assert summary["num_edges"] == 0, f"Expected 0 edges, got {summary['num_edges']}"

    node_ids = {n["node_id"] for n in summary["nodes"]}
    assert "add_numbers__0" in node_ids
    assert "multiply_numbers__1" in node_ids

    # Metadata preserved
    add_node = next(n for n in summary["nodes"] if n["task_name"] == "add_numbers")
    assert add_node["module_name"] == "Math Operations"
    assert add_node["status"] == "success"
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Nested execution → three nodes, two directed edges
# ---------------------------------------------------------------------------

def test_nested_graph():
    print("\n\n>>> Test 2: Nested execution → graph")
    reset_trace()

    compute_pipeline(2, 3)

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 2 — Nested execution")

    assert summary["num_nodes"] == 3
    assert summary["num_edges"] == 2

    # compute_pipeline is the only root
    assert len(summary["root_nodes"]) == 1
    root_id = summary["root_nodes"][0]
    assert root_id.startswith("compute_pipeline__")

    # Both edges should originate from compute_pipeline
    for src, dst in summary["edges"]:
        assert src == root_id, (
            f"Expected edge source to be {root_id!r}, got {src!r}"
        )

    # Child node names
    child_task_names = {
        n["task_name"] for n in summary["nodes"]
        if n["parent_task"] == "compute_pipeline"
    }
    assert "add_numbers" in child_task_names
    assert "multiply_numbers" in child_task_names
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — Mixed types: metadata preserved correctly
# ---------------------------------------------------------------------------

def test_mixed_metadata():
    print("\n\n>>> Test 3: Mixed metadata preserved")
    reset_trace()

    multiply_numbers(7, 8)
    build_sentence(56)

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 3 — Mixed metadata")

    assert summary["num_nodes"] == 2

    nodes_by_name = {n["task_name"]: n for n in list_graph_nodes(graph)}
    # numeric output preview stored as a string
    assert isinstance(
        graph.nodes["multiply_numbers__0"]["output_preview"], str
    )
    # string output preview also a string
    assert isinstance(
        graph.nodes["build_sentence__1"]["output_preview"], str
    )
    # module names distinct
    assert graph.nodes["multiply_numbers__0"]["module_name"] == "Math Operations"
    assert graph.nodes["build_sentence__1"]["module_name"] == "Text Construction"
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Error node appears in graph with correct metadata
# ---------------------------------------------------------------------------

def test_error_node():
    print("\n\n>>> Test 4: Error node in graph")
    reset_trace()

    try:
        divide_numbers(10, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 4 — Error node")

    assert summary["num_nodes"] == 1
    assert summary["status_counts"].get("error", 0) == 1

    node_data = graph.nodes["divide_numbers__0"]
    assert node_data["status"] == "error"
    assert node_data["error_message"] is not None
    assert "division by zero" in node_data["error_message"]
    assert node_data["output_preview"] == ""
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Same function called twice → two distinct nodes
# ---------------------------------------------------------------------------

def test_repeated_task():
    print("\n\n>>> Test 5: Repeated task execution → distinct nodes")
    reset_trace()

    add_numbers(1, 2)
    add_numbers(10, 20)

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 5 — Repeated task")

    assert summary["num_nodes"] == 2
    node_ids = {n["node_id"] for n in summary["nodes"]}
    assert "add_numbers__0" in node_ids
    assert "add_numbers__1" in node_ids

    # They should be independent (no edges)
    assert summary["num_edges"] == 0
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 6 — Debug summary helper returns expected structure
# ---------------------------------------------------------------------------

def test_debug_summary():
    print("\n\n>>> Test 6: Debug summary helper")
    reset_trace()

    compute_pipeline(5, 7)
    build_sentence(120)

    try:
        divide_numbers(120, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Test 6 — Debug summary")

    assert "num_nodes" in summary
    assert "num_edges" in summary
    assert "root_nodes" in summary
    assert "nodes" in summary
    assert "edges" in summary
    assert "module_counts" in summary
    assert "status_counts" in summary

    assert summary["num_nodes"] == 5  # pipeline×3 + sentence + divide_error
    assert summary["status_counts"]["success"] == 4
    assert summary["status_counts"]["error"] == 1
    assert "Math Operations" in summary["module_counts"]
    assert "Text Construction" in summary["module_counts"]
    print("  PASSED")


# ---------------------------------------------------------------------------
# Bonus: full pipeline visual walkthrough
# ---------------------------------------------------------------------------

def run_full_pipeline():
    print("\n\n>>> Bonus: Full pipeline graph walkthrough")
    reset_trace()

    result = compute_pipeline(5, 7)
    sentence = build_sentence(result)
    try:
        divide_numbers(result, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    graph = build_graph(trace)
    summary = graph_debug_summary(graph)
    print_graph_summary(summary, "Full Pipeline Graph")

    print(f"  Final sentence : {sentence!r}")
    print(f"  Nodes          : {summary['num_nodes']}")
    print(f"  Edges          : {summary['num_edges']}")
    print(f"  Root nodes     : {summary['root_nodes']}")

    print("\n  Full node metadata (first node):")
    first_node_id = list_graph_nodes(graph)[0]["node_id"]
    pprint.pprint(dict(graph.nodes[first_node_id]), indent=4)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_sequential_graph,
        test_nested_graph,
        test_mixed_metadata,
        test_error_node,
        test_repeated_task,
        test_debug_summary,
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

    run_full_pipeline()

    if all_passed:
        print("\n\nAll tests passed.")
    else:
        print("\n\nSome tests FAILED.")
        sys.exit(1)
