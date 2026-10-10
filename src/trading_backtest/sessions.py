"""Regular-session schedule for US equities.

Minutes are counted from the 9:30 ET open. Open and close times come from the NYSE
(`XNYS`) calendar in `exchange_calendars`, which knows holidays and early closes (13:00,
minute 210). The schedule comes from the calendar, not the bars, because data vendors
return after-hours bars after an early close. Times are local New York time, so
daylight-saving changes need no special handling.

A session is *tradable* when it has at least two bars in the flatten window (the last
`FLATTEN_MINUTES` before the close): one to send the closing order on, and a later one for
it to fill at. Other sessions cannot be flattened without inventing a price, so they are
dropped from backtests rather than repaired.
"""

from datetime import date
from functools import cache

import exchange_calendars as xc
import numpy as np
import pandas as pd

TZ = "America/New_York"
FULL_CLOSE = 390
EARLY_CLOSE = 210
FLATTEN_MINUTES = 5


@cache
def calendar() -> xc.ExchangeCalendar:
    return xc.get_calendar("XNYS")


def schedule(start: date, end: date) -> pd.DataFrame:
    """`open` and `close` (New York time) of each session in [start, end], indexed by date."""
    s = calendar().schedule.loc[pd.Timestamp(start) : pd.Timestamp(end), ["open", "close"]]
    s = s.apply(lambda col: col.dt.tz_convert(TZ))
    s.index = s.index.date
    return s


def is_early_close(d: date) -> bool:
    s = schedule(d, d)
    return len(s) == 1 and s.close.iloc[0].hour < 16


def minute_of_day(index: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(index.hour * 60 + index.minute - (9 * 60 + 30))


def close_minute(index: pd.DatetimeIndex) -> np.ndarray:
    """Session close (minutes after 9:30) for each bar's day; 0 on non-session days."""
    if len(index) == 0:
        return np.zeros(0, dtype=int)
    s = schedule(index.date.min(), index.date.max())
    minutes = (s.close.dt.hour * 60 + s.close.dt.minute - (9 * 60 + 30)).to_dict()
    return np.array([minutes.get(d, 0) for d in index.date], dtype=int)


def in_session(index: pd.DatetimeIndex) -> np.ndarray:
    minute = minute_of_day(index)
    return (minute >= 0) & (minute < close_minute(index))


def tradable(index: pd.DatetimeIndex) -> np.ndarray:
    """Boolean per bar: does this bar's session have enough bars to flatten in time?

    Expects only in-session bars (see `in_session`).
    """
    minute = minute_of_day(index)
    in_window = pd.Series(minute >= close_minute(index) - FLATTEN_MINUTES, index=index)
    return np.asarray(in_window.groupby(index.date).transform("sum") >= 2)


def tradable_bars(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Keep in-session bars of tradable sessions; return them and the dropped dates."""
    df = df[in_session(df.index)]
    keep = tradable(df.index)
    dropped = sorted(set(df.index[~keep].date))
    return df[keep], dropped
