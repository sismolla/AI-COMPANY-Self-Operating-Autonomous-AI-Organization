"""Facebook / Meta Operations Adapter for Page Publishing and Engagement Insights."""

import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger("ai_company.integrations.facebook")


class FacebookAdapter:
    """Provides dual-mode (Live & Simulated) Facebook Page publishing and post insights."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        page_id: Optional[str] = None
    ):
        self.access_token = access_token if access_token is not None else settings.FACEBOOK_PAGE_ACCESS_TOKEN
        self.page_id = page_id if page_id is not None else (settings.FACEBOOK_PAGE_ID or "pharma_gebeya_page")
        self.graph_base = "https://graph.facebook.com/v19.0"

    def is_configured(self) -> bool:
        """Check if real Facebook Page credentials are provided."""
        return bool(self.access_token and self.page_id)

    async def get_connection_status(self) -> Dict[str, Any]:
        """Verify Meta Graph API connectivity or report simulation status."""
        if not self.access_token:
            return {
                "platform": "facebook",
                "status": "connected_simulation",
                "configured": False,
                "live": False,
                "page_id": self.page_id,
                "details": "Running in dry-run simulation mode (no page access token provided)."
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.graph_base}/{self.page_id}",
                    params={"access_token": self.access_token, "fields": "name,about,followers_count"}
                )
                if resp.status_code == 200:
                    page_info = resp.json()
                    return {
                        "platform": "facebook",
                        "status": "connected_live",
                        "configured": True,
                        "live": True,
                        "page_name": page_info.get("name"),
                        "page_id": self.page_id,
                        "followers": page_info.get("followers_count", 0)
                    }
                return {
                    "platform": "facebook",
                    "status": "auth_error",
                    "configured": True,
                    "live": False,
                    "error": f"Meta Graph API returned {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            return {
                "platform": "facebook",
                "status": "unreachable",
                "configured": True,
                "live": False,
                "error": str(e)
            }

    async def publish_page_post(
        self,
        message: str,
        link: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish a post to the authorized Facebook Page feed."""
        now = datetime.utcnow().isoformat()

        if not self.access_token:
            logger.info(f"[SIMULATED FACEBOOK POST] Page: {self.page_id} | Message: {message[:80]}...")
            return {
                "success": True,
                "mode": "simulated",
                "platform": "facebook",
                "post_id": f"sim_fb_post_{int(datetime.utcnow().timestamp())}",
                "page_id": self.page_id,
                "timestamp": now,
                "message": message,
                "link": link
            }

        payload: Dict[str, Any] = {
            "message": message,
            "access_token": self.access_token
        }
        if link:
            payload["link"] = link

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{self.graph_base}/{self.page_id}/feed", data=payload)
                if resp.status_code in (200, 201):
                    res_data = resp.json()
                    post_id = res_data.get("id")
                    logger.info(f"Published Facebook post successfully: {post_id}")
                    return {
                        "success": True,
                        "mode": "live",
                        "platform": "facebook",
                        "post_id": post_id,
                        "data": res_data
                    }
                logger.error(f"Facebook publishing failed: {resp.status_code} - {resp.text}")
                return {
                    "success": False,
                    "mode": "live",
                    "status_code": resp.status_code,
                    "error": resp.text
                }
        except Exception as e:
            logger.exception(f"Exception during Facebook publishing: {e}")
            return {"success": False, "mode": "live", "error": str(e)}

    async def fetch_page_insights(self) -> Dict[str, Any]:
        """Fetch high-level reach and engagement metrics from Meta Graph API."""
        if not self.access_token:
            return {
                "mode": "simulated",
                "platform": "facebook",
                "page_id": self.page_id,
                "page_impressions_weekly": 1420,
                "page_impressions": 1420,
                "post_engagements": 184,
                "page_engaged_users": 184,
                "page_views": 310,
                "timestamp": datetime.utcnow().isoformat()
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.graph_base}/{self.page_id}/insights",
                    params={
                        "metric": "page_impressions,page_post_engagements",
                        "period": "week",
                        "access_token": self.access_token
                    }
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    return {
                        "mode": "live",
                        "page_id": self.page_id,
                        "insights": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                return {"mode": "live", "error": resp.text}
        except Exception as e:
            return {"mode": "live", "error": str(e)}

    get_page_insights = fetch_page_insights


# Global singleton
facebook_adapter = FacebookAdapter()
