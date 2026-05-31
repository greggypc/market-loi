"""
4AM CT Snapshot Job
───────────────────
Captures the bid, ask, last price and premarket context for every
ticker at the 4AM CT premarket open. Saves to Supabase table: snapshots_4am.
"""

import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from config import WATCHLIST, DERIVED_TICKERS
from tradier import get_quotes
from db import upsert_rows
from email_report import send_snapshot_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

CT = ZoneInfo("America/Chicago")


def run_4am_snapshot():
    now      = datetime.now(CT)
    snap_date = now.strftime("%Y-%m-%d")
    snap_ts   = now.isoformat()

    logger.info(f"=== 4AM Snapshot starting — {snap_date} ===")

    # Pull all quotes in one API call (Tradier supports comma-separated symbols)
    from config import ALL_TICKERS
    quotes = get_quotes(ALL_TICKERS)

    if not quotes:
        logger.error("No quotes returned — check TRADIER_TOKEN")
        return

    rows = []
    for sector_name, sector_data in WATCHLIST.items():
        for ticker in sector_data["tickers"]:
            q = quotes.get(ticker, {})
            if not q:
                logger.warning(f"  {ticker}: no quote data")
                continue

            bid   = q.get("bid")
            ask   = q.get("ask")
            last  = q.get("last") or q.get("close")
            prev  = q.get("prevclose")

            # Spread and midpoint
            spread  = round(float(ask) - float(bid), 4) if bid and ask else None
            midpoint = round((float(bid) + float(ask)) / 2, 4) if bid and ask else None

            is_derived = ticker in DERIVED_TICKERS
            note = "derived index — no premarket bid/ask" if is_derived else None

            row = {
                "snap_date":  snap_date,
                "snap_ts":    snap_ts,
                "symbol":     ticker,
                "sector":     sector_name,
                "bid":        float(bid)  if bid  else None,
                "ask":        float(ask)  if ask  else None,
                "spread":     spread,
                "midpoint":   midpoint,
                "last":       float(last) if last else None,
                "prev_close": float(prev) if prev else None,
                "is_derived": is_derived,
                "note":       note,
            }
            rows.append(row)
            logger.info(
                f"  {ticker:<6} bid={bid or 'N/A':>10}  ask={ask or 'N/A':>10}"
                f"  spread={spread or 'N/A':>7}  last={last or 'N/A':>10}"
            )
            time.sleep(0.1)  # gentle rate limiting

    ok = upsert_rows("snapshots_4am", rows)
    logger.info(f"=== Saved {len(rows)} rows to snapshots_4am — {'OK' if ok else 'FAILED'} ===")

    # Send the 3AM snapshot email
    send_snapshot_report(rows, snap_date)


if __name__ == "__main__":
    run_4am_snapshot()
