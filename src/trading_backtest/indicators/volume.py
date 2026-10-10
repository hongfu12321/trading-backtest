import numpy as np
import pandas as pd

from trading_backtest.features.sessions import complete_sessions, session_info, session_lengths

FULL_SESSION = 390


def cumulative_rvol(df: pd.DataFrame, lookback_sessions: int = 20) -> pd.Series:
    """Session-to-date volume divided by its average at the same minute of prior sessions.

    For a bar at minute m of today's session: today's cumulative regular-session volume
    through m, divided by the mean cumulative volume through m over the last
    `lookback_sessions` eligible sessions before today. Eligible sessions are full-length
    (no early close) with every minute present, so half-days and gappy days never enter the
    baseline. Today itself may be any session. NaN outside the regular session, until
    `lookback_sessions` eligible sessions exist, and where the baseline volume is zero.
    """
    if lookback_sessions <= 0:
        raise ValueError("lookback_sessions must be positive")
    info = session_info(df)
    reg = info.is_regular_session.to_numpy()
    out = pd.Series(np.nan, index=df.index, name="RVOL")
    if not reg.any():
        return out

    day = info.session_date[reg]
    minute = info.minute_of_session[reg].astype(int)
    cum = df.Volume[reg].groupby(day).cumsum()

    eligible = complete_sessions(df) & (session_lengths(info) == FULL_SESSION)
    rows = pd.DataFrame({"day": day, "minute": minute, "cum": cum})
    rows = rows[rows.day.isin(eligible.index[eligible])]
    if rows.empty:
        return out
    grid = rows.pivot(index="day", columns="minute", values="cum")

    # Baseline for each session: the window ending at the last eligible session before it.
    all_days = pd.Index(sorted(day.unique()))
    baseline = grid.rolling(lookback_sessions).mean().reindex(all_days).ffill().shift(1)

    base = baseline.to_numpy()[all_days.get_indexer(day), minute.to_numpy()]
    out[reg] = cum.to_numpy() / np.where(base > 0, base, np.nan)
    return out
