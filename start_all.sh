#!/usr/bin/env bash
# =============================================================================
#  OpenGold — 1-Click Startup (macOS)
#  Starts: Gold API · Forex API · Gold Bot · Forex Bot · Next.js Dashboard
#
#  Usage:
#    chmod +x start_all.sh
#    ./start_all.sh
#
#  Requires: Terminal.app (default) or iTerm2 (auto-detected)
# =============================================================================

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv/bin/activate"

# ── Detect terminal emulator ──────────────────────────────────────────────────
if [[ "$TERM_PROGRAM" == "iTerm.app" ]] || osascript -e 'id of app "iTerm"' &>/dev/null 2>&1; then
  USE_ITERM=true
else
  USE_ITERM=false
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "  ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  ██████╗ ██╗     ██████╗ "
echo " ██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔═══██╗██║     ██╔══██╗"
echo " ██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ███╗██║   ██║██║     ██║  ██║"
echo " ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║██║     ██║  ██║"
echo " ╚██████╔╝██║     ███████╗██║ ╚████║╚██████╔╝╚██████╔╝███████╗██████╔╝"
echo "  ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝ "
echo ""
echo "  AI-Powered Gold & Forex Trading Bot"
echo ""

# ── Helper: open a new Terminal/iTerm window and run a command ─────────────────
# Usage: open_window <title> <command>
open_window() {
  local title="$1"
  local cmd="$2"

  if [[ "$USE_ITERM" == true ]]; then
    # iTerm2: open a new window via AppleScript
    osascript <<EOF
tell application "iTerm"
  create window with default profile
  tell current session of current window
    write text "printf '\\\\033]0;${title}\\\\007'; cd '${ROOT}'; source '${VENV}'; ${cmd}"
  end tell
end tell
EOF
  else
    # Terminal.app: open a new window via AppleScript
    osascript <<EOF
tell application "Terminal"
  do script "printf '\\\\033]0;${title}\\\\007'; cd '${ROOT}'; source '${VENV}'; ${cmd}"
  set custom title of front window to "${title}"
end tell
EOF
  fi
}

# ── 1. Gold API ───────────────────────────────────────────────────────────────
echo "[1/5] Starting Gold API  (port 8000)..."
open_window "gold api" "uvicorn src.api.app:app --host 127.0.0.1 --port 8000"
sleep 3

# ── 2. Forex API ──────────────────────────────────────────────────────────────
echo "[2/5] Starting Forex API (port 8001)..."
open_window "forex api" "ENV_FILE=forex.env uvicorn src.api.app:app --host 127.0.0.1 --port 8001"
sleep 3

# ── 3. Gold Bot ───────────────────────────────────────────────────────────────
echo "[3/5] Starting Gold Bot  (XAUUSDM M1)..."
open_window "gold bot" "python main.py"
sleep 2

# ── 4. Forex Bot ──────────────────────────────────────────────────────────────
echo "[4/5] Starting Forex Bot (GBPUSD M5)..."
open_window "forex bot" "python main.py --env forex.env"
sleep 2

# ── 5. Dashboard ──────────────────────────────────────────────────────────────
echo "[5/5] Starting Dashboard (http://localhost:3000)..."
if [[ "$USE_ITERM" == true ]]; then
  osascript <<EOF
tell application "iTerm"
  create window with default profile
  tell current session of current window
    write text "printf '\\\\033]0;dashboard\\\\007'; cd '${ROOT}/dashboard'; npm run dev"
  end tell
end tell
EOF
else
  osascript <<EOF
tell application "Terminal"
  do script "printf '\\\\033]0;dashboard\\\\007'; cd '${ROOT}/dashboard'; npm run dev"
  set custom title of front window to "dashboard"
end tell
EOF
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  All services starting in separate windows."
echo "  Dashboard → http://localhost:3000"
echo "  Gold API  → http://localhost:8000/docs"
echo "  Forex API → http://localhost:8001/docs"
echo ""
echo "  To stop: Cmd+Q Terminal / close each window individually."
echo ""
