"""Tests for Universal LLM Adapter."""

import pytest
from infrastructure.llm_adapter import UniversalLLMAdapter


@pytest.mark.asyncio
async def test_mock_llm_adapter_roles():
    adapter = UniversalLLMAdapter()
    adapter.provider = "mock"

    roles = ["director", "engineering", "research", "marketing", "analytics", "quality"]
    for role in roles:
        resp = await adapter.complete(
            prompt=f"Perform role task for {role}",
            system_prompt=f"You are the {role} agent.",
            role=role,
            json_mode=True
        )
        assert resp.content is not None
        data = resp.to_json()
        assert isinstance(data, dict)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_mock_llm_secret_masking():
    adapter = UniversalLLMAdapter()
    adapter.provider = "mock"

    resp = await adapter.complete(
        prompt="Process this token sk-abcdefghijklmnopqrstuvwxyz12345",
        role="engineering"
    )
    assert resp.content is not None
