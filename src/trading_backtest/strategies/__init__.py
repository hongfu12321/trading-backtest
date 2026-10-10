"""Strategy registry. Add new strategies here to expose them on the CLI."""

from backtesting import Strategy

from trading_backtest.strategies.orb import OpeningRangeBreakout

STRATEGIES: dict[str, type[Strategy]] = {
    "orb": OpeningRangeBreakout,
}


def get_strategy(name: str) -> type[Strategy]:
    try:
        return STRATEGIES[name]
    except KeyError:
        raise ValueError(f"Unknown strategy {name!r}; choose from {sorted(STRATEGIES)}") from None
