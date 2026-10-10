# Research 001 — results

Run 2026-10-10T07:40:05+00:00 at commit `78ea923f608335e4a2315afd3a92a44deb788ffc`. Definitions: `src/trading_backtest/research/intraday_momentum.py`.

Splits (chronological, fixed before running): {'exploration': ['2024-10-09', '2025-10-08'], 'holdout': ['2026-04-13', '2026-10-08'], 'validation': ['2025-10-09', '2026-04-10']}. Base cost 2.0 bps round trip; bootstrap 2000 draws, seed 0.

## QQQ — verdict: **inconclusive**

Coverage 2024-10-09 to 2026-10-08: 501 sessions, 496 included, excluded {'early_close': 5}, 0 with missing minutes.

| Sample | n | Pearson [95% CI] | Spearman | Slope [95% CI] | NW t | Sign agree | Sign-timed bps [95% CI] |
|---|---|---|---|---|---|---|---|
| full | 496 | 0.041 [-0.072, 0.147] | -0.001 | 0.024 [-0.038, 0.087] | 0.77 | 0.478 | -0.46 [-2.82, 1.85] |
| overnight def. | 490 | -0.016 [-0.139, 0.104] | -0.012 | -0.005 [-0.040, 0.031] | -0.26 | 0.504 | 0.36 [-2.02, 2.88] |
| split exploration | 247 | 0.115 [-0.048, 0.271] | 0.065 | 0.077 [-0.031, 0.175] | 1.87 | 0.486 | 0.79 [-2.98, 4.42] |
| split holdout | 125 | 0.021 [-0.178, 0.211] | -0.036 | 0.011 [-0.076, 0.141] | 0.18 | 0.488 | -0.51 [-4.59, 3.99] |
| split validation | 124 | -0.117 [-0.320, 0.110] | -0.072 | -0.057 [-0.152, 0.051] | -1.18 | 0.452 | -2.91 [-6.81, 0.95] |
| year 2024 | 56 | 0.055 [-0.198, 0.302] | 0.051 | 0.032 [-0.119, 0.157] | 0.71 | 0.482 | -1.33 [-7.65, 4.46] |
| year 2025 | 247 | 0.096 [-0.061, 0.246] | 0.029 | 0.063 [-0.049, 0.157] | 1.51 | 0.482 | 0.88 [-2.98, 4.68] |
| year 2026 | 193 | -0.048 [-0.210, 0.120] | -0.056 | -0.023 [-0.093, 0.065] | -0.51 | 0.472 | -1.92 [-5.39, 1.40] |

Mean r_close by r_open quintile (bps, full sample): {'Q1': -0.673, 'Q2': 2.436, 'Q3': 1.464, 'Q4': -1.224, 'Q5': 1.759}. Unconditional mean r_close: 0.75 bps.

### Trades: `last_half_hour` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Total % | Max DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.15 [-4.96, 2.67] | -0.60 | 0.457 | 0.89 | -2.84 | -4.84 |
| validation | 122 | -4.98 [-9.09, -1.06] | -2.43 | 0.377 | 0.56 | -6.07 | -6.22 |
| holdout | 125 | -2.49 [-6.62, 1.90] | -1.13 | 0.432 | 0.75 | -3.12 | -3.86 |

Mean net bps by round-trip cost: {'0.0': -0.44, '1.0': -1.44, '2.0': -2.44, '5.0': -5.44, '10.0': -10.44}. Always-long same window: -1.25 bps; no trade: 0.

### Trades: `from_1000` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Total % | Max DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 7.21 [-5.53, 21.14] | 1.05 | 0.530 | 1.26 | 17.80 | -9.10 |
| validation | 122 | -5.65 [-21.71, 9.14] | -0.70 | 0.541 | 0.83 | -6.89 | -11.66 |
| holdout | 125 | -1.13 [-13.96, 11.63] | -0.17 | 0.472 | 0.96 | -1.41 | -8.83 |

