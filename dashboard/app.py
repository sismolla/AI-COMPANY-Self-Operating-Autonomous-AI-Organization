"""FastAPI Web Application and Owner Control Panel for AI-COMPANY.

Ultra-Modern, Autonomous Multi-Agent OS & Command Center.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config.settings import settings
from infrastructure.database import db
from infrastructure.memory import memory_store
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


# --- API Routes ---
@app.get("/api/status")
async def get_status():
    """Retrieve aggregate enterprise health and deep telemetry."""
    health = await system_monitor.get_company_health_summary()
    scorecards = await system_monitor.get_agent_scorecards()

    agent_details = []
    agent_instances = {
        "director": ("AI CEO / Executive Director", "Plans, delegates, evaluates, allocates resources", 3),
        "research": ("Market Intelligence & Research", "Gathers information, monitors trends, builds briefs", 1),
        "engineering": ("Software & Tool Architect", "Writes software, builds internal tools, runs sandbox tests", 2),
        "marketing": ("Audience Growth & Content", "Drafts copy, content strategies, stages social campaigns", 2),
        "analytics": ("Performance & Optimization", "Computes metrics, detects bottlenecks, tracks KPIs", 2),
        "operations": ("Infrastructure Hygiene", "Maintains recurring jobs, health checks, queue cleanup", 2),
        "quality": ("Security & Quality Officer", "Audits code AST, enforces least-privilege, checks tests", 2)
    }

    for sc in scorecards:
        agent_name = sc["agent"]
        role_title, desc, perm_level = agent_instances.get(agent_name, (agent_name.capitalize(), "Autonomous Agent", 1))

        # Fetch latest task for this agent
        recent_tasks = await db.get_tasks_by_agent(agent_name, limit=1)
        latest_task = recent_tasks[0] if recent_tasks else None

        # Count workspace files
        ws_dir = settings.WORKSPACE_DIR / agent_name
        files_count = len([f for f in ws_dir.glob("**/*") if f.is_file()]) if ws_dir.exists() else 0

        # Count memories
        mem_rows = await db.fetch_all("SELECT COUNT(*) as c FROM agent_memory WHERE agent_name = ?", (agent_name,))
        mem_count = mem_rows[0]["c"] if mem_rows else 0

        # Determine live state
        is_running = any(
            t_id in task_queue.running_tasks and not task_queue.running_tasks[t_id].done()
            for t_id, t in [(latest_task["id"], latest_task)] if latest_task
        ) if latest_task else False

        status_label = "EXECUTING" if is_running else ("IDLE STANDBY" if sc["total_tasks"] == 0 else "READY")

        agent_details.append({
            **sc,
            "role_title": role_title,
            "description": desc,
            "permission_level": perm_level,
            "status_label": status_label,
            "is_running": is_running,
            "latest_task": latest_task,
            "workspace_files_count": files_count,
            "memory_count": mem_count
        })

    return {
        "enterprise": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health": health,
        "agents": agent_details
    }


@app.get("/api/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Deep inspect an agent: instructions, workspace files, private memories, recent tasks."""
    clean_name = agent_name.lower().strip()
    ws_dir = settings.WORKSPACE_DIR / clean_name
    files = []
    if ws_dir.exists():
        for f in ws_dir.glob("**/*"):
            if f.is_file():
                files.append({
                    "name": f.name,
                    "rel_path": str(f.relative_to(ws_dir)),
                    "size_bytes": f.stat().st_size
                })

    memories = await memory_store.list_by_type(clean_name, "long_term", limit=10)
    episodic = await memory_store.list_by_type(clean_name, "episodic", limit=10)
    tasks = await db.get_tasks_by_agent(clean_name, limit=10)

    # Read instructions
    instr_path = settings.BASE_DIR / "agents" / clean_name / "instructions.md"
    instructions = ""
    if instr_path.exists():
        with open(instr_path, "r", encoding="utf-8") as inf:
            instructions = inf.read()

    return {
        "agent": clean_name,
        "instructions": instructions,
        "workspace_files": files,
        "long_term_memories": memories,
        "episodic_memories": episodic,
        "recent_tasks": tasks
    }


@app.get("/api/workspace/{agent_name}/file")
async def get_workspace_file(agent_name: str, path: str = Query(...)):
    """Read contents of an agent workspace file."""
    clean_name = agent_name.lower().strip()
    ws_dir = settings.WORKSPACE_DIR / clean_name
    target = (ws_dir / path).resolve()
    if not str(target).startswith(str(ws_dir.resolve())) or not target.exists():
        raise HTTPException(status_code=404, detail="File not found in agent workspace.")

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return {"agent": clean_name, "filename": target.name, "content": content}


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
    if agent:
        return await db.get_tasks_by_agent(agent, limit=limit)
    return await db.get_all_tasks(limit=limit)


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

    appr = await db.fetch_one("SELECT task_id FROM approvals WHERE id = ?", (approval_id,))
    if appr and appr.get("task_id"):
        new_status = "pending" if req.status == "approved" else "failed"
        await db.update_task(appr["task_id"], status=new_status)

    return {"success": True, "approval_id": approval_id, "status": req.status}


