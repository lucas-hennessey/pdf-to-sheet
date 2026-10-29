#!/bin/zsh
# Double-click to start the app. First run creates the virtualenv and installs dependencies.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python -W ignore app.py
