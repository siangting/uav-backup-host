#!/usr/bin/env bash
#
# reset_rtt_tmux.sh
#
# Opens 4 panes: openocd / telnet / RTT log / reset helper.
# Uses pane IDs (not indices) to be immune to pane-base-index settings.
# Waits for the openocd telnet port to be ready before sending RTT commands,
# so rtt_log_capture.sh always starts with a live RTT server.

SESSION="rtt_debug"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENOCD_PORT=4444

tmux kill-session -t $SESSION 2>/dev/null || true
tmux new-session -d -s $SESSION -c "$SCRIPT_DIR"

# Grab the initial pane ID (will run openocd)
P_OPENOCD=$(tmux display-message -t $SESSION -p '#{pane_id}')

# =========================
# Pane: openocd
# =========================
tmux send-keys -t "$P_OPENOCD" \
    "openocd -f interface/cmsis-dap.cfg -f target/rp2350.cfg -c \"adapter speed 5000\"" C-m

# =========================
# Pane: telnet
# =========================
P_TELNET=$(tmux split-window -h -t "$P_OPENOCD" -P -F '#{pane_id}' -c "$SCRIPT_DIR")

# Wait for openocd telnet port — avoids dropping rtt commands on a slow start
echo "[rtt] waiting for openocd telnet on port ${OPENOCD_PORT}..."
for _i in $(seq 1 30); do
    if timeout 0.5 bash -c "</dev/tcp/localhost/${OPENOCD_PORT}" 2>/dev/null; then
        echo "[rtt] openocd ready"
        break
    fi
    sleep 0.5
done

tmux send-keys -t "$P_TELNET" "telnet localhost ${OPENOCD_PORT}" C-m
sleep 0.5   # wait for telnet handshake

tmux send-keys -t "$P_TELNET" "rtt setup 0x20000000 0x10000 \"SEGGER RTT\"" C-m
sleep 0.1
tmux send-keys -t "$P_TELNET" "rtt server start 19021 0" C-m
sleep 0.1
tmux send-keys -t "$P_TELNET" "rtt start" C-m

# =========================
# Pane: RTT log (auto-reconnect)
# =========================
P_LOG=$(tmux split-window -v -t "$P_TELNET" -P -F '#{pane_id}' -c "$SCRIPT_DIR")
sleep 0.8   # give openocd time to open the RTT server port
tmux send-keys -t "$P_LOG" "./rtt_log_capture.sh" C-m

# =========================
# Pane: reset helper
# =========================
P_HELPER=$(tmux split-window -v -t "$P_OPENOCD" -P -F '#{pane_id}' -c "$SCRIPT_DIR")

tmux send-keys -t "$P_HELPER" \
"clear; \
echo '=================================='; \
echo ' Reset Pico helper'; \
echo '=================================='; \
echo ''; \
echo '  ./reset_pico.sh             # 1 次 reset'; \
echo '  ./reset_pico.sh 100         # 100 次，間隔 8s'; \
echo '  ./reset_pico.sh 100 10      # 100 次，間隔 10s'; \
echo ''; \
echo '右下 RTT log pane 會持續顯示 Pico log。'; \
echo '每次 boot 各自寫進 log/pico_<TS>.log。'" C-m

tmux select-layout -t $SESSION tiled
tmux attach -t $SESSION
