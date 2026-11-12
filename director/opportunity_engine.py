"""Opportunity Detection and Dynamic Timing Engine for Multi-Platform Operations."""

import logging
from datetime import datetime
from typing import Dict, Any, List
from integrations.telegram_adapter import telegram_adapter
from integrations.social_media import social_media
from infrastructure.cognitive_memory import cognitive_memory

logger = logging.getLogger("ai_company.director.opportunity_engine")


class OpportunityDetectionEngine:
    """Continuously evaluates community signals, audience engagement windows, and time-sensitivity."""

    def __init__(self):
        self.telegram = telegram_adapter
        self.memory = cognitive_memory

    async def detect_opportunities(self) -> List[Dict[str, Any]]:
        """Scan community signals and platform analytics to identify high-conviction opportunities."""
        opportunities = []
        now = datetime.utcnow()
        current_hour = now.hour
        is_weekday = now.weekday() < 5

        # 1. Telegram Community Signal Analysis
        tg_sentiment = await self.telegram.analyze_group_sentiment()
        top_topic = tg_sentiment.get("dominant_community_topic")
        sample_questions = tg_sentiment.get("sample_questions", [])

        if top_topic:
            opportunities.append({
                "id": f"opp_tg_{int(now.timestamp())}",
                "type": "community_question_surge",
                "priority": "high",
                "platform": "telegram_group",
                "topic": top_topic,
                "signal_summary": f"Group members asking about '{top_topic}'. {sample_questions[0] if sample_questions else ''}",
                "recommended_action": "Synthesize a verified practical answer and stage a Telegram digest response.",
                "detected_at": now.isoformat()
            })

        # 2. LinkedIn Opportunity Window (Optimal morning/afternoon business windows)
        is_linkedin_window = is_weekday and (8 <= current_hour <= 11 or 13 <= current_hour <= 15)
        opportunities.append({
            "id": f"opp_li_{int(now.timestamp())}",
            "type": "audience_activity_window",
            "priority": "high" if is_linkedin_window else "medium",
            "platform": "linkedin",
            "topic": top_topic or "pharmaceutical_supply_transparency",
            "signal_summary": (
                "Optimal professional LinkedIn engagement window is OPEN."
                if is_linkedin_window else
                f"Outside peak LinkedIn window (Current UTC hour: {current_hour}). Staging recommended for next morning peak."
            ),
            "recommended_action": "Stage evidence-backed supplier spotlight with clear call-to-action." if is_linkedin_window else "Prepare and queue draft post for tomorrow's morning window.",
            "timing_verdict": "PUBLISH_NOW" if is_linkedin_window else "STAGE_FOR_PEAK",
            "detected_at": now.isoformat()
        })

        # 3. Facebook Community / Healthcare Network Opportunity
        opportunities.append({
            "id": f"opp_fb_{int(now.timestamp())}",
            "type": "content_syndication",
            "priority": "medium",
            "platform": "facebook",
            "topic": "verified_healthcare_directory",
            "signal_summary": "Syndicate verified supplier spotlight to Facebook Page network.",
            "recommended_action": "Syndicate verified supplier spotlight to Facebook Page network with community link.",
            "timing_verdict": "STAGE_FOR_EVENING",
            "detected_at": now.isoformat()
        })

        logger.info(f"Detected {len(opportunities)} active multi-channel opportunities.")
        return opportunities

    async def get_timing_decision(self, platform: str) -> Dict[str, Any]:
        """Arbitrate whether an initiative on a platform should be posted now, delayed, or scheduled."""
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday() < 5

        if platform in ("linkedin", "li"):
            if weekday and (8 <= hour <= 12 or 13 <= hour <= 16):
                return {"decision": "PUBLISH_NOW", "reason": "Within prime professional reading hours."}
            return {"decision": "DELAY_TO_WINDOW", "scheduled_hour_utc": 9, "reason": "Schedule for next business morning peak."}

        if platform in ("telegram_channel", "telegram_group", "tg"):
            # Telegram engagement is active midday and evenings
            if 11 <= hour <= 21:
                return {"decision": "PUBLISH_NOW", "reason": "Active community discussion window."}
            return {"decision": "DELAY_TO_WINDOW", "scheduled_hour_utc": 12, "reason": "Hold for midday broadcast."}

        if platform in ("facebook", "fb"):
            return {"decision": "PUBLISH_NOW", "reason": "Standard multi-channel page update."}

        return {"decision": "PUBLISH_NOW", "reason": "Standard dispatch."}


# Global opportunity engine singleton
opportunity_engine = OpportunityDetectionEngine()
