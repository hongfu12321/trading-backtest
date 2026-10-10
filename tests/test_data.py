import json
from datetime import date

import pandas as pd
import pytest
import requests

from trading_backtest.data import massive, store
from trading_backtest.data.massive import normalize
from trading_backtest.data.store import load_bars, save_bars
from trading_backtest.data.validation import validate


def make_raw(times_ms):
    n = len(times_ms)
    return pd.DataFrame(
        {
            "t": times_ms,
            "o": [1.0] * n,
            "h": [2.0] * n,
            "l": [0.5] * n,
            "c": [1.5] * n,
            "v": [10] * n,
        }
    )


# 2025-10-08 09:29 and 09:30 New York time, in epoch ms
PRE_OPEN = 1759930140000
OPEN = 1759930200000


def test_normalize_converts_timezone_and_dedupes():
    df = normalize(make_raw([OPEN, PRE_OPEN, OPEN]))
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert str(df.timestamp.dt.tz) == "America/New_York"
    assert df.timestamp.iloc[0].strftime("%H:%M") == "09:29"


def test_save_merges_and_load_filters_regular_hours(tmp_path):
    path = tmp_path / "X_minute.parquet"
    save_bars(normalize(make_raw([PRE_OPEN])), path)
    save_bars(normalize(make_raw([OPEN])), path)

    assert len(pd.read_parquet(path)) == 2
    bars = load_bars(path)
    assert list(bars.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(bars) == 1


# --- resumable downloads (HTTP mocked) ---


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self.payload, self.status_code, self.headers = payload or {}, status, headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)


