# PRD 05 — FastAPI Delivery Layer and Bridge to Real PDF Input

## Title

**FastAPI Delivery Layer and Bridge to Real PDF Input for Runtime Visual Debugging**

## Document Purpose

This PRD defines the fifth implementation milestone for the Visual Debugging for AI-Generated Python Code project.

This milestone exposes the working prototype through a lightweight FastAPI backend so the system can be run from a browser, deployed on Render, and demonstrated from a phone or laptop without relying on local scripts alone.

If PRD 04 proved the concept in a controlled script, PRD 05 turns it into a usable application surface.

This milestone also establishes the first bridge from the synthetic pipeline toward a real PDF-oriented flow, while keeping the scope disciplined enough to ship.

---

## Objective

Build a lightweight FastAPI backend that can:

- trigger the synthetic demo pipeline
- generate a runtime trace
- build a graph from that trace
- export the graph as HTML
- return or serve the resulting artifact to the user
- support a simple pathway for later PDF-based input

The goal is not to build a polished production web app.

The goal is to create a stable, demoable backend interface that makes the system easy to run, inspect, and show to other people.

---

## Why This Milestone Comes Fifth

By the time this milestone begins, the project should already have:

1. instrumentation
2. trace-to-graph conversion
3. HTML graph rendering
4. a synthetic demo pipeline

At that point the core idea is proven, but the user experience is still developer-centric.

PRD 05 matters because a conference demo should not depend entirely on explaining terminal commands while balancing a laptop on your knees like a doomed field engineer in a windstorm.

This milestone makes the prototype easier to run from anywhere and sets up the deployment story.

---

## Scope

This milestone includes:

- a FastAPI backend application
- routes for triggering the synthetic pipeline
- routes for serving generated graph HTML
- a simple landing or health endpoint
- basic handling of output file paths
- deployment-friendly structure for Render
- a first bridge toward PDF-based input
- minimal error handling suitable for demo use

This milestone does **not** include:

- a polished frontend application
- authentication
- multi-user session isolation
- persistent database storage
- asynchronous task queues
- live graph streaming
- full production security hardening
- sophisticated upload management
- complete PDF pipeline replacement of the synthetic demo

---

## Product Goal of This Milestone

A user should be able to do the following from a browser or HTTP request:

- trigger a demo run
- receive a generated graph
- open and inspect the graph HTML
- rerun the demo with a success or failure scenario
- verify that the service is healthy

This is the milestone that makes the project feel like an application rather than a pile of scripts.

---

## FastAPI Application Requirements

### Functional Requirement 1 — Create FastAPI Application

Create a FastAPI application that acts as the delivery layer for the prototype.

#### Recommended file

api/server.py

#### Responsibilities

The server should:

- create the FastAPI app
- register routes
- call into existing pipeline, graph, and visualization modules
- return useful responses
- remain thin and orchestration-focused

The API layer should not duplicate business logic from earlier milestones.

---

### Functional Requirement 2 — Health Endpoint

Provide a simple health endpoint.

#### Recommended route

GET /health

#### Expected behavior

Return a simple JSON response indicating that the service is running.

Example structure:

status = ok

This endpoint is useful for Render deployment checks and quick sanity testing.

---

### Functional Requirement 3 — Run Synthetic Demo Endpoint

Provide an endpoint that triggers the synthetic demo pipeline end to end.

#### Recommended route

POST /run-demo

or

GET /run-demo

POST is cleaner if parameters are later added, but either is acceptable for MVP.

#### Responsibilities

This endpoint should:

- reset the runtime trace
- run the synthetic pipeline
- collect the trace
- build the execution graph
- render the graph to HTML
- return information about the result

#### Response should include useful information such as:

- whether the run succeeded
- number of trace events
- number of nodes
- number of edges
- path or URL to the generated graph
- whether the run was success-path or failure-path

The endpoint should not try to inline the whole HTML in JSON unless that is the simplest implementation and clearly beneficial.

---

### Functional Requirement 4 — Serve Graph HTML

Provide a route that serves the generated graph HTML so it can be opened in a browser.

#### Recommended route

GET /graph

or

