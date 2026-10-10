import pandas as pd

from trading_backtest.features.sessions import session_info

PRICE_SOURCES = {
    "hlc3": lambda df: (df.High + df.Low + df.Close) / 3,
    "ohlc4": lambda df: (df.Open + df.High + df.Low + df.Close) / 4,
    "close": lambda df: df.Close,
}


def session_vwap(df: pd.DataFrame, *, price_source: str = "hlc3") -> pd.Series:
    """Volume-weighted average price, reset at each regular-session open (9:30 ET).

    cumsum(price x volume) / cumsum(volume) over the session's bars up to and including the
    current one. Only regular-session bars contribute; other bars are NaN, as is any bar
    before the session has traded volume. This is an approximation from minute bars
    (`price_source` stands in for each bar's trades), not the exchange's trade-level VWAP.
    """
    if price_source not in PRICE_SOURCES:
        raise ValueError(f"price_source must be one of {sorted(PRICE_SOURCES)}")
    info = session_info(df)
    reg = info.is_regular_session
    day = info.session_date
    volume = df.Volume.where(reg)
    pv = (PRICE_SOURCES[price_source](df) * volume).groupby(day).cumsum()
    cum_volume = volume.groupby(day).cumsum()
    return (pv / cum_volume.where(cum_volume > 0)).rename("VWAP")
