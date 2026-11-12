"""Comprehensive Unit and Integration Tests for AI Cognitive Operating Model.
Tests 5-tier Cognitive Memory, Adversarial Debate Loop, Opportunity Detection, and CEO Integration.
"""

import pytest
from infrastructure.cognitive_memory import CognitiveMemoryStore, cognitive_memory
from director.cognitive_engine import CognitiveDebateEngine
from director.opportunity_engine import OpportunityDetectionEngine
from director.ceo import ceo


@pytest.mark.asyncio
async def test_cognitive_memory_tiers():
    """Verify that all 5 tiers of cognitive memory can store and retrieve structured knowledge."""
    memory = CognitiveMemoryStore()

    # 1. Mission Memory
    mission = await memory.get_mission()
    assert "mission" in mission
    assert "Pharma Gebeya" in mission["mission"] or "Ethiopia" in mission["mission"]

    await memory.update_mission({
        "mission": "Empower healthcare professionals across Ethiopia with transparent, verified medicine supply.",
        "primary_objective": "Verified supplier onboarding and zero counterfeit stockouts.",
        "core_constraints": ["Zero false claims", "EFDA regulatory compliance"]
    })
    updated_mission = await memory.get_mission()
    assert "zero counterfeit" in updated_mission.get("primary_objective", "").lower()

    # 2. Knowledge Memory
    await memory.save_knowledge(
        key="cold_chain_ethiopia_2026",
        knowledge_data={"distributors_with_cold_chain": ["BioPharma Ltd", "Zenith Health"], "coverage": "85% Addis"},
        tags=["supply_chain", "logistics"]
    )
    recent_knowledge = await memory.get_recent_knowledge(limit=5)
    assert len(recent_knowledge) >= 1
    assert any(k.get("key") == "cold_chain_ethiopia_2026" for k in recent_knowledge)

    # 3. Decision Memory
    sample_decision = {
        "id": "deb_test_001",
        "topic": "Pediatric Antibiotic Availability",
        "verdict": "APPROVE_WITH_MODIFICATIONS",
        "winning_strategy": "Direct supplier case study instead of generic awareness",
        "selected_channel": "linkedin",
        "final_action_plan": "Publish supplier testimonial highlighting 48h fulfillment",
        "rationale": "High past engagement on practical supplier proof."
    }
    await memory.save_decision(sample_decision)
    recent_decisions = await memory.get_recent_decisions(limit=5)
    assert len(recent_decisions) >= 1
    assert any(d.get("id") == "deb_test_001" for d in recent_decisions)

    # 4. Experience Memory (Action -> Hypothesis -> Result -> Reflection)
    await memory.record_experience(
        channel="linkedin",
        initiative="Cold Chain Supplier Showcase",
        hypothesis="Showcasing real storage infrastructure will drive pharmacy registrations",
        result={"impressions": 480, "inquiries": 12, "registrations": 4},
        lesson_learned="Concrete warehouse photos and temperature compliance proof doubled inbound leads.",
        strategic_adjustment="Always require photographic or verifiable evidence in supplier posts."
    )
    relevant_exp = await memory.get_relevant_experiences(channel="linkedin", limit=3)
    assert len(relevant_exp) >= 1
    assert any("doubled inbound leads" in e.get("lesson_learned", "") for e in relevant_exp)

    # 5. Operational Memory
    op_context = await memory.get_operational_context()
    assert "supported_platforms" in op_context
    assert "telegram_channel" in op_context["supported_platforms"]
    assert "linkedin" in op_context["supported_platforms"]
    assert "facebook" in op_context["supported_platforms"]


@pytest.mark.asyncio
async def test_cognitive_debate_loop():
    """Verify adversarial deliberation loop (Strategist Proposal -> Challenger Attack -> Evidence -> Judge Verdict)."""
    engine = CognitiveDebateEngine()
    
    topic = "Should we launch a Telegram AMA for wholesale pharmacies this Thursday?"
    decision_record = await engine.deliberate_initiative(
        topic=topic,
        channel_preference="telegram_group"
    )

    # Validate Deliberation Structure
    assert "id" in decision_record
    assert decision_record["topic"] == topic
    assert "proposal" in decision_record
    assert "challenge" in decision_record
    assert "evidence" in decision_record
    assert "verdict" in decision_record
    assert "winning_strategy" in decision_record
    assert "selected_channel" in decision_record
    assert "final_action_plan" in decision_record

    # Verify Challenger did not simply agree
    challenge = decision_record["challenge"]
    assert "flaws_and_objections" in challenge or "vulnerabilities" in challenge or len(challenge) > 0

    # Verify Independent Judge reached an outcome
    assert decision_record["verdict"] in (
        "APPROVE", "APPROVE_WITH_MODIFICATIONS", "REVISE_WITH_CONDITIONS", "REJECT"
    )


@pytest.mark.asyncio
async def test_opportunity_detection_engine():
    """Verify opportunity detection identifies real-time community inquiries and posting windows."""
    opp_engine = OpportunityDetectionEngine()
    opportunities = await opp_engine.detect_opportunities()

    assert isinstance(opportunities, list)
    assert len(opportunities) >= 1

    # Check that at least one community signal or activity window was identified
    platforms = [o.get("platform") for o in opportunities]
    assert any(p in ("telegram_group", "telegram_channel", "linkedin", "facebook") for p in platforms)
    for opp in opportunities:
        assert "type" in opp
        assert "recommended_action" in opp
        assert "priority" in opp


@pytest.mark.asyncio
async def test_ceo_cognitive_integration():
    """Verify CEO orchestrates deliberation and stores strategic decision records."""
    await ceo.initialize()
    
    topic = "Supply chain transparency campaign for regional hospitals"
    decision = await ceo.run_cognitive_deliberation(
        topic=topic,
        channel_preference="linkedin"
    )

    assert "id" in decision
    assert decision["topic"] == topic
    assert "winning_strategy" in decision
    assert "final_action_plan" in decision
