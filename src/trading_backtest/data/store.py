"""Local parquet storage and loading of bar data.

Each `<SYMBOL>_<timespan>.parquet` file has a `.json` manifest beside it listing the date
ranges that were fully downloaded. A range in the manifest with no bars was queried and is
genuinely empty (e.g. holidays); a date outside every range has never been downloaded or
its download did not finish. Completeness is never inferred from the parquet file alone.
"""

import json
import os
from datetime import date, time, timedelta
from pathlib import Path

import pandas as pd

TZ = "America/New_York"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def bar_path(raw_dir: Path, symbol: str, timespan: str = "minute") -> Path:
    return raw_dir / f"{symbol.upper()}_{timespan}.parquet"


def _replace_atomically(path: Path, write) -> None:
    """Write via a temp file and rename, so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


def save_bars(df: pd.DataFrame, path: Path) -> None:
    """Write bars, merging with any existing file so downloads can be incremental."""
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp")
    _replace_atomically(path, lambda tmp: df.to_parquet(tmp, index=False))


def manifest_path(path: Path) -> Path:
    return path.with_suffix(".json")


def completed_ranges(path: Path) -> list[tuple[date, date]]:
    mpath = manifest_path(path)
    if not mpath.exists():
        return []
    ranges = json.loads(mpath.read_text())["completed"]
    return [(date.fromisoformat(s), date.fromisoformat(e)) for s, e in ranges]


def mark_completed(path: Path, start: date, end: date) -> None:
    """Record [start, end] as fully downloaded, merging overlapping or adjacent ranges."""
    merged: list[list[date]] = []
    for s, e in sorted([*completed_ranges(path), (start, end)]):
        if merged and s <= merged[-1][1] + timedelta(days=1):
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    text = json.dumps({"completed": [[s.isoformat(), e.isoformat()] for s, e in merged]})
    _replace_atomically(manifest_path(path), lambda tmp: tmp.write_text(text))


def missing_ranges(path: Path, start: date, end: date) -> list[tuple[date, date]]:
    """Sub-ranges of [start, end] not yet recorded as completed."""
    gaps, cursor = [], start
    for s, e in completed_ranges(path):
        if s > cursor:
            gaps.append((cursor, min(end, s - timedelta(days=1))))
        cursor = max(cursor, e + timedelta(days=1))
        if cursor > end:
            break
    if cursor <= end:
        gaps.append((cursor, end))
    return [(s, e) for s, e in gaps if s <= e]


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
