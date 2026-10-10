"""Research 001: does the first half hour predict the last half hour? (QQQ, SPY)

See docs/research/001-intraday-momentum.md. Everything below was fixed before the study
was run on real data; nothing is tuned on results.

Timestamps mark the *start* of each one-minute bar, in New York time, regular session only.
Boundary prices:

- `p_open`:  Open of the 09:30 bar (first regular-session trade; not the official auction).
- `p_1000`:  Close of the 09:59 bar, i.e. the last price before 10:00:00.
- `p_1530`:  Close of the 15:29 bar, the last price before 15:30:00.
- `p_close`: Close of the 15:59 bar (last regular-session minute; a proxy for the
  closing-auction price, which minute bars do not report).
- `p_prev_close`: `p_close` of the previous exchange session, if in the data.

Returns: `r_open = p_1000 / p_open - 1` (primary), `r_open_overnight = p_1000 /
p_prev_close - 1` (the first half-hour return as used by Gao et al. 2018, from the previous
close; not verified against the paper's text), `r_close = p_close / p_1530 - 1`, and
`r_mid = p_1530 / p_1000 - 1`.

Days are excluded (with a reason, never filled) when they close early (their windows end
at 13:00) or lack any boundary bar. Other missing minutes are counted but kept.

Phase B statistics are descriptive and ex post: they use same-day closing returns.
Phase C trades only use `r_open`, which is known at 10:00:
- `last_half_hour`: side = sign(r_open), enter at the 15:30 bar's Open, exit at `p_close`.
- `from_1000`: side = sign(r_open), enter at the 10:00 bar's Open, exit at `p_close`.
Costs are a round-trip charge in basis points of notional (spread + slippage +
commission); the base case is `BASE_COST_BPS`, with `COST_GRID_BPS` as sensitivity.
"""

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from trading_backtest import sessions
from trading_backtest.features import session_info

BOUNDARY_MINUTES = {"p_open": (0, "Open"), "p_1000": (29, "Close"), "p_1000_entry": (30, "Open"),
                    "p_1530": (359, "Close"), "p_1530_entry": (360, "Open"),
                    "p_close": (389, "Close")}  # fmt: skip
BASE_COST_BPS = 2.0
COST_GRID_BPS = [0.0, 1.0, 2.0, 5.0, 10.0]
SPLITS = {"exploration": 0.50, "validation": 0.25, "holdout": 0.25}  # chronological
NW_LAGS = 5
VARIANTS = {"last_half_hour": "p_1530_entry", "from_1000": "p_1000_entry"}


@dataclass(frozen=True)
class Settings:
    symbols: tuple[str, ...] = ("QQQ", "SPY")
    seed: int = 0
    n_boot: int = 2000
    base_cost_bps: float = BASE_COST_BPS
    cost_grid_bps: tuple[float, ...] = tuple(COST_GRID_BPS)
    splits: dict = field(default_factory=lambda: dict(SPLITS))


# --- Phase A: per-day windows ---


def daily_windows(bars: pd.DataFrame) -> pd.DataFrame:
    """One row per regular session with boundary prices, returns and exclusion reasons."""
    info = session_info(bars)
    reg = info.is_regular_session.to_numpy()
    df = bars[reg].assign(day=info.session_date[reg], minute=info.minute_of_session[reg])
    df["ret"] = df.Close.groupby(df.day).pct_change()

    by_day = df.groupby("day")
    out = pd.DataFrame(
        {
            "n_bars": by_day.size(),
            "scheduled_minutes": sessions_length(by_day.minute.size().index),
            "day_volatility": by_day.ret.std(),
            "day_volume": by_day.Volume.sum(),
        }
    )
    out["missing_minutes"] = out.scheduled_minutes - out.n_bars
    out["early_close"] = out.scheduled_minutes < 390
    for name, (minute, col) in BOUNDARY_MINUTES.items():
        rows = df[df.minute == minute].set_index("day")[col]
        out[name] = rows.reindex(out.index)

    cal = sessions.calendar()
    prev = [cal.previous_session(d).tz_localize(None) for d in out.index]
    out["p_prev_close"] = out.p_close.where(~out.early_close).reindex(prev).to_numpy()

    out["r_open"] = out.p_1000 / out.p_open - 1
    out["r_open_overnight"] = out.p_1000 / out.p_prev_close - 1
    out["r_mid"] = out.p_1530 / out.p_1000 - 1
    out["r_close"] = out.p_close / out.p_1530 - 1

    reason = pd.Series("", index=out.index)
    reason[out.early_close] = "early_close"
    core = ["p_open", "p_1000", "p_1530", "p_close"]
    missing = out[core].isna().any(axis=1) & ~out.early_close
    reason[missing] = "missing_boundary_bar"
    out["exclude_reason"] = reason
    out["included"] = reason == ""
    out.index.name = "date"
    return out


