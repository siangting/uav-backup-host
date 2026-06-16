"""
Plot 5: Disconnect → backup activation latency

- disc_to_backup = pico [EVT] Backup activation completed
                 - pico [EVT] AGENT_DISCONNECTED
- One value per round (1000 rounds, defined by the host's "Stopping
  processes" boundaries) — NOT one value per disconnect line.

Why per-round and not per-disconnect-line:
  Pico's connection sometimes flickers (disconnects/reconnects more than
  once) within a single round, so the pico log can contain more
  AGENT_DISCONNECTED / Backup-activation lines than there are rounds (e.g.
  1329 lines for 1000 rounds). If we measured every line, we'd silently be
  counting reconnection blips as if they were extra rounds. Instead, each
  round only contributes ONE disc_to_backup sample: the FIRST disconnect
  in that round's window, paired with the backup line right after it. Any
  extra disconnect/backup pairs in the same round are flicker, not a new
  round — counted separately and charted in plot_disc_to_backup_flicker.png.
"""
import matplotlib.pyplot as plt
import numpy as np
from log_parser import (
    latest_log, parse_pico_log, parse_host_log, ensure_result_dir,
    stat_block, save_csv, ms_between, events_in_each_window, first_at_or_after,
)

PICO_LOG = latest_log("pico")
HOST_LOG = latest_log("host")
OUT_PNG          = ensure_result_dir() / "plot_disc_to_backup.png"
OUT_CSV          = ensure_result_dir() / "plot_disc_to_backup.csv"
OUT_FLICKER_PNG  = ensure_result_dir() / "plot_disc_to_backup_flicker.png"
OUT_FLICKER_CSV  = ensure_result_dir() / "plot_disc_to_backup_flicker.csv"

pico = parse_pico_log(PICO_LOG)
host = parse_host_log(HOST_LOG)
stops   = host["stop"]
discs   = pico["disc"]
backups = pico["backup"]

# All AGENT_DISCONNECTED lines that fall inside each round's window.
disc_windows = events_in_each_window(stops, discs)

pairs        = []   # (round, disc_to_backup_ms)  -- first disconnect only
flicker_rows = []   # (round, disconnect_count, reconnect_count)
for i, ds in enumerate(disc_windows):
    flicker_rows.append((i + 1, len(ds), max(0, len(ds) - 1)))
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
flicker_rounds, disc_counts, reconnect_counts = (
    np.array([r[0] for r in flicker_rows]),
    np.array([r[1] for r in flicker_rows]),
    np.array([r[2] for r in flicker_rows]),
)
n_flickered = int((reconnect_counts > 0).sum())
print(f"[disc2backup] {gap_ms.size} rounds; mean={gap_ms.mean():.2f} ms "
      f"| {n_flickered}/{len(stops)} rounds had extra reconnects "
      f"(max {reconnect_counts.max()})")

save_csv(OUT_CSV, ["round", "disc_to_backup_ms"], pairs)
print(f"[disc2backup] saved -> {OUT_CSV}")
save_csv(OUT_FLICKER_CSV, ["round", "disconnect_count", "reconnect_count"], flicker_rows)
print(f"[disc2backup] saved -> {OUT_FLICKER_CSV}")

# ============================================================
# Chart 1: disc_to_backup latency (histogram + per-round series)
# ============================================================
fig, (ax_h, ax_t) = plt.subplots(1, 2, figsize=(13, 5),
                                 gridspec_kw={"width_ratios": [1, 1.4]})

bins = max(10, min(60, int(np.sqrt(gap_ms.size) * 2)))
ax_h.hist(gap_ms, bins=bins, color="#6554C0",
          edgecolor="black", linewidth=0.5)
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
    kernel = np.ones(window) / window
    rolling = np.convolve(gap_ms, kernel, mode="valid")
    rounds_r = rounds_idx[window - 1:]
    ax_t.plot(rounds_r, rolling, color="black", linewidth=1.8,
              label=f"rolling mean (w={window})")
ax_t.axhline(gap_ms.mean(), color="black", linestyle="--", linewidth=0.8,
             alpha=0.5, label=f"overall mean = {gap_ms.mean():.2f} ms")
ax_t.set_xlabel("Round")
ax_t.set_ylabel("Disconnect → backup activation (ms)")
ax_t.set_title("Per-Round Time Series (first disconnect only)")
ax_t.grid(linestyle=":", alpha=0.5)
ax_t.legend(loc="upper right", fontsize=9)

fig.suptitle(
    f"Disconnect → Backup Activation   pico 'AGENT_DISCONNECTED' → pico 'Backup activation completed'\n"
    f"({PICO_LOG.name})",
    fontsize=11, y=1.02
)
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"[disc2backup] saved -> {OUT_PNG}")

# ============================================================
# Chart 2: reconnect-flicker summary (extra disconnects per round)
# ============================================================
fig2, (ax_b, ax_s) = plt.subplots(1, 2, figsize=(13, 5),
                                  gridspec_kw={"width_ratios": [1, 1.4]})

# ----- left: how many rounds had 0 / 1 / 2 / ... extra reconnects -----
max_reconnect = int(reconnect_counts.max())
levels = np.arange(0, max_reconnect + 1)
level_counts = np.array([(reconnect_counts == lvl).sum() for lvl in levels])
bar_colors = ["#36B37E" if lvl == 0 else "#DE350B" for lvl in levels]
ax_b.bar(levels, level_counts, color=bar_colors, edgecolor="black", linewidth=0.5)
for lvl, cnt in zip(levels, level_counts):
    ax_b.text(lvl, cnt, f"{cnt}", ha="center", va="bottom", fontsize=9)
ax_b.set_xlabel("Extra reconnects within the round")
ax_b.set_ylabel("Round count")
ax_b.set_title(f"Rounds by Reconnect Count  ({n_flickered}/{len(stops)} flickered)")
ax_b.set_xticks(levels)
ax_b.grid(axis="y", linestyle=":", alpha=0.5)

# ----- right: per-round reconnect count over time -----
colors = np.where(reconnect_counts > 0, "#DE350B", "#36B37E")
ax_s.scatter(flicker_rounds, reconnect_counts, s=14, alpha=0.7, c=colors,
             edgecolor="black", linewidth=0.3)
ax_s.scatter([], [], s=20, c="#36B37E", edgecolor="black", label="clean round (0 extra)")
ax_s.scatter([], [], s=20, c="#DE350B", edgecolor="black", label="flickered round (>=1 extra)")
ax_s.set_xlabel("Round")
ax_s.set_ylabel("Extra reconnects within the round")
ax_s.set_title("Per-Round Reconnect Count")
ax_s.set_yticks(levels)
ax_s.grid(linestyle=":", alpha=0.5)
ax_s.legend(loc="upper right", fontsize=9)

fig2.suptitle(
    f"Reconnect Flicker   (rounds where Pico disconnected/reconnected more than once)\n"
    f"({PICO_LOG.name} | {HOST_LOG.name})",
    fontsize=11, y=1.02
)
plt.tight_layout()
plt.savefig(OUT_FLICKER_PNG, dpi=150, bbox_inches="tight")
print(f"[disc2backup] saved -> {OUT_FLICKER_PNG}")
