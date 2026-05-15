import os
import pickle
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
BASE_URL = "https://api.nasa.gov/neo/rest/v1"
CACHE_PATH = Path(__file__).parent.parent / "data" / "cache.pkl"


def _get(endpoint: str, params: dict) -> dict:
    params["api_key"] = NASA_API_KEY
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_feed(start_date: str, end_date: str) -> dict:
    """Fetch NEO close approach feed for a date range (max 7 days)."""
    return _get("feed", {"start_date": start_date, "end_date": end_date})


def get_browse(page: int = 0, size: int = 20) -> dict:
    """Fetch paginated NEO browse data including orbital information."""
    return _get("neo/browse", {"page": page, "size": size})


def get_cached_historical(months: int = 6) -> list[dict]:
    """
    Return cached historical feed data. Fetches and caches if not present.
    Collects `months` worth of weekly feed windows.
    """
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "rb") as f:
            return pickle.load(f)

    records = []
    end = datetime.utcnow().date()
    cursor = end - timedelta(weeks=months * 4)

    while cursor < end:
        window_end = min(cursor + timedelta(days=6), end)
        try:
            raw = get_feed(cursor.isoformat(), window_end.isoformat())
            records.append(raw)
        except Exception:
            pass
        cursor += timedelta(days=7)

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(records, f)

    return records
