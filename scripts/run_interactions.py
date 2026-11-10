import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import threading
import uvicorn
from playwright.sync_api import sync_playwright

def run_server():
    from dashboard.app import app
    uvicorn.run(app, host="127.0.0.1", port=8098, log_level="warning")

def test_interactions():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)

    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://127.0.0.1:8098/...")
        page.goto("http://127.0.0.1:8098/", wait_until="networkidle")

        # 1. Test clicking "Profile" button for Engineering
        print("Testing Profile modal for Engineering...")
        page.click("#card-agent-engineering button:has-text('Profile')")
        page.wait_for_selector("#modal-agent-dossier.active", timeout=3000)
        assert page.is_visible("#modal-agent-dossier")
        print("Profile modal opened successfully!")
        page.click("#modal-agent-dossier .modal-close")
        page.wait_for_selector("#modal-agent-dossier", state="hidden", timeout=3000)

        # 2. Test clicking "Inspect" for latest output of Engineering
        print("Testing Inspect latest output for Engineering...")
        page.click("#card-agent-engineering button:has-text('Inspect')")
        # Should open modal-task-inspector if there is an output
        time.sleep(1)
        inspector_active = page.is_visible("#modal-task-inspector.active")
        print(f"Task inspector active: {inspector_active}")
        if inspector_active:
            page.click("#modal-task-inspector .modal-close")

        # 3. Test clicking "+ Objective"
        print("Testing + Objective modal...")
        page.click("button:has-text('+ Objective')")
        page.wait_for_selector("#modal-new-objective.active", timeout=3000)
        page.click("#modal-new-objective .modal-close")
        page.wait_for_selector("#modal-new-objective", state="hidden", timeout=3000)

        # 4. Test clicking "+ Dispatch Task"
        print("Testing + Dispatch Task modal...")
        page.click("button:has-text('+ Dispatch Task')")
        page.wait_for_selector("#modal-new-task.active", timeout=3000)
        page.click("#modal-new-task .modal-close")
        page.wait_for_selector("#modal-new-task", state="hidden", timeout=3000)

        # 5. Test clicking "+ Synthesize Tool"
        print("Testing + Synthesize Tool modal...")
        page.click("button:has-text('+ Synthesize Tool')")
        page.wait_for_selector("#modal-build-tool.active", timeout=3000)
        page.click("#modal-build-tool .modal-close")
        page.wait_for_selector("#modal-build-tool", state="hidden", timeout=3000)

        # 6. Test Task Inspector button from Tasks Table
        print("Testing Task Inspector from table...")
        inspect_btn = page.query_selector("#tasks-table-body button:has-text('Inspect')")
        if inspect_btn:
            inspect_btn.click()
            page.wait_for_selector("#modal-task-inspector.active", timeout=3000)
            page.click("#modal-task-inspector .modal-close")
            print("Task inspector from table opened successfully!")

        # 7. Test Tool Code viewer from Tools list
        print("Testing Tool Code viewer...")
        code_btn = page.query_selector("#tools-container button:has-text('Code')")
        if code_btn:
            code_btn.click()
            page.wait_for_selector("#modal-tool-code.active", timeout=3000)
            page.click("#modal-tool-code .modal-close")
            print("Tool Code modal opened successfully!")

        # 8. Test Chart metric switch
        print("Testing switchChartMetric...")
        page.click("button:has-text('Execution Latency')")
        time.sleep(1)
        page.click("button:has-text('Task Throughput')")
        time.sleep(1)

        print("Console errors detected:", console_errors)
        browser.close()

if __name__ == "__main__":
    test_interactions()
