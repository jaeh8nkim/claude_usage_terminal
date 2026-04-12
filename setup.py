#!/usr/bin/env python3
"""One-time setup: open a dedicated Chrome, wait for the user to sign in
to claude.ai, auto-close once the session is detected."""
import os
os.environ["NODE_OPTIONS"] = "--no-deprecation"
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PROFILE = HERE / "chrome-profile"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9222
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")

GRAY = "\x1b[38;2;180;180;180m"
BLUE = "\x1b[38;2;64;117;208m"
RESET = "\x1b[0m"


def info(msg: str) -> None:
    print(GRAY + msg + RESET, flush=True)


def port_free() -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind(("127.0.0.1", PORT)); return True
        except OSError: return False


def wait_cdp(timeout=20.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    print(BLUE + "Claude Usage · Setup" + RESET)
    print()
    info("A Chrome window will open in a moment.")
    info("Sign in to claude.ai (your Anthropic account).")
    info("You do NOT need to sign in to Chrome itself — skip any Google prompts.")
    info("This window closes automatically once you're signed in to claude.ai.")
    print()

    PROFILE.mkdir(exist_ok=True)

    if not port_free():
        # Kill any prior dashboard-spawned Chrome.
        subprocess.run(["pkill", "-f", f"remote-debugging-port={PORT}"], check=False)
        time.sleep(1)

    proc = subprocess.Popen(
        [CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
         f"--user-agent={UA}", "--new-window", "https://claude.ai/login"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_cdp():
            info("Couldn't start Chrome. Try again.")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
            ctx = browser.contexts[0]
            info("Waiting for sign-in…")
            deadline = time.time() + 600  # 10 min cap
            while time.time() < deadline:
                time.sleep(2)
                cookies = ctx.cookies("https://claude.ai")
                names = {c["name"] for c in cookies}
                # claude.ai sets these once authenticated.
                if "sessionKey" in names or "lastActiveOrg" in names:
                    # Double-check by visiting the usage page.
                    page = ctx.new_page()
                    try:
                        page.goto("https://claude.ai/settings/usage",
                                  wait_until="domcontentloaded", timeout=30_000)
                        for _ in range(20):
                            page.wait_for_timeout(1000)
                            body = page.inner_text("body").lower()
                            if "plan usage limits" in body:
                                browser.close()
                                print()
                                info("✓ Signed in. You're all set.")
                                info("Launch Claude Usage.app to open the dashboard.")
                                return 0
                            if "log in" in body and "sign up" in body:
                                break
                    finally:
                        try: page.close()
                        except Exception: pass
            info("Timed out waiting for sign-in. Run setup again to retry.")
            return 1
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()


if __name__ == "__main__":
    sys.exit(main())
