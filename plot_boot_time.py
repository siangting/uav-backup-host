"""
Plot 1: Pico Boot Time

- Source: log/pico_*.log, line `[T_BOOT] boot_time = X ms`
- Pico calculates this internally; one value per power-on.
- Designed for the 1000-round scenario but also works when Pico only booted once.

Boot time is effectively a discrete, two-valued measurement (e.g. 552 / 553 ms),
so the figure is a value-count bar chart (count + percentage per observed value)
plus a stats box, rather than a continuous-distribution histogram.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, ensure_result_dir, save_csv,
)

PICO_LOG = latest_log("pico")
OUT_PNG  = ensure_result_dir() / "plot_boot_time.png"
OUT_CSV  = ensure_result_dir() / "plot_boot_time.csv"

data = parse_pico_log(PICO_LOG)
boot = data["boot"]
if not boot:
    raise SystemExit(f"no [T_BOOT] line in {PICO_LOG}")

print(f"[boot] loaded {len(boot)} samples from {PICO_LOG.name}")

x = np.arange(1, len(boot) + 1)
boot_ms = np.array(boot, dtype=float)
save_csv(OUT_CSV, ["power_on", "boot_time_ms"], zip(x, boot))
print(f"[boot] saved -> {OUT_CSV}")

# Unique boot-time values and their counts (data is discrete, usually 2 values).
vals, counts = np.unique(boot_ms, return_counts=True)
pct = counts / counts.sum() * 100.0


def discrete_stat_block(unit="ms") -> str:
    """Monospace stats block tailored to discrete, few-valued data."""
    lines = [
        f"n      = {len(boot_ms)}",
        f"unique = {len(vals)} value(s)",
    ]
    for v, c, p in zip(vals, counts, pct):
        lines.append(f"{int(v):>4} {unit} = {c:>5}  ({p:4.1f}%)")
    lines.append(f"min    = {int(boot_ms.min())} {unit}")
    lines.append(f"max    = {int(boot_ms.max())} {unit}")
    return "\n".join(lines)


# Single plot: the bar chart on the left, with the stats box in the reserved
# right margin so it stays outside the plot area without being clipped.
fig, ax_h = plt.subplots(figsize=(8, 5))
fig.subplots_adjust(left=0.10, right=0.60, top=0.86, bottom=0.12)

# ----- value-count bar chart -----
bar_labels = [f"{int(v)} ms" for v in vals]
bars = ax_h.bar(bar_labels, counts, color="#4C9AFF",
                edgecolor="black", linewidth=0.5, width=0.6)
for bar, c, p in zip(bars, counts, pct):
    ax_h.text(bar.get_x() + bar.get_width() / 2, c,
              f"{c}\n({p:.1f}%)", ha="center", va="bottom", fontsize=9)
ax_h.set_xlabel("Boot time")
ax_h.set_ylabel("count")
ax_h.set_title("Boot-Time Value Counts")
ax_h.set_ylim(0, counts.max() * 1.2)
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
# stats box sits outside, to the right of the bar chart
ax_h.text(1.08, 1.0, discrete_stat_block(), transform=ax_h.transAxes,
          va="top", ha="left", family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

fig.suptitle(
    f"Pico Boot Time  ({PICO_LOG.name})",
    fontsize=11
)
for out in (OUT_PNG, OUT_PNG.with_suffix(".pdf"), OUT_PNG.with_suffix(".svg")):
    plt.savefig(out, dpi=150)
    print(f"[boot] saved -> {out}")
