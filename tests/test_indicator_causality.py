"""Every strategy-usable output at bar t must be unchanged when later bars are appended."""

import pandas as pd
import pytest
from bars import random_days

from trading_backtest import features, indicators

# Spans a weekend, an early close (11-28), a holiday (11-27) and DST end (11-02).
DATES = [
    "2025-10-31",
    "2025-11-03",
    "2025-11-24",
    "2025-11-25",
    "2025-11-26",
    "2025-11-28",
    "2025-12-01",
]
DATA = random_days(DATES, skip={"2025-11-25": [100]})

FUNCS = {
    "session_info": features.session_info,
    "opening_range": lambda df: features.opening_range(df, 15),
    "previous_day_levels": features.previous_day_levels,
    "intraday_levels": features.intraday_levels,
    "session_vwap": indicators.session_vwap,
    "ema": lambda df: indicators.ema(df.Close, 20),
    "atr": lambda df: indicators.atr(df, 14),
    "cumulative_rvol": lambda df: indicators.cumulative_rvol(df, 2),
}


def cut_points(df):
    """Bar positions around session boundaries and opening-range completion, plus a spread."""
    ts = df.index.tz_convert("America/New_York")
    minute = ts.hour * 60 + ts.minute - 570
    marks = [i for i, m in enumerate(minute) if m in (-1, 0, 1, 13, 14, 15, 209, 210, 389, 390)]
    return sorted(set(marks + list(range(1, len(df), 397))))


@pytest.mark.parametrize("name", FUNCS)
def test_prefix_values_unchanged_by_future_bars(name):
    func = FUNCS[name]
    full = func(DATA)
    for k in cut_points(DATA):
        part = func(DATA.iloc[:k])
        expected = full.iloc[:k]
        if isinstance(full, pd.Series):
            pd.testing.assert_series_equal(part, expected, check_dtype=False)
        else:
            pd.testing.assert_frame_equal(part, expected, check_dtype=False)
