"""Deterministic synthetic minute bars for tests."""

import pandas as pd

TZ = "America/New_York"


def session(day: str, minutes: int = 390, price: float = 100.0, skip=()) -> pd.DataFrame:
    """Flat bars from 9:30 for `minutes` minutes, high/low 0.01 around `price`."""
    start = pd.Timestamp(day, tz=TZ) + pd.Timedelta("9h30min")
    idx = pd.date_range(start, periods=minutes, freq="min")
    idx = idx[[i not in skip for i in range(minutes)]]
    return pd.DataFrame(
        {"Open": price, "High": price + 0.01, "Low": price - 0.01, "Close": price, "Volume": 1000},
        index=idx,
    )


def days(*frames: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(frames)


def set_bar(df: pd.DataFrame, day: str, minute: int, o=None, h=None, low=None, c=None):
    """Overwrite OHLC of the bar `minute` minutes after 9:30 on `day`."""
    ts = pd.Timestamp(day, tz=TZ) + pd.Timedelta(minutes=9 * 60 + 30 + minute)
    for col, val in (("Open", o), ("High", h), ("Low", low), ("Close", c)):
        if val is not None:
            df.loc[ts, col] = val
    return df


def at(day: str, minute: int) -> pd.Timestamp:
    return pd.Timestamp(day, tz=TZ) + pd.Timedelta(minutes=9 * 60 + 30 + minute)
