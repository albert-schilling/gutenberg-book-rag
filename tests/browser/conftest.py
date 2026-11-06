"""Browser tests: the real app in headless Chromium, with the language model switched off (offline mode).

Setup, once:  uv run playwright install chromium
Run:          uv run pytest -m browser
They are skipped when Playwright or its browser is not installed.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def app_url(tmp_path_factory):
    """Start the Streamlit app with its own vector store and without Groq."""
    port = _free_port()
    env = {
        **os.environ,
        "BOOK_RAG_OFFLINE": "1",
        "BOOK_RAG_CHROMA_DIR": str(tmp_path_factory.mktemp("chroma")),
        "GROQ_API_KEY": "not-used-in-offline-mode",
    }
    log = (tmp_path_factory.mktemp("server") / "server.log").open("w")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                if urllib.request.urlopen(f"{url}/_stcore/health", timeout=1).read() == b"ok":
                    break
            except OSError:
                time.sleep(1)
        else:
            pytest.fail("The Streamlit app did not start")
        yield url
    finally:
        server.terminate()
        server.wait(timeout=20)


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch()
        except Exception as error:  # the browser is not installed
            pytest.skip(
                f"Chromium is not available ({str(error).splitlines()[0]}). Run: uv run playwright install chromium"
            )
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser, app_url):
    """A fresh browser session (a new Streamlit session) on the chat page of the app."""
    context = browser.new_context(viewport={"width": 1500, "height": 900})
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.goto(f"{app_url}/chat")  # the start screen lists the books; the tests use the chat
    page.wait_for_selector("textarea", timeout=90_000)
    yield page
    assert page.errors == [], f"JavaScript errors: {page.errors}"
    context.close()