GET /graph/latest

#### Expected behavior

Return the most recently generated graph HTML file.

#### Requirements

- browser should render the graph directly
- route should be simple and predictable
- implementation should work in local development and on Render

The graph artifact must be easy to access from a phone browser.

---

### Functional Requirement 5 — Support Success and Failure Demo Runs

The API should allow both a happy-path run and a failure-path run.

#### Recommended approach

Accept a simple query parameter or request field such as:

failure_mode = true

or

mode = success / failure

#### Requirements

- success mode should run the normal synthetic pipeline
- failure mode should run the deterministic broken scenario from PRD 04
- response should clearly indicate which mode was used
- graph output should reflect the selected scenario

This is important for demonstrating the debugging value of the product.

---

### Functional Requirement 6 — Minimal Landing or Info Endpoint

Provide a simple root route.

#### Recommended route

GET /

#### Responsibilities

Return a lightweight JSON or plain-text description of the service and available routes.

This can help when opening the deployed service from a phone and is more graceful than staring into a blank endpoint void.

Example content may mention:

- /health
- /run-demo
- /graph

Keep it simple.

---

## Bridge to Real PDF Input

This milestone should establish a path toward real PDF processing without forcing full production PDF support yet.

### Functional Requirement 7 — Add a Minimal PDF-Oriented Placeholder Route

Provide a lightweight placeholder or early-stage route that makes room for the real PDF path.

#### Possible route ideas

POST /run-pdf-demo  
POST /upload-pdf  
POST /analyze-pdf

#### MVP expectation

This route does not need to implement a full PDF extraction pipeline yet.

Instead, it should do one of the following:

Option A:
accept an uploaded PDF file but return a “not yet implemented” or “coming next” response while preserving the route contract

Option B:
accept a file and pass it through a minimal placeholder pipeline if a trivial PDF text extraction step is easy to add safely

#### Recommendation

Keep this route thin and clearly marked as an early bridge unless PDF support is already stable.

The goal is to establish the shape of the future interface without derailing the current prototype.

---

## Output Handling Requirements

### Functional Requirement 8 — Stable Output Path Management

The server must manage output HTML paths cleanly.

#### Requirements

- generated graph HTML should be written to a predictable location
- the app should be able to serve the latest graph reliably
- file path handling should work in local development and deployment

#### Recommended approach

Use an output directory such as:

output/

and save the latest generated graph to a stable file name such as:

output/latest_graph.html

Optional:
timestamped files may also be saved, but the server should still maintain one stable “latest” path for simplicity.

---

### Functional Requirement 9 — Clear Error Handling

The FastAPI layer should handle failures gracefully enough for demo use.

#### Requirements

If a pipeline run fails unexpectedly, the API should:

- return a structured error response
- avoid crashing the whole server
- expose enough information for debugging

This does not need elaborate exception architecture.

Simple, honest error reporting is enough.

---

## Technical Design Guidance

### Recommended file structure additions

repo/
  api/
    server.py

  output/
    latest_graph.html

Optional files if helpful:

- api/routes.py
- api/models.py

Only introduce these if they genuinely improve clarity.

For MVP, keeping everything in server.py is acceptable if it remains readable.

---

### Recommended dependency expectations

The FastAPI application will likely require:

- fastapi
- uvicorn
- existing project dependencies from previous milestones

If a requirements or dependency file exists, update it accordingly.

The project should be runnable locally with a standard FastAPI development server.

---

## API Design Guidance

### Recommended routes summary

GET /  
GET /health  
POST or GET /run-demo  
GET /graph  
Optional early bridge route for PDF

### Response design

Responses should be simple and structured.

For example, the run-demo route should communicate:

- mode used
- success or failure
- artifact path or URL
- trace count
- node count
- edge count

Avoid overcomplicating the response schema.

---

## Render Deployment Requirements

### Functional Requirement 10 — Deployment-Friendly Entrypoint

The project should include a deployment-ready FastAPI entrypoint for Render.

#### Requirements

- server should be startable via uvicorn
- project should expose the FastAPI app object clearly
- file paths should not assume local-only development quirks
- health endpoint should work for deployment checks

