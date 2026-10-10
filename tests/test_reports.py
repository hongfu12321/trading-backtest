import json

import pandas as pd
import pytest
from test_strategies import breakout_day, random_bars

from trading_backtest import cli, engine
from trading_backtest.analytics import metrics
from trading_backtest.strategies.orb import OpeningRangeBreakout


def test_r_multiple_uses_actual_fill_and_stop():
    df = breakout_day("2025-01-06")  # long at 101.5, stop 99, flattened at 100
    stats = engine.run(df, OpeningRangeBreakout, costs=engine.CostModel(spread=0.0))
    m = metrics.summarize(stats)
    assert m["total_trades"] == 1 and m["win_rate"] == 0
    assert m["avg_r"] == pytest.approx((100 - 101.5) / (101.5 - 99))


def test_costs_lower_net_pnl():
    df = breakout_day("2025-01-06")
    free = metrics.summarize(engine.run(df, OpeningRangeBreakout, costs=engine.CostModel(0, 0)))
    paid = metrics.summarize(engine.run(df, OpeningRangeBreakout))
    assert paid["net_pnl"] < free["net_pnl"]


def bars_file(tmp_path, df):
    raw = df.rename(columns=str.lower).rename_axis("timestamp").reset_index()
    path = tmp_path / "data" / "raw" / "QQQ_minute.parquet"
    path.parent.mkdir(parents=True)
    raw.to_parquet(path, index=False)


def test_cli_split_optimizes_in_sample_and_reports_both(tmp_path, monkeypatch, capsys):
    bars_file(tmp_path, random_bars(n_days=10))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", "data")
    cli.main(["backtest", "orb", "--split", "2025-01-13", "--optimize", "range_minutes=5,15,30"])
    out = tmp_path / "reports" / "orb_QQQ"
    ins = json.loads((out / "in_sample" / "summary.json").read_text())
    oos = json.loads((out / "out_of_sample" / "summary.json").read_text())
    assert ins["params"] == oos["params"]
    assert ins["data_end"] < "2025-01-13" <= oos["data_start"]
    trades = pd.read_csv(out / "out_of_sample" / "trades.csv")
    assert (trades.EntryTime >= "2025-01-13").all()
    for name in ("equity.csv", "by_day.csv", "by_entry_time.csv"):
        assert (out / "in_sample" / name).exists()
