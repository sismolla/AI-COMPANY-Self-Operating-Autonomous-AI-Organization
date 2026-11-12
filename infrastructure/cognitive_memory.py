"""5-Tier Structured Cognitive Memory Architecture.

Replaces raw conversation dumps with structured, searchable cognitive memory tiers:
1. Mission Memory: Long-term organizational mission, constraints, and KPIs.
2. Knowledge Memory: Verified market intelligence, audience pain points, competitor gaps.
3. Decision Memory: Formal records of debates, approved strategies, and rejected proposals.
4. Experience Memory: Experiments, predicted vs actual outcomes, and actionable lessons.
5. Operational Memory: Platform rate limits, verified credentials, and active channels.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from infrastructure.database import db

logger = logging.getLogger("ai_company.cognitive_memory")


class CognitiveMemoryStore:
    """Manages the 5 distinct cognitive memory tiers with SQLite backing."""

    def __init__(self):
        self.default_mission = {
            "mission": "Build a trusted professional digital presence and acquire genuine healthcare professionals and suppliers for Pharma Gebeya.",
            "primary_objective": "Increase verified Ethiopian healthcare professionals and licensed suppliers actively using the platform.",
            "success_metrics": [
                "Qualified new healthcare registrations",
                "Active supplier verified listings",
                "Community discussion engagement",
                "Platform transaction inquiries"
            ],
            "operating_boundaries": [
                "Always verify medicine supply-chain claims against credible sources",
                "Never invent certainty when evidence is missing; investigate first",
                "Live external financial or credential actions require human approval"
            ]
        }

    # 1. Mission Memory
    async def get_mission(self) -> Dict[str, Any]:
        """Fetch current strategic mission and constraints."""
        row = await db.fetch_one(
            "SELECT value_json FROM agent_memory WHERE agent_name = 'director' AND key = 'corporate_mission'",
        )
        if row:
            try:
                return json.loads(row["value_json"])
            except Exception:
                pass
        return self.default_mission

    async def update_mission(self, mission_data: Dict[str, Any]) -> None:
        """Update or refine the corporate mission memory."""
        now = datetime.utcnow().isoformat()
        await db.execute(
            """
            INSERT OR REPLACE INTO agent_memory (agent_name, memory_type, key, value_json, tags_json, created_at, updated_at)
            VALUES ('director', 'mission', 'corporate_mission', ?, '["mission", "strategic_constraints"]', ?, ?)
            """,
            (json.dumps(mission_data, indent=2), now, now)
        )

    # 2. Knowledge Memory
    async def save_knowledge(self, key: str, knowledge_data: Dict[str, Any], tags: List[str] = None) -> None:
        """Store verified market intelligence or competitor data."""
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(tags or ["knowledge"])
        await db.execute(
            """
            INSERT OR REPLACE INTO agent_memory (agent_name, memory_type, key, value_json, tags_json, created_at, updated_at)
            VALUES ('research', 'knowledge', ?, ?, ?, ?, ?)
            """,
            (key, json.dumps(knowledge_data), tags_json, now, now)
        )

    async def get_recent_knowledge(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent market and audience intelligence."""
        rows = await db.fetch_all(
            "SELECT key, value_json, updated_at FROM agent_memory WHERE memory_type = 'knowledge' ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        results = []
        for r in rows:
            try:
                val = json.loads(r["value_json"])
            except Exception:
                val = r["value_json"]
            results.append({"key": r["key"], "data": val, "updated_at": r["updated_at"]})
        return results

    # 3. Decision Memory
    async def save_decision(self, decision_record: Dict[str, Any]) -> None:
        """Record why a strategy was chosen, what the Challenger objected to, and the Judge ruling."""
        decision_id = decision_record.get("id") or f"dec_{int(datetime.utcnow().timestamp())}"
        now = datetime.utcnow().isoformat()
        await db.execute(
            """
            INSERT OR REPLACE INTO agent_memory (agent_name, memory_type, key, value_json, tags_json, created_at, updated_at)
            VALUES ('judge', 'decision', ?, ?, '["decision_record", "debate"]', ?, ?)
            """,
            (f"decision_{decision_id}", json.dumps(decision_record), now, now)
        )
        logger.info(f"Recorded Decision Memory entry: {decision_id} (Verdict: {decision_record.get('verdict')})")

    async def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch past deliberation records and debate outcomes."""
        rows = await db.fetch_all(
            "SELECT key, value_json, updated_at FROM agent_memory WHERE memory_type = 'decision' ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        decisions = []
        for r in rows:
            try:
                decisions.append(json.loads(r["value_json"]))
            except Exception:
                pass
        return decisions

    # 4. Experience Memory
    async def record_experience(
        self,
        hypothesis: Optional[str] = None,
        action_taken: Optional[str] = None,
        predicted_outcome: Optional[str] = None,
        actual_outcome: Optional[str] = None,
        lesson_learned: Optional[str] = None,
        channel: str = "general",
        initiative: Optional[str] = None,
        result: Optional[Any] = None,
        strategic_adjustment: Optional[str] = None,
        **kwargs
    ) -> None:
        """Store the outcome of an experiment and its actionable strategic lesson."""
        exp_id = f"exp_{int(datetime.utcnow().timestamp())}"
        now = datetime.utcnow().isoformat()
        payload = {
            "experiment_id": exp_id,
            "hypothesis": hypothesis or initiative or "Operational initiative",
            "action_taken": action_taken or initiative or "Platform operation",
            "predicted_outcome": predicted_outcome or "Anticipated engagement",
            "actual_outcome": actual_outcome if actual_outcome is not None else (json.dumps(result) if result else "Executed"),
            "lesson_learned": lesson_learned or strategic_adjustment or "Observed performance",
            "strategic_adjustment": strategic_adjustment,
            "channel": channel,
            "recorded_at": now
        }
        await db.execute(
            """
            INSERT OR REPLACE INTO agent_memory (agent_name, memory_type, key, value_json, tags_json, created_at, updated_at)
            VALUES ('evaluator', 'experience', ?, ?, ?, ?, ?)
            """,
            (exp_id, json.dumps(payload), json.dumps(["experience", channel]), now, now)
        )
        logger.info(f"Recorded Experience Memory: {exp_id} -> Lesson: {payload['lesson_learned'][:60]}...")

    async def get_relevant_experiences(self, channel: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve historical lessons learned for a channel or strategy."""
        query = "SELECT value_json FROM agent_memory WHERE memory_type = 'experience' ORDER BY updated_at DESC LIMIT ?"
        rows = await db.fetch_all(query, (limit,))
        experiences = []
        for r in rows:
            try:
                exp = json.loads(r["value_json"])
                if channel is None or exp.get("channel") == channel or exp.get("channel") == "general":
                    experiences.append(exp)
            except Exception:
                pass
        return experiences

    # 5. Operational Memory
    async def get_operational_context(self) -> Dict[str, Any]:
        """Current operational state, active platform rate limits, and hygiene notes."""
        return {
            "supported_platforms": ["telegram_channel", "telegram_group", "linkedin", "facebook"],
            "posting_frequency_limits": {
                "linkedin": "Max 2 posts per day to preserve algorithmic reach",
                "facebook": "Max 2 page updates per day",
                "telegram_channel": "Max 3 broadcasts per day",
                "telegram_group": "Active discussion responses as needed"
            },
            "security_clearance_default": "Level 3 Owner sign-off required for live broadcasts",
            "last_evaluated": datetime.utcnow().isoformat()
        }


# Global memory singleton
cognitive_memory = CognitiveMemoryStore()
