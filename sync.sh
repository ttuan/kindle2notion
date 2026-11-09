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

# Colors only when stdout is a terminal and NO_COLOR (https://no-color.org) is unset.
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  BOLD=$'\e[1m'; DIM=$'\e[2m'; ITALIC=$'\e[3m'
  RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; CYAN=$'\e[36m'
  RESET=$'\e[0m'
else
  BOLD=""; DIM=""; ITALIC=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; CYAN=""; RESET=""
fi

info()  { echo "${BLUE}ℹ${RESET}  $*"; }
step()  { echo "${CYAN}▶${RESET}  ${BOLD}$*${RESET}"; }
ok()    { echo "${GREEN}✔${RESET}  $*"; }
warn()  { echo "${YELLOW}⚠${RESET}  $*" >&2; }
fail()  { echo "${RED}✖${RESET}  ${BOLD}${RED}$*${RESET}" >&2; }
hint()  { echo "   ${DIM}${ITALIC}$*${RESET}" >&2; }

cd "$REPO_DIR"

if [[ "${1:-}" == "--reinstall" ]]; then
  shift
  step "Removing ${DIM}$VENV_DIR${RESET}"
  rm -rf "$VENV_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  step "Creating Python environment at ${DIM}$VENV_DIR${RESET}"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q --upgrade pip
  "$VENV_DIR/bin/pip" install -q -r requirements.txt
  ok "Environment ready"
fi

if [[ ! -f .env ]]; then
  fail "Missing .env"
  hint "Copy .env.example to .env and fill it in."
  exit 1
fi

# Fail early with a clear message when the Kindle is not plugged in.
if [[ " $* " != *" --help "* ]]; then
  clippings="$(grep -E '^KINDLE_CLIPPINGS_PATH=' .env | cut -d= -f2- | sed -E "s/^[\"']//; s/[\"']$//")"
  if [[ -n "$clippings" && ! -f "$clippings" ]]; then
    fail "Clippings file not found: $clippings"
    hint "Plug in your Kindle and try again."
    exit 1
  fi
  echo
  echo "${BOLD}${CYAN}📚 kindle2notion${RESET} ${DIM}— syncing Kindle highlights to Notion${RESET}"
  echo
fi

exec "$VENV_DIR/bin/python" -m kindle2notion "$@"
