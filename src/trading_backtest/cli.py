import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from trading_backtest import engine
from trading_backtest.config import load_settings
from trading_backtest.data import bar_path, load_bars
from trading_backtest.data.massive import MassiveClient, download
from trading_backtest.data.validation import write_report
from trading_backtest.strategies import STRATEGIES, get_strategy


def parse_params(pairs: list[str], multi: bool = False) -> dict:
    """Parse key=value (or key=a,b,c when multi) into numbers where possible."""

    def num(s: str):
        try:
            return int(s)
        except ValueError:
            return float(s)

    out = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key] = [num(v) for v in value.split(",")] if multi else num(value)
    return out


def cmd_download(args, settings):
    client = MassiveClient(settings.massive_api_key, settings.request_interval)
    end = args.end or date.today() - timedelta(days=1)
    start = args.start or end - timedelta(days=365)
    for symbol in (s.upper() for s in args.symbols):
        path = bar_path(settings.raw_dir, symbol)
        saved = download(client, symbol, start, end, path)
        if not path.exists():
            print(f"{symbol}: no bars returned for {start}..{end}")
            continue
        report_path = path.with_suffix(".validation.json")
        report = write_report(pd.read_parquet(path), report_path, adjusted=True)
        print(
            f"{symbol}: saved {saved:,} new bars to {path} ({report['rows']:,} total, "
            f"{len(report['incomplete_sessions'])} incomplete sessions; see {report_path})"
        )


def cmd_backtest(args, settings):
    data = load_bars(bar_path(settings.raw_dir, args.symbol), args.start, args.end)
    strategy = get_strategy(args.strategy)
    costs = engine.CostModel(commission=args.commission, spread=args.spread)

    if args.optimize:
        stats = engine.optimize(
            data, strategy, parse_params(args.optimize, multi=True), costs=costs
        )
        print(stats)
        print("\nBest params:", stats._strategy)
        return

    plot = Path("reports") / f"{args.strategy}_{args.symbol}.html" if args.plot else None
    stats = engine.run(data, strategy, parse_params(args.param), plot_path=plot, costs=costs)
    print(stats)
    if plot:
        print(f"\nPlot: {plot}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="trading-backtest")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="download minute bars from Massive")
    dl.add_argument("symbols", nargs="+", metavar="SYMBOL")
    dl.add_argument("--start", type=date.fromisoformat)
    dl.add_argument("--end", type=date.fromisoformat)
    dl.set_defaults(func=cmd_download)

    bt = sub.add_parser("backtest", help="backtest a strategy on stored bars")
    bt.add_argument("strategy", choices=sorted(STRATEGIES))
    bt.add_argument("--symbol", default="QQQ")
    bt.add_argument("--start", help="YYYY-MM-DD")
    bt.add_argument("--end", help="YYYY-MM-DD")
    bt.add_argument("--param", nargs="*", default=[], metavar="KEY=VALUE")
    bt.add_argument("--optimize", nargs="*", metavar="KEY=V1,V2,...")
    bt.add_argument("--commission", type=float, default=0.0)
    bt.add_argument("--spread", type=float, default=0.0001)
    bt.add_argument("--plot", action="store_true", help="write an HTML chart to reports/")
    bt.set_defaults(func=cmd_backtest)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose or args.command == "download" else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args.func(args, load_settings())


if __name__ == "__main__":
    main()