class FakeSession:
    """Serves one bar at 10:00 on each chunk's first day; `script` overrides by call."""

    def __init__(self, script=None):
        self.urls, self.params, self.script = [], [], list(script or [])

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        self.params.append(params)
        if self.script:
            step = self.script.pop(0)
            if isinstance(step, BaseException):
                raise step
            if step is not None:
                return step
        chunk_start = url.rsplit("/", 2)[-2]
        ts = pd.Timestamp(chunk_start, tz="America/New_York") + pd.Timedelta("10h")
        bar = {"t": int(ts.timestamp() * 1000), "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 9}
        return FakeResponse({"results": [bar]})


@pytest.fixture
def client(monkeypatch):
    sleeps = []
    monkeypatch.setattr(massive.time, "sleep", sleeps.append)
    c = massive.MassiveClient("key", request_interval=0)
    c.session = FakeSession()
    c.sleeps = sleeps
    return c


JAN1, FEB28 = date(2025, 1, 1), date(2025, 2, 28)  # two 30-day chunks: Jan 1-30, Jan 31-Feb 28


def test_pagination_follows_next_url(client):
    page2 = f"{massive.BASE_URL}/QQQ/range/1/minute/2025-01-01/2025-01-05?cursor=2"
    client.session.script = [FakeResponse({"results": [], "next_url": page2}), None]
    chunks = list(client.iter_chunks("QQQ", JAN1, date(2025, 1, 5)))
    assert client.session.urls[1] == page2
    assert len(chunks) == 1


def test_api_key_is_sent_as_header_not_in_url():
    c = massive.MassiveClient("secret-key", request_interval=0)
    assert c.session.headers["Authorization"] == "Bearer secret-key"
    c.session = FakeSession()
    list(c.iter_chunks("QQQ", JAN1, date(2025, 1, 5)))
    assert "secret-key" not in repr((c.session.urls, c.session.params))


def test_rate_limit_and_network_errors_are_retried(client):
    client.session.script = [
        FakeResponse(status=429, headers={"Retry-After": "7"}),
        requests.ConnectionError("reset"),
        FakeResponse(status=503),
    ]
    [(_, _, bars)] = client.iter_chunks("QQQ", JAN1, date(2025, 1, 5))
    assert len(bars) == 1
    assert client.sleeps[:3] == [7.0, 2, 4]


def test_gives_up_after_max_retries(client):
    client.session.script = [FakeResponse(status=503)] * massive.MAX_RETRIES
    with pytest.raises(RuntimeError, match="Giving up"):
        list(client.iter_chunks("QQQ", JAN1, date(2025, 1, 5)))


def test_interrupted_download_keeps_finished_chunks_and_resumes(client, tmp_path):
    path = tmp_path / "QQQ_minute.parquet"
    client.session.script = [None, KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        massive.download(client, "QQQ", JAN1, FEB28, path)
    assert len(pd.read_parquet(path)) == 1
    assert store.completed_ranges(path) == [(JAN1, date(2025, 1, 30))]

    client.session.urls.clear()
    massive.download(client, "QQQ", JAN1, FEB28, path)
    assert [u.rsplit("/", 2)[-2] for u in client.session.urls] == ["2025-01-31"]
    assert store.completed_ranges(path) == [(JAN1, FEB28)]

    massive.download(client, "QQQ", JAN1, FEB28, path)  # nothing left to fetch
    assert len(client.session.urls) == 1
    assert len(pd.read_parquet(path)) == 2


def test_empty_range_is_recorded_as_downloaded(client, tmp_path):
    path = tmp_path / "QQQ_minute.parquet"
    client.session.script = [FakeResponse({"results": []})]
    massive.download(client, "QQQ", JAN1, date(2025, 1, 5), path)
    assert not path.exists()
    assert store.missing_ranges(path, JAN1, date(2025, 1, 10)) == [
        (date(2025, 1, 6), date(2025, 1, 10))
    ]


def test_failed_write_leaves_existing_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "X_minute.parquet"
    save_bars(normalize(make_raw([PRE_OPEN])), path)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
    with pytest.raises(OSError):
        save_bars(normalize(make_raw([OPEN])), path)
    monkeypatch.undo()
    assert len(pd.read_parquet(path)) == 1


# --- validation ---


def bars_frame(day, minutes, price=1.0):
    ts = pd.date_range(
        pd.Timestamp(day, tz="America/New_York") + pd.Timedelta("9h30min"),
        periods=minutes,
        freq="min",
    )
    return pd.DataFrame(
        {"timestamp": ts, "open": price, "high": price, "low": price, "close": price, "volume": 1}
    )


def test_validation_flags_bad_rows_and_short_sessions():
    df = pd.concat([bars_frame("2025-01-06", 390), bars_frame("2025-01-07", 300)])
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # duplicate, out of order
    df.loc[5, "high"] = 0.5  # high below open/close
    df.loc[6, "volume"] = -1
    report = validate(df)
    assert report["duplicate_timestamps"] == 1 and report["unsorted"]
    assert report["invalid_ohlc"] == 1 and report["negative_volume"] == 1
    assert report["incomplete_sessions"] == {"2025-01-07": 90}
    assert report["untradable_sessions"] == ["2025-01-07"]
    json.dumps(report)


def test_validation_handles_early_close_and_dst():
    # 2025-11-28 is an early close (after-hours bars to 16:00 included);
    # 2025-03-10 is the first session after DST starts.
    df = pd.concat([bars_frame("2025-11-28", 390), bars_frame("2025-03-10", 390)])
    df = df.sort_values("timestamp", ignore_index=True)
    report = validate(df)
    assert report["early_close_sessions"] == ["2025-11-28"]
    assert report["incomplete_sessions"] == {}
    assert report["untradable_sessions"] == []


def test_dst_timestamps_map_to_930_local():
    # 2025-03-10 09:30 EDT == 13:30 UTC (before DST it would be 14:30 UTC)
    utc_ms = int(pd.Timestamp("2025-03-10 13:30", tz="UTC").timestamp() * 1000)
    assert normalize(make_raw([utc_ms])).timestamp.iloc[0].strftime("%H:%M") == "09:30"
