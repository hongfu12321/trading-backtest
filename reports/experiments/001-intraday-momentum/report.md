# Research 001 — results

Run 2026-10-10T07:54:47+00:00 at commit `1a31e9bab35020f2ab7e292a17d5a0b268415a6e`. Definitions: `src/trading_backtest/research/intraday_momentum.py`.

Splits (chronological, fixed before the first run): {'exploration': ['2024-10-09', '2025-10-08'], 'holdout': ['2026-04-13', '2026-10-08'], 'validation': ['2025-10-09', '2026-04-10']}. Base cost 2.0 bps round trip; bootstrap 2000 draws in blocks of 5 days, seed 0.

Bar timestamps are bar starts (ET); a signal from the 09:59 bar's Close exists at 10:00:00. The decision uses exploration + validation days only; the holdout is a single final check of a supported decision (it was also seen in the first run). `full` and per-year rows are descriptive and include holdout days. Trade sums assume a fixed notional per trade (no compounding).

## QQQ — verdict: **inconclusive**

Development decision (exploration + validation): inconclusive.

Coverage 2024-10-09 to 2026-10-08: 501 sessions, 496 included, excluded {'early_close': 5}, 0 with missing minutes.

| Sample | n | Pearson [95% CI] | Spearman | Slope [95% CI] | NW t | Sign agree | Sign-timed bps [95% CI] |
|---|---|---|---|---|---|---|---|
| development | 371 | 0.048 [-0.070, 0.157] | 0.010 | 0.029 [-0.040, 0.093] | 0.82 | 0.474 | -0.44 [-3.11, 2.24] |
| full | 496 | 0.041 [-0.065, 0.139] | -0.001 | 0.024 [-0.035, 0.086] | 0.77 | 0.478 | -0.46 [-2.62, 1.84] |
| overnight def. | 490 | -0.016 [-0.150, 0.100] | -0.012 | -0.005 [-0.042, 0.026] | -0.26 | 0.504 | 0.36 [-1.79, 2.55] |
| split exploration | 247 | 0.115 [-0.019, 0.236] | 0.065 | 0.077 [-0.021, 0.154] | 1.87 | 0.486 | 0.79 [-2.34, 4.26] |
| split holdout | 125 | 0.021 [-0.201, 0.229] | -0.036 | 0.011 [-0.083, 0.141] | 0.18 | 0.488 | -0.51 [-5.16, 4.64] |
| split validation | 124 | -0.117 [-0.306, 0.083] | -0.072 | -0.057 [-0.152, 0.041] | -1.18 | 0.452 | -2.91 [-6.81, 0.92] |
| year 2024 | 56 | 0.055 [-0.121, 0.253] | 0.051 | 0.032 [-0.070, 0.129] | 0.71 | 0.482 | -1.33 [-6.93, 2.89] |
| year 2025 | 247 | 0.096 [-0.037, 0.216] | 0.029 | 0.063 [-0.030, 0.141] | 1.51 | 0.482 | 0.88 [-2.34, 4.34] |
| year 2026 | 193 | -0.048 [-0.235, 0.134] | -0.056 | -0.023 [-0.105, 0.077] | -0.51 | 0.472 | -1.92 [-5.44, 1.78] |

Mean r_close by r_open quintile (bps, full sample): {'Q1': -0.673, 'Q2': 2.436, 'Q3': 1.464, 'Q4': -1.224, 'Q5': 1.759}. Unconditional mean r_close: 0.75 bps. Development slope CI by bootstrap block length (days): {'1': '[-0.051, 0.106]', '5': '[-0.048, 0.093]', '20': '[-0.038, 0.084]'}.

### Trades: `last_half_hour` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.15 [-4.45, 2.29] | -0.60 | 0.457 | 0.89 | -2.84 | -4.84 |
| validation | 122 | -4.98 [-8.82, -1.18] | -2.43 | 0.377 | 0.56 | -6.07 | -6.22 |
| holdout | 125 | -2.49 [-7.12, 2.50] | -1.13 | 0.432 | 0.75 | -3.12 | -3.86 |

