"""Tests for Permission and Security Engine."""

import pytest
from infrastructure.permissions import permission_engine


def test_level_1_permissions():
    """Level 1 actions should be permitted for research and engineering."""
    res = permission_engine.check_permission("research", "read_file")
    assert res.allowed is True
    assert res.permission_level == 1
    assert res.requires_approval is False


def test_level_2_permissions():
    """Level 2 actions should be allowed for engineering, but not research by default."""
    res_eng = permission_engine.check_permission("engineering", "write_workspace_file")
    assert res_eng.allowed is True
    assert res_eng.permission_level == 2

    res_res = permission_engine.check_permission("research", "write_workspace_file")
    assert res_res.allowed is False
    assert res_res.requires_approval is True


def test_level_3_requires_director_approval():
    """Level 3 external actions require Director sign-off."""
    res = permission_engine.check_permission("marketing", "browser_navigate")
    assert res.allowed is False
    assert res.permission_level == 3
    assert res.requires_approval is True
    assert res.approved_by == "director"


def test_level_4_strictly_owner():
    """Level 4 critical actions strictly require Owner sign-off."""
    res = permission_engine.check_permission("director", "financial_transfer")
    assert res.allowed is False
    assert res.permission_level == 4
    assert res.requires_approval is True
    assert res.approved_by == "owner"


def test_immutable_security_policy():
    """Agents cannot modify permissions.yaml."""
    res = permission_engine.check_permission(
        "director", "write_workspace_file", target_path="config/permissions.yaml"
    )
    assert res.allowed is False
    assert res.permission_level == 4
    assert res.approved_by == "owner"


def test_prompt_sanitization():
    """Credentials and secrets must be masked."""
    raw = "Here is my secret key sk-1234567890abcdef1234567890 and bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    sanitized = permission_engine.sanitize_prompt(raw)
    assert "sk-" not in sanitized
    assert "[API_KEY_REDACTED]" in sanitized
