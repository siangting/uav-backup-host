#!/usr/bin/env bash
#
# reset_pico.sh
#
# 透過 openocd 的 telnet port (4444) 直接送指令，不依賴 tmux pane。
# 這樣不管 tmux 怎麼排版、pane index 是 0-based 還是 1-based 都不會出錯。
#
# 用法:
#   ./reset_pico.sh             # 1 次
#   ./reset_pico.sh 100         # 100 次，每次間隔 8 秒
#   ./reset_pico.sh 100 10      # 100 次，每次間隔 10 秒

OPENOCD_HOST="${OPENOCD_HOST:-localhost}"
OPENOCD_PORT="${OPENOCD_PORT:-4444}"

# Sanity check: 確認 openocd telnet 可連
if ! timeout 1 bash -c "</dev/tcp/${OPENOCD_HOST}/${OPENOCD_PORT}" 2>/dev/null; then
    echo "Error: cannot reach openocd telnet at ${OPENOCD_HOST}:${OPENOCD_PORT}"
    echo "Make sure ./rtt_tmux.sh is running."
    exit 1
fi

COUNT="${1:-1}"
INTERVAL="${2:-8}"   # 預設 8 秒 = 5.5s boot + ~2.5s buffer

# 對 openocd 送 reset 序列：reset → 等 SEGGER_RTT_Init → rtt stop/start 重新綁
reset_once() {
    {
        echo "reset run"
        sleep 0.5        # let the hardware reset propagate before touching RTT
        echo "rtt stop"  # disconnect existing RTT clients (rtt_log_capture nc gets EOF)
        sleep 0.1
        echo "rtt start" # re-scan for control block; openocd polls until Pico's
        sleep 0.3        # SEGGER_RTT_Init() writes the magic string (~5.5 s after reset)
    } | timeout 3 nc "${OPENOCD_HOST}" "${OPENOCD_PORT}" > /dev/null 2>&1
}

echo "[reset_pico] count=${COUNT}, interval=${INTERVAL}s"
echo "[reset_pico] 注意：右下 RTT log pane 才是會看到 [T_BOOT] 的地方"
echo

for ((i=1; i<=COUNT; i++)); do
    echo "[$(date +%H:%M:%S)] reset $i/$COUNT"
    reset_once
    if (( i < COUNT )); then
        sleep "$INTERVAL"
    fi
done

echo
echo "[reset_pico] done. issued ${COUNT} reset(s)."
echo "[reset_pico] grep [T_BOOT] log/pico_*.log | wc -l    # 應該等於 reset 次數 + 開機那 1 次"