Mean net bps by round-trip cost: {'0.0': -0.44, '1.0': -1.44, '2.0': -2.44, '5.0': -5.44, '10.0': -10.44}. Always-long same window: -1.25 bps; no trade: 0.

### Trades: `last_half_hour_1531` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.01 [-4.11, 2.30] | -0.57 | 0.466 | 0.90 | -2.50 | -4.69 |
| validation | 122 | -4.70 [-8.11, -1.29] | -2.41 | 0.393 | 0.56 | -5.74 | -5.90 |
| holdout | 125 | -2.93 [-7.65, 1.99] | -1.35 | 0.432 | 0.70 | -3.67 | -4.15 |

Mean net bps by round-trip cost: {'0.0': -0.41, '1.0': -1.41, '2.0': -2.41, '5.0': -5.41, '10.0': -10.41}. Always-long same window: -1.90 bps; no trade: 0.

### Trades: `from_1000` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 7.21 [-3.12, 18.36] | 1.05 | 0.530 | 1.26 | 17.80 | -9.10 |
| validation | 122 | -5.65 [-25.16, 10.79] | -0.70 | 0.541 | 0.83 | -6.89 | -11.66 |
| holdout | 125 | -1.13 [-14.86, 12.34] | -0.17 | 0.472 | 0.96 | -1.41 | -8.83 |

Mean net bps by round-trip cost: {'0.0': 3.92, '1.0': 2.92, '2.0': 1.92, '5.0': -1.08, '10.0': -6.08}. Always-long same window: 0.05 bps; no trade: 0.

### Trades: `from_1001` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 5.83 [-4.55, 16.18] | 0.88 | 0.530 | 1.21 | 14.40 | -9.45 |
| validation | 122 | -7.00 [-26.55, 9.75] | -0.86 | 0.525 | 0.79 | -8.54 | -12.40 |
| holdout | 125 | 0.02 [-14.20, 13.81] | 0.00 | 0.488 | 1.00 | 0.02 | -8.24 |

Mean net bps by round-trip cost: {'0.0': 3.19, '1.0': 2.19, '2.0': 1.19, '5.0': -1.81, '10.0': -6.81}. Always-long same window: -0.22 bps; no trade: 0.

## SPY — verdict: **inconclusive**

Development decision (exploration + validation): inconclusive.

Coverage 2024-10-09 to 2026-10-08: 501 sessions, 496 included, excluded {'early_close': 5}, 0 with missing minutes.

| Sample | n | Pearson [95% CI] | Spearman | Slope [95% CI] | NW t | Sign agree | Sign-timed bps [95% CI] |
|---|---|---|---|---|---|---|---|
| development | 371 | 0.054 [-0.108, 0.202] | -0.000 | 0.042 [-0.080, 0.156] | 0.67 | 0.464 | -0.46 [-2.84, 1.95] |
| full | 496 | 0.048 [-0.086, 0.177] | -0.002 | 0.037 [-0.068, 0.135] | 0.69 | 0.472 | -0.33 [-2.19, 1.49] |
| overnight def. | 490 | -0.036 [-0.186, 0.094] | -0.036 | -0.011 [-0.058, 0.028] | -0.53 | 0.476 | -0.47 [-2.45, 1.50] |
| split exploration | 247 | 0.123 [-0.073, 0.304] | 0.073 | 0.105 [-0.079, 0.250] | 1.28 | 0.502 | 0.67 [-2.48, 3.95] |
| split holdout | 125 | 0.026 [-0.170, 0.236] | -0.017 | 0.016 [-0.092, 0.167] | 0.25 | 0.496 | 0.07 [-2.45, 2.60] |
| split validation | 124 | -0.133 [-0.321, 0.060] | -0.103 | -0.080 [-0.194, 0.034] | -1.40 | 0.387 | -2.72 [-5.83, 0.39] |
| year 2024 | 56 | 0.046 [-0.141, 0.322] | -0.004 | 0.045 [-0.201, 0.221] | 0.51 | 0.464 | -1.99 [-6.46, 1.37] |
| year 2025 | 247 | 0.095 [-0.105, 0.270] | 0.024 | 0.077 [-0.091, 0.227] | 0.96 | 0.482 | 0.54 [-2.60, 3.97] |
| year 2026 | 193 | -0.056 [-0.229, 0.108] | -0.045 | -0.033 [-0.123, 0.072] | -0.65 | 0.461 | -0.96 [-3.24, 1.36] |

