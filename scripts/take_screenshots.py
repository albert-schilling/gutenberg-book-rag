"""Take the screenshots of the README (docs/images/) with a headless browser.

uv run playwright install chromium
uv run python scripts/take_screenshots.py            # real answers: needs the API key in .env
BOOK_RAG_OFFLINE=1 uv run python scripts/take_screenshots.py   # a fixed reply instead
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
QUESTION = "Why were the penguins reluctant to be the first to enter the water?"


def start(script: str, port: int) -> subprocess.Popen:
    command = [sys.executable, "-m", "streamlit", "run", script, "--server.headless=true", f"--server.port={port}"]
    server = subprocess.Popen(
        command, cwd=ROOT, env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    for _ in range(90):
        try:
            if urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1).read() == b"ok":
                return server
        except OSError:
            time.sleep(1)
    server.terminate()
    raise RuntimeError(f"{script} did not start")


def ask(page: Page) -> None:
    page.locator("textarea").first.fill(QUESTION)
    page.keyboard.press("Enter")
    page.get_by_text("Passage at position").first.wait_for(timeout=120_000)
    page.wait_for_timeout(500)


def desktop(page: Page, port: int) -> None:
    page.set_viewport_size({"width": 1440, "height": 860})
    page.goto(f"http://127.0.0.1:{port}")
    page.wait_for_selector("textarea", timeout=90_000)
    ask(page)
    page.get_by_text("Passage at position").first.click()
    page.get_by_role("button", name="Read in the book").first.click()
    page.wait_for_selector(".reader mark", timeout=30_000)
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "app-desktop.png")


def mobile(page: Page, port: int) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"http://127.0.0.1:{port}")
    page.wait_for_selector("textarea", timeout=90_000)
    ask(page)
    page.screenshot(path=OUT / "app-mobile.png")
    page.get_by_text("Passage at position").first.click()
    page.get_by_role("button", name="Read in the book").first.click()
    page.wait_for_selector(".reader mark", timeout=30_000)
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "app-mobile-reader.png")


def reports(page: Page, port: int) -> None:
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.goto(f"http://127.0.0.1:{port}")
    page.wait_for_selector("table, [data-testid='stDataFrame']", timeout=60_000)
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "reports.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        app = start("streamlit_app.py", 8811)
        try:
            desktop(browser.new_page(), 8811)
            mobile(browser.new_page(), 8811)
        finally:
            app.terminate()
        dashboard = start("streamlit_reports.py", 8812)
        try:
            reports(browser.new_page(), 8812)
        finally:
            dashboard.terminate()
        browser.close()


if __name__ == "__main__":
    main()
