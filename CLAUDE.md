# Claude Code Instructions — trading-backtest

## Purpose
Build a reproducible intraday market-data research and backtesting system. Prioritize correct causal inference, honest statistical evaluation, and reliable execution simulation over attractive backtest results.

## Project conventions
- Python >=3.12; use `uv run` for Python commands.
- Existing entry point: `trading-backtest` CLI.
- Preserve existing CLI commands, Parquet schemas, strategy behavior, and public APIs unless an issue explicitly authorizes a change.
- Existing regular session: 09:30–16:00 America/New_York. Account for DST, exchange holidays, and early closes.
- Never commit `.env`, API keys, downloaded market data, or large generated reports.
- Do not place trades or add live trading without explicit authorization.

## Research integrity (mandatory)
1. No look-ahead bias: at signal time, only use information that would have been available then. A completed minute candle cannot be acted upon before its close; document next-bar fill assumptions.
2. Separate descriptive *ex-post* analysis from causal, tradeable signals. Never use a full-day label to make a morning decision.
3. Handle survivorship bias, corporate actions, missing bars, and data-vendor limitations explicitly when relevant.
4. Model spread, commission, slippage, order timing, and session flattening. Do not claim simulated fills are guaranteed.
5. Distinguish in-sample exploration, validation, and untouched out-of-sample testing. Never tune on the final holdout.
6. Report baselines, sample counts, uncertainty, and results by year/regime. Avoid selecting only winning configurations.
7. Record dataset coverage, symbols, timezone, strategy parameters, costs, random seeds, and git commit SHA for reproducibility.
8. State limitations and failed hypotheses clearly. Do not claim a profitable edge based only on positive average returns or win rate.

## Implementation workflow
- Read the linked research/design document and inspect existing code before editing.
- Implement the smallest testable increment; add deterministic offline unit tests.
- Tests should cover timestamp boundaries, incomplete/early-close sessions, future-data invariance, and cost sensitivity where applicable.
- Run `uv run pytest` and `uv run ruff check .`; report results and any pre-existing failures.
- Create focused commits and a PR against `initial-backtester`. Do not push directly to `main`.
- PR description: objective, methodology, files changed, tests, limitations, reproducible run commands.
- Do not automatically merge PRs; leave review decisions to the user.

## Research directory conventions
- `docs/research/`: hypotheses and research designs.
- `docs/designs/`: implementation architecture/design documents.
- `reports/experiments/`: generated results; prefer small manifests/summaries in Git, large datasets remain local/ignored.