def sessions_length(days: pd.Index) -> pd.Series:
    s = sessions.schedule(days.min().date(), days.max().date())
    length = (s.close - s.open).dt.total_seconds() // 60
    length.index = pd.to_datetime(length.index)
    return length.reindex(days).astype(int)


def split_labels(dates: pd.Index, splits: dict = SPLITS) -> pd.Series:
    """Label sorted dates chronologically by the given fractions (no shuffling)."""
    dates = pd.Index(sorted(dates.unique()))
    edges = np.cumsum([0, *splits.values()]) * len(dates)
    labels = np.empty(len(dates), dtype=object)
    for (name, _), lo, hi in zip(splits.items(), edges[:-1], edges[1:], strict=True):
        labels[int(round(lo)) : int(round(hi))] = name
    return pd.Series(labels, index=dates)


# --- Phase B: descriptive statistics ---


def _ols_slope(x, y):
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / (xc**2).sum())


def newey_west_t(x: np.ndarray, y: np.ndarray, lags: int = NW_LAGS) -> float:
    """t-statistic of the OLS slope of y on x with Newey-West (Bartlett) standard errors."""
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    xu = X * u[:, None]
    S = xu.T @ xu
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1 - lag / (lags + 1)
        g = xu[lag:].T @ xu[:-lag]
        S += w * (g + g.T)
    inv = np.linalg.inv(X.T @ X)
    cov = inv @ S @ inv
    return float(beta[1] / np.sqrt(cov[1, 1]))


def _boot_ci(values: np.ndarray, rng: np.random.Generator, n_boot: int, stat) -> list[float]:
    """95% percentile CI, resampling whole days with replacement."""
    n = len(values)
    draws = [stat(values[rng.integers(0, n, n)]) for _ in range(n_boot)]
    return [float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5))]


def describe(days: pd.DataFrame, x: str = "r_open", *, seed: int = 0, n_boot: int = 2000) -> dict:
    """Correlation, slope, sign agreement, quintile means and baselines of r_close on x."""
    d = days[[x, "r_close"]].dropna()
    n = len(d)
    if n < 10:
        return {"n": n}
    rng = np.random.default_rng(seed)
    xy = d.to_numpy()
    x_, y_ = xy[:, 0], xy[:, 1]
    sign_timed = np.sign(x_) * y_
    quintile = pd.qcut(d[x], 5, labels=[f"Q{i}" for i in range(1, 6)])
    return {
        "n": n,
        "pearson": float(np.corrcoef(x_, y_)[0, 1]),
        "pearson_ci": _boot_ci(xy, rng, n_boot, lambda s: np.corrcoef(s[:, 0], s[:, 1])[0, 1]),
        "spearman": float(d[x].rank().corr(d.r_close.rank())),
        "slope": _ols_slope(x_, y_),
        "slope_ci": _boot_ci(xy, rng, n_boot, lambda s: _ols_slope(s[:, 0], s[:, 1])),
        "slope_t_nw": newey_west_t(x_, y_),
        "sign_agreement": float((np.sign(x_) == np.sign(y_)).mean()),
        "sign_agreement_ci": _boot_ci(
            xy, rng, n_boot, lambda s: (np.sign(s[:, 0]) == np.sign(s[:, 1])).mean()
        ),
        "r_close_by_quintile_bps": (d.r_close.groupby(quintile, observed=True).mean() * 1e4)
        .round(3)
        .to_dict(),
        "baselines_bps": {
            "unconditional_mean_r_close": float(y_.mean() * 1e4),
            "always_long": float(y_.mean() * 1e4),
            "always_short": float(-y_.mean() * 1e4),
            "sign_of_r_open": float(sign_timed.mean() * 1e4),
        },
        "sign_of_r_open_ci_bps": [v * 1e4 for v in _boot_ci(sign_timed, rng, n_boot, np.mean)],
    }


# --- Phase C: executable trades ---


