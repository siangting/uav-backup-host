import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

LOG_FILE = "pico.log"
OUTPUT = "pico_timeline.jpg"

# =========================
# PARSE TIME
# =========================
def parse_time(line):
    m = re.match(r"\[(\d+:\d+:\d+)\]", line)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%H:%M:%S")

# =========================
# PARSE LOG
# =========================
def parse_all():
    events, pings, destroys = [], [], []

    with open(LOG_FILE) as f:
        for line in f:
            t = parse_time(line)
            if not t:
                continue

            if "disconnect detected" in line:
                events.append((t, "disconnect"))

            elif "agent back online" in line:
                events.append((t, "recovery"))

            elif "[PING]" in line:
                val = int(re.findall(r"\d+", line)[-1])
                pings.append((t, val))

            elif "[DESTROY]" in line:
                val = int(re.findall(r"\d+", line)[-1])
                destroys.append((t, val))

    return events, pings, destroys

# =========================
# BUILD SEGMENTS
# =========================
def build_segments(events):
    segs = []
    for i in range(len(events)-1):
        t0, s0 = events[i]
        t1, _ = events[i+1]

        if (t1 - t0).total_seconds() > 0:
            segs.append((t0, t1, s0))
    return segs

# =========================
# NORMALIZE
# =========================
def normalize(segs, pings, destroys):
    all_times = []

    for s, e, _ in segs:
        all_times += [s, e]

    for t, _ in pings:
        all_times.append(t)

    for t, _ in destroys:
        all_times.append(t)

    t0 = min(all_times)

    seg_out = [((s-t0).total_seconds(), (e-s).total_seconds(), st) for s,e,st in segs]
    ping_out = [((t-t0).total_seconds(), v) for t,v in pings]
    destroy_out = [((t-t0).total_seconds(), v) for t,v in destroys]

    return seg_out, ping_out, destroy_out

# =========================
# MAIN
# =========================
def main():
    events, pings, destroys = parse_all()

    segs = build_segments(events)
    segs, pings, destroys = normalize(segs, pings, destroys)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(14, 6), sharex=True
    )

    # =========================
    # 1️⃣ STATE
    # =========================
    for start, dur, state in segs:
        color = "tab:orange" if state == "disconnect" else "tab:purple"
        ax1.barh(0, dur, left=start, color=color, edgecolor="black")

    ax1.set_title("State Timeline")
    ax1.set_yticks([])

    # =========================
    # 2️⃣ PING（🔥 Y軸 = latency）
    # =========================
    x_ping = [t for t, _ in pings]
    y_ping = [v for _, v in pings]

    ax2.scatter(x_ping, y_ping, color="blue", s=20)
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Ping Latency")

    # =========================
    # 3️⃣ DESTROY（🔥 Y軸 = time）
    # =========================
    x_des = [t for t, _ in destroys]
    y_des = [v for _, v in destroys]

    ax3.scatter(x_des, y_des, color="red", marker="^", s=30)
    ax3.set_ylabel("Time (ms)")
    ax3.set_title("Destroy Time")

    ax3.set_xlabel("Time (seconds)")

    # =========================
    # LEGEND
    # =========================
    handles = [
        mpatches.Patch(color="tab:orange", label="Disconnected"),
        mpatches.Patch(color="tab:purple", label="Recovered"),
        plt.Line2D([0],[0], marker='o', color='w', label='Ping', markerfacecolor='blue'),
        plt.Line2D([0],[0], marker='^', color='w', label='Destroy', markerfacecolor='red'),
    ]

    ax1.legend(handles=handles, loc="upper right")

    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=300)

    print(f"✅ saved to {OUTPUT}")

if __name__ == "__main__":
    main()