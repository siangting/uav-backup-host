"""
Plot 1: Pico Boot Time

- Source: log/pico_*.log, line `[T_BOOT] boot_time = X ms`
- Pico calculates this internally; one value per power-on.
- Designed for the 1000-round scenario but also works when Pico only booted once.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, ensure_result_dir, stat_block, save_csv,
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

fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(13, 5),
                                 gridspec_kw={"width_ratios": [1, 1.4]})

# ----- left: histogram -----
bins = max(10, min(60, int(np.sqrt(boot_ms.size) * 2)))
ax_h.hist(boot_ms, bins=bins, color="#4C9AFF",
          edgecolor="black", linewidth=0.5)
ax_h.axvline(boot_ms.mean(), color="black", linestyle="--", linewidth=1.2,
             label=f"mean = {boot_ms.mean():.1f} ms")
ax_h.axvline(np.percentile(boot_ms, 95), color="orange", linestyle=":",
             linewidth=1.2, label=f"p95 = {np.percentile(boot_ms, 95):.1f} ms")
ax_h.set_xlabel("Boot time (ms)")
ax_h.set_ylabel("count")
ax_h.set_title("Distribution")
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
ax_h.legend(loc="upper right")
ax_h.text(0.02, 0.97, stat_block(boot_ms), transform=ax_h.transAxes, va="top",
          family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

# ----- right: time series -----
ax_t.scatter(x, boot_ms, s=14, alpha=0.6, color="#4C9AFF",
             edgecolor="black", linewidth=0.3, label="per power-on")
window = max(5, boot_ms.size // 20)
if boot_ms.size >= window:
    kernel = np.ones(window) / window
    rolling = np.convolve(boot_ms, kernel, mode="valid")
    # rolling-mean x positions are aligned to the (window-1)..end-th sample
    x_r = x[window - 1:]
    ax_t.plot(x_r, rolling, color="black", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(boot_ms.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"overall mean = {boot_ms.mean():.1f} ms")
ax_t.set_xlabel("Power-on #")
ax_t.set_ylabel("Boot time (ms)")
ax_t.set_title("Per-Power-On Time Series")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper right", fontsize=9)

fig.suptitle(
    f"Pico Boot Time   ({PICO_LOG.name})",
    fontsize=11, y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[boot] saved -> {OUT_PNG}")
