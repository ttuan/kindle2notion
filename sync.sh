#!/usr/bin/env bash
# Sync Kindle highlights to Notion.
#
#   ./sync.sh                 sync using the settings in .env
#   ./sync.sh --help          show kindle2notion options
#   ./sync.sh --reinstall     rebuild the Python environment, then sync
#
# The first run creates a Python 3.13 virtualenv and installs dependencies.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${KINDLE2NOTION_VENV:-$HOME/.venv_3.13}"
PYTHON_BIN="${KINDLE2NOTION_PYTHON:-/opt/homebrew/bin/python3.13}"

cd "$REPO_DIR"

if [[ "${1:-}" == "--reinstall" ]]; then
  shift
  echo "Removing $VENV_DIR ..."
  rm -rf "$VENV_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating Python environment at $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q --upgrade pip
  "$VENV_DIR/bin/pip" install -q -r requirements.txt
fi

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill it in." >&2
  exit 1
fi

# Fail early with a clear message when the Kindle is not plugged in.
if [[ " $* " != *" --help "* ]]; then
  clippings="$(grep -E '^KINDLE_CLIPPINGS_PATH=' .env | cut -d= -f2- | sed -E "s/^[\"']//; s/[\"']$//")"
  if [[ -n "$clippings" && ! -f "$clippings" ]]; then
    echo "Clippings file not found: $clippings" >&2
    echo "Plug in your Kindle and try again." >&2
    exit 1
  fi
fi

exec "$VENV_DIR/bin/python" -m kindle2notion "$@"
