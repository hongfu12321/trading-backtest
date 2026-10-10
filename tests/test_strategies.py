import numpy as np
import pandas as pd

from trading_backtest import engine
from trading_backtest.strategies import STRATEGIES


def synthetic_bars(days=5):
    idx = pd.DatetimeIndex(
        [
            ts
            for d in pd.bdate_range("2025-01-06", periods=days)
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


def test_every_strategy_runs_and_ends_flat_each_day():
    data = synthetic_bars()
    for name, strategy in STRATEGIES.items():
        stats = engine.run(data, strategy)
        trades = stats._trades
        assert (trades.EntryTime.dt.date == trades.ExitTime.dt.date).all(), name
