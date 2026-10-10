# trading-backtest

Backtest intraday (day-trading) strategies on minute bars from [Massive](https://massive.com).

## Setup

```bash
uv sync
cp .env.example .env   # then add your MASSIVE_API_KEY
```

## Usage

```bash
# Download a year of QQQ minute bars to data/raw/QQQ_minute.parquet (merges with existing data)
uv run trading-backtest download QQQ --start 2025-10-08 --end 2026-10-08

# Backtest the opening range breakout with default params
uv run trading-backtest backtest orb --symbol QQQ

# Custom params, date range, and an HTML chart in reports/
uv run trading-backtest backtest orb --param range_minutes=30 --start 2026-01-01 --plot

# Grid search
uv run trading-backtest backtest orb --optimize range_minutes=5,15,30,60
```

Backtests use regular hours only (9:30–16:00 ET), flatten positions at 15:55, and charge a
0.01% spread per trade by default (`--spread`, `--commission` to change).

## Layout

```
src/trading_backtest/
  cli.py              command-line entry point
  config.py           settings from environment / .env
  engine.py           run/optimize backtests with a shared cost model
  data/massive.py     Massive API client (chunking, pagination, rate limits)
  data/store.py       parquet storage and loading
  strategies/base.py  IntradayStrategy: end-of-day flattening, minute-of-day helper
  strategies/orb.py   opening range breakout
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
