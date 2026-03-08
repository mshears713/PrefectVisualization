"""
preview_helpers.py — Input/output summarization helpers.

Produces compact, human-readable previews of arbitrary Python values without
storing full payloads in the trace.  All downstream consumers (decorators,
graph builder, visualizer tooltips) should use these helpers rather than
implementing their own truncation logic.

Preview format
--------------
    "length=N, head='<first 50 chars>', tail='<last 50 chars>'"

For short values where head and tail overlap, the tail is omitted:
    "length=N, head='<full value>'"

The length represents the total character count of the string representation,
not of the original Python object, so it is an approximation for non-strings.
"""

from __future__ import annotations

_HEAD_LEN = 50
_TAIL_LEN = 50


def _to_str(value: object) -> str:
    """Safely convert any value to a string suitable for preview.

    Strings are used as-is; everything else goes through repr() so that
    types like None, int, dict, and list produce readable output.
    """
    if isinstance(value, str):
        return value
    return repr(value)


def make_preview(value: object) -> tuple[str, int]:
    """Return a (preview_string, length) pair for any value.

    Parameters
    ----------
    value:
        Any Python object to summarize.

    Returns
    -------
    preview_string:
        A compact summary of the form
        "length=N, head='...', tail='...'"
        or
        "length=N, head='...'"
        when the full value fits within HEAD_LEN characters.
    length:
        Total character count of the string representation.
    """
    s = _to_str(value)
    n = len(s)

    if n <= _HEAD_LEN:
        preview = f"length={n}, head={s!r}"
    else:
        head = s[:_HEAD_LEN]
        tail = s[-_TAIL_LEN:]
        preview = f"length={n}, head={head!r}, tail={tail!r}"

    return preview, n


def make_args_preview(args: tuple, kwargs: dict) -> tuple[str, int]:
    """Summarize positional and keyword arguments together.

    Builds a combined string representation of all arguments so the trace
    carries a single input_preview rather than per-argument entries.

    Parameters
    ----------
    args:
        Positional arguments tuple from the wrapped function call.
    kwargs:
        Keyword arguments dict from the wrapped function call.

    Returns
    -------
    preview_string:
        Preview of the combined argument representation.
    length:
        Total character length of the combined argument representation.
    """
    parts = [repr(a) for a in args]
    parts += [f"{k}={v!r}" for k, v in kwargs.items()]
    combined = ", ".join(parts)
    return make_preview(combined)
