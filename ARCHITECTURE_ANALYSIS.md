# Architectural Analysis: Visual Debugging for AI-Generated Python Code
## Can the System Visualize Arbitrary Decorated Python Programs?

---

## EXECUTIVE SUMMARY

**Current Status: NOT FULLY GENERIC**

The system CAN create nodes for any decorated Python function and capture their execution metadata. However, it **CANNOT automatically connect arbitrary functions into a coherent pipeline graph** without predefined pipeline structure. The system is currently **hard-coded for the PDF processing demo pipeline**.

**Key Insight:** Tasks not in `DEMO_PIPELINE_STAGES` are added as graph nodes but left orphaned (not connected in the main spine). The graph renderer will display them, but they won't form meaningful narrative flow.

---

## PART 1: MAJOR ARCHITECTURAL COMPONENTS

### 1.1 Component Inventory

```
instrumentation/
├── decorators.py              # @module, @task decorators capture metadata
└── trace_collector.py         # In-memory trace storage (module-level lists)

graph/
├── dataflow_builder.py        # CORE: converts traces to graphs (HARDCODED PIPELINE)
├── module_graph_builder.py    # Aggregates tasks into module-level view
└── module_graph_visualizer.py # PyVis HTML rendering

pipeline/
└── demo_pipeline.py           # Example pipeline using decorators

api/
└── server.py                  # FastAPI HTTP wrapper (optional)
```

### 1.2 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Python Code                          │
│ @module("PDF Processing")                                   │
│ @task("Extract text from PDF")                              │
│ def extract_text(pdf_doc):  ...                              │
└────────────┬────────────────────────────────────────────────┘
             │ Decorated functions execute
             ▼
┌──────────────────────────────────────────────────────────────┐
│         INSTRUMENTATION LAYER (@task decorator)              │
│  • Intercepts function calls                                 │
│  • Records: task_name, module_name, inputs, outputs,        │
│    duration, status, parent_task                            │
└────────────┬─────────────────────────────────────────────────┘
             │ record_event(TraceEvent)
             ▼
┌──────────────────────────────────────────────────────────────┐
│     TRACE COLLECTOR (trace_collector.py)                     │
│  • Global runtime_trace list (Module-level list)             │
│  • Global execution_stack (for call context)                 │
│  • Functions: reset_trace(), get_trace(), record_event()    │
└────────────┬─────────────────────────────────────────────────┘
             │ trace = get_trace()
             ▼
┌──────────────────────────────────────────────────────────────┐
│     GRAPH BUILDER (dataflow_builder.py)                      │
│  • Normalizes trace events                                  │
│  • Assigns pipeline ordering from DEMO_PIPELINE_STAGES      │
│  • Creates nodes for each task                              │
│  • Creates edges using main spine + branch logic            │
│  • Returns: nx.DiGraph                                       │
└────────────┬─────────────────────────────────────────────────┘
             │
             ├──── task_graph = build_dataflow_graph(trace)
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│    MODULE GRAPH BUILDER (module_graph_builder.py)            │
│  • Groups tasks by module_name                              │
│  • Aggregates metadata (duration, status, I/O summaries)    │
│  • Creates module-level nodes                               │
│  • Creates module-to-module edges                           │
│  • Inserts decision nodes for branching                     │
│  • Returns: nx.DiGraph (7 nodes: 6 modules + 1 decision)    │
└────────────┬─────────────────────────────────────────────────┘
             │ module_graph = create_module_graph(task_graph)
             ▼
