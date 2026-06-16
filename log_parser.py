"""
Shared helpers: log parsing + auto-locate latest log files + result dir.
"""
import bisect
import csv
import re
from datetime import datetime
from pathlib import Path

LOG_DIR    = Path("log")
RESULT_DIR = Path("result")

TS_RE = r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]"


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")


def latest_log(prefix: str) -> Path:
    """Pick the lexicographically-latest log file in LOG_DIR matching `prefix_*.log`.

    Filenames embed timestamps (host_YYYYMMDD_HHMMSS.log), so lex sort == time sort.
    """
    files = sorted(LOG_DIR.glob(f"{prefix}_*.log"))
    if not files:
        raise FileNotFoundError(f"no {prefix}_*.log under {LOG_DIR.resolve()}")
    return files[-1]


def ensure_result_dir() -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    return RESULT_DIR


def parse_pico_log(path: Path):
    text = Path(path).read_text(errors="ignore")
    boot = [int(m.group(2)) for m in re.finditer(
        TS_RE + r"\s*\[T_BOOT\] boot_time = (\d+) ms", text)]
    init = [int(m.group(2)) for m in re.finditer(
        TS_RE + r"\s*\[T_UROS_INIT\] init_time = (\d+) ms", text)]
    conn = [_parse_ts(m.group(1)) for m in re.finditer(
        TS_RE + r"\s*\[EVT\] AGENT_CONNECTED", text)]
    disc = [_parse_ts(m.group(1)) for m in re.finditer(
        TS_RE + r"\s*\[EVT\] AGENT_DISCONNECTED", text)]
    backup = [_parse_ts(m.group(1)) for m in re.finditer(
        TS_RE + r"\s*\[EVT\] Backup activation completed", text)]
    return {"boot": boot, "init": init, "conn": conn,
            "disc": disc, "backup": backup}


def parse_host_log(path: Path):
    text = Path(path).read_text(errors="ignore")
    start = [_parse_ts(m.group(1)) for m in re.finditer(
        TS_RE + r"\s*\|\s*Starting micro-ROS agent", text)]
    stop = [_parse_ts(m.group(1)) for m in re.finditer(
        TS_RE + r"\s*\|\s*Stopping processes", text)]
    return {"start": start, "stop": stop}


def first_in_each_window(anchors, events):
    """Pair each `anchors[i]` with the first `events` entry timestamped at or
    after it and before `anchors[i + 1]` (the last window is open-ended).

    Returns a list the same length as `anchors`; entries with no matching
    event are None.

    Why this instead of pairing by array position (`events[i]`): the agent
    connection sometimes flickers (disconnects/reconnects more than once)
    within a single round, so pico can log more conn/disc/backup events than
    there are host rounds. Once that happens, positional pairing drifts out
    of sync for every later round and produces nonsense (often negative)
    deltas. Matching by which round's time window an event actually falls
    in is robust to that — extra events inside a window are simply ignored.

    Both `anchors` and `events` must already be chronologically sorted
    (true for everything this module parses, since log lines are appended
    in time order).
    """
    out = []
    for i, lo in enumerate(anchors):
        hi = anchors[i + 1] if i + 1 < len(anchors) else None
        lo_idx = bisect.bisect_left(events, lo)
        hi_idx = bisect.bisect_left(events, hi) if hi is not None else len(events)
        out.append(events[lo_idx] if lo_idx < hi_idx else None)
    return out


def events_in_each_window(anchors, events):
    """Like `first_in_each_window`, but return the *full list* of `events`
    falling in [anchors[i], anchors[i + 1]) (last window open-ended) instead
    of just the first one. Useful when you need to know how many extra
    (flicker) events landed in a round, not just the first.
    """
    out = []
    for i, lo in enumerate(anchors):
        hi = anchors[i + 1] if i + 1 < len(anchors) else None
        lo_idx = bisect.bisect_left(events, lo)
        hi_idx = bisect.bisect_left(events, hi) if hi is not None else len(events)
        out.append(events[lo_idx:hi_idx])
    return out


def first_at_or_after(ts, events):
    """Return the first `events` entry timestamped at or after `ts`, or None."""
    idx = bisect.bisect_left(events, ts)
    return events[idx] if idx < len(events) else None


def ms_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() * 1000.0


def save_csv(path: Path, headers, rows) -> Path:
    """Write `rows` (iterable of iterables) to a CSV file at `path` with
    `headers` as the first line. Creates parent dirs as needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def stat_block(values, unit="ms") -> str:
    """Format a monospace stats block usable inside ax.text(...)."""
    import numpy as np
    v = np.asarray(values, dtype=float)
    lines = [
        f"n     = {len(v)}",
        f"mean  = {v.mean():.2f} {unit}",
        f"std   = {v.std(ddof=0):.2f} {unit}",
        f"min   = {v.min():.2f} {unit}",
        f"p50   = {np.percentile(v, 50):.2f} {unit}",
        f"p95   = {np.percentile(v, 95):.2f} {unit}",
        f"p99   = {np.percentile(v, 99):.2f} {unit}",
        f"max   = {v.max():.2f} {unit}",
    ]
    return "\n".join(lines)