#!/usr/bin/env bash
cd "$(dirname "$0")"
clear
exec ./.venv/bin/python dashboard.py 2>/dev/null
