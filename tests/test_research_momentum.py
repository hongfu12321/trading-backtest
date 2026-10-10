import json
from datetime import date

import numpy as np
import pandas as pd
import pytest
from bars import at, session

from trading_backtest import cli, sessions
from trading_backtest.research import intraday_momentum as study


def set_close(df, day, minute, price):
    ts = at(day, minute)
    df.loc[ts, ["Close", "High", "Low"]] = [price, max(price, 100.01), min(price, 99.99)]


def make_day(day, r_open, r_close, minutes=390, skip=()):
    """Flat 100 except the 10:00 boundary (r_open) and the 16:00 close (r_close)."""
    df = session(day, minutes=minutes, skip=skip)
    if 29 not in skip:
        set_close(df, day, 29, 100 * (1 + r_open))
    if minutes == 390 and 389 not in skip:
        set_close(df, day, 389, 100 * (1 + r_close))
    return df


# Exchange sessions only: 2025-01-09 (national day of mourning) and 01-20 are closed.
DAYS = [str(d) for d in sessions.schedule(date(2025, 1, 6), date(2025, 2, 14)).index]


def test_boundary_prices_and_returns_across_dst():
    df = make_day("2025-03-10", 0.01, 0.005).tz_convert("UTC")  # first day of DST
    row = study.daily_windows(df).iloc[0]
    assert (row.p_open, row.p_1000, row.p_1530) == (100, 101, 100)
    assert row.r_open == pytest.approx(0.01) and row.r_close == pytest.approx(0.005)
    assert row.included


def test_exclusions_flag_and_never_fill():
    df = pd.concat(
        [
            make_day("2025-11-25", 0.01, 0.01, skip={29}),  # no 09:59 bar
            make_day("2025-11-26", 0.01, 0.01, skip={150}),  # gap mid-day: kept
            make_day("2025-11-28", 0.01, 0.01, minutes=210),  # early close
        ]
    )
    out = study.daily_windows(df)
    assert out.exclude_reason.tolist() == ["missing_boundary_bar", "", "early_close"]
    assert np.isnan(out.r_open.iloc[0])
    assert out.missing_minutes.tolist() == [1, 1, 0]


def test_overnight_return_uses_previous_session_close():
    df = pd.concat([make_day("2025-01-03", 0, 0.02), make_day("2025-01-06", 0.01, 0)])
    out = study.daily_windows(df)
    assert np.isnan(out.r_open_overnight.iloc[0])  # previous session not in data
    assert out.r_open_overnight.iloc[1] == pytest.approx(101 / 102 - 1)


def test_signal_unchanged_by_bars_after_1000():
    df = make_day("2025-01-06", 0.01, 0.005)
    later = df.index >= at("2025-01-06", 30)
    shocked = df.copy()
    shocked.loc[later, ["Open", "High", "Low", "Close"]] = [50.0, 51.0, 49.0, 50.0]
    prefix = df[~later]
    for variant in (df, shocked, prefix):
        assert study.daily_windows(variant).r_open.iloc[0] == pytest.approx(0.01)


def momentum_days(slope=0.5):
    rng = np.random.default_rng(1)
    r_open = rng.choice([-1, 1], len(DAYS)) * rng.uniform(0.001, 0.01, len(DAYS))
    return pd.concat(make_day(d, ro, slope * ro) for d, ro in zip(DAYS, r_open, strict=True))


def test_describe_recovers_known_relationship():
    days = study.daily_windows(momentum_days(0.5))
    d = study.describe(days, n_boot=200)
    assert d["n"] == len(DAYS)
    assert d["pearson"] == pytest.approx(1) and d["slope"] == pytest.approx(0.5, rel=1e-3)
    assert d["sign_agreement"] == 1
    expected = (days.r_close.abs().mean()) * 1e4
    assert d["baselines_bps"]["sign_of_r_open"] == pytest.approx(expected)
    assert d["slope_ci"][0] > 0


def test_trades_enter_after_signal_and_pay_costs():
    days = study.daily_windows(momentum_days(-0.5))  # reversal: momentum trades lose
    free = study.trades(days, "last_half_hour", 0.0)
    paid = study.trades(days, "last_half_hour", 5.0)
    assert (free.entry == 100).all()  # 15:30 bar's open
    assert (free.gross < 0).all()
    assert np.allclose(paid.net, free.gross - 5e-4)
    flat = study.daily_windows(make_day("2025-01-06", 0.0, 0.01))
    assert study.trades(flat, "from_1000", 0.0).empty  # no signal, no trade


def test_split_is_chronological_and_disjoint():
    labels = study.split_labels(pd.to_datetime(pd.Index(DAYS[:8])))
    assert labels.tolist() == ["exploration"] * 4 + ["validation"] * 2 + ["holdout"] * 2


@pytest.mark.parametrize(
    "ci, holdout_slope, expected",
    [
        ([0.1, 0.3], 0.2, "supported"),
        ([0.1, 0.3], -0.1, "inconclusive"),
        ([-0.3, -0.1], 0.1, "unsupported"),
        ([-0.1, 0.2], -0.05, "unsupported"),
        ([-0.1, 0.2], 0.05, "inconclusive"),
    ],
)
def test_verdict_rule(ci, holdout_slope, expected):
    assert study.verdict({"slope_ci": ci}, {"slope": holdout_slope}) == expected


def test_cli_writes_reproducible_outputs(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    for symbol in ("QQQ", "SPY"):
        bars = momentum_days(0.5).rename(columns=str.lower).rename_axis("timestamp")
        bars.reset_index().to_parquet(raw / f"{symbol}_minute.parquet", index=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", "data")
    cli.main(["research", "momentum", "--n-boot", "100", "--out", "out"])

    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert summary["git_sha"] and summary["settings"]["seed"] == 0
    assert set(summary["symbols"]) == {"QQQ", "SPY"}
    assert summary["symbols"]["QQQ"]["coverage"]["included"] == len(DAYS)
    assert "verdict" in (tmp_path / "out" / "report.md").read_text()
    daily = pd.read_csv(tmp_path / "out" / "daily.csv")
    assert set(daily.split) == {"exploration", "validation", "holdout"}
    assert summary["symbols"]["QQQ"]["verdict"] == "inconclusive"  # 7-day holdout < 10 days
