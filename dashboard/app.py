"""FastAPI Web Application and Owner Control Panel for AI-COMPANY."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
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
    """Retrieve aggregate enterprise health and telemetry."""
    health = await system_monitor.get_company_health_summary()
    scorecards = await system_monitor.get_agent_scorecards()
    return {
        "enterprise": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health": health,
        "agents": scorecards
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
    """Render the responsive Owner Management Portal."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-COMPANY | Autonomous Enterprise Control Center</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f293d;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --text: #f3f4f6;
      --text-muted: #94a3b8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --purple: #a855f7;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
    .container { max-width: 1400px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--card-border); margin-bottom: 24px; }
    .logo-area h1 { font-size: 24px; font-weight: 700; color: #fff; letter-spacing: -0.5px; display: flex; align-items: center; gap: 10px; }
    .badge { padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
    .badge-live { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
    .badge-owner { background: rgba(56, 189, 248, 0.2); color: var(--accent); border: 1px solid var(--accent); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    .btn { background: var(--accent); color: #0b0f19; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; }
    .btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn-secondary { background: #374151; color: #fff; }
    .btn-danger { background: var(--danger); color: #fff; }
    .btn-success { background: var(--success); color: #fff; }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 18px; }
    .stat-title { font-size: 13px; color: var(--text-muted); font-weight: 500; margin-bottom: 6px; }
    .stat-value { font-size: 26px; font-weight: 700; color: #fff; }

    .grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px; }
    @media(max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 20px; margin-bottom: 24px; }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 12px; }
    .card-title { font-size: 17px; font-weight: 600; }

    /* Agents Grid */
    .agents-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px; }
    .agent-pill { background: #162032; border: 1px solid var(--card-border); border-radius: 8px; padding: 14px; }
    .agent-name { font-weight: 700; font-size: 15px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
    .agent-role { font-size: 11px; color: var(--text-muted); margin-bottom: 8px; line-height: 1.3; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
    th { color: var(--text-muted); padding: 10px 12px; border-bottom: 1px solid var(--card-border); font-weight: 500; }
    td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
    tr:hover { background: rgba(255,255,255,0.02); }

    /* Progress bar */
    .progress-bar-bg { background: #1f2937; height: 8px; border-radius: 4px; overflow: hidden; width: 100%; margin-top: 6px; }
    .progress-bar-fill { background: var(--accent); height: 100%; border-radius: 4px; transition: width 0.3s; }

    /* Modal / Form */
    .form-group { margin-bottom: 14px; }
    .form-group label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
    .form-control { width: 100%; background: #0b0f19; border: 1px solid var(--card-border); border-radius: 6px; padding: 8px 12px; color: #fff; font-size: 13px; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-area">
        <h1>
          <span>🏢 AI-COMPANY</span>
          <span class="badge badge-live">Self-Operating</span>
          <span class="badge badge-owner">Owner: You</span>
        </h1>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn btn-secondary" onclick="triggerCycle()">⚡ Run Cycle Now</button>
        <button class="btn" onclick="openNewObjectiveModal()">+ New Objective</button>
      </div>
    </header>

    <!-- Top KPI Row -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">System Status</div>
        <div class="stat-value" id="kpi-status" style="color: var(--success);">Healthy</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Task Success Rate</div>
        <div class="stat-value" id="kpi-success">--%</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Tasks Processed</div>
        <div class="stat-value" id="kpi-tasks">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Approved Tools</div>
        <div class="stat-value" id="kpi-tools">--</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Pending Approvals</div>
        <div class="stat-value" id="kpi-approvals" style="color: var(--warning);">--</div>
      </div>
    </div>

    <!-- Autonomous Employees Overview -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">👥 Autonomous AI Workforce</div>
        <span style="font-size: 12px; color: var(--text-muted);">Independent memory, tools & permission limits</span>
      </div>
      <div class="agents-grid" id="agents-container">
        <!-- Rendered by JS -->
      </div>
    </div>

    <!-- Middle Grid: Objectives & Pending Approvals -->
    <div class="grid-2">
      <!-- Strategic Objectives -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🎯 Strategic Business Objectives</div>
        </div>
        <div id="objectives-container">Loading objectives...</div>
      </div>

      <!-- Human-in-the-Loop Approvals -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🛡️ Level 3/4 Approval Queue</div>
        </div>
        <div id="approvals-container">Loading approvals...</div>
      </div>
    </div>

    <!-- Bottom Grid: Task Board & Tool Factory -->
    <div class="grid-2">
      <!-- Live Task Queue -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">📋 Live Organizational Task Board</div>
          <button class="btn btn-secondary" onclick="openNewTaskModal()">+ Dispatch Task</button>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Task Title</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody id="tasks-table-body">
              <tr><td colspan="5">Loading tasks...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Self-Building Tool Factory -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">⚙️ Self-Building Tool Factory</div>
          <button class="btn btn-secondary" onclick="openBuildToolModal()">+ Build Tool</button>
        </div>
        <div id="tools-container">Loading tool catalog...</div>
      </div>
    </div>
  </div>

  <script>
    async function loadDashboard() {
      try {
        const [statusRes, objRes, tasksRes, apprRes, toolsRes] = await Promise.all([
          fetch('/api/status').then(r => r.json()),
          fetch('/api/objectives').then(r => r.json()),
          fetch('/api/tasks?limit=15').then(r => r.json()),
          fetch('/api/approvals').then(r => r.json()),
          fetch('/api/tools').then(r => r.json())
        ]);

        // 1. Update KPIs
        const h = statusRes.health || {};
        document.getElementById('kpi-status').innerText = h.status ? h.status.toUpperCase() : 'OK';
        document.getElementById('kpi-success').innerText = (h.success_rate_pct || 100) + '%';
        document.getElementById('kpi-tasks').innerText = h.total_tasks || 0;
        document.getElementById('kpi-tools').innerText = h.approved_tools_count || 0;
        document.getElementById('kpi-approvals').innerText = h.pending_approvals_count || 0;

        // 2. Render Agents
        const agents = statusRes.agents || [];
        const agentRoles = {
          director: "Plans, delegates, supervises",
          research: "Market intel & data collection",
          engineering: "Builds tools & software",
          marketing: "Content strategy & audience",
          analytics: "KPIs & performance metrics",
          operations: "Recurring tasks & queue hygiene",
          quality: "Security audit & test verification"
        };
        const agentContainer = document.getElementById('agents-container');
        agentContainer.innerHTML = agents.map(a => `
          <div class="agent-pill">
            <div class="agent-name">
              <span>${a.agent.toUpperCase()}</span>
              <span class="badge ${a.health === 'active' ? 'badge-live' : 'badge-owner'}">${a.health}</span>
            </div>
            <div class="agent-role">${agentRoles[a.agent] || "Autonomous Employee"}</div>
            <div style="font-size: 11px; color: #94a3b8;">
              Tasks: <b>${a.completed}/${a.total_tasks}</b> (${a.success_rate_pct}%)<br>
              Avg Latency: <b>${a.avg_duration_sec}s</b>
            </div>
          </div>
        `).join('');

        // 3. Render Objectives
        const objContainer = document.getElementById('objectives-container');
        objContainer.innerHTML = (objRes || []).map(o => `
          <div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <b>${o.title}</b>
              <span class="badge badge-owner">${o.priority.toUpperCase()}</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin: 4px 0;">${o.description}</div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted);">
              <span>Assigned: ${o.target_agent}</span>
              <span>Progress: <b>${o.progress}%</b></span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${o.progress}%;"></div>
            </div>
          </div>
        `).join('');

        // 4. Render Approvals
        const apprContainer = document.getElementById('approvals-container');
        if (!apprRes || apprRes.length === 0) {
          apprContainer.innerHTML = '<div style="font-size: 13px; color: var(--text-muted);">No pending approvals. All actions cleared.</div>';
        } else {
          apprContainer.innerHTML = apprRes.map(ap => `
            <div style="padding: 10px; background: #1a2234; border-radius: 6px; margin-bottom: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <b>Level ${ap.permission_level}: ${ap.action_name}</b>
                <span class="badge badge-warning">Pending</span>
              </div>
              <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Requested by: <b>${ap.requested_by}</b></div>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-success" style="padding: 4px 10px; font-size: 11px;" onclick="reviewApproval('${ap.id}', 'approved')">Approve</button>
                <button class="btn btn-danger" style="padding: 4px 10px; font-size: 11px;" onclick="reviewApproval('${ap.id}', 'rejected')">Reject</button>
              </div>
            </div>
          `).join('');
        }

        // 5. Render Tasks Table
        const tasksBody = document.getElementById('tasks-table-body');
        tasksBody.innerHTML = (tasksRes || []).slice(0, 10).map(t => {
          let badgeClass = 'badge-warning';
          if (t.status === 'completed') badgeClass = 'badge-live';
          if (t.status === 'failed') badgeClass = 'badge-danger';
          return `
            <tr>
              <td><b>${t.owner_agent}</b></td>
              <td>${t.title}</td>
              <td><span class="badge ${badgeClass}">${t.status}</span></td>
              <td>${t.priority}</td>
              <td style="color: var(--text-muted); font-size: 11px;">${t.created_at ? t.created_at.split('T')[1].slice(0,8) : ''}</td>
            </tr>
          `;
        }).join('');

        // 6. Render Tools Catalog
        const toolsContainer = document.getElementById('tools-container');
        toolsContainer.innerHTML = (toolsRes || []).map(tl => `
          <div style="padding: 10px; background: #162032; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; font-size: 13px;">${tl.name} <span style="font-size: 10px; color: #38bdf8;">v${tl.version}</span></div>
              <div style="font-size: 11px; color: var(--text-muted);">${tl.description}</div>
            </div>
            <span class="badge badge-live">Approved (L${tl.permission_level})</span>
          </div>
        `).join('');

      } catch (err) {
        console.error("Dashboard refresh error:", err);
      }
    }

    async function triggerCycle() {
      const res = await fetch('/api/cycle/run', { method: 'POST' });
      const data = await res.json();
      alert(`Executive Cycle Completed in ${data.duration_seconds}s! Dispatched: ${data.tasks_dispatched}`);
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
      const title = prompt("Enter Strategic Objective Title:");
      if (!title) return;
      const description = prompt("Enter Objective Details / Context:");
      if (!description) return;
      await fetch('/api/objectives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, priority: "high" })
      });
      loadDashboard();
    }

    async function openNewTaskModal() {
      const agent = prompt("Target Agent (research, engineering, marketing, analytics, operations, quality):", "research");
      if (!agent) return;
      const title = prompt("Task Title:");
      if (!title) return;
      const description = prompt("Task Description:");
      await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_agent: agent, title, description, priority: "medium" })
      });
      loadDashboard();
    }

    async function openBuildToolModal() {
      const name = prompt("Tool Name (e.g. sentiment_analyzer, csv_validator):");
      if (!name) return;
      const description = prompt("What should this tool do?");
      if (!description) return;
      alert("Dispatching to Tool Factory Sandbox for synthesis and test verification...");
      const res = await fetch('/api/tools/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, category: "custom" })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Tool '${name}' successfully built, tested, and registered in catalog!`);
      } else {
        alert(`Tool build failed: ${data.error}`);
      }
      loadDashboard();
    }

    // Initial load and periodic refresh
    loadDashboard();
    setInterval(loadDashboard, 5000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
