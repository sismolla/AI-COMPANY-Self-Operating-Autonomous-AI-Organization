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

        # 8. Test GET /api/agents
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        agents_data = resp.json()
        assert len(agents_data) == 7
        agent_names = [a["agent"] for a in agents_data]
        assert "director" in agent_names
        assert "engineering" in agent_names
        assert "research" in agent_names
        assert "marketing" in agent_names
        assert "analytics" in agent_names
        assert "operations" in agent_names
        assert "quality" in agent_names
        # Verify enrichment fields
        for a in agents_data:
            assert "role_title" in a
            assert "clearance" in a
            assert "total_tasks" in a
            assert "success_rate_pct" in a
            assert "memory_count" in a

        # 9. Test GET /api/agents/{agent_name}
        resp = await client.get("/api/agents/engineering")
        assert resp.status_code == 200
        eng_data = resp.json()
        assert eng_data["agent"] == "engineering"
        assert "metadata" in eng_data
        assert "memories" in eng_data
        assert "tasks" in eng_data

        # 10. Test GET /api/agents 404 for invalid agent
        resp = await client.get("/api/agents/nonexistent_agent")
        assert resp.status_code == 404

        # 11. Test GET /api/tasks/{task_id}
        created_task_id = post_task_resp = resp_task_id = (await client.post("/api/tasks", json={
            "owner_agent": "quality",
            "title": "Audit Pipeline Test",
            "description": "Inspect task test"
        })).json()["id"]
        resp = await client.get(f"/api/tasks/{created_task_id}")
        assert resp.status_code == 200
        task_data = resp.json()
        assert task_data["id"] == created_task_id
        assert task_data["owner_agent"] == "quality"

        # 12. Test GET /api/tasks/invalid 404
        resp = await client.get("/api/tasks/task_invalid_99999")
        assert resp.status_code == 404

        # 13. Test GET /api/telemetry/activity
        resp = await client.get("/api/telemetry/activity")
        assert resp.status_code == 200
        telem = resp.json()
        assert "latencies" in telem
        assert "completed_counts" in telem

        # 14. Test GET /api/tools/{tool_name}
        resp = await client.get("/api/tools")
        tools = resp.json()
        if tools:
            first_tool = tools[0]["name"]
            resp = await client.get(f"/api/tools/{first_tool}")
            assert resp.status_code == 200
            assert resp.json()["name"] == first_tool

        # 15. Test GET /api/logs
        resp = await client.get("/api/logs?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # 16. Test GET /api/workspace/{agent}/files
        resp = await client.get("/api/workspace/marketing/files")
        assert resp.status_code == 200
        assert "files" in resp.json()
        assert resp.json()["agent"] == "marketing"

        # Invalid agent 404
        resp = await client.get("/api/workspace/unknown_agent_xyz/files")
        assert resp.status_code == 404

        # 17. Test GET /api/workspace/{agent}/file
        ws_files = (await client.get("/api/workspace/marketing/files")).json()["files"]
        if ws_files:
            first_rel = ws_files[0]["rel_path"]
            resp = await client.get(f"/api/workspace/marketing/file?path={first_rel}")
            assert resp.status_code == 200
            assert "content" in resp.json()
            assert resp.json()["filename"] == ws_files[0]["name"]

        # Traversal protection
        resp = await client.get("/api/workspace/marketing/file?path=../../config/settings.py")
        assert resp.status_code == 404

        # 18. Test GET /api/pipeline
        resp = await client.get("/api/pipeline")
        assert resp.status_code == 200
        pipeline = resp.json()
        assert "now" in pipeline
        assert "next" in pipeline
        assert "later" in pipeline
        assert "counts" in pipeline
        assert isinstance(pipeline["later"], list)
        assert len(pipeline["later"]) >= 1

        # 19. Test GET /api/schedules and POST /api/schedules/{id}/trigger
        resp = await client.get("/api/schedules")
        assert resp.status_code == 200
        schedules = resp.json()
        assert len(schedules) >= 1
        first_sched_id = schedules[0]["id"]
        resp_trig = await client.post(f"/api/schedules/{first_sched_id}/trigger")
        assert resp_trig.status_code == 200
        assert resp_trig.json()["success"] is True

        # 20. Test fallback for virtual artifact (e.g. path=description or path=code)
        resp_virt = await client.get("/api/workspace/engineering/file?path=description")
        assert resp_virt.status_code in (200, 404)
        if resp_virt.status_code == 200:
            assert "content" in resp_virt.json()

        # 21. Test GET /api/integrations/status
        resp_status = await client.get("/api/integrations/status")
        assert resp_status.status_code == 200
        int_status = resp_status.json()
        assert "telegram" in int_status
        assert "linkedin" in int_status
        assert "facebook" in int_status

        # 22. Test POST /api/integrations/test
        resp_tg_test = await client.post("/api/integrations/test", json={
            "platform": "telegram_channel",
            "message": "Test message to Telegram channel from test suite"
        })
        assert resp_tg_test.status_code == 200
        assert resp_tg_test.json()["result"]["success"] is True

        resp_li_test = await client.post("/api/integrations/test", json={
            "platform": "linkedin",
            "message": "Test share to LinkedIn from test suite"
        })
        assert resp_li_test.status_code == 200
        assert resp_li_test.json()["result"]["success"] is True

        # 23. Test GET /api/cognitive/decisions
        resp_dec = await client.get("/api/cognitive/decisions")
        assert resp_dec.status_code == 200
        assert isinstance(resp_dec.json(), list)

        # 24. Test GET /api/cognitive/opportunities
        resp_opp = await client.get("/api/cognitive/opportunities")
        assert resp_opp.status_code == 200
        assert isinstance(resp_opp.json(), list)
        assert len(resp_opp.json()) >= 1

        # 25. Test POST /api/cognitive/deliberate
        resp_delib = await client.post("/api/cognitive/deliberate", json={
            "topic": "Cold Chain Medicine Tracking Campaign",
            "channel": "linkedin"
        })
        assert resp_delib.status_code == 200
        delib_res = resp_delib.json()
        assert "id" in delib_res
        assert "verdict" in delib_res
        assert "winning_strategy" in delib_res


