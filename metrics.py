from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd


TIMESTAMP_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6})\]"
)
LOG_TIMESTAMP_RE = re.compile(r"_(?P<suffix>\d{8}_\d{6})$")


@dataclass
class RoundMetrics:
    round: int
    connect_latency_ms: float | None
    backup_time_ms: float | None
    recovery_time_ms: float | None


def parse_timestamp(line: str) -> datetime | None:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None

    try:
        return datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


def iter_timestamped_lines(path: Path) -> list[tuple[datetime, str]]:
    events: list[tuple[datetime, str]] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            timestamp = parse_timestamp(raw_line)
            if timestamp is not None:
                events.append((timestamp, raw_line.strip()))

    return events


def host_rounds(host_log: Path) -> list[dict[str, datetime | int | None]]:
    rounds: list[dict[str, datetime | int | None]] = []
    current: dict[str, datetime | int | None] | None = None

    for timestamp, line in iter_timestamped_lines(host_log):
        round_start = re.search(r"ROUND\s+(\d+)\s+START", line)
        if round_start:
            if current is not None:
                rounds.append(current)

            current = {
                "round": int(round_start.group(1)),
                "start": timestamp,
                "agent_started": None,
                "end": None,
            }
            continue

        if current is None:
            continue

        if "Starting micro-ROS agent" in line:
            current["agent_started"] = timestamp
            continue

        if "ROUND" in line and "END" in line:
            current["end"] = timestamp
            rounds.append(current)
            current = None

    if current is not None:
        rounds.append(current)

    return rounds


def find_first_event(
    events: list[tuple[datetime, str]],
    contains: str,
    after: datetime,
    before: datetime | None = None,
) -> datetime | None:
    for timestamp, line in events:
        if timestamp < after:
            continue
        if before is not None and timestamp > before:
            break
        if contains in line:
            return timestamp

    return None


def find_next_different_round_disconnect(
    events: list[tuple[datetime, str]],
    after: datetime,
) -> datetime | None:
    for timestamp, line in events:
        if timestamp <= after:
            continue
        if "[STATE] disconnect detected" in line:
            return timestamp

    return None


def ms_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() * 1000, 3)


def compute_metrics(host_log: Path, pico_log: Path) -> list[RoundMetrics]:
    rounds = host_rounds(host_log)
    pico_events = iter_timestamped_lines(pico_log)
    metrics: list[RoundMetrics] = []

    for index, round_info in enumerate(rounds):
        round_no = int(round_info["round"])
        round_start = round_info["start"]
        round_end = round_info["end"]

        if not isinstance(round_start, datetime):
            continue

        if not isinstance(round_end, datetime):
            if index + 1 < len(rounds) and isinstance(rounds[index + 1]["start"], datetime):
                round_end = rounds[index + 1]["start"]
            else:
                round_end = None

        agent_started = round_info["agent_started"]
        if not isinstance(agent_started, datetime):
            agent_started = None

        agent_connected = find_first_event(
            pico_events,
            "[STATE] agent connected",
            after=agent_started or round_start,
            before=round_end,
        )
        if agent_connected is None:
            agent_connected = find_first_event(
                pico_events,
                "[STATE] agent back online",
                after=agent_started or round_start,
                before=round_end,
            )

        disconnect = find_first_event(
            pico_events,
            "[STATE] disconnect detected",
            after=round_start,
            before=round_end,
        )
        backup_done = find_first_event(
            pico_events,
            "[STATE] Backup activation completed",
            after=disconnect or round_start,
            before=round_end,
        )

        next_disconnect = (
            find_next_different_round_disconnect(pico_events, after=disconnect)
            if disconnect is not None
            else None
        )
        agent_back_online = find_first_event(
            pico_events,
            "[STATE] agent back online",
            after=disconnect or round_start,
            before=next_disconnect,
        )

        metrics.append(
            RoundMetrics(
                round=round_no,
                connect_latency_ms=ms_between(agent_started, agent_connected),
                backup_time_ms=ms_between(disconnect, backup_done),
                recovery_time_ms=ms_between(disconnect, agent_back_online),
            )
        )

    return metrics


def output_suffix(host_log: Path) -> str:
    match = LOG_TIMESTAMP_RE.search(host_log.stem)
    if match:
        return match.group("suffix")

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def metrics_to_dataframe(metrics: list[RoundMetrics]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "round": metric.round,
                "connect_latency_ms": metric.connect_latency_ms,
                "backup_time_ms": metric.backup_time_ms,
                "recovery_time_ms": metric.recovery_time_ms,
            }
            for metric in metrics
        ],
        columns=["round", "connect_latency_ms", "backup_time_ms", "recovery_time_ms"],
    )


def plot_metrics(df: pd.DataFrame, output: Path) -> None:
    round_count = max(len(df), 1)
    figure_width = min(max(9, round_count * 0.22), 24)
    fig, axes = plt.subplots(3, 1, figsize=(figure_width, 11), sharex=True)

    metric_configs = [
        ("connect_latency_ms", "Connect Latency (ms)"),
        ("backup_time_ms", "Backup Time (ms)"),
        ("recovery_time_ms", "Recovery Time (ms)"),
    ]

    for ax, (column, title) in zip(axes, metric_configs):
        (line,) = ax.plot(df["round"], df[column], marker="o", linewidth=2, label=column)
        line_color = line.get_color()
        average = df[column].mean(skipna=True)

        if not pd.isna(average):
            average_label = f"avg = {average:.2f} ms"
            ax.axhline(
                average,
                color=line_color,
                linestyle="--",
                linewidth=1.5,
                label=average_label,
            )

            if len(df) > 0:
                right_round = df["round"].max()
                ax.annotate(
                    average_label,
                    xy=(right_round, average),
                    xytext=(6, 0),
                    textcoords="offset points",
                    va="center",
                    color=line_color,
                )

        ax.set_ylabel("Time (ms)")
        ax.set_title(title)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=min(round_count, 20)))
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend()

    axes[-1].set_xlabel("Round")

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)


def print_summary(df: pd.DataFrame) -> None:
    fields = [
        ("average connect latency", "connect_latency_ms"),
        ("average backup time", "backup_time_ms"),
        ("average recovery time", "recovery_time_ms"),
    ]

    print()
    print("Summary:")

    for label, field_name in fields:
        average = df[field_name].mean(skipna=True)
        if pd.isna(average):
            print(f"- {label}: n/a")
        else:
            print(f"- {label}: {average:.3f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute micro-ROS host/Pico round metrics.")
    parser.add_argument("--host-log", type=Path, default=Path("log/host_20260428_120610.log"))
    parser.add_argument("--pico-log", type=Path, default=Path("log/pico_20260428_120613.log"))
    parser.add_argument("--csv", type=Path, help="Optional CSV output path.")
    parser.add_argument(
        "--plot",
        type=Path,
        default=None,
        help="Plot output path.",
    )
    args = parser.parse_args()

    suffix = output_suffix(args.host_log)
    plot_output = args.plot or Path(f"result/system_timing_analysis_{suffix}.png")

    metrics = compute_metrics(args.host_log, args.pico_log)
    df = metrics_to_dataframe(metrics)

    print(df.to_string(index=False))
    print_summary(df)

    if args.csv is not None:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.csv, index=False)
        print(f"\nWrote CSV: {args.csv}")

    plot_metrics(df, plot_output)
    print(f"Wrote plot: {plot_output}")


if __name__ == "__main__":
    main()
