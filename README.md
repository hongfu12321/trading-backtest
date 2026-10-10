# trading-backtest

Backtest intraday (day-trading) strategies on minute bars from [Massive](https://massive.com).

## Setup

```bash
uv sync
cp .env.example .env   # then add your MASSIVE_API_KEY
```

## Usage

```bash
# Download a year of minute bars for one or more symbols to data/raw/<SYMBOL>_minute.parquet.
# Safe to interrupt and rerun: finished 30-day chunks are kept and skipped next time.
uv run trading-backtest download QQQ SPY --start 2025-10-08 --end 2026-10-08

# Backtest the opening range breakout with default params; writes reports/orb_QQQ/
uv run trading-backtest backtest orb --symbol QQQ

# Custom params, date range, and an HTML chart
uv run trading-backtest backtest orb --param range_minutes=30 --start 2026-01-01 --plot

# Grid search on data before the split date, then evaluate the winner on data after it
uv run trading-backtest backtest orb --optimize range_minutes=5,15,30,60 --split 2026-06-01
```

Each download writes `<SYMBOL>_minute.json` (date ranges fully downloaded) and
`<SYMBOL>_minute.validation.json` (duplicates, bad prices, incomplete or early-close
sessions, and so on). Problems are reported, not repaired.

Each backtest writes `trades.csv`, `equity.csv`, `by_day.csv`, `by_entry_time.csv` and
`summary.json` (params, symbol, data range, costs, metrics) to `reports/<strategy>_<symbol>/`,
with `in_sample/` and `out_of_sample/` subfolders when `--split` is used.

## Execution model

- Regular hours only (9:30–16:00 ET). Signals use completed bars; market orders fill at the
  next bar's open.
- Positions are flattened in the last 5 minutes of each session: 15:55 normally, 12:55 on
  NYSE early-close days (from the `exchange_calendars` XNYS calendar), whose after-hours
  bars are ignored. Pending entry orders are cancelled
  there, and no entry can fill inside that window, so nothing is held overnight.
- Sessions with fewer than two bars in that window cannot be flattened without inventing a
  price, so they are skipped with a warning.
- Stops fill at the stop price, or at the open if the price gaps through it. If a stop and a
  target are both inside one bar, the stop is assumed hit.
- `--spread` (default 0.01%) is charged once per trade on entry; `--commission` on both sides.
  A fixed spread understates costs for illiquid or volatile stocks, so raise it for those.
- Orders use ~100% of equity in whole shares, no margin.
- ORB: the range is built only from bars already seen and is complete at `range_minutes`.
  A close beyond it signals; days missing the 9:30 bar are not traded. On the first day of
  a dataset, backtesting.py skips bars until the indicator has a value, so the first bar
  after the range cannot signal on that day only.

## Indicators and features

Causal building blocks for strategies: pandas in, pandas out, same index as the input. A
value at bar t uses only bars up to and including t (a timestamp is the bar's *start*, so
act on it after t closes). Sessions, holidays, early closes and DST come from the NYSE
calendar (`exchange_calendars`). Bad input (naive or unsorted index, duplicates, NaN,
inconsistent OHLC) raises `ValueError`.

| Function | Output | Notes |
|---|---|---|
| `features.session_info(df)` | session date, minute of session, open/close, regular flag | off-session bars marked, not assigned |
| `features.opening_range(df, minutes)` | `OR_High/Low/Mid/Complete` | final on the completing bar; never if a range bar is missing |
| `features.previous_day_levels(df)` | `PDH/PDL/Prev_Close` | previous exchange session; NaN if it is incomplete |
| `features.intraday_levels(df)` | `HOD/LOD`, `*_Previous_Bar` | reset each session |
| `features.complete_sessions(df)` | bool per session | retrospective data quality, not a live signal |
| `indicators.session_vwap(df)` | `VWAP` | bar-based (hlc3) approximation, resets 9:30 |
| `indicators.ema(close, period)` | `EMA{period}` | `adjust=False`, NaN for first period-1 bars, no daily reset |
| `indicators.atr(df, period)` | `ATR{period}` | Wilder; seed = mean of first `period` true ranges |
| `indicators.cumulative_rvol(df, n)` | `RVOL` | vs. mean of last n full, complete sessions at the same minute |

```python
from pathlib import Path

from trading_backtest.data import load_bars
from trading_backtest.features import opening_range
from trading_backtest.indicators import ema, session_vwap

bars = load_bars(Path("data/raw/QQQ_minute.parquet"))
vwap = session_vwap(bars)
ema20 = ema(bars.Close, 20)
orb = opening_range(bars, minutes=15)
```

In a backtesting.py strategy, compute once in `init()`:
`self.vwap = self.I(lambda: session_vwap(self.data.df).to_numpy())`.

## Layout

```
src/trading_backtest/
  cli.py               command-line entry point
  config.py            settings from environment / .env
  engine.py            run/optimize backtests with a shared cost model
  sessions.py          NYSE session schedule and flatten window
  data/massive.py      Massive API client and resumable downloader
  data/store.py        parquet storage, download manifest, loading
  data/validation.py   data-quality report
  analytics/metrics.py trade metrics and report files
  indicators/          VWAP, EMA, ATR, cumulative RVOL
  features/            session metadata, opening range, previous-day and intraday levels
  strategies/base.py   IntradayStrategy: session-aware flattening
  strategies/orb.py    opening range breakout
tests/
```

## Adding a strategy

1. Create `strategies/my_strategy.py` with a subclass of `IntradayStrategy`; declare tunable
   params as class attributes and put the trading logic in `on_bar()`.
2. Register it in `STRATEGIES` in `strategies/__init__.py`.
3. `uv run pytest` checks every registered strategy runs and closes trades the same day.

## Development

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
```
