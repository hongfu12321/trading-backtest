"""Client for the Massive aggregates API."""

import logging
import time
from datetime import date, timedelta

import pandas as pd
import requests

from trading_backtest.data.store import COLUMNS, TZ

log = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com/v2/aggs/ticker"
CHUNK_DAYS = 30  # keeps each request under the 50k-bar limit for minute data
RATE_LIMIT_WAIT = 65


class MassiveClient:
    def __init__(self, api_key: str, request_interval: float = 13.0):
        if not api_key:
            raise ValueError("MASSIVE_API_KEY is missing; set it in .env")
        self.api_key = api_key
        self.request_interval = request_interval
        self.session = requests.Session()

    def get_bars(
        self, symbol: str, start: date, end: date, multiplier: int = 1, timespan: str = "minute"
    ) -> pd.DataFrame:
        """Download bars for [start, end], paginating and chunking as needed."""
        frames = []
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end)
            log.info("Downloading %s %s to %s", symbol, current, chunk_end)
            url = f"{BASE_URL}/{symbol}/range/{multiplier}/{timespan}/{current}/{chunk_end}"
            frames.extend(self._fetch_pages(url))
            current = chunk_end + timedelta(days=1)

        if not frames:
            raise RuntimeError(f"No data returned for {symbol} {start}..{end}")
        return normalize(pd.concat(frames, ignore_index=True))

    def _fetch_pages(self, url: str) -> list[pd.DataFrame]:
        frames = []
        # next_url already carries the query except the API key.
        params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc", "limit": 50000}
        while url:
            response = self.session.get(url, params=params, timeout=60)
            if response.status_code == 429:
                log.warning("Rate limited; waiting %ss", RATE_LIMIT_WAIT)
                time.sleep(RATE_LIMIT_WAIT)
                continue
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "ERROR":
                raise RuntimeError(payload)
            if results := payload.get("results"):
                frames.append(pd.DataFrame(results))
            url = payload.get("next_url")
            params = {"apiKey": self.api_key}
            time.sleep(self.request_interval)
        return frames


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert API rows to the standard bar schema with New York timestamps."""
    df = raw.rename(
        columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(TZ)
    return (
        df[COLUMNS]
        .drop_duplicates(subset="timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
