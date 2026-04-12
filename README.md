# claude_usage_terminal

A tiny macOS terminal dashboard that shows your Claude plan usage, scraped from `claude.ai/settings/usage` in a headless Chrome.

## Features

- Live terminal TUI with current session % and weekly all-models %
- Reset times for both session and weekly windows
- Auto-refreshes every 60s
- Writes `~/.cache/claude-usage-monitor/latest.json` so cron jobs / other scripts can read the latest values
- Double-clickable `.app` launchers (iTerm first, Terminal fallback)
- Dedicated Chrome profile — won't touch your main browser

## Install

1. Clone or download this folder.
2. Double-click **Setup Claude Usage.app**. A Chrome window opens on claude.ai — sign in with your Anthropic account. It auto-closes once a valid session is detected. Setup also creates a local Python venv and installs Playwright.
   - You do **not** need to sign in to Chrome itself — skip any Google prompts.
3. Double-click **Claude Usage.app** to launch the dashboard. `Ctrl-C` or close the window to quit.

If Claude signs you out, just run **Setup Claude Usage.app** again.

## Files

- `setup.py` / `setup.command` / `Setup Claude Usage.app` — one-time sign-in.
- `dashboard.py` / `dashboard.command` / `Claude Usage.app` — the live dashboard.

## Caveats

- `claude.ai/settings/usage` is a private page; scripted reads sit in a gray area of Anthropic's ToS. Keep polling infrequent and don't share widely.
- macOS only (AppleScript `.app` bundles, Chrome install path, iTerm/Terminal launchers).
- If the page markup changes, the text-parsing heuristic may need updating.
