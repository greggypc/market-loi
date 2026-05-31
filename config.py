import os

# ── Tradier ────────────────────────────────────────────────────────────────────
TRADIER_TOKEN = os.environ.get("TRADIER_TOKEN", "")
TRADIER_BASE  = "https://api.tradier.com/v1"

# ── Email ──────────────────────────────────────────────────────────────────────
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "")

# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ── Tickers with no premarket bid/ask (cash indices) ──────────────────────────
# Watchlist is now stored in Supabase — the is_derived flag lives there too.
# This set is kept as a fast in-memory lookup for the Tradier client.
DERIVED_TICKERS = {"SPX", "NDX"}

# ── Available sectors (used in the Add Ticker dropdown) ───────────────────────
SECTORS = [
    "Indexes",
    "Semiconductors",
    "Tech / Cloud / AI",
    "Networking / Comms",
    "Crypto Mining",
    "Aerospace",
    "Clean Energy",
    "Other",
]

# ── Schedule (Central Time) ────────────────────────────────────────────────────
SNAPSHOT_TIME_CT = "03:00"   # 3AM CT = 4AM ET — premarket open bid/ask snapshot
LOI_TIME_CT      = "08:00"   # 8AM CT = 9AM ET — LOI snapshot 30 min before open
