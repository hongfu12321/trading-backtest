"""Data-quality checks for stored bars. Problems are reported, never silently repaired."""

import json
from pathlib import Path

import pandas as pd

from trading_backtest import sessions
from trading_backtest.data.store import TZ


def validate(df: pd.DataFrame) -> dict:
    """Check bars in the stored schema (lowercase columns, `timestamp` column)."""
    ts = df["timestamp"]
    prices = df[["open", "high", "low", "close"]]
    invalid_ohlc = (
        (df.high < prices.max(axis=1)) | (df.low > prices.min(axis=1)) | (df.high < df.low)
    )

    stamps = pd.DatetimeIndex(ts.drop_duplicates())
    regular = stamps[sessions.in_session(stamps)]
    counts = pd.Series(1, index=regular).groupby(regular.date).sum()
    expected = (
        pd.Series(sessions.close_minute(regular), index=regular).groupby(regular.date).first()
    )
    short = counts[counts < expected]

    return {
        "rows": len(df),
        "first": str(ts.min()) if len(df) else None,
        "last": str(ts.max()) if len(df) else None,
        "timezone_ok": str(ts.dt.tz) == TZ,
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "unsorted": not ts.is_monotonic_increasing,
        "rows_with_missing_values": int(
            df[["open", "high", "low", "close", "volume"]].isna().any(axis=1).sum()
        ),
        "nonpositive_prices": int((prices <= 0).any(axis=1).sum()),
        "invalid_ohlc": int(invalid_ohlc.sum()),
        "negative_volume": int((df.volume < 0).sum()),
        "sessions": len(counts),
        "early_close_sessions": [str(d) for d in expected.index[expected == sessions.EARLY_CLOSE]],
        "weekend_sessions": [str(d) for d in counts.index if d.weekday() >= 5],
        "incomplete_sessions": {
            str(d): int(expected[d] - n) for d, n in short.items()
        },  # date -> missing regular-hours minutes
        "untradable_sessions": sorted({str(d) for d in regular[~sessions.tradable(regular)].date}),
    }


def write_report(df: pd.DataFrame, path: Path, **extra) -> dict:
    report = {**validate(df), **extra}
    path.write_text(json.dumps(report, indent=2))
    return report
