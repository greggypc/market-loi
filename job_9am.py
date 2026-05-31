"""
8AM CT LOI Job
──────────────
Calculates Levels of Interest for every active ticker at 8AM CT
(30 minutes before the 9:30AM ET open).
Saves to Supabase: lois_9am, then sends the LOI email report.
"""

import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from tradier import get_quotes, get_prior_day_ohlc, get_premarket_range
from db import upsert_rows, get_watchlist
from email_report import send_report
from config import DERIVED_TICKERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")


def round_levels(price: float, step: float = 0.50, count: int = 4) -> list:
    """Generate nearby round-number support/resistance levels."""
    if not price:
        return []
    base   = round(round(price / step) * step, 2)
    levels = [round(base + i * step, 2) for i in range(-count, count + 1)]
    return sorted(levels)


def calc_loi(symbol: str, sector: str, is_derived: bool,
             snap_date: str, snap_ts: str) -> Optional[dict]:
    """Build the full LOI record for one ticker."""
    quotes = get_quotes([symbol])
    q = quotes.get(symbol, {})
    if not q:
        logger.warning(f"  {symbol}: no quote — skipping")
        return None

    last  = q.get("last") or q.get("close")
    bid   = q.get("bid")
    ask   = q.get("ask")
    prev  = q.get("prevclose")

    pd = get_prior_day_ohlc(symbol)
    pd_open  = pd["open"]  if pd else None
    pd_high  = pd["high"]  if pd else None
    pd_low   = pd["low"]   if pd else None
    pd_close = pd["close"] if pd else None

    pm = get_premarket_range(symbol, snap_date)
    pm_high = pm.get("high")
    pm_low  = pm.get("low")
    pm_open = pm.get("open")
    pm_vwap = pm.get("vwap")
    pm_note = pm.get("note")

    price_for_levels = float(last) if last else (float(pd_close) if pd_close else None)
    round_lvls = round_levels(price_for_levels) if price_for_levels else []

    pm_mid = (
        round((pm_high + pm_low) / 2, 4)
        if pm_high and pm_low else None
    )

    gap = gap_pct = None
    if pm_open and pd_close and float(pd_close) > 0:
        gap     = round(float(pm_open) - float(pd_close), 4)
        gap_pct = round((gap / float(pd_close)) * 100, 3)

    logger.info(
        f"  {symbol:<6}  last={str(last or 'N/A'):>10}  "
        f"pd_H={str(pd_high or 'N/A'):>10}  pd_L={str(pd_low or 'N/A'):>10}  "
        f"pm_H={str(pm_high or 'N/A'):>10}  pm_L={str(pm_low or 'N/A'):>10}  "
        f"gap={str(round(gap_pct,2)) + '%' if gap_pct else 'N/A':>8}"
    )

    return {
        "snap_date":     snap_date,
        "snap_ts":       snap_ts,
        "symbol":        symbol,
        "sector":        sector,
        "last":          float(last)     if last     else None,
        "bid":           float(bid)      if bid      else None,
        "ask":           float(ask)      if ask      else None,
        "prev_close":    float(prev)     if prev     else None,
        "pd_open":       pd_open,
        "pd_high":       pd_high,
        "pd_low":        pd_low,
        "pd_close":      pd_close,
        "pm_open":       pm_open,
        "pm_high":       pm_high,
        "pm_low":        pm_low,
        "pm_vwap":       pm_vwap,
        "pm_mid":        pm_mid,
        "gap":           gap,
        "gap_pct":       gap_pct,
        "round_levels":  ",".join(str(l) for l in round_lvls) if round_lvls else None,
        "is_derived":    is_derived,
        "note":          pm_note,
    }


def run_9am_loi():
    now       = datetime.now(CT)
    snap_date = now.strftime("%Y-%m-%d")
    snap_ts   = now.isoformat()

    logger.info(f"=== 8AM LOI Job starting — {snap_date} ===")

    watchlist = get_watchlist()
    if not watchlist:
        logger.error("Watchlist is empty — check Supabase watchlist table")
        return

    rows = []
    current_sector = None
    for entry in watchlist:
        if entry["sector"] != current_sector:
            current_sector = entry["sector"]
            logger.info(f"  [{current_sector}]")

        row = calc_loi(
            symbol     = entry["symbol"],
            sector     = entry["sector"],
            is_derived = entry.get("is_derived", False),
            snap_date  = snap_date,
            snap_ts    = snap_ts,
        )
        if row:
            rows.append(row)
        time.sleep(0.3)

    ok = upsert_rows("lois_9am", rows)
    logger.info(f"=== Saved {len(rows)} LOI rows — {'OK' if ok else 'FAILED'} ===")

    send_report(rows, snap_date)


if __name__ == "__main__":
    run_9am_loi()
