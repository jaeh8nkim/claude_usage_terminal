# claude_usage_terminal

Terminal dashboard showing your Claude plan usage (current session %, weekly all-models %, with reset times), read from `claude.ai/settings/usage` in a headless Chrome.

## Setup (once)

Double-click **Setup Claude Usage.app**. A Chrome window opens on claude.ai — sign in. The window auto-closes when it detects a valid session. The setup also bootstraps a local Python venv and installs Playwright if missing.

## Use

Double-click **Claude Usage.app**. A terminal opens showing the dashboard, refreshing every 60s. `Ctrl-C` or close the window to quit.

If Claude ever signs you out of the dedicated profile (rare), run **Setup Claude Usage.app** again.

## Files

- `setup.py` / `setup.command` / `Setup Claude Usage.app` — one-time sign-in.
- `dashboard.py` / `dashboard.command` / `Claude Usage.app` — the live dashboard.
- `usage.py` — minimal one-shot script; prints the raw usage block. Useful for debugging.
- `chrome-profile/` (gitignored) — dedicated Chrome profile with your session cookies.
- `.venv/` (gitignored) — Python venv with Playwright.

## How it works

A headless Chrome is launched against a dedicated user-data-dir, loads the usage page, scrapes the visible text, parses session/weekly percentages, then shuts Chrome down. The dashboard wraps this in a loading screen (3-step progress) and a live TUI.

## Why it's built this way (the dead ends)

Several simpler approaches didn't work:

1. **Copy the main Chrome profile to a temp dir, run Playwright headless against it.** Fails on macOS — cookies are encrypted with a login-Keychain key; a Playwright-spawned Chrome can't decrypt them, so claude.ai sees no session.

2. **Attach via CDP to the user's running main Chrome** (`--remote-debugging-port=9222`). Fails since Chrome 136: a security mitigation refuses to bind the debug port on the default profile. You must use a non-default user-data-dir.

3. **Headless Chrome with the default User-Agent.** Cloudflare blocks it — the UA contains `HeadlessChrome`. The page gets stuck on "Performing security verification."

What works:

- Dedicated `chrome-profile/` directory (bypasses the Chrome 136 mitigation).
- User signs in to claude.ai once in that profile via the setup app.
- Subsequent runs spawn `--headless=new` Chrome against that profile with a spoofed normal User-Agent and `--disable-blink-features=AutomationControlled`. Cloudflare passes, session is valid, the page renders.

## Caveats

- `claude.ai/settings/usage` is a private page. Anthropic's ToS generally prohibits automated access; scripted reads of your own usage sit in a gray area. Keep polling infrequent (≥1 min). Don't share widely.
- If the page markup changes, the text-parsing heuristic may need updating.
- The dedicated Chrome profile is separate from your main Chrome — logins/extensions/history don't carry over.
