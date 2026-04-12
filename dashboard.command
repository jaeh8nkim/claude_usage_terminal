#!/usr/bin/env bash
cd "$(dirname "$0")"
clear
ln -f ./.venv/bin/python "./.venv/bin/Claude Usage" 2>/dev/null
exec "./.venv/bin/Claude Usage" dashboard.py 2>/dev/null
