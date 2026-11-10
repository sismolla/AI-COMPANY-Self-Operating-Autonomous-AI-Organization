"""Tests for Persistent Scheduler Subsystem."""

import pytest
from infrastructure.scheduler import PersistentScheduler
from infrastructure.database import db


@pytest.mark.asyncio
async def test_scheduler_trigger():
    await db.init_db()
    sched = PersistentScheduler()

    # Register an immediately due schedule (interval 0 seconds)
    sched_id = await sched.register_schedule(
        name="Test Urgent Job",
        interval_seconds=0,
        target_agent="operations",
        action="test_action",
        payload={"param": 1}
    )

    triggered = await sched.check_and_trigger()
    assert triggered >= 1

    # Verify task was placed in DB
    tasks = await db.get_tasks_by_agent("operations")
    assert any(t["title"] == "Test Urgent Job" for t in tasks)
