import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import tickers, prices, sentiment, portfolio, opportunities, signals, market

app = FastAPI(
    title="EdgeBoard API",
    description="Market Intelligence Platform for Stock Traders",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow local dev + any Vercel deployment
_extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
_extra = [o.strip() for o in _extra_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://edgeboard-black.vercel.app",
        "https://*.vercel.app",
        *_extra,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(tickers.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(sentiment.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(opportunities.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(market.router, prefix="/api")


@app.get("/", tags=["health"])
def root():
    return {
        "app": "EdgeBoard API",
        "version": "0.1.0",
        "status": "running",
        "env": settings.app_env,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}