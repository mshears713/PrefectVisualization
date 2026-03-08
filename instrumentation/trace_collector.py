"""
instrumentation/trace_collector.py — In-memory runtime trace storage.

Responsibilities
----------------
- Maintain the global runtime_trace list that accumulates TraceEvent dicts.
- Maintain the global execution_stack list used by decorators to detect the
  current parent task during synchronous nested calls.
- Provide reset_trace(), get_trace(), and record_event() helpers so decorators
  never touch the storage structures directly.

Design notes
------------
- Both structures are plain module-level lists.  They are simple, inspectable,
  and sufficient for synchronous single-process use in MVP.
- Async support would require replacing execution_stack with a
  contextvars.ContextVar; that change is isolated to this module.
- record_event() stamps the event with its trace_index before appending so
  callers do not have to track list length themselves.
"""

from __future__ import annotations

from typing import List

from schema import TraceEvent

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

# Ordered list of completed trace events for the current run.
runtime_trace: List[TraceEvent] = []

# Stack of task_name strings representing the active call chain.
# The *last* element is the currently executing task; the element before it
# is the parent.  Pushed on task entry, popped on task exit (always, even on
# exceptions).
execution_stack: List[str] = []


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def reset_trace() -> None:
    """Clear all trace events and the execution stack.

    Call this at the start of each demo or test run to ensure a clean state.
    """
    runtime_trace.clear()
    execution_stack.clear()


def get_trace() -> List[TraceEvent]:
    """Return a shallow copy of the current runtime trace.

    Returns a copy so callers cannot accidentally mutate shared state.
    The original list remains intact for further appends.
    """
    return list(runtime_trace)


def record_event(event: TraceEvent) -> None:
    """Append a completed trace event to the runtime trace.

    Stamps event['trace_index'] with the current list length before appending,
    so the index always reflects insertion order.

    Parameters
    ----------
    event:
        A fully-populated TraceEvent dict.  The trace_index field will be
        overwritten with the correct value here.
    """
    event["trace_index"] = len(runtime_trace)
    runtime_trace.append(event)
