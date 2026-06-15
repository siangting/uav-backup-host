"""
Plot 4: Backup time
- backup_time = pico (first  [EVT] Backup activation completed  after each
                       [EVT] AGENT_DISCONNECTED)
              - host  "Stopping processes"
- One value per round.

Why "first backup after disconnect" instead of just AGENT_DISCONNECTED:
  AGENT_DISCONNECTED is the *detection* event. The next "Backup activation
  completed" is the moment Pico actually writes 1000us to the backup servo —
  the real end-to-end "agent dead → backup running" point.

  Note: at initial boot Pico has no agent yet and emits many "Backup activation
  completed" before round 1's AGENT_DISCONNECTED. Those are filtered out by
  only taking the first backup line *after* each disconnect.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    stat_block, ms_between,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG  = ensure_result_dir() / "plot_backup_time.png"

pico = parse_pico_log(PICO_LOG)
host = parse_host_log(HOST_LOG)
stops   = host["stop"]
discs   = pico["disc"]
backups = pico["backup"]


def first_backup_after_each_disconnect(discs, backups):
    """For each disconnect timestamp, return the next backup timestamp.

    Both lists are already in chronological order (events appended to log
    in time order), so we can sweep in O(n+m).
    """
    out, j = [], 0
    for d in discs:
        # advance j past anything before this disconnect
        while j < len(backups) and backups[j] < d:
            j += 1
        out.append(backups[j] if j < len(backups) else None)
    return out


first_backups = first_backup_after_each_disconnect(discs, backups)

n = min(len(stops), len(first_backups))
if n == 0:
    raise SystemExit("no paired stop / first-backup events")

pairs = []
for i in range(n):
    if first_backups[i] is None:
        continue
    pairs.append((i + 1, ms_between(stops[i], first_backups[i])))
rounds_idx = np.array([p[0] for p in pairs])
backup_ms  = np.array([p[1] for p in pairs], dtype=float)
print(f"[backup] {backup_ms.size} pairs; mean={backup_ms.mean():.1f} ms")

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