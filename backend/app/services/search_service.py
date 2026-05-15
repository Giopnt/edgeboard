import logging
import yfinance as yf

from app.services.yf_session import get_history, get_ticker
from app.services.live_radar_service import _build_df, _scan_df, _generate_insight

logger = logging.getLogger(__name__)


def search_stocks(query: str) -> list[dict]:
    """Search for stocks worldwide by name or ticker."""
    try:
        from app.services.yf_session import get_session
        results = yf.Search(query, max_results=10, session=get_session())
        quotes = results.quotes if hasattr(results, 'quotes') else []
        stocks = []
        for q in quotes:
            symbol = q.get("symbol", "")
            name   = q.get("longname") or q.get("shortname") or symbol
            etype  = q.get("quoteType", "")
            if etype not in ("EQUITY", "ETF", ""):
                continue
            stocks.append({
                "symbol":   symbol,
                "name":     name,
                "exchange": q.get("exchange", ""),
                "type":     etype,
                "sector":   q.get("sector") or None,
            })
        return stocks[:8]
    except Exception as e:
        logger.error(f"Stock search failed for '{query}': {e}")
        return []


def live_scan_symbol(symbol: str) -> dict:
    """Fetch live data and run full signal detection on any stock ticker."""
    symbol = symbol.upper().strip()
    try:
        hist = get_history(symbol, period="6mo")

        if hist.empty:
            return {
                "symbol":  symbol,
                "has_data": False,
                "error":   f"No price data found for {symbol}. Check the ticker symbol is correct.",
                "signals": [],
                "insight": None,
            }

        try:
            ticker    = get_ticker(symbol)
            full_info = ticker.info
            name      = full_info.get("longName") or full_info.get("shortName") or symbol
            sector    = full_info.get("sector") or full_info.get("industry") or "—"
            currency  = full_info.get("currency", "USD")
            exchange  = full_info.get("exchange") or full_info.get("market", "")
        except Exception:
            name = symbol; sector = "—"; currency = "USD"; exchange = ""

        df   = _build_df(hist)
        scan = _scan_df(symbol, df)

        if scan is None:
            return {
                "symbol":        symbol,
                "name":          name,
                "sector":        sector,
                "has_data":      True,
                "signal_count":  0,
                "signals":       [],
                "summary":       f"No active signals for {symbol} right now — market appears neutral.",
                "insight":       None,
                "current_price": round(float(df.iloc[-1]["close"]), 4) if not df.empty else None,
                "currency":      currency,
                "exchange":      exchange,
                "as_of":         str(df.iloc[-1]["date"]) if not df.empty else None,
                "disclaimer":    "⚠ Pattern-based signals only. Not financial advice.",
            }

        meta    = {"name": name, "sector": sector}
        insight = _generate_insight(scan, meta)

        return {
            "symbol":        symbol,
            "name":          name,
            "sector":        sector,
            "currency":      currency,
            "exchange":      exchange,
            "has_data":      True,
            "as_of":         scan.get("as_of"),
            "current_price": scan.get("current_price"),
            "signal_count":  scan.get("signal_count", 0),
            "bullish_count": scan.get("bullish_count", 0),
            "bearish_count": scan.get("bearish_count", 0),
            "signals":       scan.get("signals", []),
            "summary":       insight["insight"] if insight else f"No strong signals for {symbol} right now.",
            "priority":      insight["priority"] if insight else "low",
            "tags":          insight["tags"] if insight else [],
            "insight":       insight,
            "disclaimer":    "⚠ Pattern-based signals only. Not financial advice.",
        }

    except Exception as e:
        logger.error(f"Live scan failed for {symbol}: {e}")
        return {"symbol": symbol, "has_data": False, "error": str(e), "signals": [], "insight": None}