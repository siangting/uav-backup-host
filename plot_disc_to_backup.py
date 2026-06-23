"""
Plot: Disconnect → backup activation latency

disc_to_backup = pico [EVT] Backup activation completed
               - pico [EVT] AGENT_DISCONNECTED

One value per round (defined by the host's "Stopping processes" boundaries).
Uses the FIRST AGENT_DISCONNECTED in each round's window so that flicker
(extra disconnect/reconnect cycles within the same round) does not create
phantom extra samples.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    stat_block, save_csv, ms_between, events_in_each_window, first_at_or_after,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG = ensure_result_dir() / "plot_disc_to_backup.png"
OUT_CSV = ensure_result_dir() / "plot_disc_to_backup.csv"

pico    = parse_pico_log(PICO_LOG)
host    = parse_host_log(HOST_LOG)
stops   = host["stop"]
discs   = pico["disc"]
backups = pico["backup"]

disc_windows = events_in_each_window(stops, discs)

pairs = []   # (round, disc_to_backup_ms)
for i, ds in enumerate(disc_windows):
    if not ds:
        continue
    first_disc = ds[0]
    backup = first_at_or_after(first_disc, backups)
    if backup is None:
        continue
    pairs.append((i + 1, ms_between(first_disc, backup)))

if not pairs:
    raise SystemExit(f"no paired AGENT_DISCONNECTED / Backup-activation events in {PICO_LOG}")

rounds_idx = np.array([p[0] for p in pairs])
gap_ms     = np.array([p[1] for p in pairs], dtype=float)
print(f"[disc2backup] {gap_ms.size} rounds paired; mean={gap_ms.mean():.2f} ms")

save_csv(OUT_CSV, ["round", "disc_to_backup_ms"], pairs)
print(f"[disc2backup] saved -> {OUT_CSV}")

# ---- histogram + per-round time series ----
fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(13, 5),
                                  gridspec_kw={"width_ratios": [1, 1.4]})

bins = max(10, min(60, int(np.sqrt(gap_ms.size) * 2)))
ax_h.hist(gap_ms, bins=bins, color="#6554C0", edgecolor="black", linewidth=0.5)
ax_h.axvline(gap_ms.mean(), color="black", linestyle="--", linewidth=1.2,
             label=f"mean = {gap_ms.mean():.2f} ms")
ax_h.axvline(np.percentile(gap_ms, 95), color="orange", linestyle=":",
             linewidth=1.2, label=f"p95 = {np.percentile(gap_ms, 95):.2f} ms")
ax_h.set_xlabel("Disconnect → backup activation (ms)")
ax_h.set_ylabel("count")
ax_h.set_title("Distribution")
ax_h.grid(axis="y", linestyle=":", alpha=0.5)
ax_h.legend(loc="upper right")
ax_h.text(0.02, 0.97, stat_block(gap_ms), transform=ax_h.transAxes, va="top",
          family="monospace", fontsize=9,
          bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))

ax_t.scatter(rounds_idx, gap_ms, s=14, alpha=0.6, color="#6554C0",
             edgecolor="black", linewidth=0.3, label="per round")
window = max(5, gap_ms.size // 20)
if gap_ms.size >= window:
    kernel  = np.ones(window) / window
    rolling = np.convolve(gap_ms, kernel, mode="valid")
    ax_t.plot(rounds_idx[window - 1:], rolling, color="black", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(gap_ms.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"overall mean = {gap_ms.mean():.2f} ms")
ax_t.set_xlabel("Round")
ax_t.set_ylabel("Disconnect → backup activation (ms)")
ax_t.set_title("Per-Round Time Series (first disconnect only)")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper right", fontsize=9)

fig.suptitle(
    "Disconnect → Backup Activation   "
    "pico 'AGENT_DISCONNECTED' → pico 'Backup activation completed'\n"
    f"({PICO_LOG.name})",
    fontsize=11, y=1.02,
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[disc2backup] saved -> {OUT_PNG}")
