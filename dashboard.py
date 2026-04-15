#!/usr/bin/env python3
"""Terminal dashboard for Claude usage."""
import os
os.environ["NODE_OPTIONS"] = "--no-deprecation"
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path(__file__).resolve().parent / "chrome-profile"
CACHE_DIR = Path.home() / ".cache" / "claude-usage-monitor"
CACHE_FILE = CACHE_DIR / "latest.json"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
URL = "https://claude.ai/settings/usage"
PORT = 9222
REFRESH = 50
REFRESH_DISPLAY = 60
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")

STEPS = [
    ("Booting headless browser", 3),
    ("Loading claude.ai", 4),
    ("Reading usage data", 3),
]
TOTAL_EST = sum(s[1] for s in STEPS)

BLUE = (64, 117, 208)
DIM = (40, 40, 40)
GRAY = (180, 180, 180)
DARK_GRAY = (110, 110, 110)
RED = (177, 20, 52)
RESET = "\x1b[0m"
HOME = "\x1b[H"
CLEAR_EOL = "\x1b[K"
CLEAR_EOS = "\x1b[J"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


def fg(r, g, b): return f"\x1b[38;2;{r};{g};{b}m"


def port_free() -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind(("127.0.0.1", PORT)); return True
        except OSError: return False


def wait_cdp(timeout=15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


class FetchJob:
    def __init__(self):
        self.step = 0          # 0 = not started, 1..3 = active, 4 = done
        self.result: dict | None = None
        self.error: str | None = None
        self.started = time.time()

    def run(self):
        try:
            if not port_free():
                self.error = "port 9222 in use"
                return
            self.step = 1
            proc = subprocess.Popen(
                [CHROME, f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
                 "--headless=new", "--disable-gpu",
                 "--disable-blink-features=AutomationControlled",
                 f"--user-agent={UA}", "--window-size=1280,900"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                if not wait_cdp():
                    self.error = "browser didn't start"
                    return
                self.step = 2
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
                    page = browser.contexts[0].new_page()
                    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
                    self.step = 3
                    for _ in range(30):
                        page.wait_for_timeout(1000)
                        if "plan usage limits" in page.inner_text("body").lower():
                            break
                    page.wait_for_timeout(1500)
                    body = page.inner_text("body")
                    browser.close()
            finally:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill()
            result = parse(body)
            if not result:
                low = body.lower()
                if "log in" in low and "sign up" in low:
                    self.error = "signed out — run Setup again"
                else:
                    self.error = "couldn't read usage page"
            else:
                self.result = result
            self.step = 4
        except Exception as e:
            self.error = str(e)


def parse(body: str) -> dict:
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    out = {}
    for i, ln in enumerate(lines):
        low = ln.lower()
        if low == "current session" and i + 2 < len(lines):
            out["session"] = (pct(lines[i+2]), lines[i+1])
        if low == "all models" and i + 2 < len(lines):
            out["week_all"] = (pct(lines[i+2]), lines[i+1])
    return out


def pct(s: str) -> int:
    m = re.match(r"(\d+)%", s)
    return int(m.group(1)) if m else 0


def bar_line(filled: int, empty: int, fill_color: tuple) -> str:
    return fg(*fill_color) + ("█" * filled) + fg(*DIM) + ("█" * empty) + RESET


def usage_bar(label: str, percent: int, reset_text: str, width: int) -> list[str]:
    header = f"{label}  {percent}% used  ·  {reset_text}"
    body_w = max(20, width)
    filled = int(round(body_w * percent / 100))
    return [fg(*GRAY) + header + RESET, bar_line(filled, body_w - filled, BLUE)]


def render_loading(job: FetchJob) -> None:
    cols = shutil.get_terminal_size((80, 24)).columns
    elapsed = int(time.time() - job.started)
    remaining = max(0, TOTAL_EST - elapsed)
    rows = [fg(*GRAY) + "Claude Usage" + RESET, ""]
    current_step = min(max(job.step, 1), len(STEPS))
    for i, (name, _) in enumerate(STEPS, start=1):
        if i < current_step:
            mark = "✓"
        elif i == current_step:
            mark = "›"
        else:
            mark = " "
        rows.append(fg(*GRAY) + f"  {mark}  step {i}/{len(STEPS)}  {name}" + RESET)
    rows.append("")
    rows.append(fg(*GRAY) + f"  about {remaining}s remaining (~{TOTAL_EST}s total)" + RESET)
    paint(rows)


def render_data(data: dict, last_fetch: float, error: str | None = None) -> None:
    cols = shutil.get_terminal_size((80, 24)).columns
    rows = [fg(*GRAY) + "Claude Usage" + RESET, ""]
    for key, title in [("session", "Current session"),
                       ("week_all", "Weekly limits")]:
        if key in data:
            p, r = data[key]
            rows.extend(usage_bar(title, p, r, cols))
            rows.append("")
    age = int(time.time() - last_fetch)
    if error:
        status = f"updated {age}s ago · fetch failed · refreshes every {REFRESH_DISPLAY}s · ctrl-c to quit"
        rows.append(fg(*RED) + status + RESET)
    else:
        status = f"updated {age}s ago · refreshes every {REFRESH_DISPLAY}s · ctrl-c to quit"
        rows.append(fg(*DARK_GRAY) + status + RESET)
    paint(rows)


def write_cache(data: dict, fetched_at: float) -> None:
    payload = {
        "fetched_at": fetched_at,
        "fetched_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(fetched_at)),
        "usage": {k: {"percent": p, "resets": r} for k, (p, r) in data.items()},
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(CACHE_FILE)


def paint(rows: list[str]) -> None:
    buf = HOME + "".join(r + CLEAR_EOL + "\n" for r in rows) + CLEAR_EOS
    sys.stdout.write(buf)
    sys.stdout.flush()


def main() -> int:
    sys.stdout.write("\x1b]0;Claude Usage\x07")
    sys.stdout.write(HIDE_CURSOR + "\x1b[2J")
    data: dict | None = None
    last_fetch = 0.0
    last_error: str | None = None
    try:
        while True:
            job = FetchJob()
            t = threading.Thread(target=job.run, daemon=True)
            t.start()
            while t.is_alive():
                if data is None:
                    render_loading(job)
                else:
                    render_data(data, last_fetch, last_error)
                time.sleep(0.25)
            if job.result:
                data = job.result
                last_fetch = time.time()
                last_error = None
                write_cache(data, last_fetch)
            elif job.error:
                last_error = job.error
            # Idle countdown until next refresh.
            next_fetch = time.time() + REFRESH
            while time.time() < next_fetch:
                if data is not None:
                    render_data(data, last_fetch, last_error)
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
