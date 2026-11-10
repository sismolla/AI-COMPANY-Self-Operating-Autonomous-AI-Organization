"""Database abstraction and repository layer for AI-COMPANY."""

import json
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config.settings import settings


class Database:
    """Async-compatible SQLite repository for persistent company operations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def execute(self, query: str, params: tuple = ()) -> None:
        async with self._lock:
            def _run():
                with self._get_connection() as conn:
                    conn.execute(query, params)
                    conn.commit()
            await asyncio.to_thread(_run)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        async with self._lock:
            def _run():
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    return dict(row) if row else None
            return await asyncio.to_thread(_run)

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        async with self._lock:
            def _run():
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
            return await asyncio.to_thread(_run)

    async def init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS objectives (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                target_agent TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                progress INTEGER NOT NULL DEFAULT 0,
                kpis_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                objective_id TEXT,
                owner_agent TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                permission_level INTEGER NOT NULL DEFAULT 1,
                inputs_json TEXT NOT NULL DEFAULT '{}',
                outputs_json TEXT NOT NULL DEFAULT '{}',
                error TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                scheduled_at TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(agent_name, memory_type, key)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL DEFAULT '1.0.0',
                description TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                author_agent TEXT NOT NULL,
                code TEXT NOT NULL,
                test_code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                permission_level INTEGER NOT NULL DEFAULT 2,
                security_audit_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}',
                level TEXT NOT NULL DEFAULT 'info',
                status TEXT NOT NULL DEFAULT 'success'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                requested_by TEXT NOT NULL,
                action_name TEXT NOT NULL,
                permission_level INTEGER NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                comment TEXT,
                created_at TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron_expression TEXT,
                interval_seconds INTEGER,
                target_agent TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                last_run_at TEXT,
                next_run_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);",
            "CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(owner_agent);",
            "CREATE INDEX IF NOT EXISTS idx_memory_agent ON agent_memory(agent_name, memory_type);",
            "CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);"
        ]
        for q in queries:
            await self.execute(q)

    # --- Objectives ---
    async def create_objective(self, obj: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT OR REPLACE INTO objectives 
            (id, title, description, priority, target_agent, status, progress, kpis_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj["id"],
                obj["title"],
                obj["description"],
                obj.get("priority", "medium"),
                obj["target_agent"],
                obj.get("status", "active"),
                obj.get("progress", 0),
                json.dumps(obj.get("kpis", [])),
                obj.get("created_at", now),
                now
            )
        )

    async def get_objectives(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            rows = await self.fetch_all("SELECT * FROM objectives WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            rows = await self.fetch_all("SELECT * FROM objectives ORDER BY created_at DESC")
        for r in rows:
            r["kpis"] = json.loads(r["kpis_json"])
        return rows

    async def update_objective_progress(self, obj_id: str, progress: int, status: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        if status:
            await self.execute(
                "UPDATE objectives SET progress = ?, status = ?, updated_at = ? WHERE id = ?",
                (progress, status, now, obj_id)
            )
        else:
            await self.execute(
                "UPDATE objectives SET progress = ?, updated_at = ? WHERE id = ?",
                (progress, now, obj_id)
            )

    # --- Tasks ---
    async def create_task(self, task: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT INTO tasks 
            (id, objective_id, owner_agent, title, description, status, priority, permission_level, 
             inputs_json, outputs_json, error, retry_count, max_retries, scheduled_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                task.get("objective_id"),
                task["owner_agent"],
                task["title"],
                task["description"],
                task.get("status", "pending"),
                task.get("priority", "medium"),
                task.get("permission_level", 1),
                json.dumps(task.get("inputs", {})),
                json.dumps(task.get("outputs", {})),
                task.get("error"),
                task.get("retry_count", 0),
                task.get("max_retries", settings.MAX_RETRIES),
                task.get("scheduled_at"),
                task.get("created_at", now)
            )
        )

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = await self.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row:
            row["inputs"] = json.loads(row["inputs_json"])
            row["outputs"] = json.loads(row["outputs_json"])
        return row

    async def update_task(self, task_id: str, **kwargs) -> None:
        fields = []
        values = []
        for k, v in kwargs.items():
            if k in ("inputs", "outputs"):
                fields.append(f"{k}_json = ?")
                values.append(json.dumps(v))
            else:
                fields.append(f"{k} = ?")
                values.append(v)
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
        await self.execute(query, tuple(values))

    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        priority_order = "CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END"
        rows = await self.fetch_all(
            f"SELECT * FROM tasks WHERE status = 'pending' ORDER BY {priority_order}, created_at ASC LIMIT ?",
            (limit,)
        )
        for r in rows:
            r["inputs"] = json.loads(r["inputs_json"])
            r["outputs"] = json.loads(r["outputs_json"])
        return rows

    async def get_tasks_by_agent(self, agent_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        rows = await self.fetch_all(
            "SELECT * FROM tasks WHERE owner_agent = ? ORDER BY created_at DESC LIMIT ?",
            (agent_name, limit)
        )
        for r in rows:
            r["inputs"] = json.loads(r["inputs_json"])
            r["outputs"] = json.loads(r["outputs_json"])
        return rows

    async def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = await self.fetch_all("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
        for r in rows:
            r["inputs"] = json.loads(r["inputs_json"])
            r["outputs"] = json.loads(r["outputs_json"])
        return rows

    # --- Audit Logs ---
    async def log_audit(
        self,
        actor: str,
        action: str,
        details: Dict[str, Any],
        level: str = "info",
        status: str = "success"
    ) -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT INTO audit_logs (timestamp, actor, action, details_json, level, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, actor, action, json.dumps(details), level, status)
        )

    async def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = await self.fetch_all("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        for r in rows:
            r["details"] = json.loads(r["details_json"])
        return rows

    # --- Tool Registry Storage ---
    async def save_tool(self, tool_data: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT OR REPLACE INTO tools 
            (id, name, version, description, category, author_agent, code, test_code, 
             status, permission_level, security_audit_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool_data["id"],
                tool_data["name"],
                tool_data.get("version", "1.0.0"),
                tool_data["description"],
                tool_data.get("category", "general"),
                tool_data["author_agent"],
                tool_data["code"],
                tool_data["test_code"],
                tool_data.get("status", "draft"),
                tool_data.get("permission_level", 2),
                json.dumps(tool_data.get("security_audit", {})),
                tool_data.get("created_at", now),
                now
            )
        )

    async def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        row = await self.fetch_one("SELECT * FROM tools WHERE name = ?", (name,))
        if row:
            row["security_audit"] = json.loads(row["security_audit_json"])
        return row

    async def get_approved_tools(self) -> List[Dict[str, Any]]:
        rows = await self.fetch_all("SELECT * FROM tools WHERE status = 'approved' ORDER BY name ASC")
        for r in rows:
            r["security_audit"] = json.loads(r["security_audit_json"])
        return rows

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        rows = await self.fetch_all("SELECT * FROM tools ORDER BY created_at DESC")
        for r in rows:
            r["security_audit"] = json.loads(r["security_audit_json"])
        return rows

    # --- Approvals (Level 3 / 4) ---
    async def create_approval(self, app_data: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT INTO approvals 
            (id, task_id, requested_by, action_name, permission_level, payload_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app_data["id"],
                app_data.get("task_id"),
                app_data["requested_by"],
                app_data["action_name"],
                app_data["permission_level"],
                json.dumps(app_data.get("payload", {})),
                app_data.get("status", "pending"),
                now
            )
        )

    async def update_approval(self, approval_id: str, status: str, reviewed_by: str, comment: str = "") -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            UPDATE approvals 
            SET status = ?, reviewed_by = ?, reviewed_at = ?, comment = ?
            WHERE id = ?
            """,
            (status, reviewed_by, now, comment, approval_id)
        )

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        rows = await self.fetch_all("SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at ASC")
        for r in rows:
            r["payload"] = json.loads(r["payload_json"])
        return rows

    # --- Metrics ---
    async def record_metric(self, agent_name: str, metric_name: str, value: float, unit: str = "") -> None:
        now = datetime.utcnow().isoformat()
        await self.execute(
            """
            INSERT INTO performance_metrics (agent_name, metric_name, value, unit, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent_name, metric_name, value, unit, now)
        )

    async def get_metrics_summary(self) -> List[Dict[str, Any]]:
        return await self.fetch_all(
            """
            SELECT agent_name, metric_name, AVG(value) as avg_val, COUNT(*) as count, unit
            FROM performance_metrics
            GROUP BY agent_name, metric_name
            """
        )

    # --- Seed Objectives ---
    async def seed_objectives_if_empty(self) -> None:
        count_res = await self.fetch_one("SELECT COUNT(*) as count FROM objectives")
        if count_res and count_res["count"] == 0:
            import yaml
            obj_path = settings.CONFIG_DIR / "company_objectives.yaml"
            if obj_path.exists():
                with open(obj_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for obj in data.get("objectives", []):
                    await self.create_objective(obj)


# Global database instance
db = Database()
