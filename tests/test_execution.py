"""Pin down the fill and cost assumptions documented in engine.py."""

from backtesting import Strategy
from bars import at, session, set_bar

from trading_backtest import engine

D = "2025-01-06"


class BuyAt(Strategy):
    """Market buy on bar `minute` with optional stop-loss / take-profit."""

    minute = 20
    sl = None
    tp = None
    size = None

    def init(self):
        pass

    def next(self):
        if len(self.data) - 1 == self.minute:
            kw = {"size": self.size} if self.size else {}
            self.buy(sl=self.sl, tp=self.tp, **kw)


NO_COSTS = engine.CostModel(spread=0.0)


def first_trade(df, costs=NO_COSTS, **params):
    return engine.run(df, BuyAt, params, costs=costs)._trades.iloc[0]


def test_market_order_fills_at_next_open():
    df = session(D)
    set_bar(df, D, 21, o=100.5)
    assert first_trade(df).EntryTime == at(D, 21)
    assert first_trade(df).EntryPrice == 100.5


def test_spread_is_charged_on_entry():
    trade = first_trade(session(D), engine.CostModel(spread=0.001))
    assert trade.EntryPrice == 100 * 1.001


def test_commission_reduces_pnl_on_both_sides():
    costs = engine.CostModel(commission=0.001, spread=0.0)
    trade = first_trade(session(D), costs, size=100)
    assert round(trade.PnL, 6) == -2 * 100 * 100 * 0.001


def test_stop_gapped_through_fills_at_open():
    df = session(D)
    set_bar(df, D, 30, o=98.0, h=98.2, low=97.5, c=98.0)
    trade = first_trade(df, sl=99.0)
    assert trade.ExitTime == at(D, 30) and trade.ExitPrice == 98.0


def test_stop_and_target_in_same_bar_assumes_stop():
    df = session(D)
    set_bar(df, D, 30, h=102.0, low=98.0)
    trade = first_trade(df, sl=99.0, tp=101.0)
    assert trade.ExitPrice == 99.0


def test_size_never_exceeds_cash():
    trade = first_trade(session(D))
    assert trade.Size * trade.EntryPrice <= 100_000