#### Recommended startup shape

Render should be able to run the app with a command equivalent to:

uvicorn api.server:app --host 0.0.0.0 --port 10000

Adjust port handling if necessary based on environment expectations.

---

## Demo UX Guidance

The user experience in this milestone should be boring in the best possible way.

That means:

- trigger demo run
- open graph
- inspect graph

Do not turn this into a web design detour.

The backend should do the useful thing with minimal ceremony.

A very simple flow is enough:

1. open service
2. run demo
3. open graph
4. inspect nodes

That is plenty for the current stage.

---

## Non-Functional Requirements

### Simplicity

The API layer should remain thin.

It should orchestrate existing components, not replace them.

### Demo Reliability

The endpoints should work consistently enough for repeated conference demos.

### Debuggability

If something breaks, the API responses and server logs should make it reasonably obvious where the failure occurred.

### Extensibility

The route shapes should make it easy later to add:

- real PDF upload
- graph summaries
- a frontend app
- different demo modes
- stored run history

But none of those should be fully built here unless they are low-risk and straightforward.

---

## Acceptance Criteria

This milestone is complete when all of the following are true:

1. A FastAPI application exists and starts successfully
2. The root route responds with useful service information
3. The health route returns a healthy response
4. A demo endpoint triggers the synthetic pipeline end to end
5. The graph HTML is generated and served through an accessible route
6. The API supports both a success and failure demo mode
7. The generated graph can be opened in a browser after triggering a run
8. The app can be started locally in a way compatible with Render deployment
9. A placeholder or bridge route exists for future PDF-oriented input

---

## Test Plan

### Test 1 — Health check

Call the health endpoint.

#### Expected result

- response indicates service is running

---

### Test 2 — Success demo run

Call the run-demo endpoint in success mode.

#### Expected result

- synthetic pipeline runs successfully
- runtime trace is created
- graph is built
- HTML is exported
- response includes artifact location and summary counts

---

### Test 3 — Failure demo run

Call the run-demo endpoint in failure mode.

#### Expected result

- deterministic failure scenario is triggered
- response clearly indicates failure mode
- graph still reflects the run or error clearly
- generated graph or response makes failure understandable

---

### Test 4 — Graph serving

Open the graph route in a browser after a run.

#### Expected result

- graph HTML renders
- user can inspect the graph interactively
- route works from browser without extra tooling

---

### Test 5 — Root info route

Open the root route.

#### Expected result

- user sees clear information about what the service is and which routes exist

---

### Test 6 — Render deployment sanity

Deploy the service to Render or validate that the server entrypoint is deployment-ready.

#### Expected result

- server starts
- health route works
- demo route works
- graph route serves artifact successfully

---

## Deliverables

At the end of this milestone, the repo should contain:

- a FastAPI server module
- a health route
- a root/info route
- a demo execution route
- a graph-serving route
- stable output file handling
- a placeholder or bridge route for PDF-oriented input
- deployment-ready startup configuration for local and Render use

---

## Definition of Done

This milestone is done when a developer can deploy or run the FastAPI service, trigger a pipeline run from a browser or HTTP request, and open the resulting graph without touching the code.

At that point, the prototype has become genuinely demoable in the wild.

That matters because the remaining work after this is refinement, debugging, and realism—not whether the system can be shown to another human without a long technical preamble.

---

## Future Bridge Beyond PRD 05

After this milestone, likely next steps include:

- replacing the placeholder PDF route with a real PDF pipeline
- letting a lightweight frontend trigger runs
- adding LLM-generated natural-language graph summaries
- introducing session-aware run history
- improving graph layout and module-level views

But none of those are required for this milestone.

The job here is simpler and more important:

Make the prototype runnable, accessible, and demoable through a clean backend surface.

---

## Implementation Cautions

Avoid these traps:

- building too much frontend too early
- letting the API layer duplicate core business logic
- overcomplicating file serving
- trying to make PDF support fully real before the app surface is stable
- creating fragile route contracts that will be hard to extend later
- overengineering deployment before the happy-path backend works

Stay focused on the smallest useful application shell.

That is the fastest route from working prototype to real demo.
