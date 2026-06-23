#!/usr/bin/env bash
# Regenerate every per-timeout figure from the logs in log/<timeout>/.
#
# Each timeout subfolder (log/1ms, log/2ms, ... log/1000ms) holds one
# pico_*.log and one host_*.log. We point LOG_DIR / RESULT_DIR at it (both are
# read by log_parser.py) so the plot scripts run unchanged and write their
# PNG/CSV output into result/<timeout>/.
#
# Force a headless backend so it works over SSH / without a display.
export MPLBACKEND=Agg

SCRIPTS=(
    plot_uros_init.py
    plot_disc_to_backup.py
    plot_disc_to_backup_flicker.py
)

failed=0
for d in log/*/; do
    name=$(basename "$d")
    # skip folders without a complete pico+host log pair
    if ! compgen -G "${d}pico_*.log" > /dev/null \
       || ! compgen -G "${d}host_*.log" > /dev/null; then
        echo "== skip ${name} (no pico/host log pair) =="
        continue
    fi
    echo "== ${name} =="
    for s in "${SCRIPTS[@]}"; do
        if ! LOG_DIR="$d" RESULT_DIR="result/${name}" python3 "$s"; then
            echo "!! ${name}/${s} failed" >&2
            failed=$((failed + 1))
        fi
    done
done

if [ "$failed" -ne 0 ]; then
    echo "Done with ${failed} failure(s)." >&2
    exit 1
fi
echo "Done."
