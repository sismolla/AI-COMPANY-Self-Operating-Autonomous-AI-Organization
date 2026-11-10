"""Main CLI Entrypoint for AI-COMPANY.

Orchestrates the autonomous AI organization, background scheduler,
web dashboard, and command line operations.
"""

import sys
import asyncio
import logging
import argparse
from typing import Optional

from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ai_company")


async def run_cycle_cmd():
    """Execute a single executive cycle and print results."""
    from director.ceo import ceo
    await ceo.initialize()
    summary = await ceo.run_cycle()
    print("\n" + "="*50)
    print(" EXECUTIVE AUTONOMOUS CYCLE REPORT")
    print("="*50)
    for k, v in summary.items():
        print(f" {k.replace('_', ' ').capitalize():<30}: {v}")
    print("="*50 + "\n")


async def run_status_cmd():
    """Print current organizational status and metrics."""
    from director.ceo import ceo
    from infrastructure.monitoring import system_monitor
    from infrastructure.database import db

    await ceo.initialize()
    health = await system_monitor.get_company_health_summary()
    scorecards = await system_monitor.get_agent_scorecards()
    objectives = await db.get_objectives()

    print("\n" + "="*60)
    print(" AI-COMPANY STATUS & PERFORMANCE DASHBOARD")
    print("="*60)
    print(f" Health Status       : {health['status'].upper()}")
    print(f" Success Rate        : {health['success_rate_pct']}%")
    print(f" Total Tasks         : {health['total_tasks']} (Completed: {health['completed_tasks']}, Failed: {health['failed_tasks']})")
    print(f" Pending Approvals   : {health['pending_approvals_count']}")
    print(f" Approved Tools      : {health['approved_tools_count']}")
    print(f" Active Objectives   : {len(objectives)}")

    print("\n--- Division Scorecards ---")
    for s in scorecards:
        print(f" • {s['agent'].upper():<14} | Health: {s['health']:<6} | Tasks: {s['completed']}/{s['total_tasks']} ({s['success_rate_pct']}%) | Avg Latency: {s['avg_duration_sec']}s")

    print("\n--- Strategic Objectives ---")
    for o in objectives:
        print(f" • [{o['id']}] {o['title']:<40} | Progress: {o['progress']}% | Status: {o['status']}")
    print("="*60 + "\n")


async def run_objective_cmd(title: str, description: Optional[str] = None):
    """Submit a strategic objective from CLI."""
    from director.ceo import ceo
    await ceo.initialize()
    desc = description or f"Execute objective: {title}"
    res = await ceo.submit_owner_objective(title=title, description=desc)
    print(f"\n[SUCCESS] Injected Objective {res['objective']['id']}: '{title}'")
    print(f"Director decomposed objective into {res['subtasks_created']} agent subtasks.\n")


async def run_build_tool_cmd(name: str, description: str):
    """Autonomously synthesize and test a new tool."""
    from director.ceo import ceo
    from tool_factory.builder import tool_builder
    await ceo.initialize()
    print(f"\n[TOOL FACTORY] Synthesizing tool '{name}'...")
    res = await tool_builder.build_tool_from_specification(
        name=name,
        description=description,
        category="custom",
        author_agent="engineering"
    )
    if res.get("success"):
        print(f"[SUCCESS] Tool '{name}' passed sandbox AST verification & unit tests and is approved!")
    else:
        print(f"[FAILED] Tool build failed: {res.get('error')}")


def run_server():
    """Launch FastAPI dashboard and autonomous background loop."""
    import uvicorn
    print("\n" + "="*60)
    print(" STARTING AUTONOMOUS AI-COMPANY SERVICE")
    print(f" Web Dashboard : http://{settings.HOST}:{settings.PORT}")
    print(f" Database       : {settings.DB_PATH}")
    print(f" LLM Provider   : {settings.LLM_PROVIDER}")
    print("="*60 + "\n")
    uvicorn.run("dashboard.app:app", host=settings.HOST, port=settings.PORT, reload=False)


def main():
    parser = argparse.ArgumentParser(description="AI-COMPANY Autonomous Management System")
    subparsers = parser.add_subparsers(dest="command")

    # Start command
    subparsers.add_parser("start", help="Start web dashboard and autonomous background loop")

    # Cycle command
    subparsers.add_parser("cycle", help="Execute one autonomous executive cycle")

    # Status command
    subparsers.add_parser("status", help="Show system status and agent metrics")

    # Objective command
    obj_parser = subparsers.add_parser("objective", help="Submit a new strategic objective")
    obj_parser.add_argument("title", help="Objective title")
    obj_parser.add_argument("--description", "-d", help="Objective details", default=None)

    # Build-tool command
    tool_parser = subparsers.add_parser("build-tool", help="Commission tool factory to build a new tool")
    tool_parser.add_argument("name", help="Tool name")
    tool_parser.add_argument("description", help="Tool purpose and description")

    args = parser.parse_args()

    if args.command == "start" or args.command is None:
        run_server()
    elif args.command == "cycle":
        asyncio.run(run_cycle_cmd())
    elif args.command == "status":
        asyncio.run(run_status_cmd())
    elif args.command == "objective":
        asyncio.run(run_objective_cmd(args.title, args.description))
    elif args.command == "build-tool":
        asyncio.run(run_build_tool_cmd(args.name, args.description))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