Mean net bps by round-trip cost: {'0.0': 3.92, '1.0': 2.92, '2.0': 1.92, '5.0': -1.08, '10.0': -6.08}. Always-long same window: 0.05 bps; no trade: 0.

## SPY — verdict: **inconclusive**

Coverage 2024-10-09 to 2026-10-08: 501 sessions, 496 included, excluded {'early_close': 5}, 0 with missing minutes.

| Sample | n | Pearson [95% CI] | Spearman | Slope [95% CI] | NW t | Sign agree | Sign-timed bps [95% CI] |
|---|---|---|---|---|---|---|---|
| full | 496 | 0.048 [-0.097, 0.187] | -0.002 | 0.037 [-0.070, 0.141] | 0.69 | 0.472 | -0.33 [-2.18, 1.56] |
| overnight def. | 490 | -0.036 [-0.187, 0.108] | -0.036 | -0.011 [-0.058, 0.035] | -0.53 | 0.476 | -0.47 [-2.37, 1.43] |
| split exploration | 247 | 0.123 [-0.091, 0.309] | 0.073 | 0.105 [-0.068, 0.270] | 1.28 | 0.502 | 0.67 [-2.50, 3.72] |
| split holdout | 125 | 0.026 [-0.166, 0.219] | -0.017 | 0.016 [-0.092, 0.166] | 0.25 | 0.496 | 0.07 [-2.50, 2.65] |
| split validation | 124 | -0.133 [-0.333, 0.089] | -0.103 | -0.080 [-0.204, 0.047] | -1.40 | 0.387 | -2.72 [-5.87, 0.45] |
| year 2024 | 56 | 0.046 [-0.236, 0.391] | -0.004 | 0.045 [-0.267, 0.276] | 0.51 | 0.464 | -1.99 [-8.04, 3.13] |
| year 2025 | 247 | 0.095 [-0.104, 0.280] | 0.024 | 0.077 [-0.096, 0.230] | 0.96 | 0.482 | 0.54 [-2.55, 3.76] |
| year 2026 | 193 | -0.056 [-0.220, 0.111] | -0.045 | -0.033 [-0.133, 0.073] | -0.65 | 0.461 | -0.96 [-3.39, 1.38] |

Mean r_close by r_open quintile (bps, full sample): {'Q1': 0.083, 'Q2': -0.808, 'Q3': 0.316, 'Q4': -2.896, 'Q5': 2.42}. Unconditional mean r_close: -0.18 bps.

### Trades: `last_half_hour` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Total % | Max DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | -1.29 [-4.57, 1.85] | -0.80 | 0.445 | 0.86 | -3.19 | -3.24 |
| validation | 124 | -4.70 [-7.83, -1.70] | -2.96 | 0.331 | 0.51 | -5.83 | -5.74 |
| holdout | 125 | -1.93 [-4.53, 0.98] | -1.38 | 0.392 | 0.70 | -2.41 | -2.77 |

Mean net bps by round-trip cost: {'0.0': -0.31, '1.0': -1.31, '2.0': -2.31, '5.0': -5.31, '10.0': -10.31}. Always-long same window: -2.17 bps; no trade: 0.

### Trades: `from_1000` (net of 2.0 bps)

| Split | Trades | Mean bps [95% CI] | t | Win rate | PF | Total % | Max DD % |
|---|---|---|---|---|---|---|---|
| exploration | 247 | 6.62 [-4.22, 17.99] | 1.14 | 0.538 | 1.29 | 16.35 | -6.25 |
| validation | 124 | -4.83 [-17.80, 7.08] | -0.77 | 0.532 | 0.82 | -5.99 | -9.47 |
| holdout | 125 | -2.32 [-10.83, 6.30] | -0.54 | 0.480 | 0.88 | -2.90 | -5.35 |

Mean net bps by round-trip cost: {'0.0': 3.5, '1.0': 2.5, '2.0': 1.5, '5.0': -1.5, '10.0': -6.5}. Always-long same window: -0.89 bps; no trade: 0.
