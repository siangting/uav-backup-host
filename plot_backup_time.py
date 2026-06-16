"""
Plot 4: Backup time
- backup_time = pico (first  [EVT] Backup activation completed  in the round's
                       window, i.e. after host "Stopping processes" and before
                       the next round's stop)
              - host  "Stopping processes"
- One value per round.

Why "first backup after stop" instead of pairing events by array position:
  Pico's connection sometimes flickers (disconnects/reconnects more than
  once) within a single round, so it can log more AGENT_DISCONNECTED /
  Backup-activation lines than there are host rounds. Pairing stop[i] with
  backup[i] by plain index breaks the moment that happens — every later
  round ends up paired with the wrong round's backup line, producing
  nonsense (often negative) deltas. Matching each stop to the first backup
  line that actually falls inside its time window is robust to that, and
  also naturally discards the many "Backup activation completed" lines
  Pico emits before round 1 even starts (no agent yet at initial boot) —
  those timestamps fall before stops[0], so they're outside every window.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    stat_block, ms_between, save_csv, first_in_each_window,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG  = ensure_result_dir() / "plot_backup_time.png"
OUT_CSV  = ensure_result_dir() / "plot_backup_time.csv"

pico = parse_pico_log(PICO_LOG)
host = parse_host_log(HOST_LOG)
stops   = host["stop"]
backups = pico["backup"]

first_backups = first_in_each_window(stops, backups)

pairs = [(i + 1, ms_between(stops[i], first_backups[i]))
         for i in range(len(stops)) if first_backups[i] is not None]
if not pairs:
    raise SystemExit("no paired stop / backup events")
rounds_idx = np.array([p[0] for p in pairs])
backup_ms  = np.array([p[1] for p in pairs], dtype=float)
print(f"[backup] {backup_ms.size} pairs; mean={backup_ms.mean():.1f} ms")

save_csv(OUT_CSV, ["round", "backup_time_ms"], pairs)
print(f"[backup] saved -> {OUT_CSV}")

fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(13, 5),
                                 gridspec_kw={"width_ratios": [1, 1.4]})

# ----- left: histogram -----
bins = max(10, min(60, int(np.sqrt(backup_ms.size) * 2)))
ax_h.hist(backup_ms, bins=bins, color="#DE350B",
          edgecolor="black", linewidth=0.5)
ax_h.axvline(backup_ms.mean(), color="black", linestyle="--", linewidth=1.2,
             label=f"mean = {backup_ms.mean():.1f} ms")
ax_h.axvline(np.percentile(backup_ms, 95), color="orange", linestyle=":",
             linewidth=1.2, label=f"p95 = {np.percentile(backup_ms, 95):.1f} ms")
ax_h.set_xlabel("Backup time (ms)")
ax_h.set_ylabel("count")
ax_h.set_title("Distribution")
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
ax_h.legend(loc="upper right")
ax_h.text(0.02, 0.97, stat_block(backup_ms), transform=ax_h.transAxes, va="top",
          family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

# ----- right: time series -----
ax_t.scatter(rounds_idx, backup_ms, s=14, alpha=0.6, color="#DE350B",
             edgecolor="black", linewidth=0.3, label="per round")
window = max(5, backup_ms.size // 20)
if backup_ms.size >= window:
    kernel = np.ones(window) / window
    rolling = np.convolve(backup_ms, kernel, mode="valid")
    # rolling-mean x positions are aligned to the (window-1)..end-th sample
    rounds_r = rounds_idx[window - 1:]
    ax_t.plot(rounds_r, rolling, color="black", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(backup_ms.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"overall mean = {backup_ms.mean():.1f} ms")
ax_t.set_xlabel("Round")
ax_t.set_ylabel("Backup time (ms)")
ax_t.set_title("Per-Round Time Series")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper right", fontsize=9)

fig.suptitle(
    f"Backup Time   host 'Stopping processes' → pico first 'Backup activation completed'\n"
    f"({HOST_LOG.name} | {PICO_LOG.name})",
    fontsize=11, y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[backup] saved -> {OUT_PNG}")