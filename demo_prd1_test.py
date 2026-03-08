"""
demo_prd1_test.py — Verification script for PRD 01 (Instrumentation Core).

Run with:
    python demo_prd1_test.py

What this script demonstrates
------------------------------
1. Basic success path          — two tasks run sequentially, both succeed.
2. Nested call path            — compute_pipeline calls add_numbers and
                                 multiply_numbers; parent-child relationships
                                 appear in the trace.
3. Mixed data types            — build_sentence converts a number to a string;
                                 previews handle both int and str without error.
4. Error capture               — divide_numbers raises when divisor is zero;
                                 the trace records the error and the exception
                                 propagates to the caller.
5. Trace reset                 — reset_trace() clears previous state so a fresh
                                 run starts from an empty trace.

Expected output highlights
--------------------------
- Every decorated function produces a trace entry.
- trace_index shows insertion order (0, 1, 2, …).
- parent_task is non-None for tasks called inside another task.
- duration_ms is a non-negative float.
- input_preview and output_preview include length and head/tail snippets.
- The error entry has status="error" and a non-None error_message.
- After reset_trace(), only the post-reset calls appear.
"""

import pprint
import sys

from instrumentation.decorators import module, task
from instrumentation.trace_collector import get_trace, reset_trace


# ---------------------------------------------------------------------------
# Define the demo pipeline functions
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
# Helper for readable trace output
# ---------------------------------------------------------------------------

def print_trace(trace, title="Runtime Trace"):
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {title}  ({len(trace)} event(s))")
    print(separator)
    for event in trace:
        print(
            f"\n[{event['trace_index']}] {event['task_name']}"
            f"  module={event['module_name']!r}"
            f"  parent={event['parent_task']!r}"
            f"  status={event['status']}"
        )
        print(f"     duration   : {event['duration_ms']:.4f} ms")
        print(f"     input      : {event['input_preview']}")
        print(f"     output     : {event['output_preview']}")
        if event["error_message"]:
            print(f"     ERROR      : {event['error_message']}")
    print(separator)


# ---------------------------------------------------------------------------
# Test 1 — Basic success path
# ---------------------------------------------------------------------------

def test_basic_success():
    print("\n\n>>> Test 1: Basic success path")
    reset_trace()

    r1 = add_numbers(3, 4)
    r2 = multiply_numbers(5, 6)

    trace = get_trace()
    print_trace(trace, "Test 1 — Basic success path")

    assert len(trace) == 2, f"Expected 2 events, got {len(trace)}"
    assert trace[0]["task_name"] == "add_numbers"
    assert trace[1]["task_name"] == "multiply_numbers"
    assert all(e["status"] == "success" for e in trace)
    assert r1 == 7
    assert r2 == 30
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 2 — Nested call path
# ---------------------------------------------------------------------------

def test_nested_calls():
    print("\n\n>>> Test 2: Nested call path")
    reset_trace()

    result = compute_pipeline(2, 3)

    trace = get_trace()
    print_trace(trace, "Test 2 — Nested call path")

    assert len(trace) == 3, f"Expected 3 events, got {len(trace)}"

    # Events record on completion, so children finish before the parent.
    # Locate the root and child events by their parent_task field rather
    # than by index position.
    roots = [e for e in trace if e["parent_task"] is None]
    children = [e for e in trace if e["parent_task"] is not None]

    assert len(roots) == 1, f"Expected 1 root task, got {len(roots)}"
    root = roots[0]
    assert root["task_name"] == "compute_pipeline"

    # add_numbers and multiply_numbers are children of compute_pipeline
    assert len(children) == 2
    child_names = {e["task_name"] for e in children}
    assert "add_numbers" in child_names
    assert "multiply_numbers" in child_names

    for child in children:
        assert child["parent_task"] == "compute_pipeline", (
            f"{child['task_name']} should have parent 'compute_pipeline', "
            f"got {child['parent_task']!r}"
        )

    assert result == 50  # (2+3)*10
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 3 — Mixed data types
# ---------------------------------------------------------------------------

def test_mixed_types():
    print("\n\n>>> Test 3: Mixed data types")
    reset_trace()

    num_result = multiply_numbers(7, 8)
    sentence = build_sentence(num_result)

    trace = get_trace()
    print_trace(trace, "Test 3 — Mixed data types")

    assert len(trace) == 2
    # multiply_numbers produces an int — preview should still be a string
    assert isinstance(trace[0]["output_preview"], str)
    assert "length=" in trace[0]["output_preview"]
    # build_sentence produces a str
    assert isinstance(trace[1]["output_preview"], str)
    assert "length=" in trace[1]["output_preview"]
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 4 — Error capture
# ---------------------------------------------------------------------------

def test_error_capture():
    print("\n\n>>> Test 4: Error capture")
    reset_trace()

    raised = False
    try:
        divide_numbers(10, 0)
    except ZeroDivisionError:
        raised = True

    assert raised, "ZeroDivisionError should have propagated to caller"

    trace = get_trace()
    print_trace(trace, "Test 4 — Error capture")

    assert len(trace) == 1
    err = trace[0]
    assert err["status"] == "error"
    assert err["error_message"] is not None
    assert "division by zero" in err["error_message"]
    assert err["output_preview"] == ""
    assert err["output_length"] == 0
    print("  PASSED")


# ---------------------------------------------------------------------------
# Test 5 — Trace reset
# ---------------------------------------------------------------------------

def test_trace_reset():
    print("\n\n>>> Test 5: Trace reset")

    # Run something, then reset, then run something different.
    reset_trace()
    add_numbers(1, 2)
    add_numbers(3, 4)
    assert len(get_trace()) == 2

    reset_trace()
    assert len(get_trace()) == 0, "Trace should be empty after reset"

    multiply_numbers(9, 9)
    trace = get_trace()
    print_trace(trace, "Test 5 — Trace after reset")

    assert len(trace) == 1
    assert trace[0]["task_name"] == "multiply_numbers"
    assert trace[0]["trace_index"] == 0
    print("  PASSED")


# ---------------------------------------------------------------------------
# Bonus: Full pipeline run for a final readable summary
# ---------------------------------------------------------------------------

def run_full_pipeline():
    print("\n\n>>> Bonus: Full pipeline run")
    reset_trace()

    result = compute_pipeline(5, 7)
    sentence = build_sentence(result)

    # Also intentionally trigger an error (caught externally).
    try:
        divide_numbers(result, 0)
    except ZeroDivisionError:
        pass

    trace = get_trace()
    print_trace(trace, "Full Pipeline Trace")
    print(f"\n  Final sentence : {sentence!r}")
    print(f"  Total events   : {len(trace)}")
    print(
        f"  Success / Error: "
        f"{sum(1 for e in trace if e['status'] == 'success')} / "
        f"{sum(1 for e in trace if e['status'] == 'error')}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    all_passed = True
    tests = [
        test_basic_success,
        test_nested_calls,
        test_mixed_types,
        test_error_capture,
        test_trace_reset,
    ]
    for test_fn in tests:
        try:
            test_fn()
        except AssertionError as exc:
            print(f"  FAILED: {exc}")
            all_passed = False
        except Exception as exc:
            print(f"  ERROR (unexpected): {exc}")
            all_passed = False

    run_full_pipeline()

    if all_passed:
        print("\n\nAll tests passed.")
    else:
        print("\n\nSome tests FAILED.")
        sys.exit(1)
