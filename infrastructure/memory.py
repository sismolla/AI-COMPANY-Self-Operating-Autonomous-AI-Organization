"""Persistent Agent Memory Subsystem for AI-COMPANY."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from infrastructure.database import db


class MemoryStore:
    """Manages isolated and shared memories for autonomous agents across restarts."""

    def __init__(self, database=None):
        self.db = database or db

    async def save(
        self,
        agent_name: str,
        memory_type: str,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None
    ) -> None:
        """Save or update a memory record."""
        now = datetime.utcnow().isoformat()
        tags_list = tags or []
        await self.db.execute(
            """
            INSERT INTO agent_memory (agent_name, memory_type, key, value_json, tags_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name, memory_type, key) DO UPDATE SET
                value_json = excluded.value_json,
                tags_json = excluded.tags_json,
                updated_at = excluded.updated_at
            """,
            (agent_name, memory_type, key, json.dumps(value), json.dumps(tags_list), now, now)
        )

    async def get(self, agent_name: str, memory_type: str, key: str) -> Optional[Any]:
        """Retrieve a specific memory by key."""
        row = await self.db.fetch_one(
            "SELECT value_json FROM agent_memory WHERE agent_name = ? AND memory_type = ? AND key = ?",
            (agent_name, memory_type, key)
        )
        if row:
            return json.loads(row["value_json"])
        return None

    async def list_by_type(self, agent_name: str, memory_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all memories for an agent of a given type."""
        rows = await self.db.fetch_all(
            """
            SELECT key, value_json, tags_json, created_at, updated_at
            FROM agent_memory 
            WHERE agent_name = ? AND memory_type = ? 
            ORDER BY updated_at DESC LIMIT ?
            """,
            (agent_name, memory_type, limit)
        )
        results = []
        for r in rows:
            results.append({
                "key": r["key"],
                "value": json.loads(r["value_json"]),
                "tags": json.loads(r["tags_json"]),
                "updated_at": r["updated_at"]
            })
        return results

    async def search(self, agent_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory keys and values by keyword."""
        search_pattern = f"%{query}%"
        rows = await self.db.fetch_all(
            """
            SELECT memory_type, key, value_json, tags_json, updated_at
            FROM agent_memory
            WHERE (agent_name = ? OR agent_name = 'shared')
              AND (key LIKE ? OR value_json LIKE ? OR tags_json LIKE ?)
            ORDER BY updated_at DESC LIMIT ?
            """,
            (agent_name, search_pattern, search_pattern, search_pattern, limit)
        )
        results = []
        for r in rows:
            results.append({
                "memory_type": r["memory_type"],
                "key": r["key"],
                "value": json.loads(r["value_json"]),
                "tags": json.loads(r["tags_json"]),
                "updated_at": r["updated_at"]
            })
        return results

    async def delete(self, agent_name: str, memory_type: str, key: str) -> None:
        """Delete a memory record."""
        await self.db.execute(
            "DELETE FROM agent_memory WHERE agent_name = ? AND memory_type = ? AND key = ?",
            (agent_name, memory_type, key)
        )

    async def build_context_prompt(self, agent_name: str) -> str:
        """Generate a concise memory context summary to inject into agent prompt."""
        long_term = await self.list_by_type(agent_name, "long_term", limit=5)
        episodic = await self.list_by_type(agent_name, "episodic", limit=3)
        shared = await self.list_by_type("shared", "company_knowledge", limit=5)

        lines = ["[Persistent Memory Context]"]
        if long_term:
            lines.append("Long-term Domain Learnings:")
            for m in long_term:
                lines.append(f" - {m['key']}: {m['value']}")
        if episodic:
            lines.append("Recent Completed Experience:")
            for m in episodic:
                lines.append(f" - {m['key']}: {m['value']}")
        if shared:
            lines.append("Shared Company Knowledge:")
            for m in shared:
                lines.append(f" - {m['key']}: {m['value']}")

        return "\n".join(lines) if len(lines) > 1 else ""


# Global memory manager singleton
memory_store = MemoryStore()
