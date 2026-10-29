#!/bin/zsh
# Double-click to start the app. First run creates the virtualenv and installs dependencies.
cd "$(dirname "$0")"
# On Apple Silicon always run natively so the venv and the app use the same architecture.
ARCH=()
[[ "$(sysctl -in hw.optional.arm64 2>/dev/null)" == "1" ]] && ARCH=(arch -arm64)
if [ ! -d .venv ]; then
  "${ARCH[@]}" python3 -m venv .venv && "${ARCH[@]}" .venv/bin/pip install -q -r requirements.txt
fi
exec "${ARCH[@]}" .venv/bin/python -W ignore app.py
