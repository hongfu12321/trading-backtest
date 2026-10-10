"""Run and optimize strategies with consistent cost and execution assumptions.

Execution model (backtesting.py 0.6, as configured here):

- Market orders fill at the next bar's open. Signals see only completed bars.
- Stop-loss orders fill at the stop price, or at the bar's open if the price gapped
  through the stop (the worse price).
- If a stop-loss and take-profit are both inside one bar, the stop-loss is assumed hit.
- `spread` is charged once per trade, on entry; `commission` on entry and on exit.
- Orders without a size use ~100% of equity with no margin, so buying power is never
  exceeded. Sizes are whole shares.
- A fixed spread understates costs on illiquid or volatile names; raise it for those.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from backtesting import Backtest, Strategy

from trading_backtest import sessions

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CostModel:
    commission: float = 0.0  # fraction of trade value per side
    spread: float = 0.0001  # fraction of price; models bid-ask and slippage


DEFAULT_COSTS = CostModel()


def make_backtest(
    data: pd.DataFrame,
    strategy: type[Strategy],
    cash: float = 100_000,
    costs: CostModel = DEFAULT_COSTS,
) -> Backtest:
    data, dropped = sessions.tradable_bars(data)
    if dropped:
        log.warning("Skipping %d session(s) too incomplete to flatten: %s", len(dropped), dropped)
    return Backtest(
        data,
        strategy,
        cash=cash,
        commission=costs.commission,
        spread=costs.spread,
        exclusive_orders=True,
        finalize_trades=True,
    )


def run(
    data: pd.DataFrame,
    strategy: type[Strategy],
    params: dict | None = None,
    plot_path: Path | None = None,
    **kwargs,
) -> pd.Series:
    bt = make_backtest(data, strategy, **kwargs)
    stats = bt.run(**(params or {}))
    if plot_path:
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        bt.plot(filename=str(plot_path), open_browser=False, resample="5min")
    return stats


def optimize(
    data: pd.DataFrame,
    strategy: type[Strategy],
    grid: dict[str, list],
    maximize: str = "Sharpe Ratio",
    **kwargs,
) -> pd.Series:
    return make_backtest(data, strategy, **kwargs).optimize(**grid, maximize=maximize)
