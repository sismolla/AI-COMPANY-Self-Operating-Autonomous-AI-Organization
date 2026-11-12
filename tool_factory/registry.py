"""Dynamic Tool Registry and Execution Dispatcher."""

import sys
import uuid
import logging
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from infrastructure.database import db
from infrastructure.permissions import permission_engine
from config.settings import settings

logger = logging.getLogger("ai_company.tool_registry")


class ToolRegistry:
    """Stores, loads, and dispatches approved Python tools dynamically."""

    def __init__(self, tools_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or settings.TOOLS_DIR
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_modules: Dict[str, Any] = {}

    async def register_tool(
        self,
        name: str,
        code: str,
        test_code: str,
        description: str,
        category: str = "general",
        author_agent: str = "engineering",
        permission_level: int = 2,
        security_audit: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save approved tool to disk and register in database."""
        clean_name = name.lower().replace("-", "_").strip()
        tool_file = self.tools_dir / f"{clean_name}.py"

        # Write clean tool file
        with open(tool_file, "w", encoding="utf-8") as f:
            f.write(code)

        tool_id = f"tool_{uuid.uuid4().hex[:8]}"
        tool_record = {
            "id": tool_id,
            "name": clean_name,
            "version": "1.0.0",
            "description": description,
            "category": category,
            "author_agent": author_agent,
            "code": code,
            "test_code": test_code,
            "status": "approved",
            "permission_level": permission_level,
            "security_audit": security_audit or {"status": "passed"}
        }

        await db.save_tool(tool_record)
        await db.log_audit(
            actor=author_agent,
            action="register_tool",
            details={"name": clean_name, "permission_level": permission_level}
        )
        logger.info(f"Registered approved tool '{clean_name}' (Level {permission_level}).")

        # Invalidate in-memory cache
        self._loaded_modules.pop(clean_name, None)
        return tool_record

    def get_tool_module(self, name: str) -> Optional[Any]:
        """Dynamically import or retrieve cached tool module."""
        clean_name = name.lower().replace("-", "_").strip()
        if clean_name in self._loaded_modules:
            return self._loaded_modules[clean_name]

        tool_file = self.tools_dir / f"{clean_name}.py"
        if not tool_file.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(clean_name, str(tool_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[clean_name] = module
                spec.loader.exec_module(module)
                self._loaded_modules[clean_name] = module
                return module
        except Exception as e:
            logger.error(f"Failed to dynamically load tool '{clean_name}': {e}")
            return None
        return None

    async def execute_tool(
        self,
        tool_name: str,
        function_name: str,
        calling_agent: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Enforce permission boundaries and execute tool function."""
        clean_name = tool_name.lower().replace("-", "_").strip()
        tool_record = await db.get_tool_by_name(clean_name)
        if not tool_record:
            return {"success": False, "error": f"Tool '{clean_name}' not found in registry."}

        # Check permissions
        required_level = tool_record.get("permission_level", 2)
        perm_check = permission_engine.check_permission(
            agent_name=calling_agent,
            action_name=f"execute_tool_{clean_name}"
        )

        # Allow if default level satisfies or Level 2 internal clearance
        agent_max_level = permission_engine.policy.get("agent_default_permissions", {}).get(calling_agent, {}).get("max_level", 1)
        if agent_max_level < required_level:
            return {
                "success": False,
                "error": f"Permission Denied: Agent '{calling_agent}' (Level {agent_max_level}) cannot execute Level {required_level} tool '{clean_name}'."
            }

        module = self.get_tool_module(clean_name)
        if not module:
            return {"success": False, "error": f"Failed to load module for '{clean_name}'."}

        func = getattr(module, function_name, None)
        if not func or not callable(func):
            return {"success": False, "error": f"Function '{function_name}' not found in tool '{clean_name}'."}

        try:
            result = func(*args, **kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.exception(f"Tool execution exception in {clean_name}.{function_name}: {e}")
            return {"success": False, "error": str(e)}

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools registered in database."""
        return await db.get_all_tools()

    async def seed_built_in_tools(self) -> None:
        """Seed foundational utility tools for the company agents."""
        builtins = [
            {
                "name": "text_summarizer",
                "description": "Extracts key sentences and summarizes text blocks.",
                "category": "analytics",
                "code": (
                    "def summarize(text: str, max_sentences: int = 3) -> str:\n"
                    "    sentences = [s.strip() for s in text.replace('\\n', ' ').split('.') if len(s.strip()) > 5]\n"
                    "    return '. '.join(sentences[:max_sentences]) + ('.' if sentences else '')\n"
                ),
                "test_code": (
                    "from tool import summarize\n"
                    "res = summarize('First sentence. Second sentence. Third sentence. Fourth sentence.')\n"
                    "assert len(res) > 0\n"
                ),
                "author_agent": "engineering",
                "permission_level": 1
            },
            {
                "name": "markdown_report_builder",
                "description": "Constructs formatted markdown reports with tables and KPI callouts.",
                "category": "operations",
                "code": (
                    "def format_report(title: str, sections: dict) -> str:\n"
                    "    lines = [f'# {title}', '', f'> Generated on automated cycle', '']\n"
                    "    for heading, content in sections.items():\n"
                    "        lines.append(f'## {heading}')\n"
                    "        lines.append(str(content))\n"
                    "        lines.append('')\n"
                    "    return '\\n'.join(lines)\n"
                ),
                "test_code": (
                    "from tool import format_report\n"
                    "res = format_report('Status', {'Overview': 'All systems green.'})\n"
                    "assert '# Status' in res\n"
                ),
                "author_agent": "engineering",
                "permission_level": 1
            },
            {
                "name": "regex_keyword_extractor",
                "description": "Extracts trending keywords, hashtags, and mentions from text.",
                "category": "research",
                "code": (
                    "import re\n"
                    "def extract_keywords(text: str) -> list:\n"
                    "    words = re.findall(r'\\b[a-zA-Z]{4,}\\b', text.lower())\n"
                    "    stopwords = {'with', 'this', 'that', 'from', 'have', 'were', 'which'}\n"
                    "    filtered = [w for w in words if w not in stopwords]\n"
                    "    counts = {}\n"
                    "    for w in filtered:\n"
                    "        counts[w] = counts.get(w, 0) + 1\n"
                    "    return sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:10]\n"
                ),
                "test_code": (
                    "from tool import extract_keywords\n"
                    "words = extract_keywords('autonomous intelligence artificial agents automation workflows')\n"
                    "assert 'autonomous' in words\n"
                ),
                "author_agent": "engineering",
                "permission_level": 1
            },
            {
                "name": "telegram_broadcaster",
                "description": "Publishes broadcasts to Telegram channels and sends discussion messages to Telegram groups.",
                "category": "marketing",
                "code": (
                    "def format_telegram_payload(channel_or_group: str, text: str, parse_mode: str = 'HTML') -> dict:\n"
                    "    return {\n"
                    "        'target': channel_or_group,\n"
                    "        'text': text.strip(),\n"
                    "        'parse_mode': parse_mode,\n"
                    "        'status': 'ready_to_dispatch'\n"
                    "    }\n"
                ),
                "test_code": (
                    "from tool import format_telegram_payload\n"
                    "res = format_telegram_payload('@channel', 'Hello Healthcare Network')\n"
                    "assert res['target'] == '@channel' and 'Hello' in res['text']\n"
                ),
                "author_agent": "engineering",
                "permission_level": 2
            },
            {
                "name": "linkedin_publisher",
                "description": "Formats professional thought-leadership posts and multi-channel articles for LinkedIn.",
                "category": "marketing",
                "code": (
                    "def format_linkedin_post(text: str, hashtags: list = None, link_url: str = None) -> dict:\n"
                    "    tags = ' '.join([f'#{h.replace(\"#\", \"\")}' for h in (hashtags or [])])\n"
                    "    body = f'{text.strip()}\\n\\n{tags}'.strip() if tags else text.strip()\n"
                    "    return {'body': body, 'link_url': link_url, 'visibility': 'PUBLIC'}\n"
                ),
                "test_code": (
                    "from tool import format_linkedin_post\n"
                    "res = format_linkedin_post('Supply chain insight', ['Healthcare', 'Pharma'])\n"
                    "assert '#Healthcare' in res['body']\n"
                ),
                "author_agent": "engineering",
                "permission_level": 2
            },
            {
                "name": "facebook_publisher",
                "description": "Prepares and structures Page feed updates and announcements for Meta Graph API.",
                "category": "marketing",
                "code": (
                    "def format_facebook_post(message: str, call_to_action_url: str = None) -> dict:\n"
                    "    return {'message': message.strip(), 'link': call_to_action_url, 'published': True}\n"
                ),
                "test_code": (
                    "from tool import format_facebook_post\n"
                    "res = format_facebook_post('Community Announcement', 'https://pharmagebeya.com')\n"
                    "assert res['published'] is True and res['link'] is not None\n"
                ),
                "author_agent": "engineering",
                "permission_level": 2
            }
        ]

        for t in builtins:
            existing = await db.get_tool_by_name(t["name"])
            if not existing:
                await self.register_tool(
                    name=t["name"],
                    code=t["code"],
                    test_code=t["test_code"],
                    description=t["description"],
                    category=t["category"],
                    author_agent=t["author_agent"],
                    permission_level=t["permission_level"]
                )


# Global registry singleton
tool_registry = ToolRegistry()
