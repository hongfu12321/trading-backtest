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
  early-close days (a day whose bars end before 13:00). Pending entry orders are cancelled
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
