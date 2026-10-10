from backtesting import Strategy

from trading_backtest import sessions


class IntradayStrategy(Strategy):
    """Base for day-trading strategies: never holds a position or entry order overnight.

    Subclasses implement `on_bar()` instead of `next()`. Execution policy:

    - Signals use the completed current bar; market orders fill at the next bar's open.
    - The flatten window is the last `sessions.FLATTEN_MINUTES` of each session (15:55 on
      full days, 12:55 on early-close days). In it, pending entry orders are cancelled and
      any position is closed at the next bar's open.
    - `on_bar()` is not called on the bar just before the window, so no entry can fill
      inside it.
    - Sessions without two bars in the window are dropped by the engine (see `sessions`).
    """

    def init(self):
        idx = self.data.index
        self.minute_of_day = sessions.minute_of_day(idx)
        self.flatten_minute = sessions.close_minute(idx) - sessions.FLATTEN_MINUTES

    def next(self):
        i = len(self.data) - 1
        if self.minute_of_day[i] >= self.flatten_minute[i]:
            for order in self.orders:
                if not order.is_contingent:
                    order.cancel()
            if self.position:
                self.position.close()
            return
        if self.minute_of_day[i] + 1 < self.flatten_minute[i]:
            self.on_bar()

    def on_bar(self):
        raise NotImplementedError

    @property
    def minute(self) -> int:
        """Minutes since 9:30 for the current bar."""
        return int(self.minute_of_day[len(self.data) - 1])
