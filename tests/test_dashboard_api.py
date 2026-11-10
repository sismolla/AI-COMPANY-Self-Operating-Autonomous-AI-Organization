"""Tests for FastAPI Owner Dashboard and Web API."""

import pytest
import httpx
from dashboard.app import app
from director.ceo import ceo


@pytest.mark.asyncio
async def test_dashboard_api_routes():
    await ceo.initialize()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test HTML Dashboard
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "AI-COMPANY" in resp.text

        # 2. Test /api/status
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enterprise" in data
        assert "health" in data

        # 3. Test /api/objectives
        resp = await client.get("/api/objectives")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # 4. Test POST /api/objectives
        post_obj = {
            "title": "API Test Objective",
            "description": "Created via API test suite",
            "priority": "medium"
        }
        resp = await client.post("/api/objectives", json=post_obj)
        assert resp.status_code == 200
        assert "objective" in resp.json()

        # 5. Test POST /api/tasks
        post_task = {
            "owner_agent": "analytics",
            "title": "Calculate Benchmark",
            "description": "Run statistical distribution",
            "priority": "low"
        }
        resp = await client.post("/api/tasks", json=post_task)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

        # 6. Test GET /api/tools
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # 7. Test POST /api/cycle/run
        resp = await client.post("/api/cycle/run")
        assert resp.status_code == 200
        assert "cycle_id" in resp.json()
