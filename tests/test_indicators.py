import numpy as np
import pandas as pd
import pytest
from backtesting import Backtest, Strategy
from bars import TZ, random_days, session

from trading_backtest.indicators import atr, cumulative_rvol, ema, session_vwap


def bars(rows, start="2025-01-06 09:30"):
    """Bars from (open, high, low, close, volume) tuples, one minute apart."""
    idx = pd.date_range(pd.Timestamp(start, tz=TZ), periods=len(rows), freq="min")
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"], index=idx)


def test_vwap_hand_calculated_with_zero_volume_start():
    df = bars([(10, 11, 9, 10, 0), (10, 12, 9, 12, 100), (12, 13, 11, 12, 300)])
    vwap = session_vwap(df)
    assert np.isnan(vwap.iloc[0])  # no volume yet
    assert vwap.iloc[1] == pytest.approx(11)  # hlc3 = 11
    assert vwap.iloc[2] == pytest.approx((11 * 100 + 12 * 300) / 400)
    assert session_vwap(df, price_source="close").iloc[2] == pytest.approx(12)


def test_vwap_resets_each_session_and_ignores_extended_hours():
    df = pd.concat([session("2025-01-06", price=100), session("2025-01-07", price=50)])
    pre = bars([(80, 80, 80, 80, 1e6)], start="2025-01-07 09:29")
    df = pd.concat([df, pre]).sort_index()
    vwap = session_vwap(df, price_source="close")
    assert np.isnan(vwap[pre.index[0]])
    assert vwap[pd.Timestamp("2025-01-07 09:30", tz=TZ)] == 50


def test_ema_known_values_and_warmup():
    close = pd.Series([1.0, 2, 3, 4, 5])
    out = ema(close, 3)  # alpha 0.5, seeded with the first close
    assert out.iloc[:2].isna().all()
    assert out.iloc[2:].tolist() == [2.25, 3.125, 4.0625]
    with pytest.raises(ValueError):
        ema(close, 0)


def test_atr_wilder_seed_and_overnight_gap():
    day1 = bars([(9, 10, 8, 9, 1), (10, 11, 9, 10, 1), (11, 12, 10, 11, 1)])
    day2 = bars([(12.5, 13, 12, 12.5, 1), (14.5, 15, 14, 14.5, 1)], start="2025-01-07 09:30")
    # True ranges: 2, 2, 2, then 2 (gap from 11 to 13), 2.5
    out = atr(pd.concat([day1, day2]), 3)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2:].tolist() == pytest.approx([2, 2, (2 * 2 + 2.5) / 3])
    assert atr(day1.iloc[:2], 3).isna().all()  # not enough bars


def full(day, volume):
    df = session(day)
    df["Volume"] = float(volume)
    return df


def test_cumulative_rvol_uses_prior_full_sessions_only():
    # 11-28 is an early close: usable as "today" but never as a baseline day.
    df = pd.concat(
        [
            full("2025-11-24", 100),
            full("2025-11-25", 300),
            full("2025-11-26", 500),
            full("2025-11-28", 1000).iloc[:210],
            full("2025-12-01", 800),
        ]
    )
    rvol = cumulative_rvol(df, lookback_sessions=2)
    day = rvol.index.date.astype(str)
    assert rvol[day <= "2025-11-25"].isna().all()
    assert (rvol[day == "2025-11-26"] == 500 / 200).all()
    assert (rvol[day == "2025-11-28"] == 1000 / 400).all()
    assert (rvol[day == "2025-12-01"] == 800 / 400).all()


def test_cumulative_rvol_skips_sessions_with_missing_minutes():
    gappy = full("2025-11-25", 300).drop(pd.Timestamp("2025-11-25 12:00", tz=TZ))
    df = pd.concat(
        [full("2025-11-24", 100), gappy, full("2025-11-26", 500), full("2025-12-01", 800)]
    )
    rvol = cumulative_rvol(df, lookback_sessions=2)
    day = rvol.index.date.astype(str)
    assert rvol[day == "2025-11-26"].isna().all()  # only one eligible prior session
    assert (rvol[day == "2025-12-01"] == 800 / 300).all()


def test_cumulative_rvol_zero_baseline_is_nan():
    df = pd.concat([full("2025-01-06", 0), full("2025-01-07", 10)])
    assert cumulative_rvol(df, 1).isna().all()


def test_backtesting_strategy_can_consume_indicators():
    class UsesIndicators(Strategy):
        def init(self):
            df = self.data.df
            self.vwap = self.I(lambda: session_vwap(df).to_numpy(), name="VWAP")
            self.ema = self.I(lambda: ema(df.Close, 20).to_numpy(), name="EMA20")
            self.atr = self.I(lambda: atr(df, 14).to_numpy(), name="ATR14")

        def next(self):
            if not self.position and self.data.Close[-1] > self.vwap[-1] > self.ema[-1]:
                self.buy()
            elif self.position and self.data.Close[-1] < self.vwap[-1]:
                self.position.close()

    data = random_days(["2025-01-06", "2025-01-07"], pre=0, post=0)
    stats = Backtest(data, UsesIndicators, cash=100_000, finalize_trades=True).run()
    assert stats["# Trades"] > 0
