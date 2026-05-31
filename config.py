import os

# ── Tradier ────────────────────────────────────────────────────────────────────
TRADIER_TOKEN = os.environ.get("TRADIER_TOKEN", "")
TRADIER_BASE  = "https://api.tradier.com/v1"

# ── Email ──────────────────────────────────────────────────────────────────────
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER", "")   # Gmail address you send FROM
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "") # Gmail App Password (16 chars)
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "") # Address to receive report

# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ── Watchlist by sector ────────────────────────────────────────────────────────
# SPX and NDX are cash indices — Tradier returns derived values, no premarket bid/ask
# SPY and QQQ are their tradeable ETF proxies with full premarket data

WATCHLIST = {
    "Indexes": {
        "tickers": ["SPY", "QQQ", "SPX", "NDX"],
        "notes": {
            "SPX": "derived",
            "NDX": "derived",
        }
    },
    "Semiconductors": {
        "tickers": ["NVDA", "AMD", "AVGO", "MU", "MRVL", "INTC", "QCOM",
                    "TXN", "ARM", "SNDK", "CEVA", "WOLF", "COHR"],
    },
    "Tech / Cloud / AI": {
        "tickers": ["MSFT", "META", "ORCL", "IBM", "NOW", "PLTR", "CRWD",
                    "APP", "CSCO", "VRT", "PENG", "NBIS", "CRWV", "TEM"],
    },
    "Networking / Comms": {
        "tickers": ["APH", "TE", "IREN", "ONDS", "AAOI", "TSSI", "ATXI"],
    },
    "Crypto Mining": {
        "tickers": ["MARA", "RIOT", "CLSK"],
    },
    "Aerospace": {
        "tickers": ["FLY"],
    },
    "Clean Energy": {
        "tickers": ["ENPH"],
    },
}

# Flat list for API calls
ALL_TICKERS = [t for sector in WATCHLIST.values() for t in sector["tickers"]]

# Tickers with no premarket bid/ask (cash indices)
DERIVED_TICKERS = {"SPX", "NDX"}

# ── Schedule (Central Time) ────────────────────────────────────────────────────
SNAPSHOT_TIME_CT = "03:00"   # 3AM CT = 4AM ET — premarket open bid/ask snapshot
LOI_TIME_CT      = "08:00"   # 8AM CT = 9AM ET — LOI snapshot 30 min before open
