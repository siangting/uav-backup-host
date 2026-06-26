"""
Plot: Reconnect flicker across all Ping Agent timeout configurations.

A cross-timeout summary of Table 4.7 (the per-timeout reconnect-flicker counts
produced by plot_disc_to_backup_flicker.py over the full sweep). Unlike the
per-timeout plot scripts, this one is not run per result/<ms>ms/ folder; it
scans every result/<ms>ms/plot_disc_to_backup_flicker.csv and aggregates them
into a single overview figure.

Each per-timeout CSV has columns (round, reconnect_count). For a timeout we derive:
  rounds_flicker = rounds with reconnect_count > 0
  total_recon    = sum of reconnect_count over all rounds

Left  : percentage of rounds that exhibited flicker, per timeout.
Right : total spurious reconnections, per timeout (symlog scale).
The zero-flicker region (smallest timeout from which all are clean) is shaded.

Output: result/flicker_by_timeout.png
"""
import csv
import os
import re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULT_DIR = Path(os.environ.get("RESULT_DIR", "result"))
CSV_NAME   = "plot_disc_to_backup_flicker.csv"
OUT_PNG    = Path(os.environ.get("OUT", str(RESULT_DIR / "flicker_by_timeout.png")))


def timeout_ms(dirname):
    """'15ms' -> 15; returns None for folders that aren't a <n>ms timeout."""
    m = re.fullmatch(r"(\d+)ms", dirname)
    return int(m.group(1)) if m else None


def read_flicker_csv(path):
    """Return (rounds_with_flicker, total_reconnections, rounds_total) from one CSV."""
    rounds_flicker = 0
    total_recon = 0
    rounds_total = 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            n = int(row["reconnect_count"])
            total_recon += n
            rounds_total += 1
            if n > 0:
                rounds_flicker += 1
    return rounds_flicker, total_recon, rounds_total


# Discover every result/<n>ms/ folder that has a flicker CSV, sorted by timeout.
entries = []
for d in sorted(RESULT_DIR.iterdir()):
    if not d.is_dir():
        continue
    t = timeout_ms(d.name)
    csv_path = d / CSV_NAME
    if t is None or not csv_path.exists():
        continue
    rf, tr, rtot = read_flicker_csv(csv_path)
    entries.append((t, rf, tr, rtot))

entries.sort(key=lambda e: e[0])
if not entries:
    raise SystemExit(f"no */{CSV_NAME} found under {RESULT_DIR}")

timeouts       = [e[0] for e in entries]
rounds_flicker = [e[1] for e in entries]
total_recon    = [e[2] for e in entries]
rounds_total   = [e[3] for e in entries]

# Rounds run per timeout (same across the sweep); derived from the data so the
# left-plot percentages don't hardcode 1000.
total_rounds = max(rounds_total)
rounds_flicker_pct = [100.0 * rf / total_rounds for rf in rounds_flicker]

x = np.arange(len(timeouts))
labels = [str(t) for t in timeouts]
bar_color = "#c0392b"

# Index of the first timeout from which everything is stable (zero flicker).
first_stable = next((i for i, _ in enumerate(rounds_flicker)
                     if all(v == 0 for v in rounds_flicker[i:])), None)


def shade_stable(ax, text_y=None):
    if first_stable is None:
        return
    ax.axvspan(first_stable - 0.5, len(timeouts) - 0.5,
               color="#27ae60", alpha=0.10, zorder=0)
    # Default: near the top of the axis. Pass an explicit y to sit the label
    # lower (e.g. mid-height of the shaded band on the log-scaled right plot).
    if text_y is None:
        text_y = ax.get_ylim()[1] * 0.92
    ax.text((first_stable - 0.5 + len(timeouts) - 0.5) / 2,
            text_y,
            "zero flicker (timeout ≥ %d ms)" % timeouts[first_stable],
            ha="center", va="top", fontsize=8, color="#1e7e45")


fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.6))

# --- Left: rounds with flicker (as a percentage of all rounds) ---
axL.bar(x, rounds_flicker_pct, color=bar_color, edgecolor="black", linewidth=0.4)
axL.set_title("Rounds with Reconnect Flicker")
axL.set_xlabel("Ping Agent timeout (ms)")
axL.set_ylabel("Rounds with flicker (%)")
axL.set_xticks(x); axL.set_xticklabels(labels)
axL.set_ylim(0, 105)
axL.grid(axis="y", ls=":", alpha=0.5)
# Sit the label in the upper-middle of the shaded band, matching the height of
# the right plot's label (~70% of the axis) rather than the near-top default.
shade_stable(axL, text_y=axL.get_ylim()[1] * 0.70)
for xi, p in zip(x, rounds_flicker_pct):
    # Drop the trailing ".0" (100.0% -> 100%) so adjacent full-height bars
    # don't collide; keep one decimal for fractional values (e.g. 5.1%).
    label = "%d%%" % p if p == int(p) else "%.1f%%" % p
    axL.text(xi, p + 1.2, label, ha="center", va="bottom", fontsize=8)

# --- Right: total spurious reconnections (symlog) ---
top_tr = max(total_recon) if max(total_recon) else 1
axR.bar(x, total_recon, color=bar_color, edgecolor="black", linewidth=0.4)
axR.set_title("Total Spurious Reconnections")
axR.set_xlabel("Ping Agent timeout (ms)")
axR.set_ylabel("Total reconnections")
axR.set_xticks(x); axR.set_xticklabels(labels)
axR.set_yscale("symlog", linthresh=1)
# Log scale: labels sit at v * 1.7, so give the tallest one clear headroom.
axR.set_ylim(0, top_tr * 6)
axR.grid(axis="y", ls=":", alpha=0.5)
shade_stable(axR, text_y=3000)
for xi, v in zip(x, total_recon):
    axR.text(xi, v * 1.7 + 0.3, str(v), ha="center", va="bottom", fontsize=8)

fig.tight_layout()
for out in (OUT_PNG, OUT_PNG.with_suffix(".pdf"), OUT_PNG.with_suffix(".svg")):
    fig.savefig(out, dpi=150)
    print("saved", out)
