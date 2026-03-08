# Visual Debugging for AI-Generated Python Code

## Working Title

**Visual Debugging for AI-Generated Python Code**  
A lightweight Python instrumentation prototype that turns program execution into a visual system map.

## One-Sentence Summary

This project explores whether Python programs can automatically generate their own functional architecture diagrams at runtime, making AI-generated code easier to understand, validate, and debug.

## Why This Exists

A growing number of developers now rely on AI coding tools to generate meaningful portions of their codebase. That changes the bottleneck.

The problem is no longer only writing code. The problem is **understanding what the generated system is actually doing**.

Many users can read a flowchart faster than they can read source code. That is especially true for:

- vibe coders
- AI-assisted developers
- technical founders
- operators debugging agent-built systems
- developers inheriting messy generated pipelines

Today, if an AI-generated Python workflow fails, the user usually has to inspect source code, logs, stack traces, or framework-specific dashboards. Those tools are useful, but they are often too low-level or too fragmented to communicate the overall behavior of the program.

This project tests a different idea:

> What if the program could automatically produce a visual diagram of what it did, using the structure the coding agent already knows when generating the code?

The goal is not to replace source code. The goal is to create a **runtime-generated software instrument panel** that helps users understand the system at a functional level.

## Core Product Idea

The prototype instruments Python code with lightweight decorators that attach semantic metadata to functions.

When the program runs, those decorators capture execution information and write a runtime trace. That trace is then converted into a directed graph showing:

- which modules exist
- which tasks ran
- how tasks connect to each other
- how long each task took
- what kind of data flowed through each step
- whether outputs passed validation

The result is an interactive graph that acts like an architecture map generated from execution rather than from static documentation.

## Intended Audience

The prototype is designed for:

- developers using AI coding agents
- users who struggle to understand generated code
- builders of agent pipelines and tool workflows
- teams interested in lightweight observability for code comprehension

The target user may not want to inspect every line of Python, but they can still reason about modules, task flow, durations, and validation status.

## Product Goals

### Primary Goal

Demonstrate that decorated Python code can automatically generate a useful, human-readable system diagram after execution.

### Secondary Goals

- Make the output legible to non-expert coders
- Show both structural flow and lightweight debugging metadata
- Create a demo suitable for discussion at a Python/AI engineering conference
- Build the system in a way that could later be inserted automatically by a coding agent

### Non-Goals for MVP

The MVP is **not** trying to:

- fully replace tracing or observability platforms
- infer every hidden library call automatically
- support asynchronous execution in the first version
- provide full production-grade debugging suggestions
- support arbitrarily deep nested module trees

## Conceptual Model

The system uses a two-level hierarchy.

### Modules

A module represents a higher-level capability or stage of the program.

Examples:

- Math Operations
- Text Construction
- Text Transformation
- PDF Extraction
- Summarization
- Storage

A module answers the question:

**What larger job is this section of the system responsible for?**

### Tasks

A task is an individual Python function that performs one specific operation inside a module.

Examples:

- add_numbers()
- multiply_numbers()
- build_sentence()
- normalize_text()
- summarize_text()

A task answers the question:

**What exact step happened here?**

For the MVP, every task must include a clear human-readable description. These descriptions are intended to be inserted by the coding agent when generating code.

## How the System Works

The runtime flow is intentionally simple:

1. Python functions are decorated with module and task metadata
2. The program executes normally
3. Decorators record runtime events in an in-memory trace
4. The trace is converted into a graph structure
5. The graph is exported as an interactive HTML visualization
6. A FastAPI app serves the graph in the browser

In compact form:

```text
decorated python code
        ↓
runtime trace collector
        ↓
graph builder
        ↓
visualization exporter
        ↓
FastAPI endpoint
        ↓
browser graph
```

## MVP Architecture

The MVP contains five major parts.

### 1. Decorator Layer

Two decorators are attached to functions:

- `@module("...")`
- `@task("...")`

These do not change the underlying business logic. Their job is to record metadata and execution details while preserving original behavior.

Each decorated task should capture:

- function name
- task description
- module name
- parent task
- start time
- end time
- duration
- summarized input preview
- summarized output preview
- validation status

### 2. Runtime Trace Collector

During execution, trace events are written to an **in-memory runtime trace**.

For the MVP, this trace is stored in a simple global in-memory structure for a single run.

This choice is intentional:

- easy to reason about
- easy to inspect while developing
- no database required
- ideal for a prototype and single-user demo flow

Later versions could replace this with persistent storage or a trace backend.

### 3. Graph Builder

After execution finishes, the runtime trace is converted into a directed graph using **NetworkX**.

The graph contains:

- nodes for tasks
- grouping metadata for modules
- edges representing execution flow between tasks

The graph should remain readable even when more steps are added later, so grouping by module is a key part of the design.

### 4. Visualization Layer

The graph is rendered as interactive HTML using **PyVis**.

Each node should display useful metadata such as:

- task name
- task description
- module name
- duration
- validation status
- input preview
- output preview
- approximate data size

For data previews, the MVP should show:

- total character count
- first 50 characters
- last 50 characters

This gives useful debugging context without flooding the graph with full payloads.

### 5. FastAPI Application

A small **FastAPI** backend runs the demo pipeline and serves the generated graph.

