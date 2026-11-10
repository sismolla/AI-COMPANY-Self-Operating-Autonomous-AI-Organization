"""Tests for Database and Repository Layer."""

import pytest
import asyncio
from pathlib import Path
from infrastructure.database import Database


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_company.db"
    return Database(db_path=db_file)


@pytest.mark.asyncio
async def test_db_init_and_crud(temp_db):
    await temp_db.init_db()

    # Create objective
    obj = {
        "id": "OBJ-TEST",
        "title": "Test Strategic Goal",
        "description": "Test objective description",
        "priority": "high",
        "target_agent": "engineering",
        "kpis": ["KPI 1", "KPI 2"]
    }
    await temp_db.create_objective(obj)

    objectives = await temp_db.get_objectives()
    assert len(objectives) == 1
    assert objectives[0]["id"] == "OBJ-TEST"
    assert objectives[0]["kpis"] == ["KPI 1", "KPI 2"]

    # Create task
    task = {
        "id": "task_1",
        "objective_id": "OBJ-TEST",
        "owner_agent": "engineering",
        "title": "Build Test Suite",
        "description": "Write automated unit tests",
        "status": "pending",
        "priority": "high",
        "permission_level": 2,
        "inputs": {"arg1": "val1"}
    }
    await temp_db.create_task(task)

    pending = await temp_db.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0]["id"] == "task_1"
    assert pending[0]["inputs"] == {"arg1": "val1"}

    # Update task
    await temp_db.update_task("task_1", status="completed", outputs={"result": "ok"})
    t = await temp_db.get_task("task_1")
    assert t["status"] == "completed"
    assert t["outputs"]["result"] == "ok"

    # Audit log
    await temp_db.log_audit("tester", "test_action", {"detail": 123})
    logs = await temp_db.get_audit_logs()
    assert len(logs) == 1
    assert logs[0]["actor"] == "tester"
