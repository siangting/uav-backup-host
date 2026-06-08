import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# =========================
# CONFIG
# =========================
HOST_LOG = "timeline.log"
PICO_LOG = "pico.log"
OUTPUT = "timeline.jpg"

# =========================
# LABEL MAP
# =========================
LABEL_MAP = {
    "round": "Loop Start",
    "agent": "Agent Up",
    "heartbeat": "Heartbeat",
    "stop": "Agent Down",
    "disconnect": "Disconnected",
    "recovery": "Recovered"
}

# =========================
# COLORS
# =========================
COLORS = {
    "round": "tab:blue",
    "agent": "tab:green",
    "heartbeat": "tab:cyan",
    "stop": "tab:red",
    "disconnect": "tab:orange",
    "recovery": "tab:purple",
}

# =========================
# PARSE HOST
# =========================
def parse_host():
    events = []

    with open(HOST_LOG) as f:
        for line in f:
            if "|" not in line:
                continue

            try:
                t = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S.%f")
            except:
                continue

            if "ROUND" in line and "START" in line:
                events.append((t, "round"))
            elif "Starting micro-ROS agent" in line:
                events.append((t, "agent"))
            elif "Starting heartbeat publisher" in line:
                events.append((t, "heartbeat"))
            elif "Stopping processes" in line:
                events.append((t, "stop"))

    return events

# =========================
# PARSE PICO
# =========================
def parse_pico(base_date):
    events = []

    with open(PICO_LOG) as f:
        for line in f:
            m = re.match(r"\[(\d+:\d+:\d+)\]", line)
            if not m:
                continue

            try:
                t = datetime.strptime(m.group(1), "%H:%M:%S")
            except:
                continue

            t = t.replace(
                year=base_date.year,
                month=base_date.month,
                day=base_date.day
            )

            if "disconnect detected" in line:
                events.append((t, "disconnect"))
            elif "agent back online" in line:
                events.append((t, "recovery"))

    return events

# =========================
# BUILD INTERVALS
# =========================
def build_intervals(events):
    intervals = []

    for i in range(len(events) - 1):
        t0, s0 = events[i]
        t1, _ = events[i + 1]

        if (t1 - t0).total_seconds() > 0:
            intervals.append((t0, t1, s0))

    return intervals

# =========================
# NORMALIZE
# =========================
def normalize(intervals, t0):
    result = []

    for s, e, stage in intervals:
        start = (s - t0).total_seconds()
        duration = (e - s).total_seconds()
        result.append((start, duration, stage))

    return result

# =========================
# DRAW BAR（無文字）
# =========================
def draw_bar(ax, intervals):
    y = 0

    for start, dur, stage in intervals:
        ax.barh(
            y,
            dur,
            left=start,
            color=COLORS.get(stage, "gray")
        )
        y += 0.3

    ax.set_yticks([])

# =========================
# MAIN
# =========================
def main():
    host_events = parse_host()

    if not host_events:
        print("❌ No host events")
        return

    base_date = host_events[0][0]
    pico_events = parse_pico(base_date)

    t0 = min(
        host_events[0][0],
        pico_events[0][0] if pico_events else host_events[0][0]
    )

    host_intervals = normalize(build_intervals(host_events), t0)
    pico_intervals = normalize(build_intervals(pico_events), t0)

    # =========================
    # PLOT
    # =========================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    draw_bar(ax1, host_intervals)
    ax1.set_title("Host Timeline (5 loops)")

    draw_bar(ax2, pico_intervals)
    ax2.set_title("Pico Timeline")

    ax2.set_xlabel("Time (seconds)")

    # =========================
    # LEGEND（右側）
    # =========================
    handles = [
        mpatches.Patch(color=COLORS[k], label=LABEL_MAP[k])
        for k in COLORS
    ]

    ax1.legend(
        handles=handles,
        bbox_to_anchor=(1.02, 1),
        loc="upper left"
    )

    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=300)
    print(f"✅ Saved to {OUTPUT}")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()