Mean r_close by r_open quintile (bps, full sample): {'Q1': 0.083, 'Q2': -0.808, 'Q3': 0.316, 'Q4': -2.896, 'Q5': 2.42}. Unconditional mean r_close: -0.18 bps. Development slope CI by bootstrap block length (days): {'1': '[-0.082, 0.160]', '5': '[-0.085, 0.156]', '20': '[-0.071, 0.138]'}.

### Trades: `last_half_hour` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.29 [-4.31, 2.02] | -0.80 | 0.445 | 0.86 | -3.19 | -3.24 |
| validation | 124 | -4.70 [-7.77, -1.66] | -2.96 | 0.331 | 0.51 | -5.83 | -5.74 |
| holdout | 125 | -1.93 [-4.45, 0.73] | -1.38 | 0.392 | 0.70 | -2.41 | -2.77 |

Mean net bps by round-trip cost: {'0.0': -0.31, '1.0': -1.31, '2.0': -2.31, '5.0': -5.31, '10.0': -10.31}. Always-long same window: -2.17 bps; no trade: 0.

### Trades: `last_half_hour_1531` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.33 [-4.16, 1.82] | -0.87 | 0.441 | 0.84 | -3.28 | -3.37 |
| validation | 124 | -4.96 [-7.82, -2.26] | -3.20 | 0.347 | 0.48 | -6.15 | -6.02 |
| holdout | 125 | -2.15 [-4.65, 0.71] | -1.54 | 0.464 | 0.66 | -2.68 | -3.08 |

Mean net bps by round-trip cost: {'0.0': -0.44, '1.0': -1.44, '2.0': -2.44, '5.0': -5.44, '10.0': -10.44}. Always-long same window: -2.52 bps; no trade: 0.

### Trades: `from_1000` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 6.62 [-2.06, 16.84] | 1.14 | 0.538 | 1.29 | 16.35 | -6.25 |
| validation | 124 | -4.83 [-18.67, 8.18] | -0.77 | 0.532 | 0.82 | -5.99 | -9.47 |
| holdout | 125 | -2.32 [-9.55, 5.04] | -0.54 | 0.480 | 0.88 | -2.90 | -5.35 |

Mean net bps by round-trip cost: {'0.0': 3.5, '1.0': 2.5, '2.0': 1.5, '5.0': -1.5, '10.0': -6.5}. Always-long same window: -0.89 bps; no trade: 0.

### Trades: `from_1001` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Sum of trades % | Fixed-notional DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 5.66 [-2.46, 15.16] | 1.01 | 0.526 | 1.25 | 13.98 | -6.49 |
| validation | 124 | -5.29 [-19.05, 7.55] | -0.84 | 0.516 | 0.80 | -6.56 | -10.04 |
| holdout | 125 | -1.56 [-8.90, 6.03] | -0.36 | 0.472 | 0.92 | -1.95 | -4.36 |

Mean net bps by round-trip cost: {'0.0': 3.1, '1.0': 2.1, '2.0': 1.1, '5.0': -1.9, '10.0': -6.9}. Always-long same window: -1.10 bps; no trade: 0.
