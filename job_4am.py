"""
3AM CT Snapshot Job
───────────────────
Captures bid, ask, spread, midpoint and last price for every active
ticker at the 3AM CT premarket open. Saves to Supabase: snapshots_4am.
Sends the 3AM snapshot email immediately after.
"""

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from tradier import get_quotes
from db import upsert_rows, get_watchlist
from email_report import send_snapshot_report
from config import DERIVED_TICKERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")


def run_4am_snapshot():
    now       = datetime.now(CT)
    snap_date = now.strftime("%Y-%m-%d")
    snap_ts   = now.isoformat()

    logger.info(f"=== 3AM Snapshot starting — {snap_date} ===")

    # Pull active watchlist from Supabase
    watchlist = get_watchlist()
    if not watchlist:
        logger.error("Watchlist is empty — check Supabase watchlist table")
        return

    all_symbols = [row["symbol"] for row in watchlist]
    sector_map  = {row["symbol"]: row["sector"]     for row in watchlist}
    derived_map = {row["symbol"]: row["is_derived"]  for row in watchlist}

    # Fetch all quotes in one API call
    quotes = get_quotes(all_symbols)
    if not quotes:
        logger.error("No quotes returned — check TRADIER_TOKEN")
        return

    rows = []
    for symbol in all_symbols:
        q = quotes.get(symbol, {})
        if not q:
            logger.warning(f"  {symbol}: no quote data")
            continue

        bid        = q.get("bid")
        ask        = q.get("ask")
        last       = q.get("last") or q.get("close")
        prev       = q.get("prevclose")
        is_derived = derived_map.get(symbol, symbol in DERIVED_TICKERS)
        spread     = round(float(ask) - float(bid), 4) if bid and ask else None
        midpoint   = round((float(bid) + float(ask)) / 2, 4) if bid and ask else None

        row = {
            "snap_date":  snap_date,
            "snap_ts":    snap_ts,
            "symbol":     symbol,
            "sector":     sector_map.get(symbol, "Other"),
            "bid":        float(bid)  if bid  else None,
            "ask":        float(ask)  if ask  else None,
            "spread":     spread,
            "midpoint":   midpoint,
            "last":       float(last) if last else None,
            "prev_close": float(prev) if prev else None,
            "is_derived": is_derived,
            "note":       "derived index — no premarket bid/ask" if is_derived else None,
        }
        rows.append(row)
        logger.info(
            f"  {symbol:<6}  bid={str(bid or 'N/A'):>10}  "
            f"ask={str(ask or 'N/A'):>10}  spread={str(spread or 'N/A'):>7}  "
            f"last={str(last or 'N/A'):>10}"
        )
        time.sleep(0.1)

    ok = upsert_rows("snapshots_4am", rows)
    logger.info(f"=== Saved {len(rows)} rows to snapshots_4am — {'OK' if ok else 'FAILED'} ===")

    send_snapshot_report(rows, snap_date)


if __name__ == "__main__":
    run_4am_snapshot()
