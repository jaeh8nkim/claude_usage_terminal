#!/usr/bin/env bash
cd "$(dirname "$0")"
clear
exec -a "Claude Usage" ./.venv/bin/python dashboard.py 2>/dev/null