┌──────────────────────────────────────────────────────────────┐
│  VISUALIZATION (module_graph_visualizer.py)                  │
│  • Converts DiGraph to PyVis Network                         │
│  • Applies styling (colors, shapes, edges)                  │
│  • Generates standalone HTML with vis.js                    │
│  • Injects navigation JS + summary banner                   │
│  • Writes to output/module_graph.html                       │
└──────────────────────────────────────────────────────────────┘
```

---

## PART 2: DECORATOR ANALYSIS

### 2.1 @task Decorator

**Location:** `instrumentation/decorators.py`

**What it captures:**
- `task_name` — the decorated function's `__name__`
- `task_description` — user-provided description (parameter)
- `module_name` — from @module wrapper (if present), else ""
- `parent_task` — from execution_stack (for nested calls)
- `trace_index` — auto-assigned by record_event()
- `start_time`, `end_time` — wall-clock times (perf_counter)
- `duration_ms` — computed as (end_time - start_time) * 1000
- `status` — "success" or "error"
- `input_preview`, `output_preview` — string summaries (via preview_helpers.py)
- `input_length`, `output_length` — byte counts
- `error_message` — exception message if status="error"

**Recording mechanism:**
```python
@functools.wraps(fn)
def wrapper(*args, **kwargs):
    execution_stack.append(task_name)
    start_time = time.perf_counter()
    input_preview, input_length = make_args_preview(args, kwargs)
    
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        # Record error event
        event = {..., status: "error", error_message: str(exc)}
        record_event(event)
        raise
    else:
        # Record success event
        output_preview, output_length = make_preview(result)
        event = {..., status: "success", output_preview: output_preview}
        record_event(event)
        return result
    finally:
        execution_stack.pop()