def trades(days: pd.DataFrame, variant: str, cost_bps: float) -> pd.DataFrame:
    """Per-day trades for a variant: side from sign(r_open), net of round-trip cost."""
    entry = days[VARIANTS[variant]]
    side = np.sign(days.r_open)
    t = pd.DataFrame({"side": side, "entry": entry, "exit": days.p_close})
    t = t[(t.side != 0) & t.notna().all(axis=1)]
    t["gross"] = t.side * (t.exit / t.entry - 1)
    t["net"] = t.gross - cost_bps / 1e4
    return t


def trade_metrics(net: pd.Series, *, seed: int = 0, n_boot: int = 2000) -> dict:
    if len(net) < 2:
        return {"n_trades": len(net)}
    wins, losses = net[net > 0], net[net <= 0]
    equity = net.cumsum()
    rng = np.random.default_rng(seed)
    return {
        "n_trades": len(net),
        "mean_net_bps": float(net.mean() * 1e4),
        "mean_net_ci_bps": [v * 1e4 for v in _boot_ci(net.to_numpy(), rng, n_boot, np.mean)],
        "t_stat": float(net.mean() / net.std(ddof=1) * np.sqrt(len(net))),
        "win_rate": float(len(wins) / len(net)),
        "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else None,
        "total_return_pct": float(net.sum() * 100),
        "max_drawdown_pct": float((equity - equity.cummax()).min() * 100),
    }


# --- Study runner ---


def verdict(full: dict, holdout: dict) -> str:
    """Pre-registered rule on the primary definition (r_open vs r_close slope).

    supported: full-sample slope CI above zero and holdout slope positive.
    unsupported: full-sample CI below zero, or CI spans zero and holdout slope <= 0.
    inconclusive: anything else.
    """
    if "slope_ci" not in full or "slope" not in holdout:
        return "inconclusive"
    lo, hi = full["slope_ci"]
    if lo > 0 and holdout["slope"] > 0:
        return "supported"
    if hi < 0 or (lo <= 0 <= hi and holdout["slope"] <= 0):
        return "unsupported"
    return "inconclusive"


def git_sha() -> str:
    """Commit of the code being run (with -dirty if it has local changes), or "unknown"."""
    repo = Path(__file__).resolve().parent
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
        )
    except OSError:
        return "unknown"
    if sha.returncode:
        return "unknown"
    return sha.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def run(bars_by_symbol: dict[str, pd.DataFrame], settings: Settings) -> tuple[dict, pd.DataFrame]:
    """Run phases A-D; return a JSON-ready summary and the per-day table."""
    kw = {"seed": settings.seed, "n_boot": settings.n_boot}
    frames = []
    for symbol, bars in bars_by_symbol.items():
        frames.append(daily_windows(bars).assign(symbol=symbol))
    daily = pd.concat(frames)
    labels = split_labels(daily.index, settings.splits)
    daily["split"] = labels.reindex(daily.index).to_numpy()
    daily["year"] = daily.index.year

    summary = {
        "study": "001-intraday-momentum",
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "settings": asdict(settings),
        "timezone": sessions.TZ,
        "split_ranges": {
            name: [str(g.index.min().date()), str(g.index.max().date())]
            for name, g in labels.groupby(labels)
        },
        "symbols": {},
    }
    for symbol, d in daily.groupby("symbol"):
        inc = d[d.included]
        s = {
            "coverage": {
                "first": str(d.index.min().date()),
                "last": str(d.index.max().date()),
                "sessions": len(d),
                "included": len(inc),
                "excluded": d.exclude_reason[~d.included].value_counts().to_dict(),
                "days_with_missing_minutes": int((d.missing_minutes > 0).sum()),
            },
            "descriptive": {
                "full": describe(inc, **kw),
                "overnight_definition": describe(inc, "r_open_overnight", **kw),
                "by_year": {str(y): describe(g, **kw) for y, g in inc.groupby("year")},
                "by_split": {k: describe(g, **kw) for k, g in inc.groupby("split")},
            },
            "trades": {},
        }
        for variant in VARIANTS:
            base = trades(inc, variant, settings.base_cost_bps)
            split_of = inc.split.reindex(base.index)
            long_only = (inc.p_close / inc[VARIANTS[variant]] - 1).dropna()
            s["trades"][variant] = {
                "by_split": {
                    k: trade_metrics(base.net[split_of == k], **kw) for k in settings.splits
                },
                "by_year": {
                    str(y): trade_metrics(g.net, **kw) for y, g in base.groupby(base.index.year)
                },
                "cost_sensitivity_mean_net_bps": {
                    str(c): float(trades(inc, variant, c).net.mean() * 1e4)
                    for c in settings.cost_grid_bps
                },
                "always_long_mean_net_bps": float(
                    (long_only - settings.base_cost_bps / 1e4).mean() * 1e4
                ),
                "no_trade_mean_net_bps": 0.0,
            }
        s["verdict"] = verdict(
            s["descriptive"]["full"], s["descriptive"]["by_split"].get("holdout", {})
        )
        summary["symbols"][symbol] = s
    return summary, daily


