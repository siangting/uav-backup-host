"""
Plot 1: Pico Boot Time

- Source: log/pico_*.log, line `[T_BOOT] boot_time = X ms`
- Pico calculates this internally; one value per power-on.
- Designed for the 1000-round scenario but also works when Pico only booted once.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, ensure_result_dir, stat_block,
)

PICO_LOG = latest_log("pico")
OUT_PNG  = ensure_result_dir() / "plot_boot_time.png"

data = parse_pico_log(PICO_LOG)
boot = data["boot"]
if not boot:
    raise SystemExit(f"no [T_BOOT] line in {PICO_LOG}")

print(f"[boot] loaded {len(boot)} samples from {PICO_LOG.name}")

fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(1, len(boot) + 1)
ax.bar(x, boot, color="#4C9AFF", edgecolor="black",
       width=0.6 if len(boot) <= 30 else 1.0)

mean = float(np.mean(boot))
ax.axhline(mean, color="red", linestyle="--", linewidth=1.2,
           label=f"mean = {mean:.0f} ms")

# Per-bar labels only when N is small enough to be readable
if len(boot) <= 30:
    for xi, v in zip(x, boot):
        ax.text(xi, v, f"{v}", ha="center", va="bottom", fontsize=9)

ax.set_xlabel("Power-on #")
ax.set_ylabel("Boot time (ms)")
ax.set_title(f"Pico Boot Time   ({PICO_LOG.name})")
ax.set_ylim(0, max(boot) * 1.18)
ax.grid(axis="y", linestyle=":", alpha=0.5)
ax.legend(loc="upper right")

ax.text(0.02, 0.97, stat_block(boot), transform=ax.transAxes, va="top",
        family="monospace", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150)
print(f"[boot] saved -> {OUT_PNG}")
