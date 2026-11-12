"""Cognitive Debate & Deliberation Engine for AI-COMPANY.

Implements the outcome-oriented cognitive protocol:
Deliberate -> Challenge -> Investigate -> Decide -> Execute -> Reflect

Prevents blind agreement by assigning adversarial roles:
- Strategist: Proposes high-conviction initiatives
- Challenger (Devil's Advocate): Attacks assumptions and spots flaws
- Researcher: Provides empirical evidence
- Independent Judge: Issues binding decision records
- Independent Evaluator: Evaluates outcomes and records lessons
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from infrastructure.llm_adapter import llm_adapter
from infrastructure.cognitive_memory import cognitive_memory
from infrastructure.database import db

logger = logging.getLogger("ai_company.director.cognitive_engine")


class CognitiveDebateEngine:
    """Orchestrates structured cognitive debate loops and outcome-driven decisions."""

    def __init__(self):
        self.memory = cognitive_memory

    async def deliberate_initiative(
        self,
        topic: str,
        channel_preference: Optional[str] = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run complete cognitive debate loop: Strategist -> Challenger -> Evidence -> Judge."""
        debate_id = f"deb_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        logger.info(f"--- Starting Cognitive Deliberation [{debate_id}] on '{topic}' ---")

        # Step 0: Ingest Mission, Past Experiences & Operational Context
        mission = await self.memory.get_mission()
        past_experiences = await self.memory.get_relevant_experiences(channel=channel_preference, limit=3)
        context = context_override or {}

        # ---------------------------------------------------------------------
        # 1. STRATEGIST PROPOSAL
        # ---------------------------------------------------------------------
        strat_prompt = f"""
You are the Strategic Proposer of an AI healthcare operating company (Pharma Gebeya).
Corporate Mission: {mission.get('mission')}
Primary Objective: {mission.get('primary_objective')}

Topic to address: {topic}
Channel preference: {channel_preference or 'Best suited channel (LinkedIn, Telegram, Facebook)'}
Past Lessons Learned from Experience Memory:
{json.dumps(past_experiences, indent=2)}

Formulate a sharp, outcome-driven operational proposal. Do NOT simply propose generic activity; explain:
1. Proposed Initiative & Main Hook
2. Target Channel (telegram_channel | telegram_group | linkedin | facebook)
3. Underlying Hypothesis (Why will this drive genuine interest or conversion?)
4. Expected Outcome (registrations, supplier leads, discussions)
5. Draft Content / Action Blueprint

Return JSON matching:
{{
    "title": "Clear initiative title",
    "channel": "linkedin | telegram_channel | telegram_group | facebook",
    "hypothesis": "Why this works based on market reality",
    "expected_outcome": "Specific measurable expectation",
    "draft_action": "Proposed content or operation",
    "key_assumptions": ["Assumption 1", "Assumption 2"]
}}
"""
        try:
            strat_res = await llm_adapter.complete(
                prompt=strat_prompt,
                system_prompt="You are a senior growth and business strategist focusing on verifiable outcomes.",
                role="marketing",
                json_mode=True
            )
            proposal = strat_res.to_json()
        except Exception as e:
            logger.warning(f"Strategist LLM invocation failed ({e}). Employing deterministic strategic proposal.")
            proposal = {}

        if not proposal.get("title"):
            proposal = {
                "title": f"Strategic Initiative for {topic}",
                "channel": channel_preference or "linkedin",
                "hypothesis": "Targeted supplier availability stories outperform generic awareness posts.",
                "expected_outcome": "Engagement from licensed pharmacies and verified suppliers.",
                "draft_action": f"Publish verified supplier spotlight addressing {topic}.",
                "key_assumptions": ["Audience values supplier credibility over high-level advice"]
            }

        logger.info(f"[{debate_id}] Strategist Proposal: {proposal.get('title')} ({proposal.get('channel')})")

        # ---------------------------------------------------------------------
        # 2. ADVERSARIAL CHALLENGER (DEVIL'S ADVOCATE)
        # ---------------------------------------------------------------------
        chal_prompt = f"""
You are the Challenger and Devil's Advocate for Pharma Gebeya.
Your job is NOT to be polite or agree. Your responsibility is to find weak assumptions, risks, and flaws.
Corporate Mission: {mission.get('mission')}

Review this Strategist proposal:
{json.dumps(proposal, indent=2)}

Challenge it aggressively:
1. Why might this fail or be a waste of resources?
2. What unproven assumptions is the Strategist taking for granted?
3. What missing evidence or credibility check is required before publishing?
4. What counter-proposal or required condition do you insist on?

Return JSON matching:
{{
    "severity": "critical | moderate | minor",
    "core_objections": ["Objection 1", "Objection 2"],
    "unverified_assumptions": ["Assumption flagged"],
    "required_conditions": ["Condition before approval"],
    "counter_recommendation": "Alternative or modified angle"
}}
"""
        try:
            chal_res = await llm_adapter.complete(
                prompt=chal_prompt,
                system_prompt="You are an uncompromising critic tasked with preventing unverified hype and wasted effort.",
                role="quality",
                json_mode=True
            )
            challenge = chal_res.to_json()
        except Exception as e:
            logger.warning(f"Challenger LLM invocation failed ({e}). Employing adversarial critique template.")
            challenge = {}

        if not challenge.get("core_objections"):
            challenge = {
                "severity": "moderate",
                "core_objections": ["Claims about supply reliability need verifiable evidence rather than promotional assertions."],
                "unverified_assumptions": ["Assumes target healthcare buyers engage with marketing copy rather than direct inventory listings."],
                "required_conditions": ["Include verifiable registration call-to-action and verify all supplier claims."],
                "counter_recommendation": "Focus on a verified cold-chain case study with direct verification link."
            }

        logger.info(f"[{debate_id}] Challenger Objections ({challenge.get('severity')}): {challenge.get('core_objections')[:1]}")

        # ---------------------------------------------------------------------
        # 3. EVIDENCE INVESTIGATION
        # ---------------------------------------------------------------------
        evidence_prompt = f"""
You are the Research & Evidence Sentinel.
Review the Challenger's objections:
{json.dumps(challenge.get('unverified_assumptions', []), indent=2)}

Topic: {topic}
State whether market evidence supports the Strategist or the Challenger, and provide a grounded fact check.
Return JSON:
{{
    "evidence_summary": "Factual assessment of market reality",
    "supporting_sources": ["EFDA regulatory guidelines", "Ethiopian pharmaceutical supply reports"],
    "verdict_recommendation": "supports_strategist | supports_challenger | requires_pivot"
}}
"""
        try:
            evi_res = await llm_adapter.complete(
                prompt=evidence_prompt,
                system_prompt="You are an evidence analyst providing grounded market facts.",
                role="research",
                json_mode=True
            )
            evidence = evi_res.to_json()
        except Exception as e:
            logger.warning(f"Researcher LLM invocation failed ({e}). Employing market evidence baseline.")
            evidence = {}

        if not evidence.get("evidence_summary"):
            evidence = {
                "evidence_summary": "Healthcare professionals prioritize verified inventory availability and licensing over generic thought-leadership.",
                "supporting_sources": ["Healthcare procurement practices"],
                "verdict_recommendation": "supports_challenger"
            }

        # ---------------------------------------------------------------------
        # 4. INDEPENDENT JUDGE RULING
        # ---------------------------------------------------------------------
        judge_prompt = f"""
You are the Independent Judge and Executive Arbiter of the Cognitive Organization.
You do not execute; you decide. Compare the arguments against the Corporate Mission:
Mission: {mission.get('mission')}

STRATEGIST PROPOSAL:
{json.dumps(proposal, indent=2)}

CHALLENGER CRITIQUE:
{json.dumps(challenge, indent=2)}

EVIDENCE EVALUATION:
{json.dumps(evidence, indent=2)}

Render a binding decision. Choose one verdict:
- 'APPROVED' (Proposal is strong and grounded)
- 'REVISE_WITH_CONDITIONS' (Approved ONLY if Challenger conditions are incorporated)
- 'REJECT_AND_INVESTIGATE' (Fatal flaws, cancel or return for deeper research)

Return JSON matching:
{{
    "verdict": "APPROVED | REVISE_WITH_CONDITIONS | REJECT_AND_INVESTIGATE",
    "winning_strategy": "Synthesis of the final approved approach",
    "selected_channel": "linkedin | telegram_channel | telegram_group | facebook",
    "required_revisions": ["Mandatory fix 1", "Mandatory fix 2"],
    "final_action_plan": "The exact message or operation to execute",
    "rationale": "Clear executive reasoning"
}}
"""
        try:
            judge_res = await llm_adapter.complete(
                prompt=judge_prompt,
                system_prompt="You are the chief arbiter balancing strategic bold moves with rigorous factual standards.",
                role="director",
                json_mode=True
            )
            decision = judge_res.to_json()
        except Exception as e:
            logger.warning(f"Judge LLM invocation failed ({e}). Employing executive arbiter verdict.")
            decision = {}

        if not decision.get("verdict"):
            decision = {
                "verdict": "REVISE_WITH_CONDITIONS",
                "winning_strategy": f"Adopt Challenger's verified case study approach for {proposal.get('title')}",
                "selected_channel": proposal.get("channel", "linkedin"),
                "required_revisions": challenge.get("required_conditions", ["Verify data with credible source"]),
                "final_action_plan": f"Publish evidence-backed spotlight on {decision.get('selected_channel', 'linkedin')} with verified CTA.",
                "rationale": "Challenger correctly noted that promotional claims without verifiable inventory proof perform poorly."
            }

        # Package complete Decision Record
        decision_record = {
            "id": debate_id,
            "topic": topic,
            "timestamp": now,
            "proposal": proposal,
            "challenge": challenge,
            "evidence": evidence,
            "verdict": decision.get("verdict"),
            "winning_strategy": decision.get("winning_strategy"),
            "selected_channel": decision.get("selected_channel", proposal.get("channel")),
            "final_action_plan": decision.get("final_action_plan"),
            "required_revisions": decision.get("required_revisions", []),
            "rationale": decision.get("rationale")
        }

        # Store in Decision Memory
        await self.memory.save_decision(decision_record)

        logger.info(f"--- Deliberation [{debate_id}] Concluded: VERDICT={decision.get('verdict')} on {decision_record['selected_channel']} ---")
        return decision_record


# Global cognitive engine singleton
cognitive_engine = CognitiveDebateEngine()
