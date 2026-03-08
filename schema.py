"""
schema.py — Shared trace event data structure.

This module defines the canonical shape of a runtime trace event.
All instrumentation code must produce events that conform to this structure.
Downstream consumers (graph builder, visualizer, API) should depend on this
schema rather than on scattered dictionary keys.
"""

from typing import Optional, TypedDict


class TraceEvent(TypedDict):
    """
    A single recorded execution event from a decorated task function.

    Fields
    ------
    task_name : str
        The name of the decorated function (e.g. "add_numbers").
    task_description : str
        Human-readable description supplied to the @task decorator.
    module_name : str
        Human-readable module label supplied to the @module decorator,
        or an empty string if the function has no @module decorator.
    parent_task : Optional[str]
        The task_name of the enclosing task that was active when this
        task started, or None if this is a root task.
    trace_index : int
        Zero-based position of this event in the global runtime_trace list.
        Preserved so the graph builder can reconstruct execution order.
    start_time : float
        Wall-clock start time in seconds, from time.perf_counter().
    end_time : float
        Wall-clock end time in seconds, from time.perf_counter().
    duration_ms : float
        Execution duration in milliseconds (end_time - start_time) * 1000.
    status : str
        "success" if the function returned normally; "error" if it raised.
    input_preview : str
        Compact summary of all arguments passed to the function.
        Format: "length=N, head='...', tail='...'"
    output_preview : str
        Compact summary of the return value.
        Format: "length=N, head='...', tail='...'"
        Empty string when status is "error".
    input_length : int
        Approximate total character length of the string representation
        of all inputs combined.
    output_length : int
        Approximate total character length of the string representation
        of the output.  0 when status is "error".
    error_message : Optional[str]
        String form of the exception if status is "error"; None otherwise.
    """

    task_name: str
    task_description: str
    module_name: str
    parent_task: Optional[str]
    trace_index: int
    start_time: float
    end_time: float
    duration_ms: float
    status: str
    input_preview: str
    output_preview: str
    input_length: int
    output_length: int
    error_message: Optional[str]
