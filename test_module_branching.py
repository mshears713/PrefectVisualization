#!/usr/bin/env python
"""
test_module_branching.py — Verify module graph branching structure.

This test script:
1. Builds the Phase 2 trace and data-flow graph
2. Creates the module overview graph (which now includes branching)
3. Prints detailed node and edge information for inspection
4. Verifies the expected branching structure
"""

from __future__ import annotations

from demo_prd10_navigation import _build_phase2_trace
from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph, module_graph_debug_summary

print("\n" + "=" * 80)
print("  TEST: Module Graph Branching Structure")
print("=" * 80)

# -----------------------------------------------------------------------
# Step 1 — Build data-flow task graph
# -----------------------------------------------------------------------
print("\n[1] Building data-flow task graph from synthetic trace...")
trace = _build_phase2_trace()
task_graph = build_dataflow_graph(trace)
print(f"    Task graph nodes: {task_graph.number_of_nodes()}")
print(f"    Task graph edges: {task_graph.number_of_edges()}")

# -----------------------------------------------------------------------
# Step 2 — Build module overview graph
# -----------------------------------------------------------------------
print("\n[2] Building module overview graph...")
module_graph = create_module_graph(task_graph)
print(f"    Module graph nodes: {module_graph.number_of_nodes()}")
print(f"    Module graph edges: {module_graph.number_of_edges()}")

# -----------------------------------------------------------------------
# Step 3 — Print module nodes
# -----------------------------------------------------------------------
print("\n[3] MODULE NODES:")
print("-" * 80)
for node_id, data in sorted(module_graph.nodes(data=True), 
                            key=lambda x: (x[1].get("stage_index", 999), 
                                          x[1].get("module_name", ""))):
    node_type = "[DECISION]" if data.get("is_decision_node") else "[MODULE]"
    stage = data.get("stage_index", "?")
    name = data.get("module_name", "?")
    status = data.get("status", "?")
    tasks = data.get("task_count", 0)
    print(f"  {node_type}  [{stage:4}]  {name:<30}  status={status:<8}  tasks={tasks}")

# -----------------------------------------------------------------------
# Step 4 — Print edges with metadata
# -----------------------------------------------------------------------
print("\n[4] EDGES (in execution order):")
print("-" * 80)
id_to_name = {nid: data.get("module_name", nid) for nid, data in module_graph.nodes(data=True)}

# Sort edges for consistent output
sorted_edges = sorted(module_graph.edges(data=True), key=lambda x: (x[0], x[1]))

for u, v, data in sorted_edges:
    from_name = id_to_name.get(u, u)
    to_name = id_to_name.get(v, v)
    edge_type = data.get("edge_type", "pipeline")
    
    # Build edge description
    if edge_type == "branch":
        branch_type = data.get("branch_type", "")
        branch_label = data.get("branch_label", "")
        branch_taken = data.get("branch_taken", False)
        taken_mark = " [TAKEN]" if branch_taken else " [ALTERNATE]"
        print(f"  {from_name:<30} -> {to_name:<30}  type={edge_type:<8}  label={branch_label:<12}  {taken_mark}")
    else:
        print(f"  {from_name:<30} -> {to_name:<30}  type={edge_type}")

# -----------------------------------------------------------------------
# Step 5 — Print summary
# -----------------------------------------------------------------------
print("\n[5] SUMMARY:")
print("-" * 80)
summary = module_graph_debug_summary(module_graph)
print(f"  Total modules: {summary['num_modules']}")
print(f"  Total edges: {summary['num_edges']}")
print(f"  Total duration: {summary['total_duration_ms']:.0f} ms")

# Print pipeline in sequence
print(f"\n  Pipeline sequence:")
for i, mod in enumerate(summary['modules'], 1):
    branch_note = " [BRANCH DETECTED]" if mod["branch_detected"] else ""
    print(f"    {i}. {mod['module_name']}{branch_note}")

# -----------------------------------------------------------------------
# Step 6 — Verify branching structure
# -----------------------------------------------------------------------
print("\n[6] BRANCHING VERIFICATION:")
print("-" * 80)

# Check for Document Size Decision node
decision_found = False
decision_node_id = None
for node_id, data in module_graph.nodes(data=True):
    if data.get("is_decision_node"):
        decision_found = True
        decision_node_id = node_id
        print(f"  ✓ Found decision node: {data.get('module_name')}")
        break

if not decision_found:
    print(f"  ✗ Decision node not found")

if decision_node_id:
    # Check outgoing edges from decision
    outgoing_edges = list(module_graph.out_edges(decision_node_id, data=True))
    print(f"  ✓ Decision node has {len(outgoing_edges)} outgoing edges:")
    for u, v, data in outgoing_edges:
        target_name = id_to_name.get(v, v)
        branch_label = data.get("branch_label", "?")
        branch_taken = data.get("branch_taken", False)
        taken_mark = " [TAKEN]" if branch_taken else " [ALTERNATE]"
        print(f"      -> {target_name} ({branch_label}){taken_mark}")

print("\n" + "=" * 80)
print("  TEST COMPLETE")
print("=" * 80 + "\n")