def write_outputs(summary: dict, daily: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    daily.round(8).to_csv(out_dir / "daily.csv")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    (out_dir / "report.md").write_text(render_report(summary))


def _fmt(v, digits=3):
    if v is None:
        return "–"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x, digits) for x in v) + "]"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def render_report(summary: dict) -> str:
    """Markdown report generated from the summary (figures only; no interpretation)."""
    lines = [
        "# Research 001 — results",
        "",
        f"Run {summary['run_at']} at commit `{summary['git_sha']}`. "
        f"Definitions: `src/trading_backtest/research/intraday_momentum.py`.",
        "",
        f"Splits (chronological, fixed before running): {summary['split_ranges']}. "
        f"Base cost {summary['settings']['base_cost_bps']} bps round trip; "
        f"bootstrap {summary['settings']['n_boot']} draws, seed {summary['settings']['seed']}.",
    ]
    for symbol, s in summary["symbols"].items():
        cov, full = s["coverage"], s["descriptive"]["full"]
        lines += [
            "",
            f"## {symbol} — verdict: **{s['verdict']}**",
            "",
            f"Coverage {cov['first']} to {cov['last']}: {cov['sessions']} sessions, "
            f"{cov['included']} included, excluded {cov['excluded'] or 'none'}, "
            f"{cov['days_with_missing_minutes']} with missing minutes.",
            "",
            "| Sample | n | Pearson [95% CI] | Spearman | Slope [95% CI] | NW t | Sign agree "
            "| Sign-timed bps [95% CI] |",
            "|---|---|---|---|---|---|---|---|",
        ]
        samples = {"full": full, "overnight def.": s["descriptive"]["overnight_definition"]}
        samples |= {f"split {k}": v for k, v in s["descriptive"]["by_split"].items()}
        samples |= {f"year {k}": v for k, v in s["descriptive"]["by_year"].items()}
        for name, d in samples.items():
            if "pearson" not in d:
                lines.append(f"| {name} | {d['n']} | too few days | | | | | |")
                continue
            lines.append(
                f"| {name} | {d['n']} | {_fmt(d['pearson'])} {_fmt(d['pearson_ci'])} "
                f"| {_fmt(d['spearman'])} | {_fmt(d['slope'])} {_fmt(d['slope_ci'])} "
                f"| {_fmt(d['slope_t_nw'], 2)} | {_fmt(d['sign_agreement'])} "
                f"| {_fmt(d['baselines_bps']['sign_of_r_open'], 2)} "
                f"{_fmt(d['sign_of_r_open_ci_bps'], 2)} |"
            )
        lines += [
            "",
            f"Mean r_close by r_open quintile (bps, full sample): "
            f"{full.get('r_close_by_quintile_bps')}. Unconditional mean r_close: "
            f"{_fmt(full.get('baselines_bps', {}).get('unconditional_mean_r_close'), 2)} bps.",
        ]
        for variant, t in s["trades"].items():
            lines += [
                "",
                f"### Trades: `{variant}` (net of {summary['settings']['base_cost_bps']} bps)",
                "",
                "| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Total % | Max DD % |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for k, m in t["by_split"].items():
                if "mean_net_bps" not in m:
                    lines.append(f"| {k} | {m['n_trades']} | | | | | | |")
                    continue
                lines.append(
                    f"| {k} | {m['n_trades']} | {_fmt(m['mean_net_bps'], 2)} "
                    f"{_fmt(m['mean_net_ci_bps'], 2)} | {_fmt(m['t_stat'], 2)} "
                    f"| {_fmt(m['win_rate'])} | {_fmt(m['profit_factor'], 2)} "
                    f"| {_fmt(m['total_return_pct'], 2)} | {_fmt(m['max_drawdown_pct'], 2)} |"
                )
            costs = {k: round(v, 2) for k, v in t["cost_sensitivity_mean_net_bps"].items()}
            lines += [
                "",
                f"Mean net bps by round-trip cost: {costs}. Always-long same window: "
                f"{_fmt(t['always_long_mean_net_bps'], 2)} bps; no trade: 0.",
            ]
    return "\n".join(lines) + "\n"
