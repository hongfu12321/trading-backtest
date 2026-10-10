from trading_backtest.strategies.base import IntradayStrategy


class OpeningRangeBreakout(IntradayStrategy):
    """Trade the first breakout of the opening range, stop at the opposite side.

    One trade per day: long above the range high, short below the range low.
    """

    range_minutes = 15

    def init(self):
        super().init()
        df = self.data.df
        day = df.index.date
        in_range = self.minute_of_day < self.range_minutes
        or_high = df.High.where(in_range).groupby(day).transform("max")
        or_low = df.Low.where(in_range).groupby(day).transform("min")
        self.or_high = self.I(lambda: or_high.to_numpy(), name="OR high", overlay=True)
        self.or_low = self.I(lambda: or_low.to_numpy(), name="OR low", overlay=True)
        self._last_trade_day = None

    def on_bar(self):
        if self.minute < self.range_minutes or self.position:
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
