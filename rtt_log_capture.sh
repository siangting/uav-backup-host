#!/usr/bin/env bash
#
# rtt_log_capture.sh
#
# Connects to the openocd RTT server (default localhost:19021).
# Each boot session (new connection with data) gets its own
# log/pico_<TS>.log file.  Auto-reconnects silently when nc drops.

LOG_HOST="${RTT_HOST:-localhost}"
LOG_PORT="${RTT_PORT:-19021}"
LOG_DIR="${LOG_DIR:-log}"

mkdir -p "$LOG_DIR"

echo "[rtt_log] log dir  : $LOG_DIR"
echo "[rtt_log] RTT server: ${LOG_HOST}:${LOG_PORT}"
echo "[rtt_log] waiting for first connection..."
echo

trap 'echo; echo "[rtt_log] stopped"; exit 0' INT TERM

BOOT=0

while true; do
    LINES=0

    # Process substitution keeps the while loop in the current shell
    # so BOOT/LINES/LOG_FILE are writable without a subshell.
    while IFS= read -r line || [[ -n "$line" ]]; do
        if (( LINES == 0 )); then
            BOOT=$((BOOT + 1))
            LOG_FILE="$LOG_DIR/pico_$(date +%Y%m%d_%H%M%S).log"
            # Open fd 3 → log file (stays open for the whole session)
            exec 3>>"$LOG_FILE"
            sep="$(printf '[%s] === BOOT #%d ===' "$(date +'%Y-%m-%d %H:%M:%S.%3N')" "$BOOT")"
            printf '\n%s\n' "$sep"
            printf '%s\n' "$sep" >&3
        fi
        ts="$(printf '[%s] %s' "$(date +'%Y-%m-%d %H:%M:%S.%3N')" "$line")"
        printf '%s\n' "$ts"
        printf '%s\n' "$ts" >&3
        LINES=$((LINES + 1))
    done < <(nc "$LOG_HOST" "$LOG_PORT" 2>/dev/null)

    if (( LINES > 0 )); then
        done_msg="$(printf '[%s] [rtt_log] boot #%d ended (%d lines) → %s' \
            "$(date +'%Y-%m-%d %H:%M:%S.%3N')" "$BOOT" "$LINES" "$LOG_FILE")"
        printf '%s\n' "$done_msg"
        printf '%s\n' "$done_msg" >&3
        exec 3>&-   # close log file
        sleep 0.2
    else
        # nc failed to connect or connected with no data — retry silently
        sleep 0.3
    fi
done
