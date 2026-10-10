import numpy as np
from backtesting import Strategy


class IntradayStrategy(Strategy):
    """Base for day-trading strategies: flattens all positions before the close.

    Subclasses implement `on_bar()` instead of `next()`.
    """

    exit_minute = 385  # minutes after 9:30 to flatten; 385 = 15:55

    def init(self):
        idx = self.data.index
        self.minute_of_day = np.asarray(idx.hour * 60 + idx.minute - (9 * 60 + 30))

    def next(self):
        if self.minute_of_day[len(self.data) - 1] >= self.exit_minute:
            if self.position:
                self.position.close()
            return
        self.on_bar()

    def on_bar(self):
        raise NotImplementedError

    @property
    def minute(self) -> int:
        """Minutes since 9:30 for the current bar."""
        return int(self.minute_of_day[len(self.data) - 1])