In the earliest version, the API can simply run a built-in demo pipeline.

Later in the MVP, the API can support a real PDF-based pipeline as an upgraded example.

## Validation Model

The MVP uses lightweight validation on task outputs.

Validation exists to answer a simple question:

**Did this task produce something structurally reasonable?**

The initial implementation may use green/red status only.

- **Green** = output passed validation
- **Red** = validation failed

A later enhancement may add:

- **Yellow** = output is structurally valid but suspicious by heuristic rules

Validation can be implemented with Pydantic models or light schema checks depending on the task.

## Demo Strategy

The demo will be built in two stages.

### Stage 1: Synthetic Pipeline

The first demo pipeline should avoid unnecessary dependency complexity.

Recommended modules:

- **Math Operations**
  - add two numbers
  - multiply values
  - compute an intermediate result

- **Text Construction**
  - convert numeric results into explanatory text
  - build a sentence or report fragment

- **Text Transformation**
  - normalize text
  - transform casing or formatting
  - generate final output text

This gives the graph a mix of numeric and string data, which is ideal for testing previews and readability.

The purpose of this synthetic pipeline is to validate the instrumentation system itself before introducing real file-processing complexity.

### Stage 2: Real PDF Pipeline

Once the core graphing system works, the demo should evolve into a real PDF-oriented example.

A likely path:

- load PDF
- extract text
- clean text
- summarize text
- save or display result

The PDF stage is valuable because it makes the project more concrete and conference-relevant, but it should be added only after the instrumentation core is stable.

## Why Build Instrumentation First

The system should be built in this order:

1. instrumentation
2. graph generation
3. visualization
4. demo pipeline
5. API delivery

This order is important.

If the graphing logic and the business pipeline are built at the same time, it becomes hard to know whether bugs come from:

- the pipeline code
- the decorators
- the runtime trace
- the graph builder
- the visualization layer

By building the instrumentation system first and testing it on tiny deterministic functions, the team can validate the core mechanism before introducing more realistic workflows.

## LLM Role in the System

LLMs may help the product, but they should **not** be responsible for generating the graph structure.

The graph should always come from deterministic runtime truth.

LLMs can be useful in later phases for:

- summarizing the pipeline in natural language
- compressing a sequence of task descriptions into a readable explanation
- offering debugging hints after a validation failure

This boundary matters.

Use deterministic systems for structure.  
Use LLMs for semantic explanation.

## Technical Choices

### Selected Technologies

- **Python** for implementation
- **FastAPI** for the backend service
- **NetworkX** for graph construction
- **PyVis** for interactive graph rendering
- **Pydantic** for lightweight validation where appropriate
- **Render** for cloud deployment

### Why These Choices

- FastAPI is fast to build with and easy to deploy
- NetworkX is a strong fit for graph construction and manipulation
- PyVis produces interactive HTML without requiring a full custom frontend
- Pydantic aligns with the conference ecosystem and supports explicit data validation
- Render makes it easy to demo from a phone through automatic deployment

## Deployment Strategy

The project should be deployed as a lightweight FastAPI service on Render.

Expected workflow:

1. code is generated or updated in GitHub
2. Render auto-deploys the backend
3. user opens the deployed endpoint from phone or laptop
4. built-in demo pipeline runs
5. graph HTML is returned and displayed in the browser

This makes the project easy to test while mobile and reduces dependence on local laptop setup.

## What Success Looks Like

A successful MVP should demonstrate the following flow:

- a small Python program is decorated with module and task metadata
- the program runs normally
- runtime events are captured automatically
- an interactive graph is generated from the run
- clicking nodes reveals task descriptions and metadata
- the graph makes the program easier to understand at a glance

For the conference, the demo should let someone quickly understand this idea:

> The coding agent can generate code in a structured way so the program can later explain itself visually.

That is the core product insight.

## Conference Value

This project is relevant to discussions around:

- observability
- orchestration
- AI coding agents
- code comprehension
- runtime debugging
- human-readable system maps

The prototype does not need to be fully general to be compelling.

It only needs to clearly show that runtime-generated architecture diagrams are possible and useful.

## Known Limitations in MVP

The first version will intentionally avoid or defer:

- asynchronous execution tracing
- distributed tracing across services
- live graph updates during execution
- automatic inference of hidden library internals
- nested module trees deeper than two levels
- robust multi-user session trace storage

These are future directions, not MVP requirements.

## Possible Future Extensions

After the MVP works, plausible extensions include:

- nested modules or submodules
- live graph updates while the program runs
- trace storage per run with history
- loop aggregation with execution counts
- async and concurrent task support
- LLM-generated graph summaries
- automatic instrumentation by coding agents
- framework adapters for common Python workflows
- PDF upload frontend with graph output and summaries

## Proposed Repo Shape

```text
repo/
  instrumentation/
    decorators.py
    trace_collector.py

  graph/
    graph_builder.py
    graph_visualizer.py

  pipeline/
    demo_pipeline.py
    validation_models.py

  api/
    server.py

  output/
    graph.html
```

## Final Framing

This project is not just about drawing a graph.

It is about testing a broader idea:

**Programs generated with AI should be easier to understand than the systems they replace.**

If coding agents can generate code, they should also be able to generate the instrumentation and metadata needed for that code to explain itself.

This prototype is a first step toward that future.
