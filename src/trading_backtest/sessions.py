"""Regular-session schedule for US equities.

Minutes are counted from the 9:30 ET open. A session closes at 16:00 (minute 390), or at
13:00 (minute 210) on NYSE's scheduled early-close days: the day after Thanksgiving, and
July 3 and December 24 when they fall Monday to Thursday. The schedule comes from the
calendar, not the bars, because data vendors return after-hours bars after an early close.
Times are local New York time, so daylight-saving changes need no special handling.
Rare one-off schedule changes (e.g. national days of mourning) are not modelled.

A session is *tradable* when it has at least two bars in the flatten window (the last
`FLATTEN_MINUTES` before the close): one to send the closing order on, and a later one for
it to fill at. Other sessions cannot be flattened without inventing a price, so they are
dropped from backtests rather than repaired.
"""

from datetime import date

import numpy as np
import pandas as pd

FULL_CLOSE = 390
EARLY_CLOSE = 210
FLATTEN_MINUTES = 5


def is_early_close(d: date) -> bool:
    if d.month == 11 and d.weekday() == 4 and 23 <= d.day <= 29:  # day after Thanksgiving
        return True
    return (d.month, d.day) in ((7, 3), (12, 24)) and d.weekday() <= 3


def minute_of_day(index: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(index.hour * 60 + index.minute - (9 * 60 + 30))


def close_minute(index: pd.DatetimeIndex) -> np.ndarray:
    """Session close (minutes after 9:30) for each bar's day."""
    early = {d: is_early_close(d) for d in set(index.date)}
    return np.array([EARLY_CLOSE if early[d] else FULL_CLOSE for d in index.date], dtype=int)


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
