"""FastAPI Web Application and Owner Control Panel for AI-COMPANY."""

import json
import logging
from pathlib import Path
from datetime import datetime
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


# --- Lifespan / Startup ---
@app.on_event("startup")
async def startup_event():
    await ceo.initialize()
    if settings.AUTO_CYCLE_ENABLED:
        ceo.start_background_engine()


@app.on_event("shutdown")
def shutdown_event():
    ceo.stop_background_engine()


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

            # Normalize artifacts into a clean list of filenames / descriptors
            artifact_list = []
            raw_artifacts = out_data.get("files_created") or out_data.get("artifacts") or []
            if isinstance(raw_artifacts, list):
                for a in raw_artifacts:
                    if isinstance(a, str):
                        artifact_list.append(a)
                    elif isinstance(a, dict) and "name" in a:
                        artifact_list.append(a["name"])
            elif isinstance(raw_artifacts, dict):
                for k in raw_artifacts.keys():
                    artifact_list.append(str(k))
            elif isinstance(raw_artifacts, str):
                artifact_list.append(raw_artifacts)

            # Check explicit saved files from specialized agents
            for file_key in ["saved_plan", "saved_report", "saved_audit", "saved_script", "saved_file"]:
                fval = out_data.get(file_key)
                if fval and isinstance(fval, str) and fval not in artifact_list:
                    artifact_list.append(fval)

            latest_output = {
                "task_id": latest_output_row["id"],
                "task_title": latest_output_row["title"],
                "summary": summary,
                "artifacts": artifact_list,
                "completed_at": latest_output_row["completed_at"]
            }

        # Inspect workspace directory
        ws_dir = (settings.WORKSPACE_DIR / name).resolve()
        ws_files = []
        if ws_dir.exists():
            for p in sorted(ws_dir.glob("**/*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if p.is_file():
                    ws_files.append({
                        "name": p.name,
                        "rel_path": str(p.relative_to(ws_dir)).replace("\\", "/"),
                        "size_bytes": p.stat().st_size
                    })

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
            "last_completed_task": dict(last_completed) if last_completed else None,
            "latest_output": latest_output,
            "workspace_files_count": len(ws_files),
            "workspace_files": ws_files[:5],
            "memory_count": memory_count,
            "recent_memories": recent_memories
        })

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
        
        artifact_list = []
        raw_artifacts = out_data.get("files_created") or out_data.get("artifacts") or []
        if isinstance(raw_artifacts, list):
            for a in raw_artifacts:
                if isinstance(a, str):
                    artifact_list.append(a)
                elif isinstance(a, dict) and "name" in a:
                    artifact_list.append(a["name"])
        elif isinstance(raw_artifacts, dict):
            for k in raw_artifacts.keys():
                artifact_list.append(str(k))
        elif isinstance(raw_artifacts, str):
            artifact_list.append(raw_artifacts)

        for file_key in ["saved_plan", "saved_report", "saved_audit", "saved_script", "saved_file"]:
            fval = out_data.get(file_key)
            if fval and isinstance(fval, str) and fval not in artifact_list:
                artifact_list.append(fval)

        latest_output = {
            "task_id": latest_output_row["id"],
            "task_title": latest_output_row["title"],
            "summary": out_data.get("summary") or "Completed",
            "artifacts": artifact_list,
            "completed_at": latest_output_row["completed_at"]
        }

    # Workspace files
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
    """Safely retrieve file content and metadata for inspection."""
    name = agent_name.lower().strip()
    if name not in AGENT_METADATA:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    ws_dir = (settings.WORKSPACE_DIR / name).resolve()
    target = (ws_dir / path).resolve()

    if not str(target).startswith(str(ws_dir)) or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File '{path}' not found in {name} workspace")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

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


# --- Owner Web Dashboard UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard_ui():
    """Render the responsive Owner Management Portal."""
    template_path = TEMPLATES_DIR / "index.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AI-COMPANY Control Deck</h1><p>Template index.html not found.</p>")
