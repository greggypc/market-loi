import requests
import logging
from datetime import datetime, timedelta
from typing import Optional
from config import TRADIER_BASE, DERIVED_TICKERS

logger = logging.getLogger(__name__)


def _headers():
    """Build headers fresh on every call so the token is always current."""
    from config import TRADIER_TOKEN
    return {
        "Authorization": f"Bearer {TRADIER_TOKEN}",
        "Accept": "application/json",
    }


def get_quotes(tickers: list) -> dict:
    """
    Fetch real-time quotes for a list of tickers.
    Returns dict keyed by symbol.
    """
    symbols = ",".join(tickers)
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/quotes",
            headers=_headers(),
            params={"symbols": symbols, "greeks": "false"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get("quotes", {}).get("quote", [])
        if isinstance(data, dict):
            data = [data]
        return {q["symbol"]: q for q in data if q}
    except Exception as e:
        logger.error(f"get_quotes failed: {e}")
        return {}


def get_timesales(ticker: str, interval: str = "1min",
                  start: str = None, end: str = None) -> list:
    """
    Fetch intraday time & sales bars.
    interval: 1min | 5min | 15min | tick
    start/end: 'YYYY-MM-DD HH:MM' format
    """
    params = {
        "symbol":         ticker,
        "interval":       interval,
        "session_filter": "all",  # includes premarket
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/timesales",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        series = r.json().get("series", {})
        if not series or series == "null":
            return []
        data = series.get("data", [])
        if isinstance(data, dict):
            data = [data]
        return data or []
    except Exception as e:
        logger.error(f"get_timesales({ticker}) failed: {e}")
        return []


def get_history(ticker: str, days_back: int = 5) -> list:
    """
    Fetch daily OHLCV history for the past N calendar days.
    """
    end_date   = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/history",
            headers=_headers(),
            params={
                "symbol":   ticker,
                "interval": "daily",
                "start":    start_date,
                "end":      end_date,
            },
            timeout=15,
        )
        r.raise_for_status()
        history = r.json().get("history", {})
        if not history or history == "null":
            return []
        days = history.get("day", [])
        if isinstance(days, dict):
            days = [days]
        return days or []
    except Exception as e:
        logger.error(f"get_history({ticker}) failed: {e}")
        return []


def get_prior_day_ohlc(ticker: str) -> Optional[dict]:
    """
    Returns the most recent completed trading day's OHLC.
    """
    days = get_history(ticker, days_back=7)
    if not days:
        return None
    d = days[-1]
    return {
        "date":   d.get("date"),
        "open":   float(d.get("open",  0)),
        "high":   float(d.get("high",  0)),
        "low":    float(d.get("low",   0)),
        "close":  float(d.get("close", 0)),
        "volume": int(d.get("volume",  0)),
    }


def verify_ticker(symbol: str) -> dict:
    """
    Check whether Tradier has data for a symbol.
    Returns a dict with keys: valid (bool), name, exchange, last, type, error.
    """
    symbol = symbol.upper().strip()
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/quotes",
            headers=_headers(),
            params={"symbols": symbol, "greeks": "false"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("quotes", {}).get("quote")

        if not data or data == "null":
            return {"valid": False, "error": f"Symbol '{symbol}' not found on Tradier"}

        if isinstance(data, list):
            data = data[0]

        last = data.get("last") or data.get("close") or data.get("prevclose")
        if last is None:
            return {"valid": False, "error": f"No price data available for '{symbol}'"}

        return {
            "valid":    True,
            "symbol":   data.get("symbol", symbol),
            "name":     data.get("description", ""),
            "exchange": data.get("exch", ""),
            "last":     float(last),
            "type":     data.get("type", ""),
            "error":    None,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def get_premarket_range(ticker: str, snapshot_date: str = None) -> dict:
    """
    Calculate premarket high, low, open (first bar), and VWAP
    from 3:00AM to 8:29AM CT using 1-minute bars.
    snapshot_date: 'YYYY-MM-DD', defaults to today
    """
    if ticker in DERIVED_TICKERS:
        return {"high": None, "low": None, "open": None, "vwap": None,
                "note": "derived index — no premarket bid/ask"}

    date = snapshot_date or datetime.now().strftime("%Y-%m-%d")

    # 3:00AM CT (= 4AM ET) is premarket open; capture through 8:29AM CT (= 9:29AM ET)
    start = f"{date} 03:00"
    end   = f"{date} 08:29"

    bars = get_timesales(ticker, interval="1min", start=start, end=end)
    if not bars:
        return {"high": None, "low": None, "open": None, "vwap": None,
                "note": "no premarket data"}

    highs   = [float(b["high"])  for b in bars]
    lows    = [float(b["low"])   for b in bars]
    volumes = [int(b["volume"])  for b in bars]

    total_vol = sum(volumes)
    weighted_vwap = (
        sum(float(b["vwap"]) * int(b["volume"]) for b in bars if b.get("vwap"))
        / total_vol
        if total_vol > 0 else None
    )

    return {
        "high": max(highs),
        "low":  min(lows),
        "open": float(bars[0]["open"]),
        "vwap": round(weighted_vwap, 4) if weighted_vwap else None,
        "bars": len(bars),
        "note": None,
    }
