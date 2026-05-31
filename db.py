import requests
import logging
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


def _headers():
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def upsert_rows(table: str, rows: list[dict]) -> bool:
    """
    Upsert a list of rows into a Supabase table.
    Uses ON CONFLICT DO UPDATE (Prefer: resolution=merge-duplicates).
    """
    if not rows:
        return True
    headers = _headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            json=rows,
            timeout=20,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"upsert_rows({table}) failed: {e} — {getattr(e, 'response', {})}")
        return False


def fetch_latest(table: str, snap_date: str) -> list[dict]:
    """
    Fetch all rows for a given snap_date from a table.
    """
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


def fetch_recent_days(table: str, limit: int = 10) -> list[dict]:
    """
    Fetch the most recent N rows per symbol (for dashboard history).
    """
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=_headers(),
            params={"order": "snap_date.desc,sector,symbol", "limit": str(limit * 50)},
            timeout=15,
        )
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        logger.error(f"fetch_recent_days({table}) failed: {e}")
        return []
