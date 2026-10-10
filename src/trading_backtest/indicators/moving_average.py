import pandas as pd


def ema(close: pd.Series, period: int = 20) -> pd.Series:
    """Exponential moving average, `ewm(span=period, adjust=False, min_periods=period)`.

    Recursive form: ema_t = a x close_t + (1 - a) x ema_{t-1}, a = 2 / (period + 1),
    seeded with the first close. The first `period - 1` values are NaN. It runs
    continuously across sessions (no daily reset) over whatever bars are passed in, so pass
    regular-hours bars if extended hours should not count.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    return close.ewm(span=period, adjust=False, min_periods=period).mean().rename(f"EMA{period}")
