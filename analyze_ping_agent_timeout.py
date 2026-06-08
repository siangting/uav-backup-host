from __future__ import annotations

import bisect
import os
import re
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt


LOG_DIR = Path("ping_agent_timeout")
OUTPUT_PLOT = Path("instability_vs_timeout_r1000.png")
ROUNDS_PER_FILE = 1000

PICO_FILENAME_RE = re.compile(r"^pico_timeout_(?P<timeout_ms>\d+)ms_r1000\.log$")
HOST_FILENAME_RE = re.compile(r"^host_timeout_(?P<timeout_ms>\d+)ms_r1000\.log$")
TIMESTAMP_RE = re.compile(r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6})\]")
STATE_RE = re.compile(r"\[STATE\]\s+(?P<state>.+)$")
ROUND_START_RE = re.compile(r"ROUND\s+\d+\s+START")
ROUND_END_RE = re.compile(r"ROUND\s+\d+\s+END")
STOPPING_PROCESSES_MESSAGE = "Stopping processes"

CONNECTED_STATE = "agent connected"
DISCONNECT_STATE = "disconnect detected"


def parse_timestamp(line: str) -> datetime | None:
    match = TIMESTAMP_RE.match(line)
    if match is None:
        return None

    return datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S.%f")


def extract_timeout_ms(path: Path, pattern: re.Pattern[str]) -> int | None:
    match = pattern.match(path.name)
    if match is None:
        return None

    return int(match.group("timeout_ms"))


def find_log_files(log_dir: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    files: dict[int, Path] = {}

    for path in log_dir.iterdir():
        if not path.is_file():
            continue

        timeout_ms = extract_timeout_ms(path, pattern)
        if timeout_ms is not None:
            files[timeout_ms] = path

    return files


def parse_host_rounds(path: Path) -> list[tuple[datetime, datetime]]:
    rounds: list[tuple[datetime, datetime]] = []
    round_start: datetime | None = None
    stopping_time: datetime | None = None

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            timestamp = parse_timestamp(line)
            if timestamp is None:
                continue

            if ROUND_START_RE.search(line):
                round_start = timestamp
                stopping_time = None
                continue

            if round_start is not None and STOPPING_PROCESSES_MESSAGE in line:
                stopping_time = timestamp
                continue

            if ROUND_END_RE.search(line) and round_start is not None:
                # ROUND END is logged after intentional teardown; use the stop
                # command time so planned disconnects do not count as failures.
                effective_end = stopping_time or timestamp
                if effective_end >= round_start:
                    rounds.append((round_start, effective_end))
                round_start = None
                stopping_time = None

                if len(rounds) >= ROUNDS_PER_FILE:
                    break

    return rounds


def parse_pico_events(path: Path) -> list[tuple[datetime, str]]:
    events: list[tuple[datetime, str]] = []

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            timestamp = parse_timestamp(line)
            if timestamp is None:
                continue

            state_match = STATE_RE.search(line)
            if state_match is None:
                continue

            events.append((timestamp, state_match.group("state").strip()))

    return events


def round_is_unstable(
    round_start: datetime,
    round_end: datetime,
    pico_events: list[tuple[datetime, str]],
    pico_timestamps: list[datetime],
) -> bool:
    start_index = bisect.bisect_left(pico_timestamps, round_start)

    first_connected_index: int | None = None
    for index in range(start_index, len(pico_events)):
        timestamp, state = pico_events[index]
        if timestamp > round_end:
            break

        if state == CONNECTED_STATE:
            first_connected_index = index
            break

    if first_connected_index is None:
        return False

    for timestamp, state in pico_events[first_connected_index:]:
        if timestamp > round_end:
            break

        if state == DISCONNECT_STATE:
            return True

    return False


def count_unstable_rounds(host_path: Path, pico_path: Path) -> int:
    rounds = parse_host_rounds(host_path)
    pico_events = parse_pico_events(pico_path)
    pico_timestamps = [timestamp for timestamp, _state in pico_events]

    unstable_count = 0
    for round_start, round_end in rounds[:ROUNDS_PER_FILE]:
        if round_is_unstable(round_start, round_end, pico_events, pico_timestamps):
            unstable_count += 1

    return unstable_count


def analyze_logs(log_dir: Path) -> list[tuple[int, int]]:
    pico_files = find_log_files(log_dir, PICO_FILENAME_RE)
    host_files = find_log_files(log_dir, HOST_FILENAME_RE)
    matched_timeouts = sorted(set(pico_files) & set(host_files))

    results: list[tuple[int, int]] = []
    for timeout_ms in matched_timeouts:
        unstable_count = count_unstable_rounds(
            host_files[timeout_ms],
            pico_files[timeout_ms],
        )
        results.append((timeout_ms, unstable_count))

    return results


def print_table(results: list[tuple[int, int]]) -> None:
    print("timeout_ms | unstable_count | ratio")
    print("-----------|----------------|------")

    for timeout_ms, unstable_count in results:
        ratio = unstable_count / ROUNDS_PER_FILE
        print(f"{timeout_ms:10d} | {unstable_count:14d} | {ratio:.2f}")


def plot_results(results: list[tuple[int, int]], output_path: Path) -> None:
    timeout_values = [timeout_ms for timeout_ms, _unstable_count in results]
    unstable_counts = [unstable_count for _timeout_ms, unstable_count in results]

    plt.figure(figsize=(8, 5))
    plt.plot(timeout_values, unstable_counts, marker="o", linestyle="None")
    for timeout_ms, unstable_count in zip(timeout_values, unstable_counts):
        plt.annotate(
            str(unstable_count),
            (timeout_ms, unstable_count),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
        )
    # plt.figure(figsize=(10, 5))

    # plt.plot(timeout_values, unstable_counts, marker="o", linestyle="None")

    # for timeout_ms, unstable_count in zip(timeout_values, unstable_counts):
    #     plt.annotate(
    #         str(unstable_count),
    #         (timeout_ms, unstable_count),
    #         textcoords="offset points",
    #         xytext=(0, 8),
    #         ha="center",
    #     )

    # plt.xticks(
    #     timeout_values,
    #     [f"{timeout_ms}" for timeout_ms in timeout_values],
    #     rotation=45,
    #     # fontsize=6
    # )

    plt.figure(figsize=(10, 5))

    plt.plot(timeout_values, unstable_counts, marker="o", linestyle="None")

    plt.xscale("log", base=2)

    plt.xticks(
        timeout_values,
        [f"{timeout_ms}" for timeout_ms in timeout_values],
        fontsize=8
    )


    plt.xlabel("Timeout (ms)")
    plt.ylabel("Unstable count")
    plt.title("Ping Timeout vs Connection Instability")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    if not LOG_DIR.exists():
        raise FileNotFoundError(f"Log directory does not exist: {LOG_DIR}")

    results = analyze_logs(LOG_DIR)
    if not results:
        print(f"No matched host/pico log pairs found in {LOG_DIR}")
        return

    print_table(results)
    plot_results(results, OUTPUT_PLOT)
    print(f"\nSaved plot to {OUTPUT_PLOT}")


if __name__ == "__main__":
    main()
