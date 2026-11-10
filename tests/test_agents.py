"""Tests for Specialized Autonomous Agents and Workspaces."""

import pytest
from infrastructure.database import db
from agents.research.agent import ResearchAgent
from agents.engineering.agent import EngineeringAgent
from agents.marketing.agent import MarketingAgent
from agents.analytics.agent import AnalyticsAgent
from agents.operations.agent import OperationsAgent
from agents.quality.agent import QualitySecurityAgent


@pytest.mark.asyncio
async def test_research_agent():
    await db.init_db()
    agent = ResearchAgent()
    task = {
        "id": "task_res_1",
        "title": "Analyze AI Agent Market",
        "description": "Examine market trends",
        "inputs": {"topic": "Autonomous Agents"}
    }
    output = await agent.execute_task(task)
    assert output is not None
    assert "research_intelligence" in output
    assert "dossier_content" in output
    assert "saved_dossier_key" in output
    assert "Intelligence Dossier" in output["dossier_content"]


@pytest.mark.asyncio
async def test_engineering_agent_tool_building():
    await db.init_db()
    agent = EngineeringAgent()
    task = {
        "id": "task_eng_1",
        "title": "Build Text Reverser Tool",
        "description": "Synthesize a string reversal utility",
        "inputs": {
            "tool_name": "string_reverser",
            "tool_description": "Reverses any input string"
        }
    }
    output = await agent.execute_task(task)
    assert output is not None
    assert output.get("status") == "completed"
    assert "tool_build_result" in output


@pytest.mark.asyncio
async def test_marketing_agent():
    await db.init_db()
    agent = MarketingAgent()
    task = {
        "id": "task_mkt_1",
        "title": "Q1 Launch Campaign",
        "description": "Plan multi-channel posts",
        "inputs": {}
    }
    output = await agent.execute_task(task)
    assert output is not None
    assert "saved_plan" in output


@pytest.mark.asyncio
async def test_analytics_agent():
    await db.init_db()
    agent = AnalyticsAgent()
    task = {
        "id": "task_ana_1",
        "title": "Weekly KPI Review",
        "description": "Measure agent velocity",
        "inputs": {}
    }
    output = await agent.execute_task(task)
    assert output is not None
    assert "telemetry" in output
    assert "agent_scorecards" in output


@pytest.mark.asyncio
async def test_quality_agent():
    await db.init_db()
    agent = QualitySecurityAgent()
    task = {
        "id": "task_qua_1",
        "title": "Security Code Audit",
        "description": "Scan code for AST violations",
        "inputs": {"code": "def hello(): return 'safe'"}
    }
    output = await agent.execute_task(task)
    assert output is not None
    assert "security_audit" in output
    assert output["security_audit"]["verdict"] == "PASSED"


def test_agent_workspace_boundary_protection():
    agent = ResearchAgent()
    with pytest.raises(PermissionError):
        agent.write_workspace_file("../../../escaped.txt", "hacked")
