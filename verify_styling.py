from demo_prd10_navigation import _build_phase2_trace
from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph

trace = _build_phase2_trace()
task_graph = build_dataflow_graph(trace)
module_graph = create_module_graph(task_graph)

print()
print("=== VISUAL STYLING FOR BRANCHING ===")
print()

# Check decision node styling
for node_id, data in module_graph.nodes(data=True):
    if data.get('is_decision_node'):
        print("DECISION NODE STYLING:")
        print("  Shape: diamond (visual indicator)")
        print("  Color: amber/yellow (#ffc107) - stands out from success nodes")
        print("  Clickable: NO (no task graph to drill into)")
        print()

# Collect branch edges
print("BRANCH EDGE STYLING:")
taken_branches = []
alternate_branches = []

for u, v, data in module_graph.edges(data=True):
    edge_type = data.get('edge_type', 'pipeline')
    if edge_type == 'branch':
        branch_taken = data.get('branch_taken', False)
        branch_label = data.get('branch_label', '')
        
        if branch_taken:
            taken_branches.append(branch_label)
        else:
            alternate_branches.append(branch_label)

if taken_branches:
    print()
    print("  [TAKEN PATHS]")
    for label in taken_branches:
        print(f"    - {label}")
    print("    Style: Solid line, dark green (#2e7d32), width 3")
    print("    Indicates: These paths WERE executed in this run")

if alternate_branches:
    print()
    print("  [ALTERNATE PATHS]")
    for label in alternate_branches:
        print(f"    - {label}")
    print("    Style: Dotted line, light grey (#b0bec5), width 2")
    print("    Indicates: These paths were NOT executed in this run")

print()
print(f"Total branches visualized: {len(taken_branches) + len(alternate_branches)}")
print(f"  - Taken: {len(taken_branches)}")
print(f"  - Alternate: {len(alternate_branches)}")
print()
