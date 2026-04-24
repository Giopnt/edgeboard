#!/bin/bash
# EdgeBoard — Install macOS automation jobs
# Runs fetch_prices.py at 7:30 AM and fetch_news.py at 7:45 AM every weekday
#
# Usage:
#   bash scripts/install_jobs.sh          # Install jobs
#   bash scripts/install_jobs.sh --remove # Uninstall jobs

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}▸ $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

REMOVE=false
if [ "$1" == "--remove" ]; then REMOVE=true; fi

# Resolve paths
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="$PROJECT_DIR/scripts"
VENV_PYTHON="$PROJECT_DIR/backend/.venv/bin/python3"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$PROJECT_DIR/logs"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  EdgeBoard — Automation Jobs${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if $REMOVE; then
  log "Removing EdgeBoard automation jobs..."

  for job in com.edgeboard.fetch-prices com.edgeboard.fetch-news; do
    PLIST="$LAUNCH_AGENTS/$job.plist"
    if [ -f "$PLIST" ]; then
      launchctl unload "$PLIST" 2>/dev/null || true
      rm "$PLIST"
      ok "Removed $job"
    else
      warn "$job not found — skipping"
    fi
  done

  echo ""
  ok "Automation jobs removed."
  exit 0
fi

# Install mode
log "Checking prerequisites..."
[ -f "$VENV_PYTHON" ] || err "Virtual environment not found at $VENV_PYTHON. Run setup.sh first."
mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"
ok "Prerequisites OK"

install_job() {
  local LABEL=$1
  local PLIST_TEMPLATE="$SCRIPT_DIR/$LABEL.plist"
  local PLIST_DEST="$LAUNCH_AGENTS/$LABEL.plist"

  log "Installing $LABEL..."

  [ -f "$PLIST_TEMPLATE" ] || err "Template not found: $PLIST_TEMPLATE"

  # Replace placeholders with actual paths
  sed \
    -e "s|VENV_PYTHON_PLACEHOLDER|$VENV_PYTHON|g" \
    -e "s|SCRIPT_PATH_PLACEHOLDER|$SCRIPT_DIR|g" \
    -e "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_DIR|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

  # Unload first if already loaded
  launchctl unload "$PLIST_DEST" 2>/dev/null || true

  # Load the job
  launchctl load "$PLIST_DEST"
  ok "Installed $LABEL"
}

install_job "com.edgeboard.fetch-prices"
install_job "com.edgeboard.fetch-news"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Automation installed! 🎉${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Schedule:"
echo "  • 7:30 AM weekdays → fetch_prices.py (latest prices for all watchlist tickers)"
echo "  • 7:45 AM weekdays → fetch_news.py   (news + sentiment for all watchlist tickers)"
echo ""
echo "  Logs:"
echo "  • $LOG_DIR/fetch_prices.log"
echo "  • $LOG_DIR/fetch_news.log"
echo ""
echo "  To test manually right now:"
echo -e "  ${CYAN}cd $PROJECT_DIR/backend && source .venv/bin/activate${NC}"
echo -e "  ${CYAN}PYTHONPATH=. python ../scripts/fetch_prices.py${NC}"
echo -e "  ${CYAN}PYTHONPATH=. python ../scripts/fetch_news.py${NC}"
echo ""
echo "  To uninstall: bash scripts/install_jobs.sh --remove"
echo ""
