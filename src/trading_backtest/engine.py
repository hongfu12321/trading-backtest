"""Run and optimize strategies with consistent cost assumptions."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from backtesting import Backtest, Strategy


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
