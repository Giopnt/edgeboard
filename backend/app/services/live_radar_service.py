import logging
import pandas as pd
import yfinance as yf

from app.services.opportunity_service import compute_rsi, compute_sma, compute_volume_zscore
from app.services.signal_service import (
    scan_rsi, scan_volume, scan_moving_average_trend, scan_price_momentum
)

logger = logging.getLogger(__name__)

# These are scanned automatically — no watchlist needed
RADAR_UNIVERSE = [
    {"symbol": "AAPL",  "name": "Apple",                "sector": "Technology"},
    {"symbol": "NVDA",  "name": "NVIDIA",               "sector": "Technology"},
    {"symbol": "MSFT",  "name": "Microsoft",            "sector": "Technology"},
    {"symbol": "TSLA",  "name": "Tesla",                "sector": "EV / Auto"},
    {"symbol": "AMD",   "name": "AMD",                  "sector": "Technology"},
    {"symbol": "META",  "name": "Meta Platforms",       "sector": "Tech / Social"},
    {"symbol": "AMZN",  "name": "Amazon",               "sector": "E-Commerce / Cloud"},
    {"symbol": "GOOGL", "name": "Alphabet",             "sector": "Tech / Ads"},
    {"symbol": "NFLX",  "name": "Netflix",              "sector": "Streaming"},
    {"symbol": "PLTR",  "name": "Palantir",             "sector": "AI / Data"},
    {"symbol": "CRWD",  "name": "CrowdStrike",          "sector": "Cybersecurity"},
    {"symbol": "PANW",  "name": "Palo Alto Networks",   "sector": "Cybersecurity"},
    {"symbol": "COIN",  "name": "Coinbase",             "sector": "Crypto / Fintech"},
    {"symbol": "SQ",    "name": "Block Inc.",           "sector": "Fintech"},
    {"symbol": "SHOP",  "name": "Shopify",              "sector": "E-Commerce"},
    {"symbol": "UBER",  "name": "Uber",                 "sector": "Transport / Tech"},
    {"symbol": "SNOW",  "name": "Snowflake",            "sector": "Cloud / Data"},
    {"symbol": "MU",    "name": "Micron Technology",    "sector": "Semiconductors"},
    {"symbol": "QCOM",  "name": "Qualcomm",             "sector": "Semiconductors"},
    {"symbol": "JPM",   "name": "JPMorgan Chase",       "sector": "Financials"},
    {"symbol": "GS",    "name": "Goldman Sachs",        "sector": "Financials"},
    {"symbol": "LLY",   "name": "Eli Lilly",            "sector": "Healthcare / Pharma"},
    {"symbol": "WMT",   "name": "Walmart",              "sector": "Retail"},
    {"symbol": "XOM",   "name": "ExxonMobil",           "sector": "Energy"},
    {"symbol": "NOW",   "name": "ServiceNow",           "sector": "Enterprise SaaS"},
]


def _build_df(hist: pd.DataFrame) -> pd.DataFrame:
    """Build a signal-ready DataFrame from yfinance history."""
    if hist.empty or len(hist) < 30:
        return pd.DataFrame()

    df = pd.DataFrame({
        "date":       [ts.date() for ts in hist.index],
        "open":       hist["Open"].values.tolist(),
        "high":       hist["High"].values.tolist(),
        "low":        hist["Low"].values.tolist(),
        "close":      [float(v) for v in hist["Close"].values],
        "volume":     [float(v) for v in hist["Volume"].values],
        "pct_change": hist["Close"].pct_change().mul(100).values.tolist(),
    })

    df["rsi"]          = compute_rsi(df["close"])
    df["sma20"]        = compute_sma(df["close"], 20)
    df["sma50"]        = compute_sma(df["close"], 50)
    df["volume_zscore"] = compute_volume_zscore(df["volume"].astype(float))
    return df


