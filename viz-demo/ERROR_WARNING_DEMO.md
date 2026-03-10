# Error & Warning Demo — Complete Setup

## Demo Created Successfully ✅

A new demonstration scenario has been created showing how the visualization system handles warnings, errors, and cascading failures in an execution pipeline.

---

## What's Included

### New Demo File
- **`demo_prd10_navigation_with_errors_and_warnings.py`** — Generates visualizations with error/warning scenario

### Generated HTML Files (in `output/` and copied to `viz-demo/`)
1. **`module_graph_with_errors.html`** — Module-level overview showing:
   - 🟢 PDF Ingestion: **success** (green)
   - 🟢 Text Processing: **success** (green)
   - 🟡 Text Extraction: **⚠ warning** (amber) — extract_text took 250ms instead of 118ms
   - 🔴 Chunking: **✖ error** (red) — split_into_chunks failed
   - 🔴 LLM Analysis: **✖ error** (red) — cascade failure
   - 🔴 Structured Output: **✖ error** (red) — cascade failure
   - Summary bar shows: "Errors encountered"

2. **Task-level drill-down files:**
   - `task_graph_pdf_ingestion.html` — All green (success)
   - `task_graph_text_extraction_warned.html` — Amber (warning)
   - `task_graph_text_processing.html` — All green (success)
   - `task_graph_chunking_error.html` — Red at split_into_chunks node
   - `task_graph_llm_analysis_error.html` — All red (cascading failures)
   - `task_graph_structured_output_error.html` — All red (cascading failures)

---

## Scenario Details

### Yellow Warning: Text Extraction
```
extract_text task:
  • Status: "warning"
  • Duration: 250 ms (expected ~118 ms)
  • Still succeeded, but performance degraded
  • Module shows amber/yellow color
```

### Red Error: Chunking Failure
```
split_into_chunks task:
  • Status: "error"
  • Error message: "Chunking strategy failed: overlap factor out of range"
  • Module shows red color
```

### Red Cascade: Downstream Failures
```
analyze_chunks, aggregate_results, generate_summary:
  • Status: "error"
  • Error message: "Dependency failed: upstream task did not complete"
  • Both LLM Analysis and Structured Output modules show red
```

---

## Visual Color Coding

The visualization system uses:

| Status | Color | Hexcode | Icon | Badge |
|--------|-------|---------|------|-------|
| **success** | 🟢 Green | #4caf50 | ✓ | ✓ success |
| **warning** | 🟡 Amber | #ff9800 | ⚠ | ⚠ warning |
| **error** | 🔴 Red | #f44336 | ✖ | ✖ error |
| **not_executed** | ⚪ Grey | #b0bec5 | — | — not executed |

---

## Summary Bar Messages

The module graph shows dynamic summary based on overall status:

| Scenario | Message | Emoji |
|----------|---------|-------|
| All succeed | "All modules succeeded" | ✓ |
| Has warnings | "Warnings present" | ⚠ |
| Has errors | "Errors encountered" | ✖ |

For the error/warning demo: **"Errors encountered"** with 🔴 red indicator

---

## Updated Index Page

The [index.html](index.html) now includes:

### Two Scenario Sections
1. **Successful Execution** — Green demo showing nominal pipeline
2. **Warnings & Errors** — Mixed status demo showing:
   - Yellow warning on extraction (performance issue)
   - Red errors on chunking and downstream
   - Cascading failure visualization

### Easy Navigation
- Click module graph to see overview
- Click task graphs to drill into details
- Each task graph has "Back to Module Overview" link

---

## How to Use

### View Locally
1. Open [viz-demo/index.html](./index.html) in browser
2. Under "Scenario: Warnings & Errors" section
3. Click "Pipeline Module Graph (With Errors)"
4. Browse the color-coded pipeline visualization
5. Click on any module to drill into task details

### In Render Deployment
- Same experience, hosted at `https://your-site.onrender.com`
- All visualizations are interactive
- Works on mobile, tablet, desktop

---

## File Structure in viz-demo/

```
viz-demo/
├── index.html                              (Updated with both scenarios)
├── 
├── Success Scenario Files:
├── module_graph.html
├── task_graph_pdf_ingestion.html
├── task_graph_text_extraction.html
├── task_graph_text_processing.html
├── task_graph_chunking.html
├── task_graph_llm_analysis.html
├── task_graph_structured_output.html
│
├── Errors & Warnings Scenario Files:
├── module_graph_with_errors.html          (Main error demo)
├── task_graph_text_extraction_warned.html (Warning example)
├── task_graph_chunking_error.html         (Failure example)
├── task_graph_llm_analysis_error.html     (Cascade failure)
├── task_graph_structured_output_error.html (Cascade failure)
│
└── Documentation:
    ├── README.md
    ├── DEPLOYMENT.md
    └── ERROR_WARNING_DEMO.md (this file)
```

---

## Technical Implementation

### Trace Events
The demo uses synthetic trace events with status values:
- `status="success"` → Green nodes
- `status="warning"` → Amber nodes
- `status="error"` → Red nodes

### Module Status Computation
Module status is derived from its tasks:
- All tasks success → Module success
- Any task warning → Module warning (if no errors)
- Any task error → Module error

### Cascade Failures
When upstream task fails:
- All downstream tasks marked as error
- Error messages reference upstream failure
- Durations show as 0 ms (not executed)

---

## Key Features Demonstrated

✅ **Color-coded visualization** — Immediately see success/warning/error status  
✅ **Error messages** — Click on failed nodes to see error details  
✅ **Cascade visualization** — See how failures propagate downstream  
✅ **Performance warnings** — Yellow indicators for degraded but successful tasks  
✅ **Module-level view** — Overview shows aggregate status (one color per module)  
✅ **Task-level detail** — Drill down to see individual task status  
✅ **Navigation** — Seamless click-through between overview and details  

---

## Running the Demo

### Generate visualizations
```bash
python demo_prd10_navigation_with_errors_and_warnings.py
```

### View locally
```bash
# Windows
start viz-demo/module_graph_with_errors.html

# macOS
open viz-demo/module_graph_with_errors.html

# Linux
xdg-open viz-demo/module_graph_with_errors.html
```

---

## Creating Custom Error Scenarios

To create your own error/warning demo:

```python
def _build_custom_trace():
    return [
        # Success tasks
        _make_event(
            "task_name", 0, "Module Name",
            status="success",  # ✓
        ),
        
        # Warning task
        _make_event(
            "slow_task", 1, "Module Name",
            duration_ms=999.0,  # Much longer than expected
            status="warning",   # ⚠
        ),
        
        # Failed task
        _make_event(
            "failing_task", 2, "Module Name",
            status="error",     # ✖
            error_message="What went wrong",
        ),
    ]
```

---

## Status Summary

| Component | Status |
|-----------|--------|
| Demo file created | ✅ |
| Error scenario generated | ✅ |
| Warning scenario generated | ✅ |
| Cascade failures working | ✅ |
| Title colors correct | ✅ |
| Summary messages updated | ✅ |
| Index page updated | ✅ |
| Files copied to viz-demo | ✅ |
| Ready for Render deployment | ✅ |

---

## Next Steps

1. **Local Testing** — Open index.html and explore both scenarios
2. **Deploy to Render** — Push to GitHub, Render auto-deploys
3. **Share URL** — Send to team/stakeholders
4. **Customize** — Create additional error scenarios as needed

---

*Error & Warning Demo setup completed: March 9, 2026*