```

**Recording location:** Global `runtime_trace` list in `trace_collector.py`

### 2.2 @module Decorator

**Location:** `instrumentation/decorators.py`

**What it does:**
- Attaches `_viz_module_name` attribute to the @task wrapper
- Delegates all calls to the inner wrapper
- Does NOT itself record events (the @task wrapper does)

**Key behavior:**
```python
def module(name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapper._viz_module_name = name  # @task reads this
        return wrapper
    return decorator
```

**Stacking requirement:**
```python
@module("Math Operations")      # OUTER (applied second)
@task("Add two numbers")        # INNER (applied first)
def add_numbers(a, b):
    return a + b
```

### 2.3 Genericness Assessment

**The decorators themselves ARE generic:**
- ✅ No hardcoded pipeline references
- ✅ Work with ANY function (any name, any signature)
- ✅ Capture all necessary metadata automatically
- ✅ Support nested function calls via execution_stack

**BUT the pipeline structure is NOT generic:**
- ❌ Graph builder requires `DEMO_PIPELINE_STAGES` (hardcoded in dataflow_builder.py)
- ❌ Pipeline ordering derived from this dict, not from runtime events
- ❌ Unknown tasks placed at stage_index=999 (after all known tasks)

---

## PART 3: RUNTIME FLOW TRACE

### 3.1 End-to-End Execution Sequence

```
STEP 1: Reset for clean state
┌─────────────────────────────────────────────────────┐
│ reset_trace()                                       │
│  • Clear runtime_trace = []                         │
│  • Clear execution_stack = []                       │
└─────────────────────────────────────────────────────┘

STEP 2: Execute decorated pipeline
┌─────────────────────────────────────────────────────┐
│ my_pipeline()                                       │
│   → @task wrapper intercepts call                   │
│   → Pushes task_name to execution_stack             │
│   → Calls real function                             │
│   → Pops from execution_stack                       │
│   → Calls record_event(trace_event)                 │
│      → Assigns trace_index = len(runtime_trace)    │
│      → Appends to runtime_trace                     │
└─────────────────────────────────────────────────────┘

STEP 3: Collect trace
┌─────────────────────────────────────────────────────┐
│ trace = get_trace()                                 │
│  • Returns shallow copy of runtime_trace            │
│  • At this point: trace has 17 events (PDF pipeline)
│    Example: [                                       │
│      {task_name: "load_pdf", trace_index: 0, ...},  │
│      {task_name: "validate_pdf", trace_index: 1,...},
│      ...                                            │
│      {task_name: "export_result", trace_index: 17}  │
│    ]                                                │
└─────────────────────────────────────────────────────┘

STEP 4: Build data-flow task graph
┌─────────────────────────────────────────────────────┐
│ task_graph = build_dataflow_graph(trace)            │
│  1. normalize_trace(trace)                          │
│     • Validate required fields                      │
│     • Add source_file, source_line_start defaults   │
│                                                     │
│  2. assign_pipeline_order(normalized)               │
│     • For EACH event:                               │
│       ├─ Look up task_name in DEMO_PIPELINE_STAGES  │
│       ├─ If found: assign (stage_index, step_order) │
│       └─ Else: assign (stage_index=999, step_order) │
│     • Sort by (stage_index, step_order, trace_index)│
│                                                     │
│  3. build_dataflow_nodes(ordered, graph)            │
│     • For EACH event:                               │
│       └─ Add node: f"{task_name}__{trace_index}"    │
│       └─ Attach all metadata fields                │
│     • Returns: {task_name: node_id} mapping         │
│                                                     │
│  4. _add_alternate_nodes(graph)                     │
│     • For EACH task in DEMO_PIPELINE_STAGES         │
│     • That is marked is_main_path=False             │
│     • But did NOT execute:                          │
│       └─ Add placeholder node: f"{task_name}__alt"  │
│                                                     │
│  5. build_dataflow_edges(graph, task_to_node, alt)  │
│     • Walk _MAIN_SPINE in order                     │
│     • Connect consecutive executed spine tasks      │
│     • Add branch metadata for branch transitions    │
│     • Connect decision tasks to alternate options   │
│                                                     │
│  Returns: DiGraph with 20 nodes, 19 edges          │
└─────────────────────────────────────────────────────┘

STEP 5: Build module-level graph
┌─────────────────────────────────────────────────────┐
│ module_graph = create_module_graph(task_graph)      │
│  1. build_module_nodes(task_graph)                  │
│     • Group tasks by module_name                    │
│     • For EACH group:                               │
│       └─ Aggregate: status, duration, I/O summaries │
│       └─ Create module node with stage_index        │
│     • Returns: DiGraph with 6 module nodes          │
│                                                     │
│  2. build_module_edges(module_graph) [NEW IN REFACTOR]
│     • Detect Text Processing → Chunking transition  │
│     • Insert decision node at stage_index=2.5       │
│     • Create two branch edges (curvedCW/CCW)        │
│     • Mark taken vs alternate paths                 │
│                                                     │
│  Returns: DiGraph with 7 nodes, 7 edges            │
└─────────────────────────────────────────────────────┘

STEP 6: Render module graph to HTML
┌─────────────────────────────────────────────────────┐
│ html = render_module_graph_html(module_graph)       │
│  1. _compute_module_positions(module_graph)        │
│     • Assign x = index * 320 pixels                 │
│     • All nodes at y = 0 (single row)               │
│                                                     │
│  2. Create PyVis Network                            │
│     • physics: disabled                             │
│     • Add 7 module nodes                            │
│       └─ colors based on status (green/red/amber)   │
│       └─ shapes: box for modules, diamond for decis.│
│       └─ size: fixed, with widthConstraint          │
│                                                     │
│  3. Add 7 edges with styling                        │
│     ├─ Pipeline edges: solid, blue-grey             │
│     ├─ Taken branches: solid, dark green            │
│     ├─ Alternate branches: dotted, light grey       │
│     └─ Labels showing branch names                  │
│                                                     │
│  4. Generate HTML (PyVis.generate_html)             │
│                                                     │
│  5. Inject enhancements                             │
│     ├─ Navigation JS (click module → task graph)    │
│     ├─ Summary banner                               │
│     ├─ Title cleanup                                │
│     └─ Write to output/module_graph.html            │
└─────────────────────────────────────────────────────┘

STEP 7: Task graphs (for each module)
┌─────────────────────────────────────────────────────┐
│ For EACH module in module_graph:                    │
│   IF is_decision_node: skip                         │
│   ELSE:                                             │
│     task_payload = build_task_graph_for_module(     │
│       task_graph, module_name                       │
│     )                                               │
│     html = render_task_graph_html(task_payload)     │
│     write to output/task_graph_<module_slug>.html   │
└─────────────────────────────────────────────────────┘
```

### 3.2 Key Files and Functions by Step

| Step | File | Function | Purpose |
|------|------|----------|---------|
| 1 | `trace_collector.py` | `reset_trace()` | Clear for new run |
| 2 | `decorators.py` | `@task wrapper` | Intercept, time, record |
| 2 | `trace_collector.py` | `record_event()` | Append to runtime_trace |
| 3 | `trace_collector.py` | `get_trace()` | Copy runtime_trace |
| 4.1 | `dataflow_builder.py` | `normalize_trace()` | Validate fields |
| 4.2 | `dataflow_builder.py` | `assign_pipeline_order()` | Map tasks to stages |
| 4.3 | `dataflow_builder.py` | `build_dataflow_nodes()` | Create task nodes |
| 4.4 | `dataflow_builder.py` | `_add_alternate_nodes()` | Create placeholder nodes |
| 4.5 | `dataflow_builder.py` | `build_dataflow_edges()` | Connect with branch logic |
| 5 | `module_graph_builder.py` | `create_module_graph()` | Build module-level view |
| 6 | `module_graph_visualizer.py` | `render_module_graph_html()` | PyVis + HTML injection |
| 7 | `task_graph_builder.py` | `build_task_graph_for_module()` | Module → task view |

---

## PART 4: GENERICNESS ASSESSMENT

### 4.1 Current Reality: NOT GENERIC

**Q: If a completely new Python script with decorated functions were run, would the system automatically generate a graph?**

**A: Partially. Nodes yes, meaningful edges no.**

Example: User writes a new script:
```python
from instrumentation.decorators import @module, @task

@module("Data Pipeline")
@task("Load data")
def load_data():
    return {"rows": 1000}

@module("Data Pipeline")
@task("Transform data")
def transform(data):
    return {"transformed": True}

@module("Data Pipeline")
@task("Export")
def export(data):
    return "exported"

reset_trace()
load_data()
transform({})
export({})
trace = get_trace()
graph = build_dataflow_graph(trace)
```

**Result:** 
- ✅ Nodes created for load_data, transform, export
- ❌ Nodes NOT connected in spine (they're not in DEMO_PIPELINE_STAGES)
- ⚠️ Nodes appear in graph but form disconnected components or connect by trace_index accident

**Why?** The `build_dataflow_edges()` function walks `_MAIN_SPINE` which comes from `DEMO_PIPELINE_STAGES`:

```python
# Only connects tasks that appear in DEMO_PIPELINE_STAGES
executed_spine = [t for t in _MAIN_SPINE if t in task_to_node]
for i in range(len(executed_spine) - 1):
    from_task = executed_spine[i]
    to_task = executed_spine[i + 1]
    # Connect from_task → to_task
```

If neither load_data, transform, nor export appear in DEMO_PIPELINE_STAGES, `executed_spine` is empty → no edges created.

### 4.2 Dependency on DEMO_PIPELINE_STAGES

**Current tight coupling:**
- `DEMO_PIPELINE_STAGES` is hardcoded in `dataflow_builder.py` (lines 167-237)
- It explicitly lists 6 modules and 18 tasks
- It defines 2 branch points (language_branch, chunk_strategy)
- All edges are built from this definition, not derived from runtime events

**Consequences:**
- ❌ Graph builder assumes these exact modules and tasks exist
- ❌ Tasks not in the list are orphaned
- ❌ Creating a new pipeline requires modifying the source code
- ❌ The system cannot adapt to arbitrary function hierarchies

### 4.3 What Changes Would Be Required to Make It Generic

**Option A: MINIMAL — Fallback trace_index-based edges (Recommended)**

When a task is not in DEMO_PIPELINE_STAGES, connect it to the next task in execution order:

```python
# In build_dataflow_edges():

# After main spine edges, connect any orphaned nodes by trace_index
all_executed_nodes = list(task_to_node.values())
all_executed_by_index = sorted(
    task_to_node.items(),
    key=lambda x: task_to_node[x[0]].trace_index  # Sort by trace index
)

for i in range(len(all_executed_by_index) - 1):
    from_node = all_executed_by_index[i]
    to_node = all_executed_by_index[i + 1]
    if not graph.has_edge(from_node, to_node):
        graph.add_edge(from_node, to_node, relationship="pipeline_flow")
```

**Effort:** ~20 lines of code. Test it with a script that has NO tasks in DEMO_PIPELINE_STAGES.

**Downside:** Loses narrative ordering. Graphs would follow trace_index exactly, which may not match intended pipeline flow.

---

**Option B: MODERATE — Parametrize the pipeline**

Allow passing a custom pipeline definition:

```python
def build_dataflow_graph(
    trace: List[TraceEvent],
    pipeline_stages: Optional[List[PipelineStage]] = None
) -> nx.DiGraph:
    # Use provided stages or fall back to DEMO_PIPELINE_STAGES
    if pipeline_stages is None:
        pipeline_stages = DEMO_PIPELINE_STAGES
    # ... rebuild index structures from stages ...
```

**Effort:** ~50 lines. Requires defining `PipelineStage` objects for each new pipeline. More flexible.

**Downside:** Users must know the pipeline structure in advance and define it manually. Not much better than Option A for live code.

---

**Option C: COMPREHENSIVE — Derive pipeline from module_name + execution order**

Use module_name as the primary ordering signal:

```python
def build_dataflow_graph(trace: List[TraceEvent]) -> nx.DiGraph:
    # Group events by module_name
    modules_by_name = {}
    for event in trace:
        mod = event.get("module_name", "unknown")
        if mod not in modules_by_name:
            modules_by_name[mod] = []
        modules_by_name[mod].append(event)
    
    # Derive ordering from first appearance in trace
    module_order = list(dict.fromkeys(
        event.get("module_name") for event in trace
    ))
    
    # Build edges based on module order NOT predefined stages
```

**Effort:** ~100 lines. Most flexible but requires all tasks to have module_name set.

---

### 4.4 Recommendation: Make It Dual-Mode

Recommended approach: Use **Option A + Option C hybrid**:

1. **If all tasks have module_name:** Derive pipeline from module occurrence order
2. **If some tasks lack module_name:** Fall back to trace_index order
3. **If user provides custom stages:** Use those (for backwards compatibility)

This keeps the PDF demo working while making arbitrary scripts functional.

---

## PART 5: DIFFICULTY OF RUNNING ARBITRARY CODE

### 5.1 Current Workflow (Synthetic - Doesn't Use Real Code)

```python
# demo_prd10_navigation.py

def _build_phase2_trace() -> list:
    # Manually construct trace events (FAKE execution)
    return [
        {task_name: "load_pdf", trace_index: 0, ...},
        {task_name: "validate_pdf", trace_index: 1, ...},
        ...
    ]

# No actual function calls happen!
trace = _build_phase2_trace()
task_graph = build_dataflow_graph(trace)
```

This is NOT exercising the decorators at all.

### 5.2 What Would Be Needed for Real Arbitrary Code

**Minimal wrapper script:**

```python
# run_arbitrary_demo.py

import sys
import importlib.util
from pathlib import Path
from instrumentation.trace_collector import reset_trace, get_trace
from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph
from graph.module_graph_visualizer import render_module_graph_html
from graph.task_graph_builder import build_task_graph_for_module
from graph.task_graph_visualizer import render_task_graph_html

def run_user_script(script_path: str, output_dir: str = "output"):
    """
    Load and execute a user's Python script, visualize it.
    
    Usage:
        python run_arbitrary_demo.py my_pipeline.py /tmp/graphs
    """
    
    # 1. Load the user's script as a module
    spec = importlib.util.spec_from_file_location("user_script", script_path)
    module = importlib.util.module_from_spec(spec)
    
    # 2. Reset trace for clean state
    reset_trace()
    
    # 3. Execute the script (this runs the @task decorators)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error executing script: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 4. Collect trace
    trace = get_trace()
    if not trace:
        print("No traced events. Did you use @module and @task decorators?")
        sys.exit(1)
    
    # 5. Build graphs
    task_graph = build_dataflow_graph(trace)
    module_graph = create_module_graph(task_graph)
    
    # 6. Render HTML
    Path(output_dir).mkdir(exist_ok=True)
    module_html = render_module_graph_html(
        module_graph,
        output_path=f"{output_dir}/module_graph.html"
    )
    print(f"Module graph: {module_html}")
    
    # 7. Render task graphs
    for mod_name in set(e.get("module_name") for e in trace if e.get("module_name")):
        payload = build_task_graph_for_module(task_graph, mod_name)
        task_html = render_task_graph_html(payload, ...)
        print(f"Task graph: {task_html}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_arbitrary_demo.py <script.py> [output_dir]")
        sys.exit(1)
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    run_user_script(sys.argv[1], output_dir)
```

**User would then write:**

```python
# my_pipeline.py

from instrumentation.decorators import module, task

@module("Load Stage")
@task("Read data from source")
def load():
    return {"data": [1, 2, 3]}

@module("Transform Stage")
@task("Apply transformations")
def transform(data):
    return {"result": [x * 2 for x in data["data"]]}

@module("Output Stage")
@task("Write results")
def output(data):
    print(data)

# Entry point
if __name__ == "__main__":
    load()
    x = transform(load())
    output(x)
```

**Run with:**

```bash
python run_arbitrary_demo.py my_pipeline.py /tmp/graphs
# Output:
#   Module graph: /tmp/graphs/module_graph.html
#   Task graph: /tmp/graphs/task_graph_load_stage.html
#   ...
```

**What still needs fixing:**

❌ The `build_dataflow_graph()` will create nodes for load, transform, output  
❌ But edges will NOT be created (tasks aren't in DEMO_PIPELINE_STAGES)  
✅ Module graph WILL work (groups by module_name)  
✅ Visualization WILL show nodes (just not connected in task view)

**Minimal patch needed (from Part 4 Option A):**
- Add fallback trace_index-based edge building (~20 lines)
- Then arbitrary scripts will work end-to-end

---

## PART 6: SIMPLEST LIVE DEMO LOOP

### 6.1 Recommended Live Demo Wrapper

```python
# live_demo.py -- Entry point for live visualization

import tempfile
from pathlib import Path
import importlib.util
import subprocess
from instrumentation.trace_collector import reset_trace, get_trace
from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph
from graph.module_graph_visualizer import render_module_graph_html

def visualize_code(code_str: str, output_dir: str = "output") -> str:
    """
    Live code → generated graph in 3 steps.
    
    Usage:
        html_path = visualize_code("""
from instrumentation.decorators import module, task

@module("Math")
@task("Add numbers")
def add(a, b):
    return a + b

add(2, 3)
        """)
        print(f"View: file://{html_path}")
    """
    
    # 1. Write code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code_str)
        temp_path = f.name
    
    try:
        # 2. Execute the code (decorators record trace)
        reset_trace()
        spec = importlib.util.spec_from_file_location("temp", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 3. Get trace and build graphs
        trace = get_trace()
        if not trace:
            raise RuntimeError("No @task-decorated functions were executed")
        
        task_graph = build_dataflow_graph(trace)
        module_graph = create_module_graph(task_graph)
        
        # 4. Render to HTML
        Path(output_dir).mkdir(exist_ok=True)
        html_path = render_module_graph_html(
            module_graph,
            output_path=f"{output_dir}/live_graph.html"
        )
        
        return html_path
        
    finally:
        Path(temp_path).unlink()  # Clean up temp file

# BROWSER INTEGRATION (Optional)
def visualize_and_open(code_str: str):
    """Visualize code and open in browser."""
    import webbrowser
    html_path = visualize_code(code_str)
    webbrowser.open(f"file://{html_path}")
```

### 6.2 Integration Points

**For AI code generation workflow:**

```python
# In an AI agent or Jupyter notebook:

user_code = ai_agent.generate_code(
    "write a pipeline that loads data, cleans it, and exports"
)

# Visualize immediately
visualize_and_open(user_code)
```

**For FastAPI server (if deployed):**

```python
# api/server.py

@app.post("/visualize")
async def visualize_code_endpoint(code: str):
    try:
        html_path = visualize_code(code)
        return {
            "status": "success",
            "html_file": html_path,
            "url": f"/graphs/{Path(html_path).name}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 6.3 Workflow

```
┌─────────────────────────────────────────┐
│ AI generates Python code with @task     │
│ @module decorators                      │
└──────────────┬──────────────────────────┘
               │ code_string
               ▼
┌─────────────────────────────────────────┐
│ visualize_code(code_string)             │
│ 1. Write to tempfile                    │
│ 2. reset_trace()                        │
│ 3. exec() the code                      │
│ 4. trace = get_trace()                  │
│ 5. task_graph = build_dataflow_graph()  │
│ 6. module_graph = create_module_graph() │
│ 7. render_module_graph_html()           │
│ 8. return html_path                     │
└──────────────┬──────────────────────────┘
               │ html_file_path
               ▼
┌─────────────────────────────────────────┐
│ Browser opens: file:///.../live_graph   │
│ User sees:                              │
│   • Module pipeline overview            │
│   • Execution timing                    │
│   • Branch visualization                │
│   • Clickable drill-down to tasks       │
└─────────────────────────────────────────┘
```

---

## PART 7: SUMMARY & RECOMMENDATIONS

### 7.1 Direct Question: Generic or Hard-Coded?

**ANSWER: Currently hard-coded for the specific PDF pipeline. NOT generic.**

**The System's Current Constraints:**

| Component | Status | Constraint |
|-----------|--------|-----------|
| @task decorator | ✅ Generic | Works with any function |
| @module decorator | ✅ Generic | Works with any module_name |
| Trace collection | ✅ Generic | Records any decorated call |
| Task graph build | ❌ NOT generic | Requires DEMO_PIPELINE_STAGES |
| Module graph build | ✅ Generic (with metadata) | Groups by module_name |
| Visualization | ✅ Generic | Renders any graph |

---

### 7.2 How to Use the System on New Scripts

**TODAY (Current State):**

1. Write a script with @module and @task decorators
2. Run: `python -c "from run_arbitrary_demo import visualize_and_open; visualize_and_open(open('my_script.py').read())"`
3. Result:
   - ✅ Module graph shows modules in execution order
   - ⚠️ Task graph edges may not be connected properly
   - ⚠️ Orphaned nodes for tasks not in DEMO_PIPELINE_STAGES

**Why it doesn't work perfectly:**
- `build_dataflow_graph()` only connects tasks in DEMO_PIPELINE_STAGES
- New tasks appear as nodes but aren't connected in the spine

---

### 7.3 Minimum Changes for Full Genericness

**REQUIRED FIX (Recommended Strategy — ~50 lines of code):**

**Version A: Add fallback trace_index edges (Simplest)**

In `graph/dataflow_builder.py` after the main spine is built:

```python
# After building main spine edges:

# Fallback: connect orphaned nodes by execution order
all_executed_ids = list(task_to_node.values())
ordered_by_index = sorted(
    all_executed_ids,
    key=lambda nid: graph.nodes[nid].get("trace_index", 999)
)

for i in range(len(ordered_by_index) - 1):
    from_id = ordered_by_index[i]
    to_id = ordered_by_index[i + 1]
    if not graph.has_edge(from_id, to_id):
        graph.add_edge(from_id, to_id, relationship="pipeline_flow")
```

**Impact:** Any task not in DEMO_PIPELINE_STAGES will be connected by execution order.

**Effort:** 20 minutes + testing

---

**RECOMMENDED FIX: Module-order-based deriving (Better)**

Detect pipeline structure from module_name without requiring DEMO_PIPELINE_STAGES:

```python
# Derive stage_index from module appearance order in trace
def derive_pipeline_stages_from_trace(trace):
    module_first_appearance = {}
    for i, event in enumerate(trace):
        mod = event.get("module_name", "")
        if mod not in module_first_appearance:
            module_first_appearance[mod] = i
    return module_first_appearance  # Use this for ordering
```

**Impact:** Generic for any module-named pipeline.

**Effort:** 30 minutes + testing

---

### 7.4 What Would Make It Fully Live-Demo Ready

```
CURRENT STATE
└─ Works: PDF demo + other predefined pipelines
└─ Breaks: Arbitrary new scripts (orphaned nodes)

AFTER MINIMAL FIX (20 lines)
└─ Works: PDF demo + arbitrary scripts
└─ Draws: All nodes with trace_index fallback ordering
└─ Limitation: May not match intended pipeline flow

AFTER BETTER FIX (50 lines)
└─ Works: PDF demo + arbitrary scripts
└─ Draws: All nodes correctly ordered by module appearance
└─ Delivers: Full generic visualization
└─ Ready: For live AI code generation demo
```

---

### 7.5 Live Demo Usage (After Fix)

```bash
# User runs AI-generated code:
python << 'EOF'
from instrumentation.decorators import module, task
from instrumentation.trace_collector import get_trace, reset_trace
from graph.dataflow_builder import build_dataflow_graph
from graph.module_graph_builder import create_module_graph
from graph.module_graph_visualizer import render_module_graph_html

@module("Extract") 
@task("Pull data from API")
def extract():
    return {"raw": "data"}

@module("Transform")
@task("Clean and format")
def transform(data):
    return {"cleaned": "data"}

@module("Load")
@task("Store to database") 
def load(data):
    print("Saved!")

reset_trace()
d1 = extract()
d2 = transform(d1)
load(d2)

trace = get_trace()
graph = build_dataflow_graph(trace)
module_graph = create_module_graph(trace)
render_module_graph_html(module_graph, "demo.html")
print("Open: demo.html")
EOF
```

**Expected output:** Clean pipeline visualization with 3 modules and all edges connected ✅

---

## CONCLUSION

### The Bottom Line

| Question | Answer |
|----------|--------|
| **Can it visualize arbitrary decorated Python?** | Almost, but not quite. Nodes yes, edges need fix. |
| **Is it generic or hardcoded?** | Hardcoded to DEMO_PIPELINE_STAGES; needs ~50 lines to fix. |
| **How hard to make it generic?** | Easy: 1-2 hours of development + testing. |
| **Is it ready for live demos?** | Almost: works for PDF demo, fails for brand new code. |
| **Recommended next step?** | Apply "RECOMMENDED FIX" (module-order-based ordering) + test with 3 new arbitrary pipelines. |

### Action Items for Live Demo Support

- [ ] Test `build_dataflow_graph()` with trace containing tasks NOT in DEMO_PIPELINE_STAGES
- [ ] Implement fallback trace_index or module-order edge building
- [ ] Write `run_arbitrary_demo.py` wrapper script (provided above)
- [ ] Test end-to-end with a completely new decorated pipeline
- [ ] Verify module graphs, task graphs, and HTML rendering all work

After these items, the system will be **production-ready for live visualization of arbitrary AI-generated Python code**.

---

## APPENDIX: Key Data Structures

### TraceEvent (from schema.py)

```python
{
    "task_name": str,
    "task_description": str,
    "module_name": str,
    "parent_task": Optional[str],
    "trace_index": int,
    "start_time": float,
    "end_time": float,
    "duration_ms": float,
    "status": str,  # "success" | "error"
    "input_preview": str,
    "output_preview": str,
    "input_length": int,
    "output_length": int,
    "error_message": Optional[str],
}
```

### Global State (trace_collector.py)

```python
runtime_trace: List[TraceEvent] = []      # Ordered events
execution_stack: List[str] = []           # Active call chain
```

### DEMO_PIPELINE_STAGES (dataflow_builder.py, lines 167-237)

```python
DEMO_PIPELINE_STAGES = [
    PipelineStage(
        name="PDF Ingestion",
        stage_index=0,
        tasks=["load_pdf", "validate_pdf", "count_pages"],
    ),
    PipelineStage(
        name="Text Extraction",
        stage_index=1,
        tasks=["extract_text", "merge_pages", "detect_language"],
        branch=BranchPoint(...)
    ),
    # ...5 more stages...
]
```

---

**END OF ANALYSIS REPORT**
