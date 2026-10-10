import numpy as np
import pandas as pd
from bars import at, days, session, set_bar

from trading_backtest import engine, sessions
from trading_backtest.strategies import STRATEGIES
from trading_backtest.strategies.base import IntradayStrategy
from trading_backtest.strategies.orb import OpeningRangeBreakout, opening_range

NO_COSTS = engine.CostModel(spread=0.0)
D1, D2 = "2025-01-06", "2025-01-07"


def random_bars(n_days=5):
    idx = pd.DatetimeIndex(
        [
            ts
            for d in pd.bdate_range("2025-01-06", periods=n_days)
            for ts in pd.date_range(d + pd.Timedelta("9h30min"), periods=390, freq="min")
        ],
        tz="America/New_York",
    )
    rng = np.random.default_rng(0)
    close = 100 + rng.normal(0, 0.05, len(idx)).cumsum()
    return pd.DataFrame(
        {"Open": close, "High": close + 0.02, "Low": close - 0.02, "Close": close, "Volume": 1000},
        index=idx,
    )


def breakout_day(day, minutes=390, skip=()):
    """Range 99-101 in the first 15 minutes, close above it at minute 20."""
    df = session(day, minutes, skip=skip)
    set_bar(df, day, 3, h=101)
    set_bar(df, day, 7, low=99)
    set_bar(df, day, 20, h=101.6, c=101.5)
    set_bar(df, day, 21, o=101.5)
    return df


def trades(data, strategy=OpeningRangeBreakout, **params):
    return engine.run(data, strategy, params, costs=NO_COSTS)._trades


def test_every_strategy_runs_and_ends_flat_each_day():
    data = random_bars()
    for name, strategy in STRATEGIES.items():
        t = engine.run(data, strategy)._trades
        assert len(t), name
        assert (t.EntryTime.dt.date == t.ExitTime.dt.date).all(), name


def test_opening_range_values_and_daily_reset():
    df = days(breakout_day(D1), session(D2, price=50))
    high, low = opening_range(df, sessions.minute_of_day(df.index), 15)
    assert high[: at(D1, 14)].isna().all()
    assert high[at(D1, 15)] == 101 and low[at(D1, 15)] == 99
    assert high[at(D2, 14)] != high[at(D2, 14)]  # NaN: next day's range not complete
    assert high[at(D2, 15)] == 50.01 and low[at(D2, 15)] == 49.99


def test_opening_range_unchanged_when_future_bars_appended():
    df = days(breakout_day(D1), session(D2, price=50))
    full, _ = opening_range(df, sessions.minute_of_day(df.index), 15)
    for cut in (10, 15, 16, 400, 500):
        part = df.iloc[:cut]
        high, _ = opening_range(part, sessions.minute_of_day(part.index), 15)
        pd.testing.assert_series_equal(high, full.iloc[:cut])


def test_breakout_enters_next_open_and_flattens_at_1556():
    t = trades(breakout_day(D1))
    assert len(t) == 1
    trade = t.iloc[0]
    assert trade.EntryTime == at(D1, 21) and trade.EntryPrice == 101.5
    assert trade.SL == 99
    assert trade.ExitTime == at(D1, 386)


def test_first_signal_is_on_first_bar_after_range():
    # Uses day 2: backtesting.py starts calling next() only once every indicator has a value.
    df = days(session(D1), breakout_day(D2))
    set_bar(df, D2, 15, h=101.6, c=101.5)
    assert trades(df).iloc[0].EntryTime == at(D2, 16)


def test_failed_breakout_hits_stop():
    df = breakout_day(D1)
    set_bar(df, D1, 30, low=98.5, c=98.6)
    t = trades(df)
    assert len(t) == 1
    assert t.iloc[0].ExitTime == at(D1, 30) and t.iloc[0].ExitPrice == 99


def test_missing_open_bar_skips_the_day():
    assert trades(breakout_day(D1, skip={0})).empty


def test_early_close_session_flattens_at_1256():
    t = trades(days(breakout_day(D1, minutes=210), session(D2)))
    assert t.iloc[0].ExitTime == at(D1, 206)


def test_session_missing_final_bars_is_dropped(caplog):
    t = trades(days(breakout_day(D1, minutes=330), breakout_day(D2)))
    assert "too incomplete" in caplog.text
    assert list(t.EntryTime.dt.date.astype(str)) == [D2]


def test_late_signal_cannot_enter_inside_flatten_window():
    df = session(D1)
    set_bar(df, D1, 3, h=101)
    set_bar(df, D1, 7, low=99)
    set_bar(df, D1, 384, h=101.6, c=101.5)  # bar before the window: signal ignored
    assert trades(df).empty


class StopEntry(IntradayStrategy):
    """Places one buy-stop far above the market that never triggers the same day."""

    placed = False

    def on_bar(self):
        if self.minute == 100 and not self.placed:
            self.buy(stop=200)
            self.placed = True


def test_pending_entry_order_cancelled_before_next_session():
    df = days(session(D1), session(D2, price=210))
    assert trades(df, StopEntry).empty
