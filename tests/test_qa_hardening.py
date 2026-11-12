"""Test suite for QA Hardening architectural upgrades."""

import os
import pytest
import asyncio
from pathlib import Path

from infrastructure.database import db
from integrations.social_media import social_media
from director.delegation import delegation_manager
from infrastructure.task_queue import task_queue
from config.settings import settings


@pytest.mark.asyncio
async def test_staged_posts_sqlite_persistence():
    """Verify that staged posts persist across restarts in SQLite."""
    await db.init_db()
    
    # 1. Stage a test post
    post = await social_media.stage_post_async(
        platform="Telegram B2B",
        content="Exclusive bulk pharmaceutical order discount for verified clinics on pharmagebeya.mesobordering.com",
        author_agent="marketing",
        metadata={"priority": "high", "campaign": "pharma_gebeya_gtm"}
    )
    post_id = post["id"]
    assert post_id is not None

    # 2. Simulate server restart: query directly from DB without relying on in-memory list
    saved_posts = await db.get_staged_posts(status="pending_approval")
    matching = [p for p in saved_posts if p["id"] == post_id]
    assert len(matching) == 1
    assert matching[0]["platform"] == "Telegram B2B"
    assert "pharmagebeya.mesobordering.com" in matching[0]["content"]

    # 3. Publish and verify DB state updates
    pub_res = await social_media.publish_post(post_id, approved_by="owner")
    assert pub_res["success"] is True

    updated_post = await db.fetch_one("SELECT status, approved_by FROM staged_posts WHERE id = ?", (post_id,))
    assert updated_post["status"] == "published"
    assert updated_post["approved_by"] == "owner"


@pytest.mark.asyncio
async def test_delegation_recursion_depth_limit():
    """Verify that inter-agent delegation rejects loops exceeding max depth of 2."""
    await db.init_db()

    # Step 1: Initial task (depth 0)
    root_task = await task_queue.submit_task(
        owner_agent="research",
        title="Root Market Research",
        description="Initial market teardown",
        delegation_depth=0
    )

    # Step 2: First delegation: research -> engineering (depth 1)
    res_1 = await delegation_manager.delegate(
        from_agent="research",
        to_agent="engineering",
        task_title="Build Data Scraper",
        task_description="Need scraper for drug prices",
        parent_task_id=root_task["id"]
    )
    assert res_1["success"] is True
    assert res_1["delegation_depth"] == 1

    # Step 3: Second delegation: engineering -> quality (depth 2)
    res_2 = await delegation_manager.delegate(
        from_agent="engineering",
        to_agent="quality",
        task_title="Audit Scraper Security",
        task_description="Verify AST compliance",
        parent_task_id=res_1["task_id"]
    )
    assert res_2["success"] is True
    assert res_2["delegation_depth"] == 2

    # Step 4: Third delegation (depth 3) -> Must be rejected to prevent infinite loop
    res_3 = await delegation_manager.delegate(
        from_agent="quality",
        to_agent="research",
        task_title="Re-verify Market Data",
        task_description="Attempting recursive loop",
        parent_task_id=res_2["task_id"]
    )
    assert res_3["success"] is False
    assert "depth limit reached" in res_3["error"].lower()


@pytest.mark.asyncio
async def test_self_delegation_rejection():
    """Verify that an agent cannot delegate a task to itself."""
    res = await delegation_manager.delegate(
        from_agent="marketing",
        to_agent="marketing",
        task_title="Recursive Copy Loop",
        task_description="Invalid self loop"
    )
    assert res["success"] is False
    assert "cannot delegate task to itself" in res["error"].lower()


@pytest.mark.asyncio
async def test_quality_gate_deliverable_verification():
    """Verify that tasks fail if an agent claims a deliverable file that does not exist or is empty."""
    await db.init_db()

    class FakeAgent:
        async def execute_task(self, task):
            # Claims it wrote a file that was never actually created
            return {
                "summary": "Completed hallucinated work",
                "saved_plan": "ghost_campaign_file_that_does_not_exist.md"
            }

    fake_task = {
        "id": "task_fake_qg",
        "owner_agent": "marketing",
        "title": "Fake Deliverable Task"
    }

    # Executing the fake agent through task wrapper should trigger Quality Gate FileNotFoundError
    with pytest.raises(FileNotFoundError, match=r"\[QUALITY GATE FAILED\]"):
        await task_queue._verify_deliverables_quality_gate(
            task=fake_task,
            output={"saved_plan": "ghost_campaign_file_that_does_not_exist.md"},
            agent_name="marketing"
        )
