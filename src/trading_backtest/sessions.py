"""Regular-session schedule for US equities, inferred from the bars themselves.

Minutes are counted from the 9:30 ET open. A session closes at 16:00 (minute 390), or at
13:00 (minute 210) on scheduled early-close days. A day whose last bar is before 13:00 is
treated as an early close; any other day as a full session. Times are local New York time,
so daylight-saving changes need no special handling.

A session is *tradable* when it has at least two bars in the flatten window (the last
`FLATTEN_MINUTES` before the close): one to send the closing order on, and a later one for
it to fill at. Other sessions cannot be flattened without inventing a price, so they are
dropped from backtests rather than repaired.
"""

import numpy as np
import pandas as pd

FULL_CLOSE = 390
EARLY_CLOSE = 210
FLATTEN_MINUTES = 5


def minute_of_day(index: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(index.hour * 60 + index.minute - (9 * 60 + 30))


def close_minute(index: pd.DatetimeIndex) -> np.ndarray:
    """Session close (minutes after 9:30) for each bar's day."""
    minute = pd.Series(minute_of_day(index), index=index)
    last = minute.groupby(index.date).transform("max")
    return np.where(last < EARLY_CLOSE, EARLY_CLOSE, FULL_CLOSE)


def tradable(index: pd.DatetimeIndex) -> np.ndarray:
    """Boolean per bar: does this bar's session have enough bars to flatten in time?"""
    minute = minute_of_day(index)
    in_window = pd.Series(minute >= close_minute(index) - FLATTEN_MINUTES, index=index)
    return np.asarray(in_window.groupby(index.date).transform("sum") >= 2)


def drop_untradable(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Remove sessions that cannot be flattened; return the kept bars and dropped dates."""
    keep = tradable(df.index)
    dropped = sorted(set(df.index[~keep].date))
    return df[keep], dropped
