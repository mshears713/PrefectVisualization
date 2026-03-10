# Render Deployment Checklist

This document confirms the static site is ready for deployment to Render.

## ✅ Pre-Deployment Verification

- [x] **viz-demo folder created** at repository root
- [x] **index.html created** with mobile-friendly design
- [x] **Mobile responsive layout** with viewport meta tag
- [x] **All HTML files copied** from output/ folder
- [x] **Relative links** used (no absolute paths)
- [x] **No server code** required (pure static site)
- [x] **No backend dependencies** needed
- [x] **README.md provided** with deployment instructions

## 📁 Folder Structure

```
viz-demo/
├── index.html                       (8 KB)   - Landing page
├── module_graph.html                (693 KB) - Main pipeline view
├── task_graph_pdf_ingestion.html    (687 KB) - Task details
├── task_graph_text_extraction.html  (688 KB) - Task details
├── task_graph_text_processing.html  (687 KB) - Task details
├── task_graph_chunking.html         (688 KB) - Task details
├── task_graph_llm_analysis.html     (687 KB) - Task details
├── task_graph_structured_output.html(687 KB) - Task details
├── README.md                        (4 KB)   - Deployment guide
└── DEPLOYMENT.md                    (this file)
```

**Total: 9 files, ~5.5 MB**

## 🚀 Deploy to Render in 3 Steps

### Step 1: Create New Static Site on Render

1. Go to [render.com](https://render.com)
2. Click "New +" → "Static Site"
3. Connect your GitHub repository

### Step 2: Configure Settings

Use these exact settings:

| Setting | Value |
|---------|-------|
| **Name** | prefect-viz-demo (or your choice) |
| **Publish directory** | `viz-demo` |
| **Build command** | (leave empty) |
| **Environment** | (leave default) |

### Step 3: Deploy

1. Click "Create Static Site"
2. Render will deploy immediately
3. Your site goes live at: `https://<your-site-name>.onrender.com`

## 📱 Features

- **Mobile responsive** — Works on phones, tablets, desktops
- **Offline capable** — Can be opened locally from disk
- **Fast loading** — Pre-rendered static HTML
- **No build process** — Deploys instantly
- **Browser compatible** — Works on all modern browsers

## 🔄 Updating Visualizations

When you regenerate visualizations:

```bash
# Copy new visualizations into viz-demo
Copy-Item output/module_graph.html viz-demo/ -Force
Copy-Item output/task_graph_*.html viz-demo/ -Force

# Commit and push
git add viz-demo/
git commit -m "Update visualizations"
git push
```

Render will automatically redeploy within seconds.

## 🎯 What Works Locally

Open `viz-demo/index.html` in your browser:

```bash
# Windows
start .\viz-demo\index.html

# macOS
open ./viz-demo/index.html

# Linux
xdg-open ./viz-demo/index.html
```

All links work without any server or build step.

## ⚠️ Important Notes

- **No backend required** — This is pure static HTML
- **No Python installed** — No dependencies needed on server
- **No database** — All data is pre-computed in HTML
- **No CDN needed** — Uses public vis.js CDN (already embedded in HTML)

## 🧪 Test Before Deploying

1. Open `viz-demo/index.html` locally
2. Click "Pipeline Module Graph" link
3. Verify graph loads and is interactive
4. Click a task graph link
5. Verify task details display correctly

Once all links work locally, they'll work on Render.

---

**Status: Ready for Production Deployment ✅**

