# claude_usage_terminal

Terminal dashboard showing your Claude plan usage (current session %, weekly all-models %, with reset times), read from `claude.ai/settings/usage` in a headless Chrome.

## Setup (once)

Double-click **Setup Claude Usage.app**. A Chrome window opens on claude.ai — sign in with your Anthropic account. The window auto-closes when it detects a valid session. Setup also bootstraps a local Python venv and installs Playwright if missing.

You do **not** need to sign in to Chrome itself — skip any Google prompts.

## Use

Double-click **Claude Usage.app**. A terminal opens showing the dashboard, refreshing every 60s. `Ctrl-C` or close the window to quit. The launchers try iTerm first, fall back to Terminal.

If Claude ever signs you out of the dedicated profile, run **Setup Claude Usage.app** again.

## Files

- `setup.py` / `setup.command` / `Setup Claude Usage.app` — one-time sign-in.
- `dashboard.py` / `dashboard.command` / `Claude Usage.app` — the live dashboard.

## How it works

A headless Chrome is launched against a dedicated user-data-dir, loads the usage page, scrapes the visible text, parses session/weekly percentages, then shuts Chrome down. The dashboard wraps this in a loading screen (3-step progress) and a live TUI.

## Caveats

- `claude.ai/settings/usage` is a private page. Anthropic's ToS generally prohibits automated access; scripted reads of your own usage sit in a gray area. Keep polling infrequent (≥1 min). Don't share widely.
- If the page markup changes, the text-parsing heuristic may need updating.
- macOS only (AppleScript `.app` bundles, Chrome install path, iTerm/Terminal launchers).
- The dedicated Chrome profile is separate from your main Chrome — logins/extensions/history don't carry over.
