"""Client for the Massive aggregates API, with resumable downloads."""

import logging
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from trading_backtest.data.store import COLUMNS, TZ, mark_completed, missing_ranges, save_bars

log = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com/v2/aggs/ticker"
CHUNK_DAYS = 30  # keeps each request under the 50k-bar limit for minute data
RATE_LIMIT_WAIT = 65
MAX_RETRIES = 5


class MassiveClient:
    def __init__(self, api_key: str, request_interval: float = 13.0):
        if not api_key:
            raise ValueError("MASSIVE_API_KEY is missing; set it in .env")
        self.api_key = api_key
        self.request_interval = request_interval
        self.session = requests.Session()

    def iter_chunks(
        self, symbol: str, start: date, end: date, multiplier: int = 1, timespan: str = "minute"
    ) -> Iterator[tuple[date, date, pd.DataFrame]]:
        """Yield (chunk_start, chunk_end, bars) for [start, end]; bars may be empty."""
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end)
            log.info("Downloading %s %s to %s", symbol, current, chunk_end)
            url = f"{BASE_URL}/{symbol}/range/{multiplier}/{timespan}/{current}/{chunk_end}"
            yield current, chunk_end, normalize(pd.DataFrame(self._fetch_rows(url)))
            current = chunk_end + timedelta(days=1)

    def _fetch_rows(self, url: str) -> list[dict]:
        rows = []
        # next_url already carries the query except the API key.
        params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc", "limit": 50000}
        while url:
            payload = self._get(url, params)
            rows.extend(payload.get("results") or [])
            url = payload.get("next_url")
            params = {"apiKey": self.api_key}
            time.sleep(self.request_interval)
        return rows

    def _get(self, url: str, params: dict) -> dict:
        """GET with retries: waits out rate limits, backs off on network and 5xx errors."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=60)
            except (requests.ConnectionError, requests.Timeout) as e:
                wait = 2**attempt
                log.warning("Network error (%s); retrying in %ss", e, wait)
            else:
                if response.status_code == 429:
                    wait = float(response.headers.get("Retry-After", RATE_LIMIT_WAIT))
                    log.warning("Rate limited; waiting %ss", wait)
                elif response.status_code >= 500:
                    wait = 2**attempt
                    log.warning("Server error %s; retrying in %ss", response.status_code, wait)
                else:
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("status") == "ERROR":
                        raise RuntimeError(payload)
                    return payload
            time.sleep(wait)
        raise RuntimeError(f"Giving up on {url} after {MAX_RETRIES} attempts")


def download(client: MassiveClient, symbol: str, start: date, end: date, path: Path) -> int:
    """Download missing ranges of [start, end] into `path`, saving each chunk as it lands.

    Interrupting loses at most the chunk in flight. Chunks ending today or later are saved
    but not marked complete, since the day's bars are not final yet. Returns bars saved.
    """
    saved = 0
    for gap_start, gap_end in missing_ranges(path, start, end):
        for chunk_start, chunk_end, bars in client.iter_chunks(symbol, gap_start, gap_end):
            if not bars.empty:
                save_bars(bars, path)
                saved += len(bars)
            if chunk_end < date.today():
                mark_completed(path, chunk_start, chunk_end)
    return saved


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert API rows to the standard bar schema with New York timestamps."""
    if raw.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = raw.rename(
        columns={
            "t": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(TZ)
    return (
        df[COLUMNS]
        .drop_duplicates(subset="timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
