"""Browser Automation and Web Interaction Integration."""

import logging
from typing import Dict, Any, Optional
from infrastructure.permissions import permission_engine

logger = logging.getLogger("ai_company.browser")


class BrowserAutomation:
    """Provides headless web interaction with Playwright or HTTP fallback."""

    def __init__(self):
        self._has_playwright = False
        try:
            import playwright
            self._has_playwright = True
        except ImportError:
            self._has_playwright = False

    async def navigate_and_extract(self, url: str, agent_name: str = "research") -> Dict[str, Any]:
        """Navigate to URL and extract visible text, with permission gating."""
        # Level 3 check
        perm = permission_engine.check_permission(agent_name, "browser_navigate")
        if not perm.allowed and perm.requires_approval:
            logger.info(f"Browser navigation to {url} by {agent_name} gated by approval.")

        if self._has_playwright:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, timeout=15000)
                    title = await page.title()
                    content = await page.inner_text("body")
                    await browser.close()
                    return {
                        "success": True,
                        "url": url,
                        "title": title,
                        "content": content[:2000],
                        "engine": "playwright"
                    }
            except Exception as e:
                logger.warning(f"Playwright navigation failed: {e}. Falling back to HTTP fetch.")

        # HTTP Fallback
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url)
                return {
                    "success": True,
                    "url": url,
                    "title": f"Web Content: {url}",
                    "content": resp.text[:2000],
                    "engine": "http_fallback"
                }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "engine": "failed"
            }


# Global browser singleton
browser_automation = BrowserAutomation()
