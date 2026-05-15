import os
import logging
import pandas as pd

from app.services.opportunity_service import compute_rsi, compute_sma, compute_volume_zscore
from app.services.signal_service import (
    scan_rsi, scan_volume, scan_moving_average_trend, scan_price_momentum
)

logger = logging.getLogger(__name__)

RADAR_UNIVERSE = [
    {"symbol": "AAPL",  "name": "Apple",              "sector": "Technology"},
    {"symbol": "NVDA",  "name": "NVIDIA",             "sector": "Technology"},
    {"symbol": "MSFT",  "name": "Microsoft",          "sector": "Technology"},
    {"symbol": "TSLA",  "name": "Tesla",              "sector": "EV / Auto"},
    {"symbol": "AMD",   "name": "AMD",                "sector": "Technology"},
    {"symbol": "META",  "name": "Meta Platforms",     "sector": "Tech / Social"},
    {"symbol": "AMZN",  "name": "Amazon",             "sector": "E-Commerce"},
    {"symbol": "GOOGL", "name": "Alphabet",           "sector": "Tech / Ads"},
    {"symbol": "NFLX",  "name": "Netflix",            "sector": "Streaming"},
    {"symbol": "PLTR",  "name": "Palantir",           "sector": "AI / Data"},
    {"symbol": "CRWD",  "name": "CrowdStrike",        "sector": "Cybersecurity"},
    {"symbol": "COIN",  "name": "Coinbase",           "sector": "Crypto / Fintech"},
    {"symbol": "UBER",  "name": "Uber",               "sector": "Transport"},
    {"symbol": "SHOP",  "name": "Shopify",            "sector": "E-Commerce"},
    {"symbol": "JPM",   "name": "JPMorgan Chase",     "sector": "Financials"},
    {"symbol": "GS",    "name": "Goldman Sachs",      "sector": "Financials"},
    {"symbol": "LLY",   "name": "Eli Lilly",          "sector": "Healthcare"},
    {"symbol": "WMT",   "name": "Walmart",            "sector": "Retail"},
    {"symbol": "XOM",   "name": "ExxonMobil",         "sector": "Energy"},
    {"symbol": "NOW",   "name": "ServiceNow",         "sector": "Enterprise SaaS"},
    {"symbol": "MU",    "name": "Micron",             "sector": "Semiconductors"},
    {"symbol": "QCOM",  "name": "Qualcomm",           "sector": "Semiconductors"},
    {"symbol": "PANW",  "name": "Palo Alto Networks", "sector": "Cybersecurity"},
    {"symbol": "SQ",    "name": "Block Inc.",         "sector": "Fintech"},
    {"symbol": "SNOW",  "name": "Snowflake",          "sector": "Cloud / Data"},
]

# Use first 8 for hosted version (Alpha Vantage free = 25 req/day)
RADAR_ACTIVE = RADAR_UNIVERSE[:8]


def _get_price_data(symbol: str) -> pd.DataFrame:
    """
    Get price data — Alpha Vantage on hosted (no IP blocking),
    yfinance locally (no API key needed).
    """
    av_key = os.environ.get("ALPHA_VANTAGE_KEY") or os.environ.get("AV_KEY")

    if av_key:
        from app.services.av_service import get_daily_prices
        df = get_daily_prices(symbol, months=3)
        if not df.empty:
            return df

    # Fallback to yfinance (works locally, may fail on cloud)
    try:
        from app.services.yf_session import get_history
        hist = get_history(symbol, period="3mo")
        if hist.empty:
            return pd.DataFrame()
        return pd.DataFrame({
            "date":   [ts.date() for ts in hist.index],
            "open":   [float(v) for v in hist["Open"].values],
            "high":   [float(v) for v in hist["High"].values],
            "low":    [float(v) for v in hist["Low"].values],
            "close":  [float(v) for v in hist["Close"].values],
            "volume": [float(v) for v in hist["Volume"].values],
        })
    except Exception as e:
        logger.error(f"yfinance fallback failed for {symbol}: {e}")
        return pd.DataFrame()


def _build_df(price_df: pd.DataFrame) -> pd.DataFrame:
    if price_df.empty or len(price_df) < 15:
        return pd.DataFrame()
    df = price_df.copy()
    close = pd.Series(df["close"].values, dtype=float)
    df["pct_change"]    = close.pct_change().mul(100)
    df["rsi"]           = compute_rsi(close)
    df["sma20"]         = compute_sma(close, 20)
    df["sma50"]         = compute_sma(close, 50)
    df["volume_zscore"] = compute_volume_zscore(pd.Series(df["volume"].values, dtype=float))
    return df


