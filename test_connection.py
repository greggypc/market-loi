"""
Quick connection test — run this locally before deploying to Railway.
Usage:
    export TRADIER_TOKEN=your_token_here
    python test_connection.py
"""

import os, sys
os.environ.setdefault("SUPABASE_URL", "placeholder")
os.environ.setdefault("SUPABASE_KEY", "placeholder")
os.environ.setdefault("EMAIL_SENDER", "placeholder")
os.environ.setdefault("EMAIL_PASSWORD", "placeholder")
os.environ.setdefault("EMAIL_RECEIVER", "placeholder")

from tradier import get_quotes, get_prior_day_ohlc, get_premarket_range

TEST_TICKERS = ["SPY", "QQQ", "NVDA", "MSFT"]

print("\n── Quote Test ───────────────────────────────────────────")
quotes = get_quotes(TEST_TICKERS)
if not quotes:
    print("❌  No quotes returned. Check your TRADIER_TOKEN.")
    sys.exit(1)

for sym, q in quotes.items():
    print(f"  {sym:<6}  bid={q.get('bid'):>10}  ask={q.get('ask'):>10}  "
          f"last={q.get('last'):>10}  prev={q.get('prevclose'):>10}")

print("\n── Prior Day OHLC Test ──────────────────────────────────")
for sym in TEST_TICKERS[:2]:
    pd = get_prior_day_ohlc(sym)
    if pd:
        print(f"  {sym:<6}  date={pd['date']}  "
              f"H={pd['high']}  L={pd['low']}  C={pd['close']}")
    else:
        print(f"  {sym:<6}  ❌ no history data")

print("\n── Premarket Range Test ─────────────────────────────────")
for sym in TEST_TICKERS[:2]:
    pm = get_premarket_range(sym)
    if pm.get("high"):
        print(f"  {sym:<6}  PM_H={pm['high']}  PM_L={pm['low']}  "
              f"VWAP={pm['vwap']}  bars={pm['bars']}")
    else:
        print(f"  {sym:<6}  note: {pm.get('note','no data')} "
              f"(expected outside premarket hours)")

print("\n✅  Tradier connection OK\n")
