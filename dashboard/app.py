"""FastAPI Web Application and Owner Control Panel for AI-COMPANY."""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import settings
from infrastructure.database import db
from infrastructure.monitoring import system_monitor
from infrastructure.task_queue import task_queue
from tool_factory.registry import tool_registry
from tool_factory.builder import tool_builder
from director.ceo import ceo
from integrations.social_media import social_media
from infrastructure.cognitive_memory import cognitive_memory
from director.opportunity_engine import opportunity_engine

logger = logging.getLogger("ai_company.dashboard")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Multi-Agent AI Company Management Dashboard"
)

# Static and Templates configuration
DASHBOARD_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Agent Dossier & Metadata Definitions
AGENT_METADATA = {
    "director": {
        "name": "director",
        "role_title": "Chief Executive Officer & Director",
        "role_short": "AI Director & CEO",
        "icon": "👑",
        "clearance": 4,
        "tagline": "Strategic planning, objective decomposition & company oversight",
        "color": "#38bdf8"
    },
    "research": {
        "name": "research",
        "role_title": "Market & Reconnaissance Intelligence Researcher",
        "role_short": "Principal Researcher",
        "icon": "🔬",
        "clearance": 2,
        "tagline": "Competitive intel, web scraping, data collection & knowledge synthesis",
        "color": "#06b6d4"
    },
    "engineering": {
        "name": "engineering",
        "role_title": "Lead Systems Architect & Tool Builder",
        "role_short": "Lead Engineer",
        "icon": "🛠️",
        "clearance": 2,
        "tagline": "Autonomous code synthesis, tool creation, refactoring & architecture",
        "color": "#10b981"
    },
    "marketing": {
        "name": "marketing",
        "role_title": "Growth Strategist & Content Synthesizer",
        "role_short": "Growth Marketer",
        "icon": "📢",
        "clearance": 2,
        "tagline": "Audience growth campaigns, multi-channel messaging & brand reach",
        "color": "#f59e0b"
    },
    "analytics": {
        "name": "analytics",
        "role_title": "Principal Data Scientist & KPI Forecaster",
        "role_short": "Lead Data Scientist",
        "icon": "📊",
        "clearance": 2,
        "tagline": "Statistical models, metrics telemetry, throughput analytics & trends",
        "color": "#8b5cf6"
    },
    "operations": {
        "name": "operations",
        "role_title": "Autonomous Operations & Workflow Hygiene Manager",
        "role_short": "Ops & Hygiene",
        "icon": "⚡",
        "clearance": 2,
        "tagline": "Scheduled automations, queue maintenance, memory GC & reliability",
        "color": "#ec4899"
    },
    "quality": {
        "name": "quality",
        "role_title": "Quality Assurance & AST Security Sentinel",
        "role_short": "Security & QA Sentinel",
        "icon": "🛡️",
        "clearance": 3,
        "tagline": "Code verification, AST security scanner, permission clearance & safety audits",
        "color": "#6366f1"
    }
}


# --- Request Models ---
class NewObjectiveRequest(BaseModel):
    title: str
    description: str
    priority: str = "high"
    target_agent: str = "director"
    kpis: Optional[List[str]] = None


class NewTaskRequest(BaseModel):
    owner_agent: str
    title: str
    description: str
    priority: str = "medium"
    permission_level: int = 1
    inputs: Optional[Dict[str, Any]] = None


class ApprovalReviewRequest(BaseModel):
    status: str  # 'approved' or 'rejected'
    reviewer: str = "owner"
    comment: Optional[str] = ""


class BuildToolRequest(BaseModel):
    name: str
    description: str
    category: str = "custom"


class PlatformTestRequest(BaseModel):
    platform: str
    message: Optional[str] = None


class DeliberationRequest(BaseModel):
    topic: str
    channel: Optional[str] = None


