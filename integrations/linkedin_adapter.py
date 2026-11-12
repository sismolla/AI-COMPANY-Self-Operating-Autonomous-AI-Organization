"""LinkedIn Operations Adapter for Professional Sharing and Post Analytics."""

import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger("ai_company.integrations.linkedin")


class LinkedInAdapter:
    """Provides dual-mode (Live & Simulated) LinkedIn publishing and performance analytics."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        author_urn: Optional[str] = None
    ):
        self.access_token = access_token if access_token is not None else settings.LINKEDIN_ACCESS_TOKEN
        self.author_urn = author_urn if author_urn is not None else (settings.LINKEDIN_AUTHOR_URN or "urn:li:organization:pharma_gebeya")
        self.api_base = "https://api.linkedin.com/v2"

    def is_configured(self) -> bool:
        """Check if real LinkedIn API credentials are provided."""
        return bool(self.access_token and self.author_urn)

    async def get_connection_status(self) -> Dict[str, Any]:
        """Verify LinkedIn API connectivity or return simulation status."""
        if not self.access_token:
            return {
                "platform": "linkedin",
                "status": "connected_simulation",
                "configured": False,
                "live": False,
                "author_urn": self.author_urn,
                "details": "Running in dry-run simulation mode (no access token provided)."
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.api_base}/userinfo", headers=headers)
                if resp.status_code == 200:
                    user_info = resp.json()
                    return {
                        "platform": "linkedin",
                        "status": "connected_live",
                        "configured": True,
                        "live": True,
                        "account_name": user_info.get("name") or user_info.get("localizedFirstName"),
                        "author_urn": self.author_urn
                    }
                return {
                    "platform": "linkedin",
                    "status": "auth_error",
                    "configured": True,
                    "live": False,
                    "error": f"LinkedIn API returned {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            return {
                "platform": "linkedin",
                "status": "unreachable",
                "configured": True,
                "live": False,
                "error": str(e)
            }

    async def publish_share(
        self,
        text: str,
        title: Optional[str] = None,
        link_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish a professional post or article to LinkedIn profile or company page."""
        now = datetime.utcnow().isoformat()

        if not self.access_token:
            logger.info(f"[SIMULATED LINKEDIN SHARE] Author: {self.author_urn} | Title: {title or 'Update'} | Text: {text[:80]}...")
            return {
                "success": True,
                "mode": "simulated",
                "platform": "linkedin",
                "post_urn": f"urn:li:share:sim_{int(datetime.utcnow().timestamp())}",
                "author": self.author_urn,
                "timestamp": now,
                "text": text,
                "link_url": link_url
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Build LinkedIn UGC Share Payload
        payload: Dict[str, Any] = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "ARTICLE" if link_url else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        if link_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "description": {"text": title or "Pharma Gebeya Professional Insight"},
                    "originalUrl": link_url,
                    "title": {"text": title or "Pharma Gebeya Healthcare Network"}
                }
            ]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{self.api_base}/ugcPosts", json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    res_data = resp.json()
                    post_urn = res_data.get("id")
                    logger.info(f"Published LinkedIn post successfully: {post_urn}")
                    return {
                        "success": True,
                        "mode": "live",
                        "platform": "linkedin",
                        "post_urn": post_urn,
                        "data": res_data
                    }
                logger.error(f"LinkedIn publishing failed: {resp.status_code} - {resp.text}")
                return {
                    "success": False,
                    "mode": "live",
                    "status_code": resp.status_code,
                    "error": resp.text
                }
        except Exception as e:
            logger.exception(f"Exception during LinkedIn publishing: {e}")
            return {"success": False, "mode": "live", "error": str(e)}

    async def fetch_post_analytics(self, share_urn: str) -> Dict[str, Any]:
        """Fetch real engagement metrics for a given post URN, with fallback simulation."""
        if not self.access_token:
            return {
                "mode": "simulated",
                "platform": "linkedin",
                "post_urn": share_urn,
                "impressions": 340,
                "clicks": 42,
                "reactions": 28,
                "comments": 6,
                "engagement_rate_pct": 12.35,
                "timestamp": datetime.utcnow().isoformat()
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.api_base}/organizationalEntityShareStatistics?q=organizationalEntity&shares[0]={share_urn}",
                    headers=headers
                )
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    stats = elements[0].get("totalShareStatistics", {}) if elements else {}
                    return {
                        "mode": "live",
                        "post_urn": share_urn,
                        "impressions": stats.get("impressionCount", 0),
                        "clicks": stats.get("clickCount", 0),
                        "reactions": stats.get("likeCount", 0),
                        "comments": stats.get("commentCount", 0),
                        "engagement_rate_pct": round(stats.get("engagement", 0.0) * 100, 2)
                    }
                return {
                    "mode": "live",
                    "error": f"Failed fetching analytics: {resp.status_code}",
                    "impressions": 0,
                    "clicks": 0
                }
        except Exception as e:
            return {"mode": "live", "error": str(e), "impressions": 0}

    get_post_analytics = fetch_post_analytics


# Global singleton
linkedin_adapter = LinkedInAdapter()
