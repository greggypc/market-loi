"""
9AM CT LOI Job
──────────────
Calculates Levels of Interest for every ticker at 9AM CT (before the
9:30AM ET open). Saves to Supabase table: lois_9am, then triggers
the email report.
"""

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from config import WATCHLIST, ALL_TICKERS, DERIVED_TICKERS
from tradier import get_quotes, get_prior_day_ohlc, get_premarket_range
from db import upsert_rows
from email_report import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")


def round_levels(price: float, step: float = 0.50, count: int = 4) -> list[float]:
    """
    Generate nearby round-number support/resistance levels.
    Snaps to nearest `step` then returns count levels above and below.
    """
    if not price:
        return []
    base = round(round(price / step) * step, 2)
    levels = []
    for i in range(-count, count + 1):
        lvl = round(base + i * step, 2)
        levels.append(lvl)
    return sorted(levels)


def calc_loi(ticker: str, sector: str, snap_date: str, snap_ts: str) -> dict | None:
    """
    Build the full LOI record for one ticker.
    """
    # Current quote
    quotes = get_quotes([ticker])
    q = quotes.get(ticker, {})
    if not q:
        logger.warning(f"  {ticker}: no quote — skipping")
        return None

    last      = q.get("last") or q.get("close")
    bid       = q.get("bid")
    ask       = q.get("ask")
    prev      = q.get("prevclose")

    # Prior day OHLC
    pd = get_prior_day_ohlc(ticker)
    pd_open  = pd["open"]  if pd else None
    pd_high  = pd["high"]  if pd else None
    pd_low   = pd["low"]   if pd else None
    pd_close = pd["close"] if pd else None

    # Premarket range (4AM–9:29AM)
    pm = get_premarket_range(ticker, snap_date)
    pm_high  = pm.get("high")
    pm_low   = pm.get("low")
    pm_open  = pm.get("open")
    pm_vwap  = pm.get("vwap")
    pm_note  = pm.get("note")

    # Round number levels around current price
    price_for_levels = float(last) if last else (float(pd_close) if pd_close else None)
    round_lvls = round_levels(price_for_levels) if price_for_levels else []

    # Midpoint of premarket range = key intraday LOI
    pm_mid = (
        round((pm_high + pm_low) / 2, 4)
        if pm_high and pm_low else None
    )

    # Gap from prior close to premarket open
    gap = None
    gap_pct = None
    if pm_open and pd_close and pd_close > 0:
        gap     = round(float(pm_open) - float(pd_close), 4)
        gap_pct = round((gap / float(pd_close)) * 100, 3)

    is_derived = ticker in DERIVED_TICKERS

    row = {
        "snap_date":     snap_date,
        "snap_ts":       snap_ts,
        "symbol":        ticker,
        "sector":        sector,
        # Current
        "last":          float(last)      if last      else None,
        "bid":           float(bid)       if bid       else None,
        "ask":           float(ask)       if ask       else None,
        "prev_close":    float(prev)      if prev      else None,
        # Prior day
        "pd_open":       pd_open,
        "pd_high":       pd_high,
        "pd_low":        pd_low,
        "pd_close":      pd_close,
        # Premarket
        "pm_open":       pm_open,
        "pm_high":       pm_high,
        "pm_low":        pm_low,
        "pm_vwap":       pm_vwap,
        "pm_mid":        pm_mid,
        # Gap
        "gap":           gap,
        "gap_pct":       gap_pct,
        # Round levels stored as comma-separated string
        "round_levels":  ",".join(str(l) for l in round_lvls) if round_lvls else None,
        "is_derived":    is_derived,
        "note":          pm_note,
    }

    logger.info(
        f"  {ticker:<6}  last={last or 'N/A':>10}  "
        f"pd_H={pd_high or 'N/A':>10}  pd_L={pd_low or 'N/A':>10}  "
        f"pm_H={pm_high or 'N/A':>10}  pm_L={pm_low or 'N/A':>10}  "
        f"gap={gap_pct or 'N/A':>+8}%"
    )
    return row


def run_9am_loi():
    now       = datetime.now(CT)
    snap_date = now.strftime("%Y-%m-%d")
    snap_ts   = now.isoformat()

    logger.info(f"=== 9AM LOI Job starting — {snap_date} ===")

    rows = []
    for sector_name, sector_data in WATCHLIST.items():
        logger.info(f"  [{sector_name}]")
        for ticker in sector_data["tickers"]:
            row = calc_loi(ticker, sector_name, snap_date, snap_ts)
            if row:
                rows.append(row)
            time.sleep(0.3)  # gentle rate limiting across 44 tickers

    ok = upsert_rows("lois_9am", rows)
    logger.info(f"=== Saved {len(rows)} LOI rows — {'OK' if ok else 'FAILED'} ===")

    # Fire the email report
    send_report(rows, snap_date)


if __name__ == "__main__":
    run_9am_loi()
