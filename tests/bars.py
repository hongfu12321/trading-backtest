"""Deterministic synthetic minute bars for tests."""

import numpy as np
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


def random_days(dates, seed=0, pre=10, post=10, skip=None) -> pd.DataFrame:
    """Random-walk bars for each date, including `pre`/`post` extended-hours minutes.

    Each date gets its scheduled regular session (13:00 close on early-close days).
    `skip` maps a date to minutes-after-9:30 to leave out.
    """
    from trading_backtest import sessions

    rng = np.random.default_rng(seed)
    frames = []
    for d in dates:
        close = sessions.schedule(pd.Timestamp(d).date(), pd.Timestamp(d).date()).close.iloc[0]
        open_ = pd.Timestamp(d, tz=TZ) + pd.Timedelta("9h30min")
        minutes = int((close - open_).total_seconds() // 60)
        offsets = [m for m in range(-pre, minutes + post) if m not in (skip or {}).get(d, ())]
        idx = pd.DatetimeIndex([open_ + pd.Timedelta(minutes=m) for m in offsets])
        c = 100 + rng.normal(0, 0.1, len(idx)).cumsum()
        o = np.r_[c[0], c[:-1]]
        frames.append(
            pd.DataFrame(
                {
                    "Open": o,
                    "High": np.maximum(o, c) + rng.uniform(0, 0.05, len(idx)),
                    "Low": np.minimum(o, c) - rng.uniform(0, 0.05, len(idx)),
                    "Close": c,
                    "Volume": rng.integers(0, 1000, len(idx)).astype(float),
                },
                index=idx,
            )
        )
    return pd.concat(frames)