def _scan_df(symbol: str, df: pd.DataFrame) -> dict | None:
    if df.empty or len(df) < 20:
        return None
    latest  = df.iloc[-1]
    signals = []
    for detector in [
        lambda: scan_rsi(df),
        lambda: scan_volume(df),
        lambda: scan_moving_average_trend(df),
        lambda: scan_price_momentum(df),
    ]:
        try:
            r = detector()
            if r:
                r["symbol"] = symbol
                signals.append(r)
        except Exception as e:
            logger.debug(f"{symbol} detector error: {e}")

    if not signals:
        return None

    bullish = [s for s in signals if s["direction"] == "bullish"]
    bearish = [s for s in signals if s["direction"] == "bearish"]
    return {
        "symbol":        symbol,
        "has_data":      True,
        "as_of":         str(latest["date"]),
        "current_price": round(float(latest["close"]), 2),
        "signal_count":  len(signals),
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "signals":       signals,
    }


def _generate_insight(scan: dict, meta: dict) -> dict | None:
    signals   = scan["signals"]
    bullish   = [s for s in signals if s["direction"] == "bullish"]
    bearish   = [s for s in signals if s["direction"] == "bearish"]
    sig_types = {s["signal_type"] for s in signals}
    priority = "low"; insight = ""; tags = []

    if len(bullish) >= 2:
        priority = "high"
        if "rsi_oversold" in sig_types and "ma_bullish_trend" in sig_types:
            insight = f"{meta['name']} has pulled back into oversold RSI while the trend remains intact above both moving averages. Patient traders pay attention to these setups."
            tags = ["Oversold in uptrend", "Trend intact"]
        elif "price_momentum" in sig_types and "ma_bullish_trend" in sig_types:
            insight = f"{meta['name']} shows strong momentum with price above both MAs — trend and momentum aligned. Pullbacks into MAs become opportunities."
            tags = ["Momentum + trend aligned"]
        elif "volume_spike" in sig_types and "ma_bullish_trend" in sig_types:
            insight = f"Unusual volume in {meta['name']} in a clean uptrend. Institutional involvement likely."
            tags = ["Possible accumulation"]
        else:
            insight = f"{meta['name']} has {len(bullish)} bullish signals aligning — notable."
            tags = ["Multiple bullish signals"]
    elif len(bearish) >= 2:
        priority = "high"
        if "rsi_overbought" in sig_types and "ma_bearish_trend" in sig_types:
            insight = f"{meta['name']} is overbought while below both moving averages. Risk is elevated here."
            tags = ["Overbought in downtrend", "Risk elevated"]
        else:
            insight = f"Multiple bearish signals on {meta['name']}. Technical picture is warning."
            tags = ["Multiple bearish signals"]
    elif len(bullish) == 1 and len(bearish) == 1:
        priority = "medium"
        insight = f"{meta['name']} has mixed signals — market undecided. Wait for resolution."
        tags = ["Mixed signals"]
    elif len(bullish) == 1:
        priority = "medium"
        st = bullish[0]["signal_type"]
        if st == "rsi_oversold":
            insight = f"{meta['name']} RSI is oversold. Aggressive selling eventually exhausts — watch for stabilization."
            tags = ["Oversold"]
        elif st == "ma_bullish_trend":
            insight = f"{meta['name']} is in a clean uptrend above both MAs. The trend is the trend until something breaks."
            tags = ["Clean uptrend"]
        elif st == "volume_spike":
            insight = f"Unusual volume on {meta['name']}. Someone was in a hurry — watch for follow-through."
            tags = ["Unusual volume"]
        else:
            insight = f"Strong momentum on {meta['name']}. Momentum tends to persist."
            tags = ["Strong momentum"]
    elif len(bearish) == 1:
        priority = "medium"
        st = bearish[0]["signal_type"]
        if st == "rsi_overbought":
            insight = f"{meta['name']} is overbought. New entries carry elevated risk."
            tags = ["Overbought"]
        else:
            insight = f"Bearish signal on {meta['name']}. Below both moving averages — avoid until structure improves."
            tags = ["Downtrend"]
    else:
        return None

    return {
        "symbol":          scan["symbol"],
        "name":            meta["name"],
        "sector":          meta["sector"],
        "current_price":   scan.get("current_price"),
        "priority":        priority,
        "insight":         insight,
        "tags":            tags,
        "bullish_signals": len(bullish),
        "bearish_signals": len(bearish),
        "signal_count":    len(signals),
        "as_of":           scan.get("as_of"),
        "raw_signals":     signals,
    }


def run_live_radar() -> dict:
    meta_map = {s["symbol"]: s for s in RADAR_ACTIVE}
    insights = []
    failed   = []

    for item in RADAR_ACTIVE:
        sym = item["symbol"]
        try:
            price_df = _get_price_data(sym)
            df       = _build_df(price_df)
            scan     = _scan_df(sym, df)
            if scan is None:
                continue
            insight = _generate_insight(scan, meta_map[sym])
            if insight:
                insights.append(insight)
        except Exception as e:
            logger.error(f"Radar failed for {sym}: {e}")
            failed.append(sym)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x["signal_count"]))

    return {
        "scanned":      len(RADAR_ACTIVE) - len(failed),
        "with_signals": len(insights),
        "failed":       failed,
        "insights":     insights,
    }