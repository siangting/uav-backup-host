"""
Shared helpers: log parsing + auto-locate latest log files + result dir.
"""
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


def ms_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() * 1000.0


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