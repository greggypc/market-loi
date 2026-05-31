import requests
import logging
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


def _headers(prefer="return=minimal"):
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        prefer,
    }


# ── Watchlist CRUD ─────────────────────────────────────────────────────────────

def get_watchlist() -> list:
    """Return all active tickers from the watchlist table, ordered by sector."""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/watchlist",
            headers=_headers(),
            params={"active": "eq.true", "order": "sector,symbol"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        logger.error(f"get_watchlist failed: {e}")
        return []


def add_ticker(symbol: str, sector: str, is_derived: bool = False) -> bool:
    """Insert or re-activate a ticker in the watchlist."""
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/watchlist",
            headers=_headers("resolution=merge-duplicates,return=minimal"),
            json={"symbol": symbol.upper(), "sector": sector,
                  "is_derived": is_derived, "active": True},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"add_ticker({symbol}) failed: {e}")
        return False


def remove_ticker(symbol: str) -> bool:
    """Soft-delete a ticker by setting active=False."""
    try:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/watchlist",
            headers=_headers(),
            params={"symbol": f"eq.{symbol.upper()}"},
            json={"active": False},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"remove_ticker({symbol}) failed: {e}")
        return False


def ticker_exists_in_watchlist(symbol: str) -> bool:
    """Check if a ticker is already active in the watchlist."""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/watchlist",
            headers=_headers(),
            params={"symbol": f"eq.{symbol.upper()}",
                    "active": "eq.true",
                    "select": "symbol"},
            timeout=10,
        )
        r.raise_for_status()
        return len(r.json()) > 0
    except Exception as e:
        logger.error(f"ticker_exists_in_watchlist({symbol}) failed: {e}")
        return False


# ── Snapshot / LOI storage ─────────────────────────────────────────────────────

def upsert_rows(table: str, rows: list) -> bool:
    """Upsert a list of rows into a Supabase table."""
    if not rows:
        return True
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=_headers("resolution=merge-duplicates,return=minimal"),
            json=rows,
            timeout=20,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"upsert_rows({table}) failed: {e}")
        return False


def fetch_latest(table: str, snap_date: str) -> list:
    """Fetch all rows for a given snap_date."""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=_headers(),
            params={"snap_date": f"eq.{snap_date}", "order": "sector,symbol"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        logger.error(f"fetch_latest({table}) failed: {e}")
        return []
