import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from trading_backtest import engine
from trading_backtest.analytics import metrics
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
    out = Path("reports") / f"{args.strategy}_{args.symbol}"

    # Parameters are chosen on the training segment only; the test segment is untouched.
    segments = {"all": data}
    if args.split:
        cut = pd.Timestamp(args.split, tz=data.index.tz)
        segments = {"in_sample": data[data.index < cut], "out_of_sample": data[data.index >= cut]}
    fit_data = next(iter(segments.values()))

    params = parse_params(args.param)
    if args.optimize:
        best = engine.optimize(
            fit_data, strategy, parse_params(args.optimize, multi=True), costs=costs
        )
        params = {
            k: v.item() if hasattr(v, "item") else v for k, v in best._strategy._params.items()
        }
        print("Best params on", next(iter(segments)), "data:", params)
        if not args.split:
            print("Warning: optimized and evaluated on the same data; use --split for a fair test.")

    for name, segment in segments.items():
        seg_out = out / name if args.split else out
        plot = seg_out / "chart.html" if args.plot else None
        stats = engine.run(segment, strategy, params, plot_path=plot, costs=costs)
        meta = {
            "strategy": args.strategy,
            "symbol": args.symbol,
            "segment": name,
            "data_start": str(segment.index[0]),
            "data_end": str(segment.index[-1]),
            "params": params,
            "costs": vars(costs),
            "cash": 100_000,
        }
        summary = metrics.write_report(stats, seg_out, meta)
        print(f"\n=== {name} ===\n{stats}\n\nReport: {seg_out}")
        print(
            {k: round(v, 4) if isinstance(v, float) else v for k, v in summary["metrics"].items()}
        )


def cmd_research(args, settings):
    from trading_backtest.research import intraday_momentum as study

    symbols = tuple(s.upper() for s in args.symbols)
    bars = {s: load_bars(bar_path(settings.raw_dir, s), args.start, args.end) for s in symbols}
    run_settings = study.Settings(symbols=symbols, seed=args.seed, n_boot=args.n_boot)
    summary, daily = study.run(bars, run_settings)
    study.write_outputs(summary, daily, args.out)
    for symbol, s in summary["symbols"].items():
        full = s["descriptive"]["full"]
        print(
            f"{symbol}: {s['verdict']} (n={full['n']}, slope={full.get('slope', float('nan')):.3f})"
        )
    print(f"Report: {args.out / 'report.md'}")


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
    bt.add_argument(
        "--split", metavar="YYYY-MM-DD", help="optimize before this date, evaluate from it on"
    )
    bt.set_defaults(func=cmd_backtest)

    rs = sub.add_parser("research", help="run a research study (no trading)")
    rs.add_argument("study", choices=["momentum"], help="momentum: Research 001")
    rs.add_argument("--symbols", nargs="+", default=["QQQ", "SPY"])
    rs.add_argument("--start", help="YYYY-MM-DD")
    rs.add_argument("--end", help="YYYY-MM-DD")
    rs.add_argument("--seed", type=int, default=0)
    rs.add_argument("--n-boot", type=int, default=2000)
    rs.add_argument("--out", type=Path, default=Path("reports/experiments/001-intraday-momentum"))
    rs.set_defaults(func=cmd_research)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose or args.command == "download" else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args.func(args, load_settings())


if __name__ == "__main__":
    main()
