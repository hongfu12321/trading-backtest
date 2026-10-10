# Research 001 — Intraday Momentum in QQQ and SPY

**Status:** Proposed; no results yet.  
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
