"""Social Media and Content Staging Integration with Multi-Platform Dispatchers."""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from infrastructure.permissions import permission_engine
from infrastructure.database import db
from integrations.telegram_adapter import telegram_adapter
from integrations.linkedin_adapter import linkedin_adapter
from integrations.facebook_adapter import facebook_adapter

logger = logging.getLogger("ai_company.social_media")


class SocialMediaIntegration:
    """Manages social content staging and controlled multi-channel publishing across Telegram, LinkedIn, Facebook."""

    def __init__(self):
        self.staged_posts: List[Dict[str, Any]] = []
        self.telegram = telegram_adapter
        self.linkedin = linkedin_adapter
        self.facebook = facebook_adapter

    async def get_all_platforms_status(self) -> Dict[str, Any]:
        """Check live connection status across all supported external channels."""
        tg_status, li_status, fb_status = await asyncio.gather(
            self.telegram.get_connection_status(),
            self.linkedin.get_connection_status(),
            self.facebook.get_connection_status(),
            return_exceptions=True
        )

        return {
            "telegram": tg_status if not isinstance(tg_status, Exception) else {"platform": "telegram", "status": "error", "error": str(tg_status)},
            "linkedin": li_status if not isinstance(li_status, Exception) else {"platform": "linkedin", "status": "error", "error": str(li_status)},
            "facebook": fb_status if not isinstance(fb_status, Exception) else {"platform": "facebook", "status": "error", "error": str(fb_status)},
            "timestamp": datetime.utcnow().isoformat()
        }

    def stage_post(
        self,
        platform: str,
        content: str,
        author_agent: str = "marketing",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Stage content for approval before external publishing and persist to DB."""
        post_id = f"post_{uuid.uuid4().hex[:8]}"
        post = {
            "id": post_id,
            "platform": platform.lower().strip(),
            "content": content,
            "author_agent": author_agent,
            "status": "pending_approval",  # Requires Level 3/4 or Judge approval to publish
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        self.staged_posts.append(post)
        logger.info(f"Staged social post [{platform}] {post_id} by {author_agent}.")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(db.save_staged_post(post))
            else:
                loop.run_until_complete(db.save_staged_post(post))
        except Exception as e:
            logger.warning(f"Failed to persist staged post to DB: {e}")

        return post

    async def stage_post_async(
        self,
        platform: str,
        content: str,
        author_agent: str = "marketing",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Explicitly awaitable staging method for async contexts."""
        post_id = f"post_{uuid.uuid4().hex[:8]}"
        post = {
            "id": post_id,
            "platform": platform.lower().strip(),
            "content": content,
            "author_agent": author_agent,
            "status": "pending_approval",
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        self.staged_posts.append(post)
        await db.save_staged_post(post)
        logger.info(f"Staged and persisted social post [{platform}] {post_id} by {author_agent}.")
        return post

    async def publish_post(self, post_id: str, approved_by: str) -> Dict[str, Any]:
        """Publish approved post through the appropriate live or simulated platform adapter."""
        now = datetime.utcnow().isoformat()

        db_post = await db.fetch_one("SELECT * FROM staged_posts WHERE id = ?", (post_id,))
        if not db_post:
            return {"success": False, "error": f"Post {post_id} not found."}

        platform = (db_post.get("platform") or "linkedin").lower().strip()
        content = db_post.get("content", "")
        dispatch_result: Dict[str, Any] = {}

        # Dispatch via dedicated adapter
        if platform in ("telegram", "telegram_channel", "tg", "tg_channel"):
            dispatch_result = await self.telegram.broadcast_to_channel(content)
        elif platform in ("telegram_group", "tg_group"):
            dispatch_result = await self.telegram.send_group_message(content)
        elif platform in ("linkedin", "li"):
            dispatch_result = await self.linkedin.publish_share(content)
        elif platform in ("facebook", "fb", "meta"):
            dispatch_result = await self.facebook.publish_page_post(content)
        else:
            # Fallback simulated dispatch
            logger.info(f"[GENERIC SOCIAL PUBLISH] Platform: {platform} | Approved by: {approved_by}")
            dispatch_result = {"success": True, "mode": "simulated", "platform": platform}

        # Update in-memory cache
        for p in self.staged_posts:
            if p["id"] == post_id:
                p["status"] = "published"
                p["published_at"] = now
                p["approved_by"] = approved_by
                p["dispatch_result"] = dispatch_result

        # Update in persistent database
        await db.update_staged_post(
            post_id,
            status="published",
            published_at=now,
            approved_by=approved_by
        )

        logger.info(f"Post {post_id} published to [{platform}] by {approved_by}. Result mode: {dispatch_result.get('mode')}")
        return {
            "success": dispatch_result.get("success", True),
            "post_id": post_id,
            "platform": platform,
            "status": "published",
            "dispatch": dispatch_result
        }

    async def get_staged_posts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve staged posts from persistent database."""
        db_posts = await db.get_staged_posts(status=status)
        if db_posts:
            self.staged_posts = db_posts
        return db_posts


# Global social media singleton
social_media = SocialMediaIntegration()
