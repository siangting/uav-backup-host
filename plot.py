from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch


HOST_LOG = Path("log/host_timeout_300ms_r100.log")
PICO_LOG = Path("log/pico_timeout_300ms_r100.log")
OUTPUT_DIR = Path("result")

TIMESTAMP_RE = re.compile(r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6})\]")
STATE_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6})\]\s+\[STATE\]\s+(?P<state>.+)$"
)
HOST_EVENT_COLORS = {
    "round": "#4c78a8",
    "agent": "#54a24b",
    "heartbeat": "#72b7b2",
}

PICO_STATE_COLORS = {
    "disconnect detected": "#f58518",
    "Backup activation completed": "#b279a2",
    "agent connected": "#e45756",
}

DEFAULT_HOST_COLOR = "#bab0ac"
DEFAULT_PICO_COLOR = "#9d9da1"


def parse_timestamp(line: str) -> datetime | None:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None

    try:
        return datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


def parse_host_log(path: Path) -> list[dict[str, object]]:
    intervals: list[dict[str, object]] = []
    open_intervals: dict[str, datetime] = {}
    current_round_label: str | None = None
    last_timestamp: datetime | None = None

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            timestamp = parse_timestamp(raw_line)
            if timestamp is None:
                continue

            last_timestamp = timestamp
            line = raw_line.strip()

            if "ROUND" in line and "START" in line:
                match = re.search(r"ROUND\s+(\d+)\s+START", line)
                round_id = match.group(1) if match else "?"
                current_round_label = f"Round {round_id}"
                open_intervals["round"] = timestamp
                continue

            if "Starting micro-ROS agent" in line:
                open_intervals["agent"] = timestamp
                continue

            if "Starting heartbeat publisher" in line:
                open_intervals["heartbeat"] = timestamp
                continue

            if "Processes stopped" in line:
                for kind in ("agent", "heartbeat"):
                    start = open_intervals.pop(kind, None)
                    if start is not None and timestamp > start:
                        intervals.append(
                            {
                                "lane": kind,
                                "label": "micro-ROS agent" if kind == "agent" else "heartbeat publisher",
                                "start": start,
                                "end": timestamp,
                                "color": HOST_EVENT_COLORS.get(kind, DEFAULT_HOST_COLOR),
                            }
                        )
                continue

            if "ROUND" in line and "END" in line:
                start = open_intervals.pop("round", None)
                if start is not None and timestamp > start:
                    intervals.append(
                        {
                            "lane": "round",
                            "label": current_round_label or "Round",
                            "start": start,
                            "end": timestamp,
                            "color": HOST_EVENT_COLORS.get("round", DEFAULT_HOST_COLOR),
                        }
                    )
                current_round_label = None

    if last_timestamp is not None:
        for kind, start in list(open_intervals.items()):
            if last_timestamp > start:
                intervals.append(
                    {
                        "lane": kind,
                        "label": current_round_label if kind == "round" and current_round_label else kind,
                        "start": start,
                        "end": last_timestamp,
                        "color": HOST_EVENT_COLORS.get(kind, DEFAULT_HOST_COLOR),
                    }
                )

    intervals.sort(key=lambda item: (item["start"], item["lane"]))  # type: ignore[index]
    return intervals


def parse_pico_states(path: Path) -> list[tuple[datetime, str]]:
    states: list[tuple[datetime, str]] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            match = STATE_RE.match(raw_line.strip())
            if not match:
                continue

            try:
                timestamp = datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                continue

            state = match.group("state").strip()
            if state == "agent back online":
                state = "agent connected"

            states.append((timestamp, state))

    return states


def collapse_consecutive_states(states: list[tuple[datetime, str]]) -> list[tuple[datetime, str]]:
    if not states:
        return []

    cleaned = [states[0]]

    for timestamp, state in states[1:]:
        _previous_timestamp, previous_state = cleaned[-1]

        if state == previous_state:
            continue

        cleaned.append((timestamp, state))

    return cleaned


def build_pico_intervals(states: list[tuple[datetime, str]], timeline_end: datetime) -> list[dict[str, object]]:
    intervals: list[dict[str, object]] = []

    for index, (start, state) in enumerate(states):
        if index + 1 < len(states):
            end = states[index + 1][0]
        else:
            end = timeline_end

        if end <= start:
            continue

        intervals.append(
            {
                "label": state,
                "start": start,
                "end": end,
                "color": PICO_STATE_COLORS.get(state, DEFAULT_PICO_COLOR),
            }
        )

    return intervals


