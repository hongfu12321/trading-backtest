import pandas as pd

from trading_backtest.data.massive import normalize
from trading_backtest.data.store import load_bars, save_bars


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
