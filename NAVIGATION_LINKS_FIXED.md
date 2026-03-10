# ✅ Navigation Links Fixed — Error Demo

## Problem Fixed

When clicking modules in `module_graph_with_errors.html`, the navigation was taking you to the **success scenario task graphs** (all green) instead of the **error scenario task graphs** (with warnings/errors). The back button also wasn't returning to the correct module graph.

## Root Cause

The error demo wasn't passing custom `task_graph_links` to the `render_module_graph_html()` function. Without them, the renderer auto-generated links to the standard task graph filenames (e.g., `task_graph_text_extraction.html`) instead of the error-scenario specific filenames (e.g., `task_graph_text_extraction_warned.html` or `task_graph_chunking_error.html`).

## Solution Implemented

Updated `demo_prd10_navigation_with_errors_and_warnings.py` to:

1. **Build custom task graph links** mapping each module to its appropriate task graph file based on status:
   ```python
   task_graph_links = {
       node_id_1: "task_graph_pdf_ingestion.html"           # success
       node_id_2: "task_graph_text_extraction_warned.html"  # warning
       node_id_3: "task_graph_text_processing.html"         # success
       node_id_4: "task_graph_chunking_error.html"          # error
       node_id_5: "task_graph_llm_analysis_error.html"      # error
       node_id_6: "task_graph_structured_output_error.html" # error
   }
   ```

2. **Pass custom links to renderer**:
   ```python
   render_module_graph_html(
       module_graph,
       output_path="output/module_graph_with_errors.html",
       task_graph_links=task_graph_links,  # ← NEW: custom links
   )
   ```

3. **Include back links** in task graphs:
   ```python
   render_task_graph_html(
       task_payload,
       output_path=out_path,
       back_link="module_graph_with_errors.html",  # ← Points back to error demo
   )
   ```

## Result

### Navigation Now Works Correctly

**Error Module Graph → Task Graphs:**
- Click "Text Extraction" (🟡 yellow) → Opens `task_graph_text_extraction_warned.html` (shows yellow warning)
- Click "Chunking" (🔴 red) → Opens `task_graph_chunking_error.html` (shows red error)
- Click "LLM Analysis" (🔴 red) → Opens `task_graph_llm_analysis_error.html` (shows red cascading failures)
- Click "Back" link → Returns to `module_graph_with_errors.html` (not the success demo)

**Success Module Graph → Task Graphs (unchanged):**
- Click any module → Opens corresponding task graph (all green)
- Click "Back" → Returns to `module_graph.html`

## Files Updated

### Demo Script
- ✏️ `demo_prd10_navigation_with_errors_and_warnings.py` (updated with custom task_graph_links)

### Generated HTML (updated)
- 📋 `output/module_graph_with_errors.html` (now has correct module click links)
- 📋 `output/task_graph_text_extraction_warned.html` (back link corrected)
- 📋 `output/task_graph_chunking_error.html` (back link corrected)
- 📋 `output/task_graph_llm_analysis_error.html` (back link corrected)
- 📋 `output/task_graph_structured_output_error.html` (back link corrected)

### Deployed to viz-demo
- ✏️ All updated HTML files copied to `viz-demo/` folder

## How to Test

1. Open [viz-demo/index.html](../../viz-demo/index.html) in browser
2. Under "Scenario: Warnings & Errors" section
3. Click "Pipeline Module Graph (With Errors)"
4. Click any red or yellow module
5. **Verify:** You see the RED or YELLOW task graph (not green!)
6. Click "Back to Module Overview" link
7. **Verify:** You return to `module_graph_with_errors.html` (not `module_graph.html`)

## Technical Details

### Module Status → Task Graph Filename Mapping

```python
status == "error"   → task_graph_{slug}_error.html
status == "warning" → task_graph_{slug}_warned.html
status == "success" → task_graph_{slug}.html
```

### Navigation Links Structure

Task graph links map NetworkX node IDs to filenames:
```python
{
    "pdf_ingestion_node_id":      "task_graph_pdf_ingestion.html",
    "text_extraction_node_id":    "task_graph_text_extraction_warned.html",
    "text_processing_node_id":    "task_graph_text_processing.html",
    "chunking_node_id":          "task_graph_chunking_error.html",
    "llm_analysis_node_id":       "task_graph_llm_analysis_error.html",
    "structured_output_node_id":  "task_graph_structured_output_error.html",
}
```

## Verification

✅ Demo runs without errors
✅ Module graph links to correct task graphs
✅ Task graphs have correct back links
✅ Success scenario still works as before
✅ Files updated in both output/ and viz-demo/
✅ Navigation now stays within scenario (success→success, error→error)

---

**Status:** ✅ Fixed and Ready

The error/warning demo now has proper context-aware navigation that stays within the appropriate scenario.