# --- Lifespan / Startup ---
@app.on_event("startup")
async def startup_event():
    await ceo.initialize()
    if settings.AUTO_CYCLE_ENABLED:
        ceo.start_background_engine()


@app.on_event("shutdown")
def shutdown_event():
    ceo.stop_background_engine()


def extract_verified_files(agent_name: str, out_data: Dict[str, Any], ws_dir: Path, ws_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract real file deliverables from task output that physically exist in workspace or on disk."""
    real_file_map = {f["name"]: f for f in ws_files}
    seen = set()
    verified: List[Dict[str, Any]] = []

    def _add_if_real(filename: Optional[str]):
        if not filename or not isinstance(filename, str):
            return
        clean_name = Path(filename).name
        if not clean_name or clean_name in seen:
            return
        
        # Check against scanned workspace files
        if clean_name in real_file_map:
            seen.add(clean_name)
            verified.append(real_file_map[clean_name])
            return

        # Check physical existence in workspace dir
        target = (ws_dir / clean_name).resolve()
        if target.is_file() and str(target).startswith(str(ws_dir)):
            seen.add(clean_name)
            stat = target.stat()
            f_obj = {
                "name": clean_name,
                "rel_path": clean_name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat()
            }
            real_file_map[clean_name] = f_obj
            verified.append(f_obj)

    # 1. Saved files explicit keys
    for file_key in ["saved_file", "saved_script", "saved_plan", "saved_report", "saved_audit", "saved_ops_log", "saved_audit_report"]:
        fval = out_data.get(file_key)
        if fval and isinstance(fval, str):
            _add_if_real(fval)

    # 2. Files created list
    raw_fc = out_data.get("files_created")
    if isinstance(raw_fc, list):
        for fc_item in raw_fc:
            if isinstance(fc_item, str):
                _add_if_real(fc_item)
            elif isinstance(fc_item, dict) and "name" in fc_item:
                _add_if_real(fc_item["name"])

    # 3. Artifacts list or dict (only actual filenames!)
    raw_artifacts = out_data.get("artifacts")
    if isinstance(raw_artifacts, list):
        for a in raw_artifacts:
            if isinstance(a, str):
                _add_if_real(a)
            elif isinstance(a, dict) and "name" in a:
                _add_if_real(a["name"])
    elif isinstance(raw_artifacts, dict):
        for k in ["module_name", "filename", "file"]:
            if k in raw_artifacts and isinstance(raw_artifacts[k], str):
                _add_if_real(raw_artifacts[k])
        # If any dict keys look like filenames (have extension)
        for k in raw_artifacts.keys():
            if any(str(k).endswith(ext) for ext in [".py", ".md", ".json", ".txt", ".sql", ".csv", ".html"]):
                _add_if_real(str(k))

    # 4. Fallback to existing workspace files if none explicitly claimed
    if not verified and ws_files:
        verified = ws_files[:3]

    return verified


# --- Telemetry & Agent Enrichment Helpers ---
async def get_enriched_agents_data() -> List[Dict[str, Any]]:
    """Synthesizes rich real-time agent status, active operations, outputs, deliverables, and cognition."""
    scorecards = await system_monitor.get_agent_scorecards()
    scorecard_map = {sc["agent"]: sc for sc in scorecards}
    agent_names = ["director", "research", "engineering", "marketing", "analytics", "operations", "quality"]
    enriched = []

    for name in agent_names:
        meta = AGENT_METADATA.get(name, {
            "name": name,
            "role_title": name.title(),
            "role_short": name.title(),
            "icon": "🤖",
            "clearance": 2,
            "tagline": "Autonomous enterprise agent",
            "color": "#38bdf8"
        })
        sc = scorecard_map.get(name, {
            "agent": name,
            "total_tasks": 0,
            "completed": 0,
            "failed": 0,
            "success_rate_pct": 100.0,
            "avg_duration_sec": 0.0,
            "health": "idle"
        })

        # Inspect workspace directory first to verify real files on disk
        ws_dir = (settings.WORKSPACE_DIR / name).resolve()
        ws_files = []
        if ws_dir.exists():
            for p in sorted(ws_dir.glob("**/*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if p.is_file():
                    ws_files.append({
                        "name": p.name,
                        "rel_path": str(p.relative_to(ws_dir)).replace("\\", "/"),
                        "size_bytes": p.stat().st_size,
                        "modified_at": datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()
                    })

        # Check running or pending tasks
        running_task = await db.fetch_one(
            "SELECT id, title, description, priority, started_at, created_at FROM tasks WHERE owner_agent = ? AND status = 'running' ORDER BY started_at DESC LIMIT 1",
            (name,)
        )
        pending_task = await db.fetch_one(
            "SELECT id, title, description, priority, created_at FROM tasks WHERE owner_agent = ? AND status = 'pending' ORDER BY created_at ASC LIMIT 1",
            (name,)
        )
        last_completed = await db.fetch_one(
            "SELECT id, title, description, priority, status, completed_at FROM tasks WHERE owner_agent = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
            (name,)
        )

        is_running = running_task is not None
        has_pending = pending_task is not None

        if running_task:
            curr_task = dict(running_task)
            curr_task["status"] = "running"
            live_state = "executing"
        elif pending_task:
            curr_task = dict(pending_task)
            curr_task["status"] = "pending"
            live_state = "queued"
        else:
            curr_task = None
            live_state = "standby"

        # Latest output & deliverable
        latest_output_row = await db.fetch_one(
            "SELECT id, title, outputs_json, completed_at FROM tasks WHERE owner_agent = ? AND status = 'completed' AND outputs_json != '{}' ORDER BY completed_at DESC LIMIT 1",
            (name,)
        )
        latest_output = None
        if latest_output_row:
            try:
                out_data = json.loads(latest_output_row["outputs_json"])
            except Exception:
                out_data = {}
            summary = out_data.get("summary") or out_data.get("status") or "Task executed successfully"

            # Extract ONLY verified physical deliverable files (never random dict keys like 'description' or 'code')
            verified_artifacts = extract_verified_files(name, out_data, ws_dir, ws_files)

            latest_output = {
                "task_id": latest_output_row["id"],
                "task_title": latest_output_row["title"],
                "summary": summary,
                "artifacts": [f["name"] for f in verified_artifacts],
                "artifact_files": verified_artifacts,
                "completed_at": latest_output_row["completed_at"]
            }

        # Cognitive Memory count and recent entries
        mem_count_res = await db.fetch_one(
            "SELECT COUNT(*) as count FROM agent_memory WHERE agent_name = ?",
            (name,)
        )
        memory_count = mem_count_res["count"] if mem_count_res else 0

        recent_mems_raw = await db.fetch_all(
            "SELECT memory_type, key, value_json, updated_at FROM agent_memory WHERE agent_name = ? ORDER BY updated_at DESC LIMIT 3",
            (name,)
        )
        recent_memories = []
        for rm in recent_mems_raw:
            try:
                val = json.loads(rm["value_json"])
            except Exception:
                val = rm["value_json"]
            val_str = val if isinstance(val, str) else json.dumps(val)
            recent_memories.append({
                "type": rm["memory_type"],
                "key": rm["key"],
                "value": val_str[:160] + ("..." if len(val_str) > 160 else ""),
                "updated_at": rm["updated_at"]
            })

        enriched.append({
            "agent": name,
            "role_title": meta["role_title"],
            "role_short": meta["role_short"],
            "icon": meta["icon"],
            "clearance": meta["clearance"],
            "tagline": meta["tagline"],
            "color": meta["color"],
            "health": "running" if is_running else ("active" if sc["total_tasks"] > 0 else "idle"),
            "is_running": is_running,
            "has_pending": has_pending,
            "live_state": live_state,
            "total_tasks": sc["total_tasks"],
            "completed": sc["completed"],
            "failed": sc["failed"],
            "success_rate_pct": sc["success_rate_pct"],
            "avg_duration_sec": sc["avg_duration_sec"],
            "current_task": curr_task,
            "next_task": dict(pending_task) if pending_task else None,
            "last_completed_task": dict(last_completed) if last_completed else None,
            "latest_output": latest_output,
            "workspace_files_count": len(ws_files),
            "workspace_files": ws_files[:8],
            "memory_count": memory_count,
            "recent_memories": recent_memories
        })

    return enriched

    return enriched


# --- API Routes ---
@app.get("/api/status")
async def get_status():
    """Retrieve aggregate enterprise health and rich telemetry."""
    health = await system_monitor.get_company_health_summary()
    enriched_agents = await get_enriched_agents_data()
    return {
        "enterprise": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health": health,
        "agents": enriched_agents,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/agents")
async def list_agents():
    """List detailed operational telemetry for all autonomous agents."""
    return await get_enriched_agents_data()


@app.get("/api/agents/{agent_name}")
async def get_agent_profile(agent_name: str):
    """Retrieve comprehensive profile, dossier, memories, workspace files, and task history for an agent."""
    name = agent_name.lower().strip()
    meta = AGENT_METADATA.get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    scorecards = await system_monitor.get_agent_scorecards()
    sc = next((s for s in scorecards if s["agent"] == name), {})

    memories_raw = await db.fetch_all(
        "SELECT memory_type, key, value_json, tags_json, updated_at FROM agent_memory WHERE agent_name = ? ORDER BY updated_at DESC LIMIT 20",
        (name,)
    )
    memories = []
    for m in memories_raw:
        try:
            val = json.loads(m["value_json"])
        except Exception:
            val = m["value_json"]
        memories.append({
            "type": m["memory_type"],
            "key": m["key"],
            "value": str(val),
            "updated_at": m["updated_at"]
        })

    tasks = await db.get_tasks_by_agent(name, limit=15)

    # Inspect workspace directory
    ws_dir = (settings.WORKSPACE_DIR / name).resolve()
    ws_files = []
    if ws_dir.exists():
        for p in sorted(ws_dir.glob("**/*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_file():
                ws_files.append({
                    "name": p.name,
                    "rel_path": str(p.relative_to(ws_dir)).replace("\\", "/"),
                    "size_bytes": p.stat().st_size,
                    "modified_at": datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()
                })

    latest_output_row = await db.fetch_one(
        "SELECT id, title, outputs_json, completed_at FROM tasks WHERE owner_agent = ? AND status = 'completed' AND outputs_json != '{}' ORDER BY completed_at DESC LIMIT 1",
        (name,)
    )
    latest_output = None
    if latest_output_row:
        try:
            out_data = json.loads(latest_output_row["outputs_json"])
        except Exception:
            out_data = {}
        
        verified_artifacts = extract_verified_files(name, out_data, ws_dir, ws_files)

        latest_output = {
            "task_id": latest_output_row["id"],
            "task_title": latest_output_row["title"],
            "summary": out_data.get("summary") or "Completed",
            "artifacts": [f["name"] for f in verified_artifacts],
            "artifact_files": verified_artifacts,
            "completed_at": latest_output_row["completed_at"]
        }

    return {
        "agent": name,
        "metadata": meta,
        "scorecard": sc,
        "latest_output": latest_output,
        "memories": memories,
        "tasks": tasks,
        "workspace_files": ws_files
    }


@app.get("/api/workspace/{agent_name}/files")
async def get_agent_workspace_files(agent_name: str):
    """List all deliverable files in an agent's workspace directory."""
    name = agent_name.lower().strip()
    if name not in AGENT_METADATA:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    ws_dir = (settings.WORKSPACE_DIR / name).resolve()
    if not ws_dir.exists():
        return {"agent": name, "files": []}

    files = []
    for p in sorted(ws_dir.glob("**/*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            stat = p.stat()
            files.append({
                "name": p.name,
                "rel_path": str(p.relative_to(ws_dir)).replace("\\", "/"),
                "size_bytes": stat.st_size,
                "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat()
            })
    return {"agent": name, "files": files}


@app.get("/api/workspace/{agent_name}/file")
async def get_agent_workspace_file(agent_name: str, path: str = Query(..., description="Relative file path")):
    """Safely retrieve file content and metadata for inspection with graceful virtual fallback."""
    name = agent_name.lower().strip()
    if name not in AGENT_METADATA:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    ws_dir = (settings.WORKSPACE_DIR / name).resolve()
    clean_filename = Path(path).name
    target = (ws_dir / path).resolve()

    # Traversal security check
    if not str(target).startswith(str(ws_dir)):
        raise HTTPException(status_code=404, detail=f"Invalid path traversal attempt")

    # 1. Exact path match on disk
    if target.is_file():
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            stat = target.stat()
            return {
                "agent": name,
                "filename": target.name,
                "rel_path": str(target.relative_to(ws_dir)).replace("\\", "/"),
                "size_bytes": stat.st_size,
                "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                "extension": target.suffix.lower(),
                "content": content
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # 2. Check if clean_filename exists in ws_dir directly
    candidate = (ws_dir / clean_filename).resolve()
    if candidate.is_file() and str(candidate).startswith(str(ws_dir)):
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
            stat = candidate.stat()
            return {
                "agent": name,
                "filename": candidate.name,
                "rel_path": candidate.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                "extension": candidate.suffix.lower(),
                "content": content
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # 3. Virtual fallback: check if requested key is in the agent's task outputs (e.g., code snippet, plan, description)
    tasks = await db.fetch_all(
        "SELECT id, title, outputs_json FROM tasks WHERE owner_agent = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 5",
        (name,)
    )
    for t in tasks:
        try:
            out = json.loads(t["outputs_json"])
            virtual_content = None
            virtual_ext = ".txt"

            arts = out.get("artifacts")
            if isinstance(arts, dict):
                if path in arts and isinstance(arts[path], str):
                    virtual_content = arts[path]
                    virtual_ext = ".py" if "code" in path else ".md"
                elif path == "code" and "code" in arts:
                    virtual_content = arts["code"]
                    virtual_ext = ".py"
                elif path == "description" and "description" in arts:
                    virtual_content = arts["description"]
                    virtual_ext = ".txt"
            elif path == "code" and "code" in out:
                virtual_content = out["code"]
                virtual_ext = ".py"
            elif path in ("dossier", "dossier_content") and "dossier_content" in out:
                virtual_content = out["dossier_content"]
                virtual_ext = ".md"
            elif path == "summary" and "summary" in out:
                virtual_content = out["summary"]
                virtual_ext = ".md"

            if virtual_content:
                return {
                    "agent": name,
                    "filename": f"{path}{virtual_ext}",
                    "rel_path": path,
                    "size_bytes": len(virtual_content.encode("utf-8")),
                    "modified_at": datetime.utcnow().isoformat(),
                    "extension": virtual_ext,
                    "content": virtual_content,
                    "is_virtual": True,
                    "note": f"Payload artifact from task '{t['title']}'"
                }
        except Exception:
            pass

    # 4. If truly not found, return clean 404 listing available workspace files
    available = [f.name for f in ws_dir.glob("*") if f.is_file()] if ws_dir.exists() else []
    raise HTTPException(
        status_code=404,
        detail=f"File '{path}' not found in {name} workspace. Available files: {', '.join(available) if available else 'none'}."
    )


# --- Pipeline & Schedules Operations Endpoints ---
@app.get("/api/pipeline")
async def get_operations_pipeline():
    """Retrieve complete operations pipeline: Operating Now, Next to Operate in queue, and Scheduled for Later."""
    # 1. Operating Now (running tasks)
    running_rows = await db.fetch_all(
        "SELECT id, owner_agent, title, description, priority, status, started_at, created_at FROM tasks WHERE status = 'running' ORDER BY started_at ASC"
    )
    now_tasks = []
    for r in running_rows:
        d = dict(r)
        d["agent_meta"] = AGENT_METADATA.get(r["owner_agent"], {})
        if r.get("started_at"):
            try:
                started_dt = datetime.fromisoformat(r["started_at"])
                d["elapsed_sec"] = int((datetime.utcnow() - started_dt).total_seconds())
            except Exception:
                d["elapsed_sec"] = 0
        now_tasks.append(d)

    # 2. Next to Operate (pending tasks in queue sequence)
    pending_rows = await db.fetch_all(
        """
        SELECT id, owner_agent, title, description, priority, status, created_at 
        FROM tasks 
        WHERE status = 'pending' 
        ORDER BY 
            CASE priority 
                WHEN 'critical' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                ELSE 4 
            END, 
            created_at ASC
        LIMIT 25
        """
    )
    next_tasks = []
    for idx, r in enumerate(pending_rows, start=1):
        d = dict(r)
        d["queue_position"] = idx
        d["agent_meta"] = AGENT_METADATA.get(r["owner_agent"], {})
        next_tasks.append(d)

    # 3. Blocked / Waiting on Approval (Level 3/4)
    blocked_rows = await db.fetch_all(
        """
        SELECT t.id, t.owner_agent, t.title, t.description, t.priority, t.permission_level, a.id as approval_id
        FROM tasks t
        LEFT JOIN approvals a ON a.task_id = t.id AND a.status = 'pending'
        WHERE t.status = 'blocked_approval'
        ORDER BY t.created_at ASC
        """
    )
    blocked_tasks = [dict(r) for r in blocked_rows]

    # 4. Scheduled for Later (recurring corporate schedules & scheduled future tasks)
    sched_rows = await db.fetch_all(
        "SELECT id, name, interval_seconds, target_agent, action, payload_json, last_run_at, next_run_at, is_active FROM schedules WHERE is_active = 1 ORDER BY next_run_at ASC"
    )
    now_utc = datetime.utcnow()
    later_items = []
    for s in sched_rows:
        item = dict(s)
        item["agent_meta"] = AGENT_METADATA.get(s["target_agent"], {})

        # Calculate human timing and countdown
        time_desc = "Scheduled"
        countdown_sec = 0
        if s.get("next_run_at"):
            try:
                next_dt = datetime.fromisoformat(s["next_run_at"])
                diff = (next_dt - now_utc).total_seconds()
                countdown_sec = int(diff)
                if diff <= 0:
                    time_desc = "Due now"
                elif diff < 60:
                    time_desc = f"In {int(diff)}s"
                elif diff < 3600:
                    time_desc = f"In {int(diff // 60)}m"
                elif diff < 86400:
                    hours = int(diff // 3600)
                    mins = int((diff % 3600) // 60)
                    time_desc = f"In {hours}h {mins}m"
                else:
                    days = int(diff // 86400)
                    time_desc = f"In {days}d"
            except Exception:
                time_desc = s["next_run_at"].split("T")[0]

        interval_sec = s.get("interval_seconds") or 3600
        if interval_sec < 3600:
            interval_str = f"Every {interval_sec // 60}m"
        elif interval_sec < 86400:
            interval_str = f"Every {interval_sec // 3600}h"
        elif interval_sec == 86400:
            interval_str = "Daily"
        elif interval_sec == 604800:
            interval_str = "Weekly"
        else:
            interval_str = f"Every {interval_sec}s"

        item["time_desc"] = time_desc
        item["countdown_sec"] = countdown_sec
        item["interval_str"] = interval_str
        later_items.append(item)

    return {
        "now": now_tasks,
        "next": next_tasks,
        "later": later_items,
        "blocked": blocked_tasks,
        "counts": {
            "now": len(now_tasks),
            "next": len(next_tasks),
            "later": len(later_items),
            "blocked": len(blocked_tasks)
        },
        "timestamp": now_utc.isoformat()
    }


@app.get("/api/schedules")
async def list_schedules():
    """List recurring schedules."""
    return await db.fetch_all("SELECT * FROM schedules ORDER BY next_run_at ASC")


@app.post("/api/schedules/{schedule_id}/trigger")
async def trigger_schedule(schedule_id: str):
    """Manually trigger a recurring schedule to execute now."""
    s = await db.fetch_one("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    try:
        payload = json.loads(s["payload_json"]) if s.get("payload_json") else {}
    except Exception:
        payload = {}
    task = await task_queue.submit_task(
        owner_agent=s["target_agent"],
        title=s["name"],
        description=f"Manual execution of scheduled routine: {s['action']}",
        priority="high",
        inputs=payload
    )
    interval = s.get("interval_seconds") or 3600
    next_run = (datetime.utcnow() + timedelta(seconds=interval)).isoformat()
    await db.execute(
        "UPDATE schedules SET last_run_at = ?, next_run_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), next_run, schedule_id)
    )
    return {"success": True, "task": task, "message": f"Triggered '{s['name']}'"}


@app.get("/api/objectives")
async def list_objectives():
    """List all corporate objectives and progress."""
    return await db.get_objectives()


@app.post("/api/objectives")
async def create_objective(req: NewObjectiveRequest):
    """Owner injects a new high-level business objective."""
    res = await ceo.submit_owner_objective(
        title=req.title,
        description=req.description,
        priority=req.priority,
        target_agent=req.target_agent,
        kpis=req.kpis
    )
    return res


@app.get("/api/tasks")
async def list_tasks(limit: int = 50, agent: Optional[str] = None):
    """List recent tasks across the organization."""
    if agent and agent != "all":
        return await db.get_tasks_by_agent(agent, limit=limit)
    return await db.get_all_tasks(limit=limit)


@app.get("/api/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Fetch complete diagnostic information for a specific task."""
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@app.post("/api/tasks")
async def create_task(req: NewTaskRequest):
    """Directly submit a task to the persistent queue."""
    task = await task_queue.submit_task(
        owner_agent=req.owner_agent,
        title=req.title,
        description=req.description,
        priority=req.priority,
        permission_level=req.permission_level,
        inputs=req.inputs
    )
    return task


@app.get("/api/approvals")
async def list_pending_approvals():
    """Get pending Level 3 / Level 4 approval requests."""
    return await db.get_pending_approvals()


@app.post("/api/approvals/{approval_id}/review")
async def review_approval(approval_id: str, req: ApprovalReviewRequest):
    """Owner or Director reviews an approval request."""
    if req.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    await db.update_approval(
        approval_id=approval_id,
        status=req.status,
        reviewed_by=req.reviewer,
        comment=req.comment or ""
    )

    # If approved, find the task and unblock it
    appr = await db.fetch_one("SELECT task_id FROM approvals WHERE id = ?", (approval_id,))
    if appr and appr.get("task_id"):
        new_status = "pending" if req.status == "approved" else "failed"
        await db.update_task(appr["task_id"], status=new_status)

    return {"success": True, "approval_id": approval_id, "status": req.status}


@app.get("/api/tools")
async def list_tools():
    """List all registered tools."""
    return await tool_registry.list_tools()


@app.get("/api/tools/{tool_name}")
async def get_tool_details(tool_name: str):
    """Get detailed specification, code, and security audit for a tool."""
    tool = await db.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return tool


@app.post("/api/tools/build")
async def build_tool(req: BuildToolRequest):
    """Trigger Tool Factory to design, sandbox-test, and register a new tool."""
    res = await tool_builder.build_tool_from_specification(
        name=req.name,
        description=req.description,
        category=req.category,
        author_agent="engineering"
    )
    return res


@app.post("/api/cycle/run")
async def trigger_executive_cycle():
    """Manually trigger an executive autonomous cycle."""
    summary = await ceo.run_cycle()
    return summary


@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """Fetch recent audit and execution logs."""
    return await db.get_audit_logs(limit=limit)


@app.get("/api/telemetry/activity")
async def get_telemetry_activity():
    """Time-series activity and throughput distribution for dashboard charts."""
    metrics = await db.fetch_all(
        "SELECT agent_name, AVG(value) as avg_latency FROM performance_metrics WHERE metric_name = 'task_execution_time' GROUP BY agent_name"
    )
    latency_map = {m["agent_name"]: round(m["avg_latency"], 3) for m in metrics}

    counts = await db.fetch_all(
        "SELECT owner_agent, count(*) as count FROM tasks WHERE status = 'completed' GROUP BY owner_agent"
    )
    count_map = {c["owner_agent"]: c["count"] for c in counts}

    recent_audits = await db.fetch_all(
        "SELECT timestamp, action, actor FROM audit_logs ORDER BY timestamp DESC LIMIT 30"
    )

    return {
        "latencies": latency_map,
        "completed_counts": count_map,
        "recent_audits": recent_audits,
        "timestamp": datetime.utcnow().isoformat()
    }


# --- Multi-Platform Channels & Cognitive Deliberation Endpoints ---
@app.get("/api/integrations/status")
async def get_integrations_status():
    """Retrieve connectivity, follower metrics, and live status for Telegram, LinkedIn, and Facebook."""
    return await social_media.get_all_platforms_status()


@app.post("/api/integrations/test")
async def test_integration(req: PlatformTestRequest):
    """Dispatch a live or simulated test message through Telegram, LinkedIn, or Facebook adapter."""
    p = req.platform.lower().strip()
    msg = req.message or f"Test message from Pharma Gebeya AI Cognitive Engine at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

    if p in ("telegram", "telegram_channel", "tg", "tg_channel"):
        res = await social_media.telegram.broadcast_to_channel(msg)
    elif p in ("telegram_group", "tg_group"):
        res = await social_media.telegram.send_group_message(msg)
    elif p in ("linkedin", "li"):
        res = await social_media.linkedin.publish_share(msg, title="Pharma Gebeya Healthcare Network Test")
    elif p in ("facebook", "fb", "meta"):
        res = await social_media.facebook.publish_page_post(msg)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform '{req.platform}'. Use 'telegram_channel', 'telegram_group', 'linkedin', or 'facebook'.")

    return {"platform": p, "result": res}


@app.get("/api/cognitive/decisions")
async def list_cognitive_decisions(limit: int = 15):
    """Fetch recent cognitive deliberation records (Strategist proposals, Challenger critiques, Judge rulings)."""
    return await cognitive_memory.get_recent_decisions(limit=limit)


@app.get("/api/cognitive/opportunities")
async def get_cognitive_opportunities():
    """Scan multi-channel community signals, unanswered questions, and optimal engagement windows."""
    return await opportunity_engine.detect_opportunities()


@app.post("/api/cognitive/deliberate")
async def trigger_cognitive_deliberation(req: DeliberationRequest):
    """Trigger an autonomous debate: Strategist proposal -> Challenger attack -> Evidence check -> Judge ruling."""
    if not req.topic:
        raise HTTPException(status_code=400, detail="Topic is required for deliberation")
    decision = await ceo.run_cognitive_deliberation(
        topic=req.topic,
        channel_preference=req.channel
    )
    return decision


# --- Owner Web Dashboard UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard_ui():
    """Render the responsive Owner Management Portal."""
    template_path = TEMPLATES_DIR / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AI-COMPANY Control Deck</h1><p>Template index.html not found.</p>")
