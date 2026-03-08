"""
pipeline/demo_pipeline.py — Synthetic demo pipeline for Milestone 4.

Overview
--------
This module defines a small, expressive pipeline that exercises the full
instrumentation → graph builder → visualization stack end-to-end.

The pipeline transforms a pair of integers through four semantic stages:

    Math Operations      — numeric computation
    Text Construction    — convert numbers to human-readable text
    Text Transformation  — clean and format the text
    Validation           — verify results meet expectations

Pipeline execution shape
------------------------

    run_demo_pipeline(base, multiplier, fail_mode)          [Pipeline]
      ├── compute_score_pipeline(base, multiplier)          [Math Operations]
      │     └── compute_intermediate_score(base, 10, mult) [Math Operations]
      │           ├── add_numbers(base, 10)                 [Math Operations]
      │           └── multiply_value(sum, multiplier)       [Math Operations]
      ├── validate_score_range(score)                       [Validation]
      ├── build_report(score)                               [Text Construction]
      │     ├── build_sentence_from_score(score)            [Text Construction]
      │     ├── build_status_phrase(score)                  [Text Construction]
      │     ├── compose_report_line(sentence, phrase)       [Text Construction]
      │     ├── normalize_text(report_line)                 [Text Transformation]
      │     ├── emphasize_keywords(normalized)              [Text Transformation]
      │     └── create_final_message(emphasized)            [Text Transformation]
      └── validate_text_nonempty(final_message)             [Validation]

Failure mode
------------
When fail_mode=True the pipeline uses base=20, multiplier=6, which produces
score=180. validate_score_range then raises ValueError because 180 > 100.
The decorator records the exception as an error event before re-raising, so
the graph shows a red failure node at the validation step and the partially
completed execution trace is still rendered correctly.

Usage
-----
    from pipeline.demo_pipeline import run_demo_pipeline

    # Happy path — all tasks succeed
    report = run_demo_pipeline(base=5, multiplier=3)

    # Failure path — validate_score_range raises, red node appears in graph
    try:
        run_demo_pipeline(base=5, multiplier=3, fail_mode=True)
    except ValueError:
        pass  # trace is already recorded; build and render the graph
"""

from __future__ import annotations

from instrumentation.decorators import module, task


# ---------------------------------------------------------------------------
# Module 1 — Math Operations
# ---------------------------------------------------------------------------

@module("Math Operations")
@task("Add two integers to produce an intermediate sum")
def add_numbers(a: int, b: int) -> int:
    return a + b


@module("Math Operations")
@task("Multiply a value by a scaling factor to produce a larger result")
def multiply_value(value: int, factor: int) -> int:
    return value * factor


@module("Math Operations")
@task("Compute an intermediate score by summing inputs then applying a multiplier")
def compute_intermediate_score(a: int, b: int, factor: int) -> int:
    total = add_numbers(a, b)
    return multiply_value(total, factor)


@module("Math Operations")
@task("Orchestrate the numeric stage: add a fixed offset then scale by multiplier")
def compute_score_pipeline(base: int, multiplier: int) -> int:
    return compute_intermediate_score(base, 10, multiplier)


# ---------------------------------------------------------------------------
# Module 2 — Text Construction
# ---------------------------------------------------------------------------

@module("Text Construction")
@task("Build a descriptive sentence that states the computed numeric score")
def build_sentence_from_score(score: int) -> str:
    return f"The computed score is {score}"


@module("Text Construction")
@task("Determine a pass/fail status phrase based on whether the score is above 50")
def build_status_phrase(score: int) -> str:
    if score >= 50:
        return "status: above threshold"
    return "status: below threshold"


@module("Text Construction")
@task("Combine the score sentence and status phrase into a single report line")
def compose_report_line(sentence: str, status_phrase: str) -> str:
    return f"{sentence}. {status_phrase}."


# ---------------------------------------------------------------------------
# Module 3 — Text Transformation
# ---------------------------------------------------------------------------

@module("Text Transformation")
@task("Normalize text by stripping surrounding whitespace and lowercasing")
def normalize_text(text: str) -> str:
    return text.strip().lower()


@module("Text Transformation")
@task("Wrap key status words in brackets to make them visually prominent")
def emphasize_keywords(text: str) -> str:
    text = text.replace("above threshold", "[ABOVE THRESHOLD]")
    text = text.replace("below threshold", "[BELOW THRESHOLD]")
    return text


@module("Text Transformation")
@task("Wrap the processed text in a formatted report header and footer")
def create_final_message(text: str) -> str:
    return f"=== PIPELINE REPORT ===\n{text}\n=== END REPORT ==="


# ---------------------------------------------------------------------------
# Text Construction — report orchestrator (calls across Text Transformation)
# ---------------------------------------------------------------------------

@module("Text Construction")
@task("Orchestrate the full text pipeline: construct, normalize, emphasize, format")
def build_report(score: int) -> str:
    sentence = build_sentence_from_score(score)
    status_phrase = build_status_phrase(score)
    report_line = compose_report_line(sentence, status_phrase)
    normalized = normalize_text(report_line)
    emphasized = emphasize_keywords(normalized)
    return create_final_message(emphasized)


# ---------------------------------------------------------------------------
# Module 4 — Validation
# ---------------------------------------------------------------------------

@module("Validation")
@task("Validate that the numeric score falls within the allowed range [0, 100]")
def validate_score_range(score: int, min_val: int = 0, max_val: int = 100) -> bool:
    if not (min_val <= score <= max_val):
        raise ValueError(
            f"Score {score} is outside the valid range [{min_val}, {max_val}]"
        )
    return True


@module("Validation")
@task("Validate that the final report text is non-empty and at least 10 characters")
def validate_text_nonempty(text: str, min_length: int = 10) -> bool:
    if not text or len(text) < min_length:
        raise ValueError(
            f"Report text is too short: length={len(text)}, minimum={min_length}"
        )
    return True


# ---------------------------------------------------------------------------
# Top-level pipeline orchestrator
# ---------------------------------------------------------------------------

@module("Pipeline")
@task("Run the complete demo pipeline from numeric inputs to a validated report")
def run_demo_pipeline(
    base: int = 5,
    multiplier: int = 3,
    *,
    fail_mode: bool = False,
) -> str:
    """Execute the full synthetic demo pipeline.

    Parameters
    ----------
    base:
        Starting integer fed into the math module.
    multiplier:
        Scaling factor applied to the intermediate sum.
    fail_mode:
        When True, overrides inputs so the score exceeds 100, causing
        validate_score_range to raise ValueError. The failure is captured in
        the trace and appears as a red node in the rendered graph.

    Returns
    -------
    str
        The final formatted report produced by the pipeline.

    Raises
    ------
    ValueError
        In failure mode when validate_score_range detects an out-of-range score.
    """
    if fail_mode:
        # add_numbers(20, 10) = 30; multiply_value(30, 6) = 180 — exceeds 100
        base = 20
        multiplier = 6

    score = compute_score_pipeline(base, multiplier)
    validate_score_range(score)
    report = build_report(score)
    validate_text_nonempty(report)
    return report
