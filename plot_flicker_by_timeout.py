"""
Plot: Reconnect flicker across all Ping Agent timeout configurations.

A cross-timeout summary of Table 4.7 (the per-timeout reconnect-flicker counts
produced by plot_disc_to_backup_flicker.py over the full sweep). Unlike the
per-timeout plot scripts, this one is not run per result/<ms>ms/ folder; it
takes the aggregated counts below and renders a single overview figure.

Left  : rounds (out of 1000) that exhibited flicker, per timeout.
Right : total spurious reconnections, per timeout (symlog scale).
The zero-flicker region (timeout >= 20 ms) is shaded for emphasis.

Output: result/flicker_by_timeout.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Table 4.7 — reconnect flicker across Ping Agent timeout configurations
# (1000 rounds each); values come from plot_disc_to_backup_flicker.py per dir.
timeouts       = [1, 2, 3, 4, 5, 10, 20, 40, 80, 100, 160, 320, 640, 1000]
rounds_flicker = [1000, 1000, 41, 648, 2, 6, 0, 0, 0, 0, 0, 0, 0, 0]
total_recon    = [29061, 22114, 69, 1045, 5, 6, 0, 0, 0, 0, 0, 0, 0, 0]

OUT_PNG = os.environ.get("OUT", "result/flicker_by_timeout.png")

x = np.arange(len(timeouts))
labels = [str(t) for t in timeouts]
bar_color = "#c0392b"

# Index of the first timeout that is completely stable (zero flicker).
first_stable = next(i for i, r in enumerate(rounds_flicker) if r == 0
                    and all(v == 0 for v in rounds_flicker[i:]))


def shade_stable(ax):
    ax.axvspan(first_stable - 0.5, len(timeouts) - 0.5,
               color="#27ae60", alpha=0.10, zorder=0)
    ax.text((first_stable - 0.5 + len(timeouts) - 0.5) / 2,
            ax.get_ylim()[1] * 0.92,
            "zero flicker (timeout ≥ %d ms)" % timeouts[first_stable],
            ha="center", va="top", fontsize=8, color="#1e7e45")


fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.6))

# --- Left: rounds with flicker (out of 1000) ---
axL.bar(x, rounds_flicker, color=bar_color, edgecolor="black", linewidth=0.4)
axL.set_title("Rounds with Reconnect Flicker  (out of 1000)")
axL.set_xlabel("Ping Agent timeout (ms)")
axL.set_ylabel("Rounds with flicker")
axL.set_xticks(x); axL.set_xticklabels(labels)
axL.set_ylim(0, 1130)
axL.grid(axis="y", ls=":", alpha=0.5)
shade_stable(axL)
for xi, v in zip(x, rounds_flicker):
    axL.text(xi, v + 14, str(v), ha="center", va="bottom", fontsize=8)

# --- Right: total spurious reconnections (symlog) ---
axR.bar(x, total_recon, color=bar_color, edgecolor="black", linewidth=0.4)
axR.set_title("Total Spurious Reconnections")
axR.set_xlabel("Ping Agent timeout (ms)")
axR.set_ylabel("Total reconnections")
axR.set_xticks(x); axR.set_xticklabels(labels)
axR.set_yscale("symlog", linthresh=1)
# Log scale: labels sit at v * 1.7, so give the tallest one clear headroom
# above the bar (was 60000, which clipped "29061" / "22114" at the top edge).
axR.set_ylim(0, 180000)
axR.grid(axis="y", ls=":", alpha=0.5)
shade_stable(axR)
for xi, v in zip(x, total_recon):
    axR.text(xi, v * 1.7 + 0.3, str(v), ha="center", va="bottom", fontsize=8)

fig.tight_layout()
fig.savefig(OUT_PNG, dpi=150)
print("saved", OUT_PNG)
