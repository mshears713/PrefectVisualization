"""
instrumentation/decorators.py — @module and @task decorators.

Public API
----------
    @module("Human-readable module name")
    @task("Human-readable description of what this task does")
    def my_function(...):
        ...

Stacking order
--------------
@module must be the *outer* decorator and @task the *inner* decorator:

    @module("Math Operations")      # outer — applied second
    @task("Add two numbers")        # inner — applied first
    def add_numbers(a, b):
        return a + b

This matches the human-readable top-down reading order.  The @module
decorator stores its label on the function object *after* @task has already
wrapped it, so @task's wrapper can always find the module name at call time
by inspecting the outermost wrapper's attribute.

Implementation notes
--------------------
- @task stores _viz_task_description on the inner wrapper.
- @module stores _viz_module_name on the outer wrapper and delegates all calls
  to the @task wrapper underneath.
- At call time the @task wrapper reads _viz_module_name from *itself* using
  getattr with a fallback of "" so plain @task usage (without @module) still
  works.
- functools.wraps is used at every wrapping level to preserve __name__,
  __doc__, and other metadata.
- execution_stack push/pop is always performed inside a try/finally block to
  guarantee cleanup even when exceptions propagate.
- Exceptions are re-raised after the error event is recorded so the caller
  sees the original exception.
"""

from __future__ import annotations

import time
import functools
from typing import Callable, Any

from instrumentation.trace_collector import (
    execution_stack,
    record_event,
)
from preview_helpers import make_args_preview, make_preview
from schema import TraceEvent


# ---------------------------------------------------------------------------
# @task decorator
# ---------------------------------------------------------------------------

def task(description: str) -> Callable:
    """Decorator that instruments a function and records a TraceEvent.

    Parameters
    ----------
    description:
        Human-readable explanation of what this task does.  Stored on the
        wrapper and written into every trace event.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_name = fn.__name__

            # Module name is attached by @module (if present) on this wrapper
            # after @task has already wrapped fn.  Fall back to "" when the
            # function is used without @module.
            module_name: str = getattr(wrapper, "_viz_module_name", "")

            # Determine parent from the current top of the execution stack.
            parent_task = execution_stack[-1] if execution_stack else None

            # Push this task onto the stack before doing anything else.
            execution_stack.append(task_name)

            start_time = time.perf_counter()
            input_preview, input_length = make_args_preview(args, kwargs)

            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                end_time = time.perf_counter()
                event: TraceEvent = {
                    "task_name": task_name,
                    "task_description": description,
                    "module_name": module_name,
                    "parent_task": parent_task,
                    "trace_index": -1,  # overwritten by record_event
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_ms": (end_time - start_time) * 1000,
                    "status": "error",
                    "input_preview": input_preview,
                    "output_preview": "",
                    "input_length": input_length,
                    "output_length": 0,
                    "error_message": str(exc),
                }
                record_event(event)
                raise
            else:
                end_time = time.perf_counter()
                output_preview, output_length = make_preview(result)
                event = {
                    "task_name": task_name,
                    "task_description": description,
                    "module_name": module_name,
                    "parent_task": parent_task,
                    "trace_index": -1,  # overwritten by record_event
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_ms": (end_time - start_time) * 1000,
                    "status": "success",
                    "input_preview": input_preview,
                    "output_preview": output_preview,
                    "input_length": input_length,
                    "output_length": output_length,
                    "error_message": None,
                }
                record_event(event)
                return result
            finally:
                # Always pop, even when an exception was raised.
                execution_stack.pop()

        # Mark the wrapper so @module can find it and so introspection works.
        wrapper._viz_task_description = description
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# @module decorator
# ---------------------------------------------------------------------------

def module(name: str) -> Callable:
    """Decorator that attaches a module label to a @task-decorated function.

    @module must be applied *outside* @task:

        @module("Math Operations")
        @task("Add two numbers")
        def add_numbers(a, b): ...

    The decorator writes _viz_module_name onto the @task wrapper so the
    wrapper can read it at call time.  @module does not add its own call
    overhead; it simply delegates to the inner wrapper.

    Parameters
    ----------
    name:
        Human-readable module label (e.g. "Math Operations").
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        # Propagate the module name onto both wrappers so that:
        # - the @task wrapper reads it from itself (module_name lookup above)
        # - the outer wrapper also carries it for external introspection.
        fn._viz_module_name = name       # type: ignore[attr-defined]
        wrapper._viz_module_name = name

        # Preserve task description if present on the inner function.
        if hasattr(fn, "_viz_task_description"):
            wrapper._viz_task_description = fn._viz_task_description

        return wrapper

    return decorator
