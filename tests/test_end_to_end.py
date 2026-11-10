"""Comprehensive End-to-End Enterprise Operations Test."""

import pytest
from director.ceo import ceo
from infrastructure.database import db
from tool_factory.builder import tool_builder
from tool_factory.registry import tool_registry


@pytest.mark.asyncio
async def test_full_autonomous_company_lifecycle():
    # 1. Initialize Company
    await ceo.initialize()

    # 2. Owner submits high-level business objective
    obj_result = await ceo.submit_owner_objective(
        title="Deploy Autonomous Market Intelligence Engine",
        description="Establish 24/7 web monitoring and automated newsletter reports.",
        priority="critical",
        kpis=["100% automated execution", "Zero security policy violations"]
    )
    assert obj_result["subtasks_created"] >= 3
    obj_id = obj_result["objective"]["id"]

    # 3. Tool Factory: Autonomously build and register a new tool needed for the goal
    tool_res = await tool_builder.build_tool_from_specification(
        name="newsletter_formatter",
        description="Formats headlines and bullet points into newsletter markdown blocks.",
        category="marketing",
        author_agent="engineering"
    )
    assert tool_res["success"] is True
    assert tool_res["tool"]["status"] == "approved"

    # 4. Execute Autonomous Executive Cycle
    cycle_summary = await ceo.run_cycle()
    assert cycle_summary["tasks_dispatched"] >= 1

    # 5. Verify the tool is loaded and callable in registry
    registered_tools = await tool_registry.list_tools()
    tool_names = [t["name"] for t in registered_tools]
    assert "newsletter_formatter" in tool_names

    # 6. Verify database records
    all_tasks = await db.get_tasks_by_agent("research")
    assert len(all_tasks) > 0

    audit_logs = await db.get_audit_logs(limit=20)
    assert len(audit_logs) > 0

    # 7. Check Objective Progress
    objectives = await db.get_objectives()
    target_obj = next((o for o in objectives if o["id"] == obj_id), None)
    assert target_obj is not None
    assert target_obj["status"] in ("active", "completed")
