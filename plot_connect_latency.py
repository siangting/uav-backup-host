"""
Plot 3: Connect latency
- connect_latency = pico [EVT] AGENT_CONNECTED  -  host "Starting micro-ROS agent"
- One value per round.
- Layout: histogram (left) + time-series (right) — designed for 1000 rounds.

NOTE: round 1 is typically inflated because Pico is still booting when the
host starts the agent for the first time. We exclude it from the steady-state
stats but still show it on the time-series (highlighted).
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    stat_block, ms_between,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG  = ensure_result_dir() / "plot_connect_latency.png"

EXCLUDE_R1 = True   # exclude first round from histogram & stats (Pico still booting)

pico = parse_pico_log(PICO_LOG)
host = parse_host_log(HOST_LOG)
starts = host["start"]
conns  = pico["conn"]

n = min(len(starts), len(conns))
if n == 0:
    raise SystemExit("no paired start/connect events")
latencies = np.array(
    [ms_between(starts[i], conns[i]) for i in range(n)], dtype=float
)
print(f"[connect] loaded {n} samples; r1={latencies[0]:.1f} ms")

steady = latencies[1:] if (EXCLUDE_R1 and n > 1) else latencies

fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(13, 5),
                                 gridspec_kw={"width_ratios": [1, 1.4]})

# ----- left: histogram (steady-state only) -----
bins = max(10, min(60, int(np.sqrt(steady.size) * 2)))
ax_h.hist(steady, bins=bins, color="#0065FF",
          edgecolor="black", linewidth=0.5)
ax_h.axvline(steady.mean(), color="red", linestyle="--", linewidth=1.2,
             label=f"mean = {steady.mean():.1f} ms")
ax_h.axvline(np.percentile(steady, 95), color="orange", linestyle=":",
             linewidth=1.2, label=f"p95 = {np.percentile(steady, 95):.1f} ms")
ax_h.set_xlabel("Connect latency (ms)")
ax_h.set_ylabel("count")
title_suffix = "  (round 1 excluded)" if EXCLUDE_R1 and n > 1 else ""
ax_h.set_title(f"Distribution{title_suffix}")
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
ax_h.legend(loc="upper right")
ax_h.text(0.02, 0.97, stat_block(steady), transform=ax_h.transAxes, va="top",
          family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

# ----- right: time series (all rounds, R1 highlighted) -----
rounds = np.arange(1, n + 1)
colors = np.where((rounds == 1) & EXCLUDE_R1, "#FFAB00", "#0065FF")
ax_t.scatter(rounds, latencies, s=14, alpha=0.7, c=colors,
             edgecolor="black", linewidth=0.3)
if EXCLUDE_R1 and n > 1:
    # legend proxies
    ax_t.scatter([], [], s=20, c="#FFAB00", edgecolor="black",
                 label="round 1 (Pico still booting)")
    ax_t.scatter([], [], s=20, c="#0065FF", edgecolor="black",
                 label="steady-state rounds")

window = max(5, steady.size // 20)
if steady.size >= window:
    kernel = np.ones(window) / window
    rolling = np.convolve(steady, kernel, mode="valid")
    # x positions: the rolling-mean covers steady[0..end], which starts at round 2
    base = 2 if (EXCLUDE_R1 and n > 1) else 1
    rounds_r = np.arange(base + window - 1, base + steady.size)
    ax_t.plot(rounds_r, rolling, color="red", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(steady.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"steady mean = {steady.mean():.1f} ms")
ax_t.set_xlabel("Round")
ax_t.set_ylabel("Connect latency (ms)")
ax_t.set_title("Per-Round Time Series")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper right", fontsize=9)

fig.suptitle(
    f"Connect Latency   host 'Starting micro-ROS agent' → pico 'AGENT_CONNECTED'\n"
    f"({HOST_LOG.name} | {PICO_LOG.name})",
    fontsize=11, y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[connect] saved -> {OUT_PNG}")