@app.get("/api/tools")
async def list_tools():
    """List all registered tools."""
    return await tool_registry.list_tools()


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


# --- Owner Web Dashboard UI ---
@app.get("/", response_class=HTMLResponse)
async def dashboard_ui():
    """Render the ultra-modern Autonomous AI Organization Command Center."""
    html = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-COMPANY // Autonomous Fleet Command Center</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #07090e;
      --card-surface: rgba(13, 18, 30, 0.88);
      --card-surface-hover: rgba(22, 30, 50, 0.95);
      --card-border: rgba(56, 189, 248, 0.16);
      --card-border-glow: rgba(56, 189, 248, 0.4);
      --neon-cyan: #00f0ff;
      --neon-cyan-glow: rgba(0, 240, 255, 0.25);
      --neon-emerald: #10b981;
      --neon-emerald-glow: rgba(16, 185, 129, 0.25);
      --neon-amber: #f59e0b;
      --neon-amber-glow: rgba(245, 158, 11, 0.25);
      --neon-purple: #a855f7;
      --neon-purple-glow: rgba(168, 85, 247, 0.25);
      --neon-rose: #f43f5e;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Space Grotesk', -apple-system, sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    body {
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px),
        radial-gradient(circle at 10% 20%, rgba(168, 85, 247, 0.06) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(0, 240, 255, 0.05) 0%, transparent 40%);
      background-size: 28px 28px, 100% 100%, 100% 100%;
      color: var(--text-main);
      padding: 20px 24px 60px;
      min-height: 100vh;
      overflow-x: hidden;
    }
    .wrapper { max-width: 1680px; margin: 0 auto; }

    /* Top HUD Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 24px;
      background: var(--card-surface);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      margin-bottom: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }
    .brand-wrap { display: flex; align-items: center; gap: 16px; }
    .brand-icon {
      width: 44px; height: 44px;
      background: linear-gradient(135deg, rgba(0,240,255,0.2), rgba(168,85,247,0.3));
      border: 1px solid var(--neon-cyan);
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 22px;
      box-shadow: 0 0 15px var(--neon-cyan-glow);
    }
    .brand-title { font-size: 20px; font-weight: 700; letter-spacing: -0.5px; color: #fff; }
    .brand-subtitle { font-size: 11px; color: var(--neon-cyan); letter-spacing: 1.5px; text-transform: uppercase; }

    .header-pills { display: flex; align-items: center; gap: 12px; }
    .status-pill {
      display: flex; align-items: center; gap: 8px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--neon-emerald);
      padding: 6px 14px; border-radius: 9999px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
    }
    .pulse-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--neon-emerald);
      box-shadow: 0 0 8px var(--neon-emerald);
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }

    .btn {
      display: inline-flex; align-items: center; gap: 8px;
      background: linear-gradient(135deg, var(--neon-cyan), #0284c7);
      color: #050b14; font-weight: 700; font-size: 12px;
      padding: 9px 18px; border-radius: 8px; border: none;
      cursor: pointer; transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    .btn:hover {
      box-shadow: 0 0 20px var(--neon-cyan-glow);
      transform: translateY(-2px);
    }
    .btn-secondary {
      background: rgba(30, 41, 59, 0.8);
      color: #e2e8f0;
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .btn-secondary:hover { background: rgba(51, 65, 85, 0.9); box-shadow: 0 0 15px rgba(255,255,255,0.08); }
    .btn-danger { background: var(--neon-rose); color: #fff; }
    .btn-success { background: var(--neon-emerald); color: #041a11; }

    /* Top Telemetry Grid */
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }
    .telem-card {
      background: var(--card-surface);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 12px; padding: 18px 20px;
      position: relative; overflow: hidden;
      transition: all 0.25s ease;
    }
    .telem-card:hover {
      border-color: var(--card-border-glow);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    .telem-card::before {
      content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
      background: var(--neon-cyan); opacity: 0.8;
    }
    .telem-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 6px; }
    .telem-val { font-size: 28px; font-weight: 700; color: #fff; display: flex; align-items: baseline; gap: 6px; }
    .telem-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; }

    /* Section Headers & Filter Nav */
    .section-bar {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; padding: 0 4px;
    }
    .section-title { font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 10px; color: #fff; }
    .filter-tabs { display: flex; gap: 6px; background: rgba(15, 23, 42, 0.7); padding: 4px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); }
    .filter-tab {
      padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 600;
      color: var(--text-muted); cursor: pointer; border: none; background: transparent;
      transition: 0.2s; text-transform: uppercase;
    }
    .filter-tab.active { background: rgba(0, 240, 255, 0.15); color: var(--neon-cyan); border: 1px solid rgba(0, 240, 255, 0.3); }

    /* Autonomous Agents Live Fleet Grid */
    .agents-matrix {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
      gap: 20px; margin-bottom: 28px;
    }
    @media(max-width: 768px) { .agents-matrix { grid-template-columns: 1fr; } }

    .agent-card {
      background: var(--card-surface);
      backdrop-filter: blur(14px);
      border: 1px solid var(--card-border);
      border-radius: 14px; padding: 22px;
      position: relative; transition: all 0.25s ease;
      display: flex; flex-direction: column; justify-content: space-between;
    }
    .agent-card:hover {
      border-color: var(--card-border-glow);
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.55), 0 0 20px rgba(0, 240, 255, 0.08);
    }
    .agent-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
    .agent-id { display: flex; align-items: center; gap: 12px; }
    .agent-avatar {
      width: 44px; height: 44px; border-radius: 10px;
      background: #1e293b; border: 1px solid rgba(255,255,255,0.15);
      display: flex; align-items: center; justify-content: center;
      font-size: 20px;
    }
    .agent-meta-name { font-size: 16px; font-weight: 700; color: #fff; text-transform: uppercase; }
    .agent-meta-role { font-size: 11px; color: var(--neon-cyan); }

    .badge-clearance {
      padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    .badge-l1 { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .badge-l2 { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
    .badge-l3 { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-l4 { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }

    /* Live Action & What They Got Boxes */
    .box-doing {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;
    }
    .box-label {
      font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
      color: var(--neon-cyan); font-weight: 700; margin-bottom: 4px;
      display: flex; justify-content: space-between;
    }
    .box-content-title { font-size: 13px; font-weight: 600; color: #f1f5f9; line-height: 1.4; }

    .box-split { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
    .box-sub {
      background: rgba(10, 15, 28, 0.75); border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px; padding: 10px; font-size: 11px;
    }
    .box-sub-label { font-size: 9px; text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px; font-weight: 700; }
    .box-sub-val { color: var(--text-muted); line-height: 1.35; max-height: 60px; overflow-y: auto; }

    /* Telemetry readout bar */
    .telem-bar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 0; border-top: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 11px; color: var(--text-muted);
    }
    .telem-item b { color: #fff; }

    /* Action footer buttons */
    .agent-actions { display: flex; gap: 8px; margin-top: 8px; }
    .btn-act {
      flex: 1; padding: 6px 10px; font-size: 10px; font-weight: 700;
      border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);
      background: rgba(30, 41, 59, 0.6); color: var(--text-muted);
      cursor: pointer; text-transform: uppercase; transition: 0.2s;
      text-align: center;
    }
    .btn-act:hover { background: rgba(51, 65, 85, 0.85); color: #fff; border-color: rgba(0,240,255,0.4); }

    /* Dual Grid Layouts for Objectives & Approvals */
    .grid-duo { display: grid; grid-template-columns: 1.3fr 1fr; gap: 20px; margin-bottom: 28px; }
    @media(max-width: 1024px) { .grid-duo { grid-template-columns: 1fr; } }

    .panel-card {
      background: var(--card-surface);
      backdrop-filter: blur(14px);
      border: 1px solid var(--card-border);
      border-radius: 14px; padding: 22px;
    }
    .panel-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 18px; padding-bottom: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* Objectives Items */
    .objective-item {
      padding: 14px; background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 10px; margin-bottom: 12px;
    }
    .obj-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .obj-title { font-weight: 700; font-size: 14px; color: #fff; }
    .obj-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4; }
    .progress-track {
      background: rgba(30, 41, 59, 0.8); height: 6px; border-radius: 4px; overflow: hidden;
      margin-top: 8px; position: relative;
    }
    .progress-fill {
      height: 100%; border-radius: 4px;
      background: linear-gradient(90deg, #0284c7, var(--neon-cyan));
      box-shadow: 0 0 10px var(--neon-cyan-glow);
      transition: width 0.4s ease;
    }

    /* Approvals Items */
    .approval-item {
      padding: 14px; background: rgba(30, 20, 10, 0.4);
      border: 1px solid rgba(245, 158, 11, 0.3);
      border-radius: 10px; margin-bottom: 12px;
    }
    .appr-title { font-weight: 700; font-size: 13px; color: #fef08a; display: flex; justify-content: space-between; }

    /* Task Stream Table */
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { color: var(--text-dim); text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; padding: 10px 12px; border-bottom: 1px solid var(--card-border); font-weight: 600; text-align: left; }
    td { padding: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); vertical-align: middle; }
    tr:hover { background: rgba(255, 255, 255, 0.02); }

    /* Deep Dive Inspector Drawer */
    .drawer-overlay {
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(8px);
      z-index: 1000; opacity: 0; pointer-events: none; transition: 0.3s;
    }
    .drawer-overlay.open { opacity: 1; pointer-events: auto; }
    .drawer {
      position: fixed; top: 0; right: -700px; width: 680px; max-width: 90vw; height: 100%;
      background: #090e18; border-left: 1px solid var(--card-border-glow);
      z-index: 1001; transition: right 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex; flex-direction: column; box-shadow: -15px 0 50px rgba(0,0,0,0.8);
    }
    .drawer.open { right: 0; }
    .drawer-header {
      padding: 20px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex; justify-content: space-between; align-items: center;
    }
    .drawer-body { padding: 24px; overflow-y: auto; flex: 1; }
    .code-view {
      background: #04070e; border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px; padding: 16px; font-family: 'JetBrains Mono', monospace;
      font-size: 11px; color: #38bdf8; overflow-x: auto; white-space: pre-wrap; line-height: 1.5;
    }

    /* Live Terminal Log Stream */
    .terminal-box {
      background: #04070d; border: 1px solid rgba(0, 240, 255, 0.2);
      border-radius: 10px; padding: 14px 18px; font-family: 'JetBrains Mono', monospace;
      font-size: 11px; height: 200px; overflow-y: auto; color: #a5f3fc;
    }
    .term-line { margin-bottom: 6px; display: flex; gap: 10px; }
    .term-time { color: var(--text-dim); }
    .term-actor { color: var(--neon-cyan); font-weight: 700; }
    .term-act { color: #f1f5f9; }
  </style>
</head>
<body>
  <div class="wrapper">
    <!-- Top HUD Header -->
    <header>
      <div class="brand-wrap">
        <div class="brand-icon">⚡</div>
        <div>
          <div class="brand-title">AI-COMPANY</div>
          <div class="brand-subtitle">Autonomous Enterprise Operating System</div>
        </div>
      </div>
      <div class="header-pills">
        <div class="status-pill">
          <span class="pulse-dot"></span>
          <span>Engine Active</span>
        </div>
        <div class="mono" style="font-size: 12px; color: var(--text-muted); background: rgba(255,255,255,0.05); padding: 6px 12px; border-radius: 6px;" id="live-clock">
          00:00:00 UTC
        </div>
        <button class="btn btn-secondary" onclick="triggerCycle()">⚡ Run Cycle</button>
        <button class="btn btn-secondary" onclick="openNewTaskModal()">+ Dispatch Task</button>
        <button class="btn" onclick="openNewObjectiveModal()">+ Directive</button>
      </div>
    </header>

    <!-- Top Telemetry Row -->
    <div class="telemetry-grid">
      <div class="telem-card">
        <div class="telem-title">Enterprise Health</div>
        <div class="telem-val" id="kpi-status" style="color: var(--neon-emerald);">OPTIMAL</div>
        <div class="telem-sub">Continuous loop running</div>
      </div>
      <div class="telem-card">
        <div class="telem-title">Task Success Rate</div>
        <div class="telem-val" id="kpi-success">--%</div>
        <div class="telem-sub"><span id="kpi-completed-tasks">0</span> tasks resolved</div>
      </div>
      <div class="telem-card">
        <div class="telem-title">Active AI Employees</div>
        <div class="telem-val" id="kpi-agents">6 + 1</div>
        <div class="telem-sub">Independent memory & tools</div>
      </div>
      <div class="telem-card">
        <div class="telem-title">Self-Built Tools</div>
        <div class="telem-val" id="kpi-tools" style="color: var(--neon-purple);">--</div>
        <div class="telem-sub">AST verified in sandbox</div>
      </div>
      <div class="telem-card">
        <div class="telem-title">Pending Approvals</div>
        <div class="telem-val" id="kpi-approvals" style="color: var(--neon-amber);">0</div>
        <div class="telem-sub">Level 3 / Level 4 gates</div>
      </div>
    </div>

    <!-- Section: Autonomous AI Workforce Fleet -->
    <div class="section-bar">
      <div class="section-title">
        <span>🤖 Autonomous Workforce Fleet</span>
        <span style="font-size: 12px; color: var(--text-muted); font-weight: normal;">(Live status: what each agent is doing, inputs received & deliverables generated)</span>
      </div>
      <div class="filter-tabs">
        <button class="filter-tab active" onclick="filterAgents('all')">ALL</button>
        <button class="filter-tab" onclick="filterAgents('research')">RESEARCH</button>
        <button class="filter-tab" onclick="filterAgents('engineering')">ENGINEERING</button>
        <button class="filter-tab" onclick="filterAgents('marketing')">MARKETING</button>
        <button class="filter-tab" onclick="filterAgents('analytics')">ANALYTICS</button>
        <button class="filter-tab" onclick="filterAgents('quality')">QUALITY</button>
      </div>
    </div>

    <!-- Live Agent Cards Grid -->
    <div class="agents-matrix" id="agents-matrix">
      <!-- Injected by JavaScript -->
    </div>

    <!-- Middle Duo: Strategic Directives & Security Approvals -->
    <div class="grid-duo">
      <!-- Left: Strategic Objectives -->
      <div class="panel-card">
        <div class="panel-header">
          <div style="font-size: 15px; font-weight: 700; color: #fff;">🎯 Strategic Business Directives</div>
          <button class="btn btn-secondary" style="font-size: 10px; padding: 4px 10px;" onclick="openNewObjectiveModal()">+ New Directive</button>
        </div>
        <div id="objectives-list">Loading objectives...</div>
      </div>

      <!-- Right: Security & Approvals Gate -->
      <div class="panel-card">
        <div class="panel-header">
          <div style="font-size: 15px; font-weight: 700; color: #fff;">🛡️ Level 3/4 Authorization Gates</div>
          <span style="font-size: 11px; color: var(--neon-amber);" id="approvals-badge">0 Actions Staged</span>
        </div>
        <div id="approvals-list">No pending authorization gates. All actions cleared.</div>
      </div>
    </div>

    <!-- Bottom Duo: Task Ledger & Tool Factory -->
    <div class="grid-duo">
      <!-- Live Task Ledger -->
      <div class="panel-card">
        <div class="panel-header">
          <div style="font-size: 15px; font-weight: 700; color: #fff;">📋 Organizational Task Ledger</div>
          <span style="font-size: 11px; color: var(--text-muted);" id="task-count-label">--</span>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Task Title</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Deliverable</th>
              </tr>
            </thead>
            <tbody id="tasks-table">
              <tr><td colspan="5">Loading ledger...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Self-Building Tool Factory -->
      <div class="panel-card">
        <div class="panel-header">
          <div style="font-size: 15px; font-weight: 700; color: #fff;">⚙️ Self-Building Tool Factory</div>
          <button class="btn" style="font-size: 10px; padding: 4px 10px;" onclick="openBuildToolModal()">+ Commission Tool</button>
        </div>
        <div id="tools-catalog" style="max-height: 380px; overflow-y: auto;">Loading tool catalog...</div>
      </div>
    </div>

    <!-- Live Terminal Audit Stream -->
    <div class="panel-card" style="margin-top: 4px;">
      <div class="panel-header" style="margin-bottom: 10px;">
        <div style="font-size: 14px; font-weight: 700; color: #fff;">📡 Live Telemetry & Audit Stream</div>
        <span class="mono" style="font-size: 10px; color: var(--neon-cyan);">REAL-TIME EVENT BUS</span>
      </div>
      <div class="terminal-box" id="terminal-stream">
        <div class="term-line"><span class="term-time">[00:00:00]</span> <span class="term-actor">SYSTEM</span> <span class="term-act">Connecting to Enterprise Orchestrator...</span></div>
      </div>
    </div>
  </div>

  <!-- Deep Dive Inspector Drawer -->
  <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
  <div class="drawer" id="drawer">
    <div class="drawer-header">
      <div>
        <div style="font-size: 16px; font-weight: 700; color: #fff;" id="drawer-title">Agent Telemetry Inspection</div>
        <div style="font-size: 11px; color: var(--neon-cyan);" id="drawer-subtitle">Memory & Workspace Files</div>
      </div>
      <button class="btn btn-secondary" style="padding: 4px 10px;" onclick="closeDrawer()">✕</button>
    </div>
    <div class="drawer-body" id="drawer-content">
      Loading agent telemetry...
    </div>
  </div>

  <script>
    let currentFilter = 'all';
    let cachedAgents = [];

    // Live Clock
    function updateClock() {
      const now = new Date();
      document.getElementById('live-clock').innerText = now.toISOString().slice(11, 19) + ' UTC';
    }
    setInterval(updateClock, 1000);
    updateClock();

    async function loadDashboard() {
      try {
        const [statusRes, objRes, tasksRes, apprRes, toolsRes, logsRes] = await Promise.all([
          fetch('/api/status').then(r => r.json()),
          fetch('/api/objectives').then(r => r.json()),
          fetch('/api/tasks?limit=12').then(r => r.json()),
          fetch('/api/approvals').then(r => r.json()),
          fetch('/api/tools').then(r => r.json()),
          fetch('/api/logs?limit=15').then(r => r.json())
        ]);

        // 1. Telemetry Stats
        const h = statusRes.health || {};
        document.getElementById('kpi-status').innerText = (h.status || 'OPTIMAL').toUpperCase();
        document.getElementById('kpi-success').innerText = (h.success_rate_pct || 100) + '%';
        document.getElementById('kpi-completed-tasks').innerText = h.completed_tasks || 0;
        document.getElementById('kpi-tools').innerText = h.approved_tools_count || 0;
        document.getElementById('kpi-approvals').innerText = h.pending_approvals_count || 0;
        document.getElementById('task-count-label').innerText = `${h.completed_tasks || 0} completed / ${h.total_tasks || 0} total`;

        // 2. Render Agents
        cachedAgents = statusRes.agents || [];
        renderAgents(cachedAgents);

        // 3. Render Objectives
        renderObjectives(objRes || []);

        // 4. Render Approvals
        renderApprovals(apprRes || []);

        // 5. Render Tasks Table
        renderTasks(tasksRes || []);

        // 6. Render Tools Catalog
        renderTools(toolsRes || []);

        // 7. Render Terminal Logs
        renderLogs(logsRes || []);

      } catch (err) {
        console.error("Dashboard refresh error:", err);
      }
    }

    function renderAgents(agents) {
      const container = document.getElementById('agents-matrix');
      const filtered = (currentFilter === 'all') ? agents : agents.filter(a => a.agent === currentFilter);

      const agentIcons = {
        director: '👑', research: '🔬', engineering: '⚡',
        marketing: '📢', analytics: '📊', operations: '⚙️', quality: '🛡️'
      };

      container.innerHTML = filtered.map(a => {
        const icon = agentIcons[a.agent] || '🤖';
        const lt = a.latest_task || {};
        const inputsJson = lt.inputs ? JSON.stringify(lt.inputs) : 'Default context';
        const outputsSummary = (lt.outputs && lt.outputs.summary) ? lt.outputs.summary : (lt.outputs ? JSON.stringify(lt.outputs).slice(0, 80) : 'Standby');

        let permClass = 'badge-l1';
        if (a.permission_level === 2) permClass = 'badge-l2';
        if (a.permission_level === 3) permClass = 'badge-l3';
        if (a.permission_level === 4) permClass = 'badge-l4';

        const statusColor = a.status_label === 'EXECUTING' ? 'var(--neon-emerald)' : (a.status_label === 'READY' ? 'var(--neon-cyan)' : 'var(--text-dim)');

        return `
          <div class="agent-card">
            <div>
              <div class="agent-top">
                <div class="agent-id">
                  <div class="agent-avatar">${icon}</div>
                  <div>
                    <div class="agent-meta-name">${a.agent}</div>
                    <div class="agent-meta-role">${a.role_title}</div>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                  <span class="badge-clearance ${permClass}">LEVEL ${a.permission_level} CLEARANCE</span>
                  <div style="display: flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 700; color: ${statusColor};">
                    <span class="pulse-dot" style="width: 6px; height: 6px; background: ${statusColor};"></span>
                    <span>${a.status_label}</span>
                  </div>
                </div>
              </div>

              <!-- Currently Doing -->
              <div class="box-doing">
                <div class="box-label">
                  <span>⚡ CURRENTLY WORKING ON</span>
                  <span class="mono">${lt.status || 'IDLE'}</span>
                </div>
                <div class="box-content-title">${lt.title || 'Standing by for next directive'}</div>
              </div>

              <!-- What it got & what it gave -->
              <div class="box-split">
                <div class="box-sub">
                  <div class="box-sub-label">📥 WHAT IT RECEIVED (INPUTS)</div>
                  <div class="box-sub-val mono">${inputsJson}</div>
                </div>
                <div class="box-sub">
                  <div class="box-sub-label">📤 WHAT IT DELIVERED (OUTPUTS)</div>
                  <div class="box-sub-val">${outputsSummary}</div>
                </div>
              </div>
            </div>

            <div>
              <!-- Telemetry -->
              <div class="telem-bar">
                <div class="telem-item">Tasks: <b>${a.completed}/${a.total_tasks}</b> (${a.success_rate_pct}%)</div>
                <div class="telem-item">Avg Latency: <b>${a.avg_duration_sec}s</b></div>
                <div class="telem-item">Memories: <b>${a.memory_count}</b></div>
                <div class="telem-item">Workspace: <b>${a.workspace_files_count} files</b></div>
              </div>

              <!-- Action buttons -->
              <div class="agent-actions">
                <button class="btn-act" onclick="inspectAgent('${a.agent}')">🧠 Inspect Memory</button>
                <button class="btn-act" onclick="inspectWorkspace('${a.agent}')">📂 Workspace Files</button>
                <button class="btn-act" onclick="dispatchDirectTask('${a.agent}')">⚡ Dispatch Task</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderObjectives(objectives) {
      const container = document.getElementById('objectives-list');
      if (!objectives || objectives.length === 0) {
        container.innerHTML = '<div style="font-size: 12px; color: var(--text-muted);">No active objectives.</div>';
        return;
      }
      container.innerHTML = objectives.map(o => `
        <div class="objective-item">
          <div class="obj-top">
            <div class="obj-title">${o.title}</div>
            <span class="badge-clearance badge-l1">${o.priority.toUpperCase()}</span>
          </div>
          <div class="obj-desc">${o.description}</div>
          <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-dim);">
            <span>Lead Agent: <b style="color: var(--neon-cyan);">${o.target_agent}</b></span>
            <span>Progress: <b style="color: #fff;">${o.progress}%</b></span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: ${o.progress}%;"></div>
          </div>
        </div>
      `).join('');
    }

    function renderApprovals(approvals) {
      const container = document.getElementById('approvals-list');
      const badge = document.getElementById('approvals-badge');
      badge.innerText = `${approvals.length} Actions Staged`;

      if (!approvals || approvals.length === 0) {
        container.innerHTML = '<div style="font-size: 12px; color: var(--text-dim); padding: 10px 0;">No pending authorization gates. All agent actions executing within boundaries.</div>';
        return;
      }

      container.innerHTML = approvals.map(ap => `
        <div class="approval-item">
          <div class="appr-title">
            <span>LEVEL ${ap.permission_level}: ${ap.action_name}</span>
            <span class="badge-clearance badge-l3">REQUIRES SIGN-OFF</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin: 6px 0;">
            Requested by: <b style="color: #fff;">${ap.requested_by.toUpperCase()}</b>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 10px;">
            <button class="btn btn-success" style="padding: 5px 12px; font-size: 11px;" onclick="reviewApproval('${ap.id}', 'approved')">Authorize Action</button>
            <button class="btn btn-danger" style="padding: 5px 12px; font-size: 11px;" onclick="reviewApproval('${ap.id}', 'rejected')">Deny Action</button>
          </div>
        </div>
      `).join('');
    }

    function renderTasks(tasks) {
      const tbody = document.getElementById('tasks-table');
      if (!tasks || tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="color: var(--text-dim);">No tasks recorded in ledger.</td></tr>';
        return;
      }
      tbody.innerHTML = tasks.slice(0, 10).map(t => {
        let statusTag = '<span style="color: var(--neon-emerald);">● COMPLETED</span>';
        if (t.status === 'running') statusTag = '<span style="color: var(--neon-cyan);">● RUNNING</span>';
        if (t.status === 'pending') statusTag = '<span style="color: var(--neon-amber);">● PENDING</span>';
        if (t.status === 'blocked_approval') statusTag = '<span style="color: #f43f5e;">● GATED</span>';

        const deliverable = (t.outputs && t.outputs.summary) ? t.outputs.summary.slice(0, 45) + '...' : '-';

        return `
          <tr>
            <td><b style="color: var(--neon-cyan);">${t.owner_agent.toUpperCase()}</b></td>
            <td><div style="font-weight: 600; color: #fff;">${t.title}</div></td>
            <td class="mono">${statusTag}</td>
            <td class="mono" style="font-size: 10px;">${t.priority}</td>
            <td style="color: var(--text-muted); font-size: 11px;">${deliverable}</td>
          </tr>
        `;
      }).join('');
    }

    function renderTools(tools) {
      const container = document.getElementById('tools-catalog');
      if (!tools || tools.length === 0) {
        container.innerHTML = '<div style="font-size: 12px; color: var(--text-muted);">No tools registered.</div>';
        return;
      }
      container.innerHTML = tools.map(t => `
        <div style="padding: 10px 12px; background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-weight: 700; font-size: 13px; color: #fff;">
              ${t.name} <span class="mono" style="font-size: 10px; color: var(--neon-cyan);">v${t.version}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted);">${t.description}</div>
          </div>
          <span class="badge-clearance badge-l2">AST SECURE</span>
        </div>
      `).join('');
    }

    function renderLogs(logs) {
      const box = document.getElementById('terminal-stream');
      if (!logs || logs.length === 0) return;
      box.innerHTML = logs.map(l => {
        const time = l.timestamp ? l.timestamp.split('T')[1].slice(0, 8) : '00:00:00';
        return `
          <div class="term-line">
            <span class="term-time">[${time}]</span>
            <span class="term-actor">${l.actor.toUpperCase()}</span>
            <span class="term-act">&gt;&gt; ${l.action} ${JSON.stringify(l.details).slice(0, 70)}</span>
          </div>
        `;
      }).join('');
    }

    function filterAgents(agent) {
      currentFilter = agent;
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      event.target.classList.add('active');
      renderAgents(cachedAgents);
    }

    // --- Actions & Modals ---
    async function triggerCycle() {
      const res = await fetch('/api/cycle/run', { method: 'POST' });
      const data = await res.json();
      loadDashboard();
    }

    async function reviewApproval(approvalId, status) {
      await fetch(`/api/approvals/${approvalId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: status, reviewer: 'owner' })
      });
      loadDashboard();
    }

    async function openNewObjectiveModal() {
      const title = prompt("Enter Strategic Business Directive Title:");
      if (!title) return;
      const description = prompt("Enter Directive Mission & Scope:");
      if (!description) return;
      await fetch('/api/objectives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, priority: "high" })
      });
      loadDashboard();
    }

    async function openNewTaskModal() {
      const agent = prompt("Target Agent (research, engineering, marketing, analytics, operations, quality):", "engineering");
      if (!agent) return;
      const title = prompt("Task Title:");
      if (!title) return;
      const description = prompt("Task Description & Scope:");
      await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_agent: agent, title, description, priority: "medium" })
      });
      loadDashboard();
    }

    async function dispatchDirectTask(agent) {
      const title = prompt(`Dispatch direct directive to ${agent.toUpperCase()}:`);
      if (!title) return;
      const description = prompt("Task Description:");
      await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_agent: agent, title, description: description || title, priority: "high" })
      });
      loadDashboard();
    }

    async function openBuildToolModal() {
      const name = prompt("Tool Name (e.g. sentiment_scorer, csv_parser):");
      if (!name) return;
      const description = prompt("Tool Purpose & Functionality:");
      if (!description) return;
      alert("Dispatching to Tool Factory Sandbox for synthesis, AST security scan, and test execution...");
      const res = await fetch('/api/tools/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, category: "custom" })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Tool '${name}' successfully synthesized, sandbox verified, and registered!`);
      } else {
        alert(`Tool build failed: ${data.error}`);
      }
      loadDashboard();
    }

    // --- Drawer Telemetry Inspection ---
    async function inspectAgent(agent) {
      document.getElementById('drawer-title').innerText = `${agent.toUpperCase()} // Memory Store`;
      document.getElementById('drawer-subtitle').innerText = "Long-Term Learnings & Episodic Experience";
      document.getElementById('drawer-overlay').classList.add('open');
      document.getElementById('drawer').classList.add('open');

      const res = await fetch(`/api/agents/${agent}`).then(r => r.json());
      const longTerm = res.long_term_memories || [];
      const episodic = res.episodic_memories || [];

      let content = '<h4 style="color: var(--neon-cyan); margin-bottom: 12px;">🧠 Long-Term Learnings</h4>';
      if (longTerm.length === 0) content += '<div style="color: var(--text-dim); margin-bottom: 20px;">No long-term memories stored yet.</div>';
      else {
        content += longTerm.map(m => `
          <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.06); padding: 12px; border-radius: 8px; margin-bottom: 8px;">
            <div class="mono" style="color: #fff; font-weight: 700; font-size: 12px;">${m.key}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${JSON.stringify(m.value)}</div>
          </div>
        `).join('');
      }

      content += '<h4 style="color: var(--neon-purple); margin: 20px 0 12px;">📜 Episodic Experience</h4>';
      if (episodic.length === 0) content += '<div style="color: var(--text-dim);">No episodic memories recorded.</div>';
      else {
        content += episodic.map(e => `
          <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.06); padding: 12px; border-radius: 8px; margin-bottom: 8px;">
            <div class="mono" style="color: #fff; font-weight: 700; font-size: 12px;">${e.key}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${e.value}</div>
          </div>
        `).join('');
      }

      document.getElementById('drawer-content').innerHTML = content;
    }

    async function inspectWorkspace(agent) {
      document.getElementById('drawer-title').innerText = `${agent.toUpperCase()} // Workspace Deliverables`;
      document.getElementById('drawer-subtitle').innerText = "Generated code, dossiers, reports & scripts";
      document.getElementById('drawer-overlay').classList.add('open');
      document.getElementById('drawer').classList.add('open');

      const res = await fetch(`/api/agents/${agent}`).then(r => r.json());
      const files = res.workspace_files || [];

      if (files.length === 0) {
        document.getElementById('drawer-content').innerHTML = '<div style="color: var(--text-dim);">No files created in this workspace yet.</div>';
        return;
      }

      let content = '<div style="display: flex; flex-direction: column; gap: 8px;">';
      for (const f of files) {
        content += `
          <div style="background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.06); padding: 12px 14px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 700; font-size: 13px; color: #fff;">${f.name}</div>
              <div class="mono" style="font-size: 10px; color: var(--text-dim);">${f.size_bytes} bytes</div>
            </div>
            <button class="btn btn-secondary" style="font-size: 10px; padding: 4px 10px;" onclick="viewFile('${agent}', '${f.rel_path}')">Read File</button>
          </div>
        `;
      }
      content += '</div><div id="file-viewer-area" style="margin-top: 20px;"></div>';
      document.getElementById('drawer-content').innerHTML = content;
    }

    async function viewFile(agent, path) {
      const res = await fetch(`/api/workspace/${agent}/file?path=${encodeURIComponent(path)}`).then(r => r.json());
      const area = document.getElementById('file-viewer-area');
      area.innerHTML = `
        <h4 style="color: var(--neon-cyan); margin-bottom: 8px;">📄 Viewing: ${res.filename}</h4>
        <div class="code-view">${res.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      `;
    }

    function closeDrawer() {
      document.getElementById('drawer-overlay').classList.remove('open');
      document.getElementById('drawer').classList.remove('open');
    }

    // Initial load and periodic live pulse
    loadDashboard();
    setInterval(loadDashboard, 3500);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
