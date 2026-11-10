"""Tests for AI Director and Executive Orchestration Layer."""

import pytest
from director.planner import strategic_planner
from director.delegation import delegation_manager
from director.performance import performance_director
from director.ceo import ceo


@pytest.mark.asyncio
async def test_strategic_planner():
    objective = {
        "id": "OBJ-100",
        "title": "Scale Audience Engagement",
        "description": "Increase organic content and newsletter reach",
        "kpis": ["+50% followers", "Sub-2s response latency"]
    }
    subtasks = await strategic_planner.deconstruct_objective(objective)
    assert len(subtasks) >= 3
    agents = [st["agent"] for st in subtasks]
    assert "marketing" in agents or "research" in agents
    for st in subtasks:
        assert st["objective_id"] == "OBJ-100"


@pytest.mark.asyncio
async def test_delegation_manager():
    await ceo.initialize()
    res = await delegation_manager.delegate(
        from_agent="marketing",
        to_agent="engineering",
        task_title="Build CSV Formatter",
        task_description="Need utility to format newsletter metrics"
    )
    assert res["success"] is True
    assert "task_id" in res


@pytest.mark.asyncio
async def test_performance_director():
    await ceo.initialize()
    evaluation = await performance_director.evaluate_organization()
    assert "health_summary" in evaluation
    assert "agent_scorecards" in evaluation


@pytest.mark.asyncio
async def test_ceo_cycle_execution():
    await ceo.initialize()
    summary = await ceo.run_cycle()
    assert summary is not None
    assert "cycle_id" in summary
    assert summary["health_verdict"] in ("healthy", "degraded")
