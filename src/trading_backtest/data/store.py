"""Local parquet storage and loading of bar data."""

from datetime import time
from pathlib import Path

import pandas as pd

TZ = "America/New_York"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def bar_path(raw_dir: Path, symbol: str, timespan: str = "minute") -> Path:
    return raw_dir / f"{symbol.upper()}_{timespan}.parquet"


def save_bars(df: pd.DataFrame, path: Path) -> None:
    """Write bars, merging with any existing file so downloads can be incremental."""
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
        df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_bars(
    path: Path,
    start: str | None = None,
    end: str | None = None,
    regular_hours: bool = True,
) -> pd.DataFrame:
    """Load bars in the format backtesting.py expects (DatetimeIndex, capitalized OHLCV)."""
    df = pd.read_parquet(path).set_index("timestamp").sort_index()
    if regular_hours:
        t = df.index.time
        df = df[(t >= MARKET_OPEN) & (t < MARKET_CLOSE)]
    df = df.loc[start:end]
    if df.empty:
        raise ValueError(f"No bars in {path} for {start}..{end}")
    return df.rename(columns=str.capitalize)
