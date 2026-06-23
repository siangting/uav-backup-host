"""
Plot: Reconnect-flicker summary

Counts the number of times pico reconnects within each round, where a round is
defined by the host log as [Agent container started, Processes stopped].

reconnect_count per round = AGENT_CONNECTED events in that window - 1
  (subtract 1 for the initial connection after the container becomes ready)
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    save_csv, events_in_range,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG  = ensure_result_dir() / "plot_disc_to_backup_flicker.png"
OUT_CSV  = ensure_result_dir() / "plot_disc_to_backup_flicker.csv"

pico        = parse_pico_log(PICO_LOG)
host        = parse_host_log(HOST_LOG)
agent_ready = host["agent_ready"]   # "Agent container started"
stopped     = host["stopped"]       # "Processes stopped"
conns       = pico["conn"]

if len(agent_ready) != len(stopped):
    raise SystemExit(
        f"mismatched round markers: {len(agent_ready)} 'Agent container started' "
        f"vs {len(stopped)} 'Processes stopped'"
    )

# For each round i, count AGENT_CONNECTED events in [agent_ready[i], stopped[i]).
# reconnect_count = total_conn - 1  (first conn is the initial connection, rest are reconnects).
flicker_rows = []   # (round, reconnect_count)
for i, (lo, hi) in enumerate(zip(agent_ready, stopped)):
    cs = events_in_range(lo, hi, conns)
    reconnect_count = max(0, len(cs) - 1)
    flicker_rows.append((i + 1, reconnect_count))

save_csv(OUT_CSV, ["round", "reconnect_count"], flicker_rows)
print(f"[flicker] saved -> {OUT_CSV}")

flicker_rounds   = np.array([r[0] for r in flicker_rows])
reconnect_counts = np.array([r[1] for r in flicker_rows])
n_rounds         = len(flicker_rows)
n_flickered      = int((reconnect_counts > 0).sum())
print(f"[flicker] {n_flickered}/{n_rounds} rounds had reconnects "
      f"(max {reconnect_counts.max()})")

# ---- bar chart (rounds by reconnect count) + scatter (per-round over time) ----
fig, (ax_b, ax_s) = plt.subplots(1, 2, figsize=(13, 5),
                                  gridspec_kw={"width_ratios": [1, 1.4]})

max_reconnect = int(reconnect_counts.max())
levels        = np.arange(0, max_reconnect + 1)
level_counts  = np.array([(reconnect_counts == lvl).sum() for lvl in levels])
bar_colors    = ["#36B37E" if lvl == 0 else "#DE350B" for lvl in levels]
ax_b.bar(levels, level_counts, color=bar_colors, edgecolor="black", linewidth=0.5)
for lvl, cnt in zip(levels, level_counts):
    ax_b.text(lvl, cnt, f"{cnt}", ha="center", va="bottom", fontsize=9)
ax_b.set_xlabel("Reconnects within the round")
ax_b.set_ylabel("Round count")
ax_b.set_title(f"Rounds by Reconnect Count  ({n_flickered}/{n_rounds} flickered)")
ax_b.set_xticks(levels)
ax_b.grid(axis="y", linestyle=":", alpha=0.5)

colors = np.where(reconnect_counts > 0, "#DE350B", "#36B37E")
ax_s.scatter(flicker_rounds, reconnect_counts, s=14, alpha=0.7, c=colors,
             edgecolor="black", linewidth=0.3)
ax_s.scatter([], [], s=20, c="#36B37E", edgecolor="black", label="clean round (0 reconnects)")
ax_s.scatter([], [], s=20, c="#DE350B", edgecolor="black", label="flickered round (>=1 reconnect)")
ax_s.set_xlabel("Round")
ax_s.set_ylabel("Reconnects within the round")
ax_s.set_title("Per-Round Reconnect Count")
ax_s.set_yticks(levels)
ax_s.grid(linestyle=":", alpha=0.5)
ax_s.legend(loc="upper right", fontsize=9)

fig.suptitle(
    "Reconnect Flicker   "
    "(rounds where Pico disconnected/reconnected more than once)\n"
    f"({PICO_LOG.name} | {HOST_LOG.name})",
    fontsize=11, y=1.02,
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[flicker] saved -> {OUT_PNG}")
