import pandas as pd

from trading_backtest.strategies.base import IntradayStrategy


def opening_range(df: pd.DataFrame, minute_of_day, range_minutes: int):
    """Opening-range high and low per bar, using only bars at or before it.

    Values are NaN until the range is complete (minute >= range_minutes) and for days
    missing the 9:30 bar, so such days are not traded.
    """
    day = df.index.date
    in_range = pd.Series(minute_of_day < range_minutes, index=df.index)
    has_open = pd.Series(minute_of_day == 0, index=df.index).groupby(day).cummax()
    ready = ~in_range & has_open

    def running(col, how):
        values = col.where(in_range).groupby(day)
        values = values.cummax() if how == "max" else values.cummin()
        return values.groupby(day).ffill().where(ready)

    return running(df.High, "max"), running(df.Low, "min")


class OpeningRangeBreakout(IntradayStrategy):
    """Trade the first breakout of the opening range, stop at the opposite side.

    One trade per day: long when a bar closes above the range high, short when it closes
    below the range low. The order fills at the next bar's open.
    """

    range_minutes = 15

    def init(self):
        super().init()
        high, low = opening_range(self.data.df, self.minute_of_day, self.range_minutes)
        self.or_high = self.I(lambda: high.to_numpy(), name="OR high", overlay=True)
        self.or_low = self.I(lambda: low.to_numpy(), name="OR low", overlay=True)
        self._last_trade_day = None

    def on_bar(self):
        if self.position or self.orders:
            return
        today = self.data.index[-1].date()
        if today == self._last_trade_day:
            return

        close, high, low = self.data.Close[-1], self.or_high[-1], self.or_low[-1]
        if close > high:
            self.buy(sl=low)
            self._last_trade_day = today
        elif close < low:
            self.sell(sl=high)
            self._last_trade_day = today
