#!/bin/zsh
# One-shot setup for a fresh Mac: checks Python, installs dependencies, builds the Dock app.
# Usage: ./install.sh [--no-open]
set -e
cd "$(dirname "$0")"

say() { print -P "%F{blue}==>%f $1"; }
fail() { print -P "%F{red}Error:%f $1" >&2; exit 1; }

[[ "$(uname)" == "Darwin" ]] || fail "This app is for macOS only."

# On Apple Silicon, a Terminal set to "Open using Rosetta" reports x86_64 and mixes Intel and
# native Python builds, which breaks the app. Re-run this script natively so install and run agree.
if [[ -z "$PTS_NATIVE" && "$(sysctl -in hw.optional.arm64 2>/dev/null)" == "1" && "$(uname -m)" != "arm64" ]]; then
  say "Terminal is running in Intel (Rosetta) mode; restarting the installer natively..."
  exec env PTS_NATIVE=1 arch -arm64 /bin/zsh "$0" "$@"
fi
ARCH="$(uname -m)"

# --- 1. Find Python 3.10 or newer (macOS's built-in python3 is usually too old) ---
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  p="$(command -v $c 2>/dev/null || true)"
  [[ -n "$p" ]] || continue
  # Must be new enough AND built for this Mac's architecture (not an Intel-only Python on Apple Silicon).
  "$p" -c "import sys, platform; sys.exit(sys.version_info < (3, 10) or platform.machine() != '$ARCH')" 2>/dev/null && { PY="$p"; break; }
done

if [[ -z "$PY" ]]; then
  if command -v brew >/dev/null 2>&1; then
    say "Python 3.10+ not found. Installing it with Homebrew..."
    brew install python
    PY="$(command -v python3)"
  else
    fail "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/macos/ (or install Homebrew from https://brew.sh and re-run this script), then run ./install.sh again."
  fi
fi
say "Using $($PY --version) at $PY"

# --- 2. Virtual environment and dependencies ---
if [[ -d .venv ]] && ! .venv/bin/python -c "import sys, platform; sys.exit(sys.version_info < (3, 10) or platform.machine() != '$ARCH')" 2>/dev/null; then
  say "Existing .venv is unusable or built for a different architecture; recreating it."
  rm -rf .venv
fi
[[ -d .venv ]] || { say "Creating virtual environment..."; "$PY" -m venv .venv; }
say "Installing dependencies (this can take a minute)..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# --- 3. Verify the install actually works ---
.venv/bin/python -W ignore -c "import flask, pymupdf, gspread, google_auth_oauthlib; import parser, sheets" \
  || fail "Dependencies installed but the app could not be imported."

# --- 4. Build the Dock app ---
say "Building the Dock app..."
chmod +x run.command build_app.sh
./build_app.sh

DEST="${APP_DEST:-$HOME/Applications}"
print ""
say "Done. Installed: $DEST/PDF to Sheet.app"
print "  1. Drag it from the folder that opens onto your Dock."
print "  2. Click it. The first launch opens Settings with Google setup steps."
print ""
if [[ "$1" != "--no-open" ]]; then open "$DEST"; fi
