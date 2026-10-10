import pandas as pd

from trading_backtest.features.sessions import check_bars


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's average true range.

    True range = max(High - Low, |High - prev Close|, |Low - prev Close|); the first bar has
    no previous close, so its true range is High - Low. The first ATR (bar `period - 1`) is
    the mean of the first `period` true ranges; after that
    ATR_t = (ATR_{t-1} x (period - 1) + TR_t) / period. Earlier values are NaN. It runs
    continuously across sessions, so overnight gaps count as true range.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    check_bars(df)
    prev_close = df.Close.shift(1)
    tr = pd.concat(
        [df.High - df.Low, (df.High - prev_close).abs(), (df.Low - prev_close).abs()], axis=1
    ).max(axis=1)
    out = pd.Series(float("nan"), index=df.index, name=f"ATR{period}")
    if len(tr) < period:
        return out
    seeded = tr.iloc[period - 1 :].copy()
    seeded.iloc[0] = tr.iloc[:period].mean()
    out.iloc[period - 1 :] = seeded.ewm(alpha=1 / period, adjust=False).mean()
    return out
