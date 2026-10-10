"""Session price levels: opening range, previous-session levels, running high/low.

All functions use regular-session bars only and return NaN outside the regular session.
See `features.sessions` for the shared input and timestamp conventions.
"""

import pandas as pd

from trading_backtest import sessions
from trading_backtest.features.sessions import complete_sessions, session_info, session_lengths


def opening_range(df: pd.DataFrame, minutes: int = 15) -> pd.DataFrame:
    """`OR_High`, `OR_Low`, `OR_Mid` and `OR_Complete` for each regular session.

    The range covers the first `minutes` *scheduled* minutes (9:30 up to 9:30 + minutes).
    It becomes final on the bar that completes it, i.e. the bar at minute `minutes - 1`;
    before that the levels are NaN and `OR_Complete` is False, and they then stay constant
    for the rest of the session. If any bar inside the range is missing, the session never
    gets a range. `minutes` must be shorter than every session in the data (early closes
    included), else `ValueError`.
    """
    info = session_info(df)
    lengths = session_lengths(info)
    if minutes < 1 or (len(lengths) and minutes >= lengths.min()):
        raise ValueError(f"minutes must be between 1 and the shortest session; got {minutes}")

    reg = info.is_regular_session
    day = info.session_date
    in_range = reg & (info.minute_of_session < minutes)
    seen = in_range.astype(int).groupby(day).cumsum()
    complete = reg & (seen == minutes)

    def level(col, how):
        running = df[col].where(in_range).groupby(day)
        running = running.cummax() if how == "max" else running.cummin()
        return running.groupby(day).ffill().where(complete)

    out = pd.DataFrame(index=df.index)
    out["OR_High"] = level("High", "max")
    out["OR_Low"] = level("Low", "min")
    out["OR_Mid"] = (out.OR_High + out.OR_Low) / 2
    out["OR_Complete"] = complete.to_numpy()
    return out


def previous_day_levels(df: pd.DataFrame) -> pd.DataFrame:
    """`PDH`, `PDL`, `Prev_Close` of the preceding exchange session, on regular-session bars.

    "Previous" means the previous NYSE session (weekends and holidays skipped), not the
    previous calendar day. Values use that session's regular-hours bars and appear from the
    next session's open. They are NaN when the previous session is missing from the data or
    has any missing minute, so partial data is never presented as the day's levels. To get
    values on the first session of a window, include the session before it in `df`.
    """
    info = session_info(df)
    reg = info.is_regular_session
    day = info.session_date[reg]
    bars = df[reg.to_numpy()]
    daily = pd.DataFrame(
        {
            "PDH": bars.High.groupby(day).max(),
            "PDL": bars.Low.groupby(day).min(),
            "Prev_Close": bars.Close.groupby(day).last(),
        }
    )
    complete = complete_sessions(df)
    daily = daily[complete.reindex(daily.index, fill_value=False)]

    cal = sessions.calendar()
    prev = {d: cal.previous_session(d).tz_localize(None) for d in daily.index.union(day.unique())}
    prev_day = info.session_date.map(prev)
    out = daily.reindex(prev_day.to_numpy())
    out.index = df.index
    return out


def intraday_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Running high/low of the current regular session.

    `HOD`/`LOD` include the current bar. `HOD_Previous_Bar`/`LOD_Previous_Bar` cover only
    the bars before it in the same session (NaN on the session's first bar), for breakout
    tests that should not compare a bar's high with itself.
    """
    info = session_info(df)
    day = info.session_date
    reg = info.is_regular_session
    out = pd.DataFrame(index=df.index)
    out["HOD"] = df.High.where(reg).groupby(day).cummax()
    out["LOD"] = df.Low.where(reg).groupby(day).cummin()
    out["HOD_Previous_Bar"] = out.HOD.groupby(day).shift(1)
    out["LOD_Previous_Bar"] = out.LOD.groupby(day).shift(1)
    return out
