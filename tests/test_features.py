import numpy as np
import pandas as pd
import pytest
from bars import TZ, at, session, set_bar

from trading_backtest.features import (
    check_bars,
    complete_sessions,
    intraday_levels,
    opening_range,
    previous_day_levels,
    session_info,
)


def ts(s):
    return pd.Timestamp(s, tz=TZ)


def test_session_info_marks_off_session_holiday_and_early_close():
    extra = session("2025-11-27", minutes=5)  # Thanksgiving: market closed
    pre = session("2025-11-28", minutes=1).shift(-1, freq="min")  # 09:29
    df = pd.concat([pre, session("2025-11-28"), extra]).sort_index()  # 11-28 closes 13:00
    info = session_info(df)
    assert info.loc[ts("2025-11-28 09:30"), "minute_of_session"] == 0
    assert info.loc[ts("2025-11-28 12:59"), "minute_of_session"] == 209
    for off in ("2025-11-28 09:29", "2025-11-28 13:00", "2025-11-27 09:30"):
        assert not info.loc[ts(off), "is_regular_session"]
        assert pd.isna(info.loc[ts(off), "session_date"])
    assert info.loc[ts("2025-11-28 10:00"), "session_close"] == ts("2025-11-28 13:00")


@pytest.mark.parametrize("day", ["2025-03-07", "2025-03-10", "2025-10-31", "2025-11-03"])
def test_session_info_across_dst(day):
    # Same 09:30 local open before and after each DST change, from UTC-stamped input.
    df = session(day).tz_convert("UTC")
    info = session_info(df)
    assert info.minute_of_session.tolist() == list(range(390))


def test_check_bars_rejects_bad_input():
    good = session("2025-01-06", minutes=3)
    cases = {
        "timezone-aware": good.tz_localize(None),
        "duplicate": pd.concat([good, good.iloc[[0]]]),
        "sorted": good.iloc[::-1],
        "positive": good.assign(Low=0.0),
        "inconsistent": good.assign(High=99.0),
        "NaN": good.assign(Volume=np.nan),
        "non-negative": good.assign(Volume=-1.0),
    }
    for message, df in cases.items():
        with pytest.raises(ValueError, match=message):
            check_bars(df)
    assert session_info(good.iloc[:0]).empty


def or_day(day="2025-01-06", **kw):
    df = session(day, **kw)
    set_bar(df, day, 3, h=101)
    set_bar(df, day, 7, low=99)
    set_bar(df, day, 20, h=102)  # after the range: must not change it
    return df


def test_opening_range_final_on_completing_bar_and_constant_after():
    out = opening_range(or_day(), 15)
    assert out.loc[: at("2025-01-06", 13), "OR_High"].isna().all()
    assert not out.loc[: at("2025-01-06", 13), "OR_Complete"].any()
    row = out.loc[at("2025-01-06", 14)]
    assert row.OR_Complete and row.OR_High == 101 and row.OR_Low == 99 and row.OR_Mid == 100
    assert (out.OR_High.iloc[14:] == 101).all()


def test_opening_range_resets_next_session():
    df = pd.concat([or_day(), session("2025-01-07", price=50)])
    out = opening_range(df, 15)
    assert out.loc[at("2025-01-07", 13), "OR_High"] != out.loc[at("2025-01-07", 13), "OR_High"]
    assert out.loc[at("2025-01-07", 14), "OR_High"] == 50.01


@pytest.mark.parametrize("missing", [0, 6])
def test_opening_range_missing_bar_never_completes(missing):
    out = opening_range(or_day(skip={missing}), 15)
    assert not out.OR_Complete.any() and out.OR_High.isna().all()


def test_opening_range_rejects_minutes_longer_than_a_session():
    early = session("2025-11-28", minutes=210)
    with pytest.raises(ValueError):
        opening_range(early, 210)
    with pytest.raises(ValueError):
        opening_range(early, 0)


def test_previous_day_levels_skip_weekends_and_holidays():
    fri, mon = or_day("2025-01-03"), session("2025-01-06", price=50)
    wed, early_fri = session("2025-11-26", price=70), session("2025-11-28", minutes=210)
    out = previous_day_levels(pd.concat([fri, mon, wed, early_fri]))
    assert out.loc[: at("2025-01-03", 389)].isna().all().all()  # no prior session
    mon_row = out.loc[at("2025-01-06", 0)]
    assert (mon_row.PDH, mon_row.PDL, mon_row.Prev_Close) == (102, 99, 100)
    assert out.loc[at("2025-11-28", 0), "PDH"] == 70.01  # Thanksgiving skipped
    assert out.loc[at("2025-11-26", 0)].isna().all()  # previous session 11-25 not in data


def test_previous_day_levels_nan_after_incomplete_session():
    fri = session("2025-01-03", skip={389})  # missing 15:59 bar
    out = previous_day_levels(pd.concat([fri, session("2025-01-06")]))
    assert out.isna().all().all()
    assert not complete_sessions(fri).iloc[0]


def test_intraday_levels_running_and_previous_bar():
    df = session("2025-01-06", minutes=4)
    df["High"] = [101, 103, 102, 104]
    df["Low"] = [99, 98, 97.5, 99]
    df["Open"] = df["Close"] = 100.0
    out = intraday_levels(df)
    assert out.HOD.tolist() == [101, 103, 103, 104]
    assert out.LOD.tolist() == [99, 98, 97.5, 97.5]
    assert np.isnan(out.HOD_Previous_Bar.iloc[0])
    assert out.HOD_Previous_Bar.tolist()[1:] == [101, 103, 103]
