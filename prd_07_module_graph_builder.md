
# PRD 07 — Module-Level Graph Builder

## Title
Module Overview Graph Builder for Narrative Pipeline Visualization

## Purpose

This PRD defines the implementation of the **module-level graph** introduced in Phase 2 of the Visual Debugging system.

PRD 06 established a new **data‑flow graph foundation**. That work created the correct semantic edges between tasks.

PRD 07 introduces a **second abstraction layer** above those tasks: the **module overview graph**.

The goal is to allow users to understand the pipeline at a glance before inspecting the detailed task execution.

Instead of seeing dozens of nodes immediately, the user should first see a clean pipeline like:

PDF Ingestion → Text Extraction → Text Processing → Chunking → LLM Analysis → Structured Output

Clicking any module will later open the **task‑level graph** for that module.

This PRD only builds the module graph builder and the data model required for it.

UI navigation and task drill‑down behavior will be implemented in later PRDs.

---

# Problem This Solves

The Phase 1 graph contains too many nodes and too much execution detail.

Users need to answer high‑level questions quickly:

• What stages exist in the pipeline?  
• Where did execution fail?  
• How long did each stage take?  
• What entered and exited each stage?

The module overview graph solves this by aggregating tasks into **logical pipeline stages**.

---

# Conceptual Model

## Task Layer (already exists)

Each node represents a function.

Example:

load_pdf  
extract_text  
detect_language  
clean_text  
split_chunks  
analyze_chunks  
generate_summary

Edges represent data‑flow between tasks.

---

## Module Layer (new)

Each node represents a **group of tasks performing a capability**.

Example:

PDF Ingestion  
Text Extraction  
Text Processing  
Chunking  
LLM Analysis  
Structured Output

Each module aggregates metadata from the tasks inside it.

---

# Module Graph Requirements

## Functional Requirement 1 — Module Aggregation

The module graph builder must aggregate tasks by `module_name`.

Example task records:

task_name: extract_text  
module_name: Text Extraction  

task_name: detect_language  
module_name: Text Extraction  

Both tasks belong to the same module node.

---

## Functional Requirement 2 — Module Ordering

Modules must appear in pipeline order.

Preferred ordering field:

stage_index

Example:

PDF Ingestion → stage 0  
Text Extraction → stage 1  
Text Processing → stage 2  
Chunking → stage 3  
LLM Analysis → stage 4  
Structured Output → stage 5  

If stage_index is unavailable, fallback to the earliest task trace index.

---

## Functional Requirement 3 — Module Node Metadata

Each module node must contain:

module_name  
module_description  
status  
total_duration_ms  
input_summary  
output_summary  
task_count  

Status rules:

• success → all tasks succeeded  
• warning → at least one warning  
• error → at least one failure  

Duration rule:

total_duration = sum(task.duration_ms)

---

## Functional Requirement 4 — Module Edge Construction

Edges represent **stage progression**.

Example:

PDF Ingestion → Text Extraction  
Text Extraction → Text Processing  
Text Processing → Chunking  
Chunking → LLM Analysis  
LLM Analysis → Structured Output

Edges are built from ordered modules.

The graph builder must ensure:

• no duplicate edges  
• deterministic ordering

---

## Functional Requirement 5 — Branch Awareness

Modules may contain internal branches.

Example:

detect_language branch inside Text Extraction

The module graph should **not expand these branches**.

Branching is only represented in the task graph.

However the module metadata may include:

branch_detected: true

This allows later UI enhancements.

---

## Functional Requirement 6 — Metadata Preservation

Module nodes must retain references to the tasks inside them.

Example:

module.tasks = [task_id_1, task_id_2, task_id_3]

This enables later drill‑down navigation.

---

# Graph Structure

## Node Structure

module_id  
module_name  
description  
stage_index  
status  
total_duration_ms  
input_summary  
output_summary  
task_ids

---

## Edge Structure

source_module  
target_module  
edge_type = pipeline

---

# Input Sources

The module graph builder will consume:

• the **data‑flow task graph produced by PRD 06**
• the task trace metadata
• module metadata assigned via decorators

---

# Architecture

Recommended module:

graph/module_graph_builder.py

Suggested functions:

build_module_nodes(task_graph)

aggregate_module_metadata(tasks)

build_module_edges(module_nodes)

create_module_graph(task_graph)

---

# Data Aggregation Rules

## Input Summary

Take the input preview from the first task in the module.

Example:

Input: PDF Document

---

## Output Summary

Take the output preview from the final task in the module.

Example:

Output: 32,441 characters

---

## Duration

Sum durations of tasks inside the module.

---

# Graph Rendering Expectations

Although rendering will be implemented later, the graph builder must support:

• left‑to‑right layout  
• square nodes  
• metadata display

The builder must return a structure compatible with the existing visualization system.

---

# Test Plan

## Test 1 — Module Aggregation

Given tasks:

load_pdf → module PDF Ingestion  
validate_pdf → module PDF Ingestion  

Expect one module node.

---

## Test 2 — Ordering

Modules should appear:

PDF Ingestion → Text Extraction → Text Processing → Chunking → LLM Analysis → Structured Output

---

## Test 3 — Duration Aggregation

Module duration equals sum of tasks.

---

## Test 4 — Input/Output Summaries

Module input = first task input  
Module output = last task output

---

## Test 5 — Graph Edge Validation

Edges must match module order exactly.

---

# Acceptance Criteria

PRD 07 is complete when:

• a module graph can be generated from task traces  
• the graph contains exactly the pipeline modules  
• metadata is aggregated correctly  
• edges follow stage order  
• tasks remain linked to their parent module  

---

# Deliverables

• module_graph_builder implementation  
• module node data model  
• module edge builder  
• tests verifying aggregation and ordering  
• example module graph output for the demo pipeline

---

# Definition of Done

A developer running the pipeline should be able to generate a module graph that clearly shows:

PDF Ingestion → Text Extraction → Text Processing → Chunking → LLM Analysis → Structured Output

with aggregated runtime and data summaries.

That module graph will serve as the **entry point for the Phase 2 visualization system**.
