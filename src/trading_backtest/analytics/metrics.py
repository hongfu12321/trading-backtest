"""Trade-level metrics and reproducible report files for a backtest run.

`PnL` from backtesting.py is net of spread (in the entry price) and commission. R-multiples
use the actual fill: initial risk = |EntryPrice - SL| x shares. Trades without a stop have
no R value. Strategies here never move their stop, so the recorded SL is the initial one.
"""

import json
from pathlib import Path

import pandas as pd


def summarize(stats: pd.Series) -> dict:
    t = stats._trades
    wins, losses = t.PnL[t.PnL > 0], t.PnL[t.PnL <= 0]
    risk = (t.EntryPrice - t.SL).abs() * t.Size.abs()
    r = (t.PnL / risk).where(risk > 0)
    return {
        "total_trades": len(t),
        "win_rate": len(wins) / len(t) if len(t) else None,
        "avg_win": wins.mean() if len(wins) else None,
        "avg_loss": losses.mean() if len(losses) else None,
        "profit_factor": wins.sum() / -losses.sum() if losses.sum() < 0 else None,
        "expectancy": t.PnL.mean() if len(t) else None,
        "avg_r": r.mean() if r.notna().any() else None,
        "net_pnl": t.PnL.sum(),
        "total_commission": t.Commission.sum(),
        "max_drawdown_pct": stats["Max. Drawdown [%]"],
        "return_pct": stats["Return [%]"],
    }


def breakdown(trades: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    return trades.PnL.groupby(key.values).agg(trades="count", net_pnl="sum", avg_pnl="mean")


def write_report(stats: pd.Series, out_dir: Path, meta: dict) -> dict:
    """Write trades, equity curve, per-day and per-entry-time P&L, and a summary JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t = stats._trades
    t.to_csv(out_dir / "trades.csv", index=False)
    stats._equity_curve.to_csv(out_dir / "equity.csv")
    breakdown(t, t.ExitTime.dt.date).to_csv(out_dir / "by_day.csv", index_label="date")
    entry_slot = t.EntryTime.dt.floor("30min").dt.strftime("%H:%M")
    breakdown(t, entry_slot).to_csv(out_dir / "by_entry_time.csv", index_label="entry_time")
    summary = {**meta, "metrics": summarize(stats)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=_plain))
    return summary


def _plain(o):
    return o.item() if hasattr(o, "item") else str(o)