def _scan_df(symbol: str, df: pd.DataFrame) -> dict | None:
    """Run all signal detectors on a pre-built DataFrame."""
    if df.empty or len(df) < 20:
        return None

    latest = df.iloc[-1]
    signals = []

    for detector in [
        lambda: scan_rsi(df),
        lambda: scan_volume(df),
        lambda: scan_moving_average_trend(df),
        lambda: scan_price_momentum(df),
    ]:
        try:
            result = detector()
            if result:
                result["symbol"] = symbol
                signals.append(result)
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
    """Translate raw signals into expert-language insight."""
    signals    = scan["signals"]
    bullish    = [s for s in signals if s["direction"] == "bullish"]
    bearish    = [s for s in signals if s["direction"] == "bearish"]
    sig_types  = {s["signal_type"] for s in signals}

    priority = "low"
    insight  = ""
    tags     = []

    if len(bullish) >= 2:
        priority = "high"
        if "rsi_oversold" in sig_types and "ma_bullish_trend" in sig_types:
            insight = (
                f"{meta['name']} has pulled back into oversold RSI territory "
                f"while still trading above both key moving averages. "
                f"The trend hasn't broken — this is the kind of setup where patient traders pay attention. "
                f"Not a signal to chase, but worth watching for stabilization."
            )
            tags = ["Oversold in uptrend", "Trend intact", "Potential re-entry zone"]
        elif "rsi_oversold" in sig_types and "volume_spike" in sig_types:
            insight = (
                f"Heavy volume hitting {meta['name']} while RSI sits in oversold territory. "
                f"That combination — aggressive selling meeting high volume — can mark the point where "
                f"sellers exhaust themselves. Not a guarantee, but historically it draws buyers back in."
            )
            tags = ["Potential selling exhaustion", "High volume", "Watch for floor"]
        elif "price_momentum" in sig_types and "ma_bullish_trend" in sig_types:
            insight = (
                f"{meta['name']} is showing strong short-term price momentum with trend fully aligned — "
                f"price above the 20 and 50-day averages. When trend and momentum agree, "
                f"stocks tend to keep moving. Pullbacks into moving averages become opportunities."
            )
            tags = ["Momentum + trend aligned", "Breakout watch"]
        elif "volume_spike" in sig_types and "ma_bullish_trend" in sig_types:
            insight = (
                f"Unusual buying volume in {meta['name']} while it sits in a clean uptrend. "
                f"Volume spikes in the direction of the trend tend to signal institutional involvement. "
                f"Worth watching — if it holds the levels, it could be accumulation."
            )
            tags = ["Possible accumulation", "Trend + volume confirmation"]
        else:
            insight = (
                f"{meta['name']} has {len(bullish)} bullish signals active at the same time. "
                f"Multiple signals aligning in the same direction is notable — "
                f"it suggests more than one technical factor is supporting a move."
            )
            tags = ["Multiple bullish signals", "Worth investigating"]

    elif len(bearish) >= 2:
        priority = "high"
        if "rsi_overbought" in sig_types and "ma_bearish_trend" in sig_types:
            insight = (
                f"{meta['name']} is overbought on RSI while price is below both moving averages. "
                f"That combination rarely ends well in the short term. "
                f"If you're holding, know where your line in the sand is."
            )
            tags = ["Overbought in downtrend", "Risk elevated", "Know your stop"]
        elif "rsi_overbought" in sig_types and "price_momentum" in sig_types:
            insight = (
                f"Strong recent momentum has pushed {meta['name']} into overbought RSI. "
                f"After extended moves like this, the risk/reward shifts — "
                f"the easy part of the move is likely behind it. Chasing here carries elevated risk."
            )
            tags = ["Extended move", "Watch for exhaustion"]
        else:
            insight = (
                f"Multiple bearish signals aligning on {meta['name']}. "
                f"The technical picture is sending warning signs. "
                f"Not a reason to panic, but worth reducing risk or tightening stops if you're long."
            )
            tags = ["Multiple bearish signals", "Tighten risk management"]

    elif len(bullish) == 1 and len(bearish) == 1:
        priority = "medium"
        insight = (
            f"{meta['name']} is sending mixed signals — one bullish, one bearish. "
            f"The market is genuinely undecided here. "
            f"These situations usually resolve with a move in one direction — "
            f"patience is the right move until clarity emerges."
        )
        tags = ["Mixed signals", "Wait for resolution"]

    elif len(bullish) == 1:
        priority = "medium"
        st = bullish[0]["signal_type"]
        if st == "rsi_oversold":
            insight = (
                f"{meta['name']} RSI has dropped into oversold territory. "
                f"This alone isn't a reason to buy — oversold stocks can stay oversold. "
                f"But it does mean recent selling has been aggressive, and that aggression eventually exhausts. "
                f"Put it on your watchlist and look for stabilization."
            )
            tags = ["Oversold", "Potential bounce zone"]
        elif st == "ma_bullish_trend":
            insight = (
                f"{meta['name']} is in a clean uptrend — price above the 20 and 50-day moving averages. "
                f"No fireworks, no red flags. The trend is the trend. "
                f"Traders who follow structure would say this is the right side to be on until something breaks."
            )
            tags = ["Clean uptrend", "Trend-following setup"]
        elif st == "volume_spike":
            insight = (
                f"Unusually high volume hit {meta['name']} today. "
                f"Someone was in a hurry. Volume spikes are rarely random — "
                f"they usually mean informed participants are active. Watch what price does next."
            )
            tags = ["Unusual volume", "Watch for follow-through"]
        elif st == "price_momentum":
            insight = (
                f"{meta['name']} is showing strong short-term price momentum. "
                f"Momentum tends to persist in the near term — stocks in motion stay in motion. "
                f"Whether it's news-driven or technical, the tape is confirming strength."
            )
            tags = ["Strong momentum"]
        else:
            insight = f"An interesting setup is forming on {meta['name']}. Worth adding to your watchlist."
            tags = ["Setup forming"]

    elif len(bearish) == 1:
        priority = "medium"
        st = bearish[0]["signal_type"]
        if st == "rsi_overbought":
            insight = (
                f"{meta['name']} RSI has pushed into overbought. "
                f"Doesn't mean it reverses immediately — strong stocks can stay overbought. "
                f"But the odds of a smooth continuation are lower from here. "
                f"New entries carry elevated risk."
            )
            tags = ["Overbought", "Elevated entry risk"]
        elif st == "ma_bearish_trend":
            insight = (
                f"{meta['name']} is trading below both moving averages with the averages themselves trending down. "
                f"Technically, this is a no-touch until the structure changes. "
                f"Trying to catch a falling knife here rarely ends well."
            )
            tags = ["Downtrend", "Avoid until structure improves"]
        else:
            insight = (
                f"Bearish signal forming on {meta['name']}. "
                f"Not alarming on its own, but worth noting."
            )
            tags = ["Caution"]
    else:
        return None

    return {
        "symbol":         scan["symbol"],
        "name":           meta["name"],
        "sector":         meta["sector"],
        "current_price":  scan.get("current_price"),
        "priority":       priority,
        "insight":        insight,
        "tags":           tags,
        "bullish_signals": len(bullish),
        "bearish_signals": len(bearish),
        "signal_count":   len(signals),
        "as_of":          scan.get("as_of"),
        "raw_signals":    signals,
    }


