#!/bin/bash
# EdgeBoard — Git setup script
# Run this once to initialize git history and push to GitHub
#
# Usage:
#   bash scripts/git_setup.sh https://github.com/yourusername/edgeboard.git

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

REMOTE_URL=$1

if [ -z "$REMOTE_URL" ]; then
  echo "Usage: bash scripts/git_setup.sh https://github.com/yourusername/edgeboard.git"
  exit 1
fi

cd "$(dirname "$0")/.."

echo -e "${CYAN}Initializing git repository...${NC}"

git init
git add .
git commit -m "feat: initial EdgeBoard implementation

Full-stack market intelligence platform for stock traders.

Backend (Python/FastAPI/PostgreSQL):
- Ticker watchlist management
- Price history ingestion via yfinance
- News sentiment engine (NewsAPI + VADER NLP)
- Portfolio risk dashboard (live P&L, concentration, drawdown scenarios)
- Past opportunity identifier (RSI, volume spikes, golden/death cross, big moves)
- Forward-looking signal scanner
- Autonomous market radar (scans 25 stocks, no watchlist needed)
- Alembic migrations, 72 pytest tests

Frontend (React/Vite/Recharts):
- Dark trading terminal UI
- Interactive price charts (5D/1M/3M/6M/YTD/1Y/2Y/MAX)
- Watchlist with stock search + autocomplete
- Portfolio risk dashboard with concentration chart
- Signal scanner with strength indicators
- Market Radar with expert-language insights

Automation:
- macOS launchd jobs for daily price + sentiment updates
- Runs at 7:30 AM and 7:45 AM on weekdays"

git branch -M main
git remote add origin "$REMOTE_URL"
git push -u origin main

echo -e "${GREEN}✓ Pushed to $REMOTE_URL${NC}"
echo ""
echo "Your repo is live. Add these to your portfolio:"
echo "  • Pin the repo on your GitHub profile"
echo "  • Add a description: 'Full-stack market intelligence platform for stock traders'"
echo "  • Add topics: python fastapi postgresql react trading finance"
