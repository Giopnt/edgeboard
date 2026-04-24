#!/bin/bash
# EdgeBoard — Mac Setup Script
# Run this once after cloning the repo: bash setup.sh

set -e  # Exit on any error

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log()  { echo -e "${CYAN}▸ $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  EdgeBoard — Development Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. Check Homebrew
log "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
ok "Homebrew ready"

# 2. Install system dependencies
log "Installing system dependencies (python, postgresql, node)..."
brew install python@3.11 postgresql@16 node git 2>/dev/null || true
ok "System dependencies ready"

# 3. Start PostgreSQL
log "Starting PostgreSQL..."
brew services start postgresql@16 2>/dev/null || true
sleep 2
ok "PostgreSQL running"

# 4. Create database
log "Creating database: edgeboard_dev..."
createdb edgeboard_dev 2>/dev/null || warn "Database may already exist — continuing"
ok "Database ready"

# 5. Python virtual environment
log "Setting up Python virtual environment..."
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
ok "Virtual environment activated"

# 6. Install Python deps
log "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Python dependencies installed"

# 7. Create .env
if [ ! -f .env ]; then
    log "Creating .env from example..."
    cp ../.env.example .env
    warn "⚠  Open backend/.env and add your NEWS_API_KEY (free at newsapi.org)"
else
    ok ".env already exists"
fi

# 8. Run migrations
log "Running database migrations..."
PYTHONPATH=$(pwd) alembic upgrade head
ok "Database schema created"

# 9. Run tests
log "Running tests..."
pip install pytest httpx -q
pytest tests/ -q
ok "All tests passed"

cd ..

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup complete! 🎉${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo "  1. Add your NEWS_API_KEY to backend/.env"
echo "  2. Start the API:"
echo ""
echo -e "     ${CYAN}cd backend${NC}"
echo -e "     ${CYAN}source .venv/bin/activate${NC}"
echo -e "     ${CYAN}uvicorn app.main:app --reload --port 8000${NC}"
echo ""
echo "  3. Open API docs: http://localhost:8000/docs"
echo ""
