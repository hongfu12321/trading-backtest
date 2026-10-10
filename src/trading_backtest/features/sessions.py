"""Input checks and per-bar session metadata shared by indicators and features.

Conventions for every indicator and feature in this package:

- Input: a DataFrame with a unique, increasing, timezone-aware `DatetimeIndex` and numeric
  `Open, High, Low, Close, Volume` columns. Bad input raises `ValueError`; nothing is
  silently sorted, de-duplicated or repaired.
- A timestamp marks the *start* of its one-minute bar; its OHLCV is only known once the bar
  has closed. A value at bar t uses bars up to and including t, so it is usable for orders
  placed after t closes (filled at t+1's open), never at t's own open.
- Output keeps the input index. Unavailable values are NaN; nothing is back-filled.
- Sessions come from the NYSE calendar (`trading_backtest.sessions`), so holidays, early
  closes and daylight saving are handled. Bars outside the regular session are marked, not
  folded into the nearest session.
"""

import numpy as np
import pandas as pd

from trading_backtest import sessions

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def check_bars(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Validate the input contract; return the index converted to New York time."""
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.tz is None:
        raise ValueError("index must be a timezone-aware DatetimeIndex")
    if not idx.is_unique:
        raise ValueError("index has duplicate timestamps")
    if not idx.is_monotonic_increasing:
        raise ValueError("index is not sorted")
    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    values = df[OHLCV]
    if not all(pd.api.types.is_numeric_dtype(t) for t in values.dtypes):
        raise ValueError("OHLCV columns must be numeric")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("OHLCV contains NaN or infinite values")
    prices = df[["Open", "High", "Low", "Close"]]
    if (prices <= 0).any().any():
        raise ValueError("prices must be positive")
    if (df.Volume < 0).any():
        raise ValueError("volume must be non-negative")
    if (df.High < prices.max(axis=1)).any() or (df.Low > prices.min(axis=1)).any():
        raise ValueError("High/Low inconsistent with Open/Close")
    return idx.tz_convert(sessions.TZ)


def session_info(df: pd.DataFrame) -> pd.DataFrame:
    """Regular-session metadata per bar.

    Columns: `session_date` (exchange trading date, NaT outside the regular session),
    `minute_of_session` (0 for the 9:30 bar, NaN outside), `session_open`,
    `session_close` (NaT outside) and `is_regular_session`. Every value depends only on the
    bar's own timestamp and the published exchange calendar, so it is causal.
    """
    idx = check_bars(df)
    out = pd.DataFrame(index=df.index)
    if len(idx) == 0:
        for col in ("session_date", "session_open", "session_close", "minute_of_session"):
            out[col] = pd.Series(dtype=float)
        out["is_regular_session"] = pd.Series(dtype=bool)
        return out

    sched = sessions.schedule(idx.date.min(), idx.date.max())
    day = pd.Index(idx.date)
    opens = pd.DatetimeIndex(day.map(sched.open.to_dict()), tz=sessions.TZ)
    closes = pd.DatetimeIndex(day.map(sched.close.to_dict()), tz=sessions.TZ)
    regular = np.asarray((idx >= opens) & (idx < closes))

    out["session_date"] = pd.Series(pd.to_datetime(day).to_numpy(), index=df.index).where(regular)
    out["session_open"] = pd.Series(opens, index=df.index).where(regular)
    out["session_close"] = pd.Series(closes, index=df.index).where(regular)
    minutes = (idx - opens).total_seconds() // 60
    out["minute_of_session"] = pd.Series(np.asarray(minutes), index=df.index).where(regular)
    out["is_regular_session"] = regular
    return out


def session_lengths(info: pd.DataFrame) -> pd.Series:
    """Scheduled length in minutes of each session in `info`, indexed by session date."""
    reg = info[info.is_regular_session]
    length = (reg.session_close - reg.session_open).dt.total_seconds() // 60
    return length.groupby(reg.session_date).first()


def complete_sessions(df: pd.DataFrame) -> pd.Series:
    """Whether each session has a bar for every scheduled minute, indexed by session date.

    Retrospective data-quality information: a session's completeness is only known once it
    has ended, so never use it as a signal during that session. It is safe to use for
    *earlier* sessions (e.g. to qualify yesterday's levels).
    """
    info = session_info(df)
    reg = info[info.is_regular_session]
    counts = reg.groupby("session_date").size()
    return counts == session_lengths(info).reindex(counts.index)
