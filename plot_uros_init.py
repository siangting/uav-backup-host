"""
Plot 2: micro-ROS init time

- Source: log/pico_*.log, line `[T_UROS_INIT] init_time = X ms`
- One value per round.
- Layout: histogram (left) + time-series (right) — designed for 1000 rounds.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, ensure_result_dir, stat_block, save_csv,
)

PICO_LOG = latest_log("pico")
OUT_PNG  = ensure_result_dir() / "plot_uros_init.png"
OUT_CSV  = ensure_result_dir() / "plot_uros_init.csv"

data = parse_pico_log(PICO_LOG)
init = np.array(data["init"], dtype=float)
if init.size == 0:
    raise SystemExit(f"no [T_UROS_INIT] line in {PICO_LOG}")

print(f"[init] loaded {init.size} samples from {PICO_LOG.name}")

save_csv(OUT_CSV, ["round", "init_time_ms"],
         zip(range(1, init.size + 1), init))
print(f"[init] saved -> {OUT_CSV}")

fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(18, 5), layout="constrained",
                                 gridspec_kw={"width_ratios": [1, 1.4]})

# ----- left: histogram -----
bins = max(10, min(60, int(np.sqrt(init.size) * 2)))
ax_h.hist(init, bins=bins, color="#36B37E",
          edgecolor="black", linewidth=0.5)
ax_h.axvline(init.mean(), color="red", linestyle="--", linewidth=1.2,
             label=f"mean = {init.mean():.2f} ms")
ax_h.axvline(np.percentile(init, 95), color="orange", linestyle=":",
             linewidth=1.2, label=f"p95 = {np.percentile(init, 95):.2f} ms")
ax_h.set_xlabel("micro-ROS init time (ms)")
ax_h.set_ylabel("count")
ax_h.set_title("Distribution")
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
# legend + stats box sit outside, to the right of the histogram axes
ax_h.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9)
ax_h.text(1.02, 0.78, stat_block(init), transform=ax_h.transAxes,
          va="top", ha="left", family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

# ----- right: time series -----
rounds = np.arange(1, init.size + 1)
ax_t.scatter(rounds, init, s=12, alpha=0.6, color="#36B37E",
             edgecolor="black", linewidth=0.3, label="per round")
# Rolling mean (window adapts to sample size)
window = max(5, init.size // 20)
if init.size >= window:
    kernel = np.ones(window) / window
    rolling = np.convolve(init, kernel, mode="valid")
    rounds_r = np.arange(window, init.size + 1)
    ax_t.plot(rounds_r, rolling, color="red", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(init.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"overall mean = {init.mean():.2f} ms")
ax_t.set_xlabel("Round")
ax_t.set_ylabel("micro-ROS init time (ms)")
ax_t.set_title("Per-Round Time Series")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9)

fig.suptitle(f"micro-ROS Entities Init Time   ({PICO_LOG.name})",
             fontsize=12)
fig.get_layout_engine().set(w_pad=0.08, wspace=0.18)
for out in (OUT_PNG, OUT_PNG.with_suffix(".pdf"), OUT_PNG.with_suffix(".svg")):
    plt.savefig(out, dpi=150)
    print(f"[init] saved -> {out}")
