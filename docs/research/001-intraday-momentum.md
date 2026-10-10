# Research 001 — Intraday Momentum in QQQ and SPY

**Status:** First run complete (Issue #1). Verdict: **inconclusive** for QQQ and SPY; no tradeable edge found.  
**Scope:** Research first, trading strategy later.  
**Primary reference:** Gao, Han, Li, and Zhou (2018), *Market Intraday Momentum*, Journal of Financial Economics. Verify the original paper's exact definitions and samples before claiming replication.

## Research question
Does the return in the first 30 minutes of regular trading predict the return in the final 30 minutes of the *same day* for QQQ and SPY, and does this relationship remain stable across 2022–2026?

This is a research hypothesis, **not** an established profitable trading rule for these instruments.

## Phase A — Data and definitions
- Instruments: QQQ, SPY; 1-minute OHLCV; regular session in America/New_York.
- Proposed study range: 2022-01-01 through latest available 2026 date. Explicitly disclose actual vendor coverage.
- Define opening return using prices available at 09:30 open and 10:00 boundary; closing-window return using the 15:30 boundary and 16:00 close. Specify exact minute-bar alignment, timestamp semantics, and whether boundary prices are executable.
- Calculate daily opening-window and closing-window returns, plus full-day volatility and volume for **descriptive** analyses only.
- Flag and separately handle early closes, holidays, missing candles, duplicates, splits/adjustments, and partial sessions.
- Do not fill missing minute bars with fabricated OHLCV values.

## Phase B — Descriptive event study
- Scatterplot opening return vs. closing-window return, by instrument and year.
- Report Pearson/Spearman correlation, sign agreement, conditional means by opening-return quantile, observations, and uncertainty.
- Use robust inference (e.g. HAC or day-block bootstrap) when justified; explain assumptions.
- Compare to unconditional closing-window mean, always-long, always-short, and a simple sign-based baseline.
- Report all years including negative or inconclusive results. Do not optimize bins and report them as pre-registered findings.

## Phase C — Executable experiment (separate from correlation)
- A signal known by 10:00 cannot enter at 09:30 or use information from the close.
- Test a clearly specified trade entered at/after 10:00, held to a defined exit, versus the paper's specific opening-to-closing-window relationship. Do not conflate the two.
- If entering at 15:30 for the final half hour, explicitly distinguish this from an all-day hold.
- Model bid/ask spread, slippage, commission, next-bar execution, and position sizing. Test cost sensitivity.
- Include no-trade baselines and realistic opportunity counts.

## Phase D — Generalization
- Split data chronologically into exploration/validation/final holdout; choose exact cutoffs before inspecting results.
- Compare QQQ and SPY separately and across calendar years.
- Explore volatility and volume conditions **only after** baseline is established, and ensure trading filters use information known before entry.
- Report confidence intervals, trade count, net expectancy, drawdown, profit factor, and parameter stability.
- Treat multiple-testing and overlapping observations carefully.

## Deliverables
1. A reproducible research CLI or script, without breaking existing `trading-backtest` commands.
2. Offline synthetic-data tests for timestamps, causality, missing bars, and expected statistics.
3. Machine-readable per-day results and a summary by symbol/year.
4. Markdown report documenting exact definitions, data coverage, methodology, costs, baselines, findings, and limitations.
5. Clear verdict: supported / unsupported / inconclusive; no profit claims without out-of-sample evidence.

## Implementation boundaries
- **Do not** modify existing ORB strategy behavior as part of this research.
- **Do not** fetch news or build a sentiment model.
- **Do not** tune thresholds against the final test set.
- Request user confirmation before any large paid API download or data-source upgrade.

## Reference
- Gao et al., *Market Intraday Momentum* (2018). Source: https://www.sciencedirect.com/science/article/pii/S0304405X18301351

## Results (Issue #1, revised after PR #3 review)

Full figures: [`reports/experiments/001-intraday-momentum/report.md`](../../reports/experiments/001-intraday-momentum/report.md); per-day data and run settings (seed 0, 2000 bootstrap draws in 5-day blocks, git SHA) in `daily.csv` and `summary.json` next to it. Reproduce with `uv run trading-backtest research momentum`.

**Coverage.** 2024-10-09 to 2026-10-08 only (501 sessions per symbol; 496 used, 5 early closes excluded; no missing minutes). The current Massive plan returns 403 for older minute data, so 2022–2024 is **not** covered; extending it needs a paid upgrade, which was not requested.

**Definitions as run.** A bar's timestamp is its start (ET); the 09:59 bar's Close is the last trade before 10:00:00, so the signal exists at 10:00:00 at the earliest. r_open = 09:59 close / 09:30 open − 1; r_close = 15:59 close / 15:29 close − 1. A previous-close-to-10:00 variant is reported as a sensitivity check. Gao et al. (2018) motivate the question, but their exact definitions were not checked against the paper, so this is **not a replication**. Splits fixed before the first run: exploration 2024-10-09–2025-10-08, validation 2025-10-09–2026-04-10, holdout 2026-04-13–2026-10-08.

**Decision rule (revised).** The decision uses exploration + validation days only: supported if the slope's 95% CI is above zero, unsupported if below, inconclusive if it spans zero. The holdout is consulted once, and only to confirm a supported decision. The first run's rule mixed full-sample (holdout-including) CIs with the holdout slope; review flagged this and it was changed. Note the holdout figures were already seen in that first run, so the holdout is not pristine; the new rule does not use it for these results.

**Findings.**
- Development decision **inconclusive** for both: slope 0.029 (QQQ) and 0.042 (SPY), 95% CIs [−0.048, 0.093] and [−0.085, 0.156]; the same with 1-, 5- and 20-day bootstrap blocks. Spearman ≈ 0, sign agreement below 50%. The previous-close variant is also ≈ 0.
- Unstable: slope positive in exploration, negative in validation, ≈ 0 in the holdout; positive in 2025, negative in 2026.
- `last_half_hour` (enter 15:30) and `last_half_hour_1531`: negative in every split for both symbols, slightly negative before costs.
- `from_1000` (enter 10:00): positive only in exploration (+7 bps at 2 bps cost); negative in validation and holdout. With one minute of latency (`from_1001`) the full-sample mean drops by about 0.4–0.7 bps; the pattern is the same.

**Verdict: inconclusive** for QQQ and SPY. No tradeable edge was found; the data shows no usable intraday momentum in these ETFs over this period.

**Limitations.** Two years only, one regime; no 2022 bear market. Minute-bar Close of 15:59 stands in for the closing auction, and the 09:30 bar's Open for the opening auction. Adjusted prices from a single vendor. Costs are a flat round-trip bps charge with no market-impact model. Trade sums and drawdowns assume a fixed notional per trade (no compounding). Block bootstrap CIs assume dependence dies out within the block length (reported for 1/5/20 days); Newey-West uses 5 lags. Quintile bins are computed ex post on the full sample and are descriptive only.
