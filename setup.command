#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
clear

GRAY=$'\e[38;2;180;180;180m'
BLUE=$'\e[38;2;64;117;208m'
RESET=$'\e[0m'

# Bootstrap venv + playwright if missing.
if [ ! -x ./.venv/bin/python ]; then
  printf "%sSetting up Python environment…%s\n" "$GRAY" "$RESET"
  python3 -m venv .venv >/dev/null 2>&1
  ./.venv/bin/pip install -q playwright >/dev/null 2>&1
fi

exec ./.venv/bin/python setup.py 2>/dev/null
