"""
tests/test_api_endpoints.py — Tests for the FastAPI delivery layer.

Uses the ASGI test client (httpx + starlette TestClient) for in-process HTTP
requests — no running server required.

Validates:
- GET /health returns {"status": "ok"}
- GET / returns service description and routes dict
- GET /run-demo (success) returns pipeline_status="success" with node_count > 0
- GET /run-demo?mode=failure returns pipeline_status="error"
- GET /graph returns HTML after a demo run
- GET /graph returns 404 before any demo run (if graph file absent)
- GET /run-demo?mode=invalid returns HTTP 400
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import app, _LATEST_GRAPH


# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Synchronous FastAPI test client (works with httpx under the hood)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_trace_between_tests():
    """Ensure a clean trace for each test."""
    from instrumentation.trace_collector import reset_trace
    reset_trace()
    yield
    reset_trace()


# ---------------------------------------------------------------------------
# 5.1  Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}

    def test_health_content_type_is_json(self, client):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# 5.2  Root endpoint
# ---------------------------------------------------------------------------

class TestRootEndpoint:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_service_key(self, client):
        data = client.get("/").json()
        assert "service" in data

    def test_root_contains_routes_key(self, client):
        data = client.get("/").json()
        assert "routes" in data

    def test_root_service_name_is_correct(self, client):
        data = client.get("/").json()
        assert data["service"] == "Runtime Visual Debugger"

    def test_root_routes_lists_health(self, client):
        data = client.get("/").json()
        routes_str = str(data["routes"])
        assert "health" in routes_str.lower()


# ---------------------------------------------------------------------------
# 5.3  Run-demo success endpoint
# ---------------------------------------------------------------------------

class TestRunDemoSuccess:

    def test_run_demo_returns_200(self, client):
        response = client.get("/run-demo")
        assert response.status_code == 200

    def test_run_demo_pipeline_status_is_success(self, client):
        data = client.get("/run-demo").json()
        assert data["pipeline_status"] == "success"

    def test_run_demo_node_count_is_positive(self, client):
        data = client.get("/run-demo").json()
        assert data["node_count"] > 0

    def test_run_demo_trace_event_count_is_positive(self, client):
        data = client.get("/run-demo").json()
        assert data["trace_event_count"] > 0

    def test_run_demo_pipeline_error_is_null_on_success(self, client):
        data = client.get("/run-demo").json()
        assert data["pipeline_error"] is None

    def test_run_demo_has_graph_url(self, client):
        data = client.get("/run-demo").json()
        assert data.get("graph_url") == "/graph"

    def test_run_demo_success_mode_explicit(self, client):
        data = client.get("/run-demo?mode=success").json()
        assert data["pipeline_status"] == "success"

    def test_run_demo_has_modules_list(self, client):
        data = client.get("/run-demo").json()
        assert "modules" in data
        assert len(data["modules"]) > 0


# ---------------------------------------------------------------------------
# 5.4  Run-demo failure endpoint
# ---------------------------------------------------------------------------

class TestRunDemoFailure:

    def test_run_demo_failure_returns_200(self, client):
        response = client.get("/run-demo?mode=failure")
        assert response.status_code == 200

    def test_run_demo_failure_pipeline_status_is_error(self, client):
        data = client.get("/run-demo?mode=failure").json()
        assert data["pipeline_status"] == "error"

    def test_run_demo_failure_has_pipeline_error_message(self, client):
        data = client.get("/run-demo?mode=failure").json()
        assert data["pipeline_error"] is not None
        assert len(data["pipeline_error"]) > 0

    def test_run_demo_failure_mode_key_is_failure(self, client):
        data = client.get("/run-demo?mode=failure").json()
        assert data["mode"] == "failure"

    def test_run_demo_failure_still_has_nodes(self, client):
        data = client.get("/run-demo?mode=failure").json()
        assert data["node_count"] > 0


# ---------------------------------------------------------------------------
# 5.7  Invalid mode returns 400
# ---------------------------------------------------------------------------

class TestRunDemoInvalidMode:

    def test_invalid_mode_returns_400(self, client):
        response = client.get("/run-demo?mode=invalid")
        assert response.status_code == 400

    def test_invalid_mode_error_mentions_mode(self, client):
        response = client.get("/run-demo?mode=bogus")
        detail = response.json().get("detail", "")
        assert "bogus" in detail or "mode" in detail.lower()


# ---------------------------------------------------------------------------
# 5.5  Graph endpoint returns HTML after demo run
# ---------------------------------------------------------------------------

class TestGraphEndpointAfterDemoRun:

    def test_graph_returns_200_after_demo(self, client):
        client.get("/run-demo")  # generate the graph first
        response = client.get("/graph")
        assert response.status_code == 200

    def test_graph_content_type_is_html(self, client):
        client.get("/run-demo")
        response = client.get("/graph")
        assert "text/html" in response.headers["content-type"]

    def test_graph_content_is_non_empty(self, client):
        client.get("/run-demo")
        response = client.get("/graph")
        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# 5.6  Graph endpoint returns 404 when no graph exists
# ---------------------------------------------------------------------------

class TestGraphEndpointNoGraph:

    def test_graph_returns_404_when_file_absent(self, client, tmp_path, monkeypatch):
        # Point the server's LATEST_GRAPH path to a non-existent file
        import api.server as server_module
        original_path = server_module._LATEST_GRAPH
        monkeypatch.setattr(server_module, "_LATEST_GRAPH", tmp_path / "no_graph.html")
        try:
            response = client.get("/graph")
            assert response.status_code == 404
        finally:
            monkeypatch.setattr(server_module, "_LATEST_GRAPH", original_path)
