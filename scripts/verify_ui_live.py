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
    uvicorn.run(app, host="127.0.0.1", port=8097, log_level="warning")

def main():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)

    console_messages = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("Navigating to dashboard...")
        page.goto("http://127.0.0.1:8097/", wait_until="networkidle")
        time.sleep(1.5)

        # Check title
        title = page.title()
        print(f"Page title: {title}")

        # Screenshot updated dashboard
        page.screenshot(path="dashboard_updated.png", full_page=True)
        print("Saved dashboard_updated.png")

        # Click on an artifact chip if present
        chips = page.query_selector_all(".chip-clickable")
        print(f"Found {len(chips)} clickable artifact chips")
        if chips:
            print("Clicking first artifact chip:", chips[0].inner_text())
            chips[0].click()
            page.wait_for_selector("#modal-file-viewer.active", timeout=4000)
            time.sleep(0.5)
            page.screenshot(path="modal_file_viewer.png")
            print("Saved modal_file_viewer.png")
            page.click("#modal-file-viewer .modal-close")
            page.wait_for_selector("#modal-file-viewer", state="hidden", timeout=3000)

        # Check profile modal
        page.click("#card-agent-engineering button:has-text('Profile')")
        page.wait_for_selector("#modal-agent-dossier.active", timeout=4000)
        time.sleep(0.5)
        page.screenshot(path="modal_agent_dossier.png")
        print("Saved modal_agent_dossier.png")
        page.click("#modal-agent-dossier .modal-close")
        page.wait_for_selector("#modal-agent-dossier", state="hidden", timeout=3000)

        # Filter console messages for errors
        errors = [m for m in console_messages if "[error]" in m.lower()]
        print("Console errors:", errors)
        print("Page runtime errors:", page_errors)
        assert len(page_errors) == 0, f"Page errors found: {page_errors}"

        browser.close()
        print("Verification finished successfully!")

if __name__ == "__main__":
    main()
