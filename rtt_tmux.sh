#!/usr/bin/env bash

SESSION="rtt_debug"

# 如果已存在就先砍掉
tmux kill-session -t $SESSION 2>/dev/null || true

# 建立 session
tmux new-session -d -s $SESSION

# =========================
# Pane 0: openocd
# =========================
tmux send-keys -t $SESSION:0.0 \
"openocd -f interface/cmsis-dap.cfg -f target/rp2350.cfg -c \"adapter speed 5000\"" C-m

# =========================
# Pane 1: telnet (RTT setup)
# =========================
tmux split-window -h -t $SESSION

# 等 openocd 起來
sleep 2

tmux send-keys -t $SESSION:0.1 "telnet localhost 4444" C-m
sleep 1

tmux send-keys -t $SESSION:0.1 "rtt setup 0x20000000 0x10000 \"SEGGER RTT\"" C-m
tmux send-keys -t $SESSION:0.1 "rtt server start 19021 0" C-m
tmux send-keys -t $SESSION:0.1 "rtt start" C-m

# =========================
# Pane 2: RTT log
# =========================
tmux split-window -v -t $SESSION

tmux send-keys -t $SESSION:0.2 \
"LOG_DIR=log; mkdir -p \$LOG_DIR; TS=\$(date +%Y%m%d_%H%M%S); \
nc localhost 19021 | while IFS= read -r line; do \
echo \"[\$(date +%Y-%m-%d\ %H:%M:%S.%3N)] \$line\"; \
done | tee \$LOG_DIR/pico_\${TS}.log" C-m

# 排版
tmux select-layout -t $SESSION tiled

# attach
tmux attach -t $SESSION