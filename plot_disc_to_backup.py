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
from matplotlib.ticker import MultipleLocator
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

# ---- left: histogram (broken x-axis) + right: per-round time series ----
fig  = plt.figure(figsize=(18, 5), layout="constrained")
gs   = fig.add_gridspec(1, 2, width_ratios=[1, 1.4])
ax_t = fig.add_subplot(gs[1])

HIST_COLOR = "#6554C0"
bins      = max(10, min(60, int(np.sqrt(gap_ms.size) * 2)))
bin_edges = np.histogram_bin_edges(gap_ms, bins=bins)
bin_w     = float(bin_edges[1] - bin_edges[0])
mean_val  = float(gap_ms.mean())
p95_val   = float(np.percentile(gap_ms, 95))

# A few far outliers (~100 ms) stretch the axis while the bulk sits < 20 ms.
# Find the widest empty gap; if it is large enough, split the histogram into a
# main panel (bulk) and an outlier panel with a broken x-axis so the empty
# middle is compressed instead of dominating the figure.
sorted_v  = np.sort(gap_ms)
diffs     = np.diff(sorted_v)
i_gap     = int(np.argmax(diffs)) if sorted_v.size > 1 else 0
data_rng  = float(sorted_v[-1] - sorted_v[0])
use_break = (sorted_v.size > 2 and data_rng > 0
             and diffs[i_gap] > 0.25 * data_rng
             and sorted_v[i_gap + 1] - sorted_v[i_gap] > 10)

if use_break:
    break_lo, break_hi = float(sorted_v[i_gap]), float(sorted_v[i_gap + 1])
    gs_h    = gs[0].subgridspec(1, 2, width_ratios=[2.5, 1], wspace=0.05)
    ax_main = fig.add_subplot(gs_h[0])
    ax_out  = fig.add_subplot(gs_h[1], sharey=ax_main)

    for ax in (ax_main, ax_out):
        ax.hist(gap_ms, bins=bin_edges, color=HIST_COLOR,
                edgecolor="black", linewidth=0.5)
        ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax_main.set_xlim(sorted_v[0] - bin_w, break_lo + bin_w)   # bulk
    ax_out.set_xlim(break_hi - bin_w, sorted_v[-1] + bin_w)   # outliers
    # main panel ticks every 5 ms; the narrow outlier panel every 10 ms
    ax_main.xaxis.set_major_locator(MultipleLocator(5))
    ax_out.xaxis.set_major_locator(MultipleLocator(10))

    # hide the inner spines and add the diagonal break marks
    ax_main.spines.right.set_visible(False)
    ax_out.spines.left.set_visible(False)
    ax_out.tick_params(axis="y", which="both", left=False, labelleft=False)
    d   = .5
    dkw = dict(marker=[(-1, -d), (1, d)], markersize=12, linestyle="none",
               color="k", mec="k", mew=1, clip_on=False)
    ax_main.plot([1, 1], [0, 1], transform=ax_main.transAxes, **dkw)
    ax_out.plot([0, 0], [0, 1], transform=ax_out.transAxes, **dkw)

    # draw mean / p95 on whichever panel the value falls in
    def _vline(value, **kw):
        ax = ax_out if value >= break_hi - bin_w else ax_main
        return ax.axvline(value, **kw)
    mean_line = _vline(mean_val, color="black", linestyle="--", linewidth=1.2,
                       label=f"mean = {mean_val:.2f} ms")
    p95_line  = _vline(p95_val, color="orange", linestyle=":", linewidth=1.2,
                       label=f"p95 = {p95_val:.2f} ms")

    ax_main.set_ylabel("count")
    ax_main.set_xlabel("Disconnect → backup activation (ms)")
    ax_main.set_title("Distribution")
    # legend sits outside, to the right of the outlier panel
    ax_out.legend(handles=[mean_line, p95_line], loc="upper left",
                  bbox_to_anchor=(1.02, 1.0), fontsize=9)
    ax_anno = ax_out
else:
    ax_h = fig.add_subplot(gs[0])
    ax_h.hist(gap_ms, bins=bin_edges, color=HIST_COLOR,
              edgecolor="black", linewidth=0.5)
    ax_h.axvline(mean_val, color="black", linestyle="--", linewidth=1.2,
                 label=f"mean = {mean_val:.2f} ms")
    ax_h.axvline(p95_val, color="orange", linestyle=":", linewidth=1.2,
                 label=f"p95 = {p95_val:.2f} ms")
    ax_h.set_xlabel("Disconnect → backup activation (ms)")
    ax_h.set_ylabel("count")
    ax_h.set_title("Distribution")
    ax_h.grid(axis="y", linestyle=":", alpha=0.5)
    ax_h.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9)
    ax_anno = ax_h

# stats box sits outside, to the right of the histogram block
ax_anno.text(1.02, 0.78, stat_block(gap_ms), transform=ax_anno.transAxes,
             va="top", ha="left", family="monospace", fontsize=9,
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
ax_t.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9)

fig.suptitle(
    "Disconnect → Backup Activation   "
    "pico 'AGENT_DISCONNECTED' → pico 'Backup activation completed'\n"
    f"({PICO_LOG.name})",
    fontsize=11,
)
fig.get_layout_engine().set(w_pad=0.08, wspace=0.18)
for out in (OUT_PNG, OUT_PNG.with_suffix(".pdf"), OUT_PNG.with_suffix(".svg")):
    plt.savefig(out, dpi=150)
    print(f"[disc2backup] saved -> {out}")