def run_live_radar() -> dict:
    """
    Fetch live price data for RADAR_UNIVERSE via yfinance batch download.
    Run signal detectors and return expert-language insights.
    No database required — fully autonomous.
    """
    symbols = [s["symbol"] for s in RADAR_UNIVERSE]
    meta_map = {s["symbol"]: s for s in RADAR_UNIVERSE}

    logger.info(f"Live radar: downloading data for {len(symbols)} symbols...")

    insights = []
    failed = []

    # Download each ticker individually — more reliable than batch for mixed exchanges
    for sym in symbols:
        try:
            ticker_obj = yf.Ticker(sym)
            hist = ticker_obj.history(period="6mo")

            if hist.empty or len(hist) < 20:
                hist = ticker_obj.history(period="3mo")

            if hist.empty or len(hist) < 15:
                failed.append(sym)
                continue

            df = _build_df(hist)
            scan = _scan_df(sym, df)
            if scan is None:
                continue

            insight = _generate_insight(scan, meta_map[sym])
            if insight:
                insights.append(insight)

        except Exception as e:
            logger.error(f"Live radar scan failed for {sym}: {e}")
            failed.append(sym)

    # Sort: high priority first, then signal count
    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: (priority_order.get(x["priority"], 3), -x["signal_count"]))

    return {
        "scanned":     len(symbols) - len(failed),
        "with_signals": len(insights),
        "failed":      failed,
        "insights":    insights,
    }