def find_time_bounds(host_intervals: list[dict[str, object]], pico_states: list[tuple[datetime, str]]) -> tuple[datetime, datetime]:
    timestamps: list[datetime] = []

    for interval in host_intervals:
        timestamps.append(interval["start"])  # type: ignore[arg-type]
        timestamps.append(interval["end"])  # type: ignore[arg-type]

    for timestamp, _state in pico_states:
        timestamps.append(timestamp)

    if not timestamps:
        raise ValueError("No timeline data found in the provided logs.")

    return min(timestamps), max(timestamps)


def seconds_from_origin(timestamp: datetime, origin: datetime) -> float:
    return (timestamp - origin).total_seconds()


def plot_host_timeline(ax, host_intervals: list[dict[str, object]], origin: datetime) -> None:
    lane_order = OrderedDict(
        [
            ("round", 2),
            ("agent", 1),
            ("heartbeat", 0),
        ]
    )

    for interval in host_intervals:
        start = seconds_from_origin(interval["start"], origin)  # type: ignore[arg-type]
        duration = (
            interval["end"] - interval["start"]  # type: ignore[operator]
        ).total_seconds()
        lane = interval["lane"]  # type: ignore[index]
        y = lane_order.get(lane, -1)

        ax.barh(
            y,
            duration,
            left=start,
            height=0.55,
            color=interval["color"],
            edgecolor="black",
            linewidth=0.8,
        )

        if duration >= 0.25:
            ax.text(
                start + duration / 2,
                y,
                str(interval["label"]),
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    ax.set_title("Host Timeline")
    ax.set_yticks(list(lane_order.values()))
    ax.set_yticklabels(["Round", "micro-ROS agent", "Heartbeat"])
    ax.grid(axis="x", linestyle="--", alpha=0.35)


def plot_pico_timeline(ax, pico_intervals: list[dict[str, object]], origin: datetime) -> None:
    for interval in pico_intervals:
        start = seconds_from_origin(interval["start"], origin)  # type: ignore[arg-type]
        duration = (
            interval["end"] - interval["start"]  # type: ignore[operator]
        ).total_seconds()

        ax.barh(
            0,
            duration,
            left=start,
            height=0.55,
            color=interval["color"],
            edgecolor="black",
            linewidth=0.8,
        )

    ax.set_title("Pico State Timeline")
    ax.set_yticks([0])
    ax.set_yticklabels(["State"])
    ax.grid(axis="x", linestyle="--", alpha=0.35)


def build_legend_items() -> list[Patch]:
    legend_items: list[Patch] = []

    for label, color in HOST_EVENT_COLORS.items():
        legend_items.append(Patch(facecolor=color, edgecolor="black", label=f"Host: {label}"))

    for label, color in PICO_STATE_COLORS.items():
        legend_items.append(Patch(facecolor=color, edgecolor="black", label=f"Pico: {label}"))

    return legend_items


def main() -> None:
    host_intervals = parse_host_log(HOST_LOG)
    pico_states = parse_pico_states(PICO_LOG)
    pico_states = collapse_consecutive_states(pico_states)
    output_file = OUTPUT_DIR / f"timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

    origin, timeline_end = find_time_bounds(host_intervals, pico_states)
    pico_intervals = build_pico_intervals(pico_states, timeline_end)

    fig, (host_ax, pico_ax) = plt.subplots(
        2,
        1,
        figsize=(16, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.2]},
    )

    plot_host_timeline(host_ax, host_intervals, origin)
    plot_pico_timeline(pico_ax, pico_intervals, origin)

    max_time = seconds_from_origin(timeline_end, origin)
    pico_ax.set_xlim(0, max_time * 1.02 if max_time > 0 else 1)
    pico_ax.set_xlabel("Time since common origin (seconds)")

    fig.legend(
        handles=build_legend_items(),
        loc="upper center",
        ncol=3,
        bbox_to_anchor=(0.5, 1.02),
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=300, bbox_inches="tight")

    print(f"Saved {output_file}")


if __name__ == "__main__":
    main()
