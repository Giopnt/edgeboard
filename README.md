# EdgeBoard 📊

**A full-stack market intelligence platform for stock traders.**

EdgeBoard combines portfolio risk analysis, news sentiment tracking, historical opportunity identification, and forward-looking signal scanning — all in one dashboard your trader friends will actually use every morning.

Built with Python, FastAPI, PostgreSQL, React, and yfinance. Runs on macOS with automated daily data pipelines.

---

## Features

| Feature | What it does |
|---|---|
| **Portfolio Risk Dashboard** | Live P&L, concentration analysis, drawdown scenarios, risk warnings |
| **Sentiment Engine** | Daily news headlines scored with NLP (VADER), stored per ticker |
| **Past Opportunity Identifier** | Historical pattern detection — RSI crossings, volume spikes, big moves, golden/death cross |
| **Signal Scanner** | Forward-looking setup detection across your watchlist |
| **Market Radar** | Autonomous scan of 25 popular stocks — expert-language insights, no hype |
| **Price Charts** | Interactive charts with 5D / 1M / 3M / 6M / YTD / 1Y / 2Y / MAX ranges |
| **Automation** | macOS launchd jobs fetch prices and sentiment every weekday morning at 7:30 AM |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API** | Python 3.11 + FastAPI + Pydantic |
| **Database** | PostgreSQL + SQLAlchemy ORM + Alembic migrations |
| **Data** | yfinance (prices) + NewsAPI (headlines) + VADER NLP (sentiment) |
| **Frontend** | React + Vite + Recharts |
| **Automation** | macOS launchd (weekday scheduled jobs) |
| **Testing** | pytest — 72 tests |

---

## Project Structure

```
edgeboard/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (tickers, prices, sentiment, portfolio, signals, opportunities, market)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (risk, sentiment, signals, opportunities, live radar)
│   │   ├── db/             # Database connection + session
│   │   └── core/           # Config + settings
│   ├── migrations/         # Alembic migration files
│   ├── tests/              # pytest test suite (72 tests)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/          # Dashboard, Watchlist, Portfolio, Signals, Opportunities, MarketRadar
│       ├── components/     # Shared UI components
│       └── api/            # Fetch wrappers for backend
├── scripts/
│   ├── fetch_prices.py     # Daily price ingestion
│   ├── fetch_news.py       # Daily sentiment ingestion
│   └── install_jobs.sh     # macOS launchd automation installer
└── logs/                   # Auto-created by install_jobs.sh
```

---

## Getting Started

### Prerequisites

```bash
# macOS
brew install python@3.11 postgresql@16 node git
brew services start postgresql@16
```

### Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/edgeboard.git
cd edgeboard

# 2. Create database
createdb edgeboard_dev

# 3. Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Environment variables
cp ../.env.example .env
# Edit .env — add your DATABASE_URL and NEWS_API_KEY
# Free NewsAPI key at https://newsapi.org

# 5. Run migrations
PYTHONPATH=. alembic upgrade head

# 6. Start API
uvicorn app.main:app --reload --port 8000
```

```bash
# 7. Frontend (new terminal tab)
cd frontend
npm install
npm run dev
```

- **API docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:5173

### Run tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

### Install automation (weekday data updates)

```bash
bash scripts/install_jobs.sh
```

Installs two macOS launchd jobs:
- **7:30 AM weekdays** — fetches latest prices for all watchlist tickers
- **7:45 AM weekdays** — fetches news headlines and scores sentiment

Logs saved to `logs/`.

To uninstall: `bash scripts/install_jobs.sh --remove`

---

## API Endpoints

### Tickers
```
GET    /api/tickers              List all tracked tickers
POST   /api/tickers              Add a ticker to watchlist
DELETE /api/tickers/{symbol}     Remove a ticker
```

### Prices
```
GET  /api/prices/{symbol}          Price history (supports ?days=N)
POST /api/prices/{symbol}/fetch    Fetch latest prices from yfinance
```

### Sentiment
```
GET  /api/sentiment/{symbol}           Daily sentiment history
GET  /api/sentiment/{symbol}/summary   7d avg, 30d avg, trend direction
POST /api/sentiment/{symbol}/fetch     Trigger news fetch + scoring
GET  /api/sentiment/{symbol}/headlines Raw headlines behind scores
```

### Portfolio
```
GET    /api/portfolio/risk         Full risk snapshot with live prices
GET    /api/portfolio/positions    All open positions with P&L
POST   /api/portfolio/positions    Add a position
DELETE /api/portfolio/positions/{id} Close a position
GET    /api/portfolio/summary      Quick value + P&L summary
```

### Signals
```
GET /api/signals                   Scan all watchlist tickers
GET /api/signals/{symbol}          Scan a single ticker
```

### Opportunities
```
POST /api/opportunities/{symbol}/scan   Scan 1 year of price history
GET  /api/opportunities/{symbol}/best   Top N biggest moves (supports ?limit=N)
GET  /api/opportunities/{symbol}/past   Full history with filters
GET  /api/opportunities/watchlist/summary  Best opportunity per ticker
```

### Market
```
GET /api/market/radar             Live scan of 25 popular stocks (no watchlist needed)
GET /api/market/radar/watchlist   Radar scoped to your watchlist
GET /api/market/popular           Curated stock list for autocomplete
```

---

## Environment Variables

```bash
# backend/.env
DATABASE_URL=postgresql://localhost/edgeboard_dev
NEWS_API_KEY=your_key_here   # Free at newsapi.org
APP_ENV=development
APP_PORT=8000
```

---

## License

MIT
