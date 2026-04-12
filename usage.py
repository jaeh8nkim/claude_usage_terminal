#!/usr/bin/env python3
"""Read Claude plan usage — fully self-contained, invisible run.

Spawns headless Chrome against the dedicated profile, reads the page,
then kills Chrome. Nothing persists between runs.

First-time setup (once): run `bash launch_chrome.sh`, sign in to
claude.ai in the window that opens, then quit that Chrome. The profile
directory retains your session for all future headless runs.
"""
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path(__file__).resolve().parent / "chrome-profile"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "https://claude.ai/settings/usage"
PORT = 9222


def port_free(port: int) -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_cdp(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    if not PROFILE.exists():
        print(f"Profile missing at {PROFILE}. Run launch_chrome.sh and sign in first.", file=sys.stderr)
        return 2
    if not port_free(PORT):
        print(f"Port {PORT} in use — another Chrome already running with CDP?", file=sys.stderr)
        return 2

    proc = subprocess.Popen(
        [
            CHROME,
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={PROFILE}",
            "--headless=new",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,900",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_cdp():
            print("Chrome CDP did not come up.", file=sys.stderr)
            return 1

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
            ctx = browser.contexts[0]
            page = ctx.new_page()
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            for _ in range(30):
                page.wait_for_timeout(1000)
                txt = page.inner_text("body")
                low = txt.lower()
                if "plan usage limits" in low:
                    break
                if "security verification" in low or "just a moment" in low:
                    continue
            page.wait_for_timeout(2000)
            body = page.inner_text("body")
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # Extract the interesting lines.
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    out = []
    # Locate "Plan usage limits" block and take the next ~25 lines.
    for i, ln in enumerate(lines):
        if "plan usage limits" in ln.lower():
            out = lines[i : i + 30]
            break
    if not out:
        out = [ln for ln in lines if re.search(r"(%|reset|session|week|limit)", ln, re.I)]

    print("=" * 50)
    for ln in out:
        print(ln)
    print("=" * 50)
    if not out:
        print("[debug] raw body:")
        print(body[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
