#!/usr/bin/env bash

set -e

# =========================
# 🔧 EXPERIMENT PARAMETERS
# =========================
RUN_DURATION=20   # seconds（agent 運行時間）
REST_DURATION=10   # seconds（兩輪間隔）
LOOP_COUNT=1000

# =========================
# LOG 設定
# =========================
LOG_DIR="log"
mkdir -p $LOG_DIR

RUN_TS=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/host_${RUN_TS}.log"

AGENT_NAME="uros_agent"

# =========================
# TIME FUNCTION
# =========================
ts() {
    date +"[%Y-%m-%d %H:%M:%S.%3N]"
}

log() {
    echo "$(ts) | $1" | tee -a $LOG_FILE
}

# =========================
# MAIN LOOP
# =========================
for ((i=1; i<=LOOP_COUNT; i++)); do
    log "===== ROUND $i START ====="

    docker rm -f $AGENT_NAME 2>/dev/null || true

    log "Starting micro-ROS agent"
    docker run -d --name $AGENT_NAME \
        --net=host --privileged \
        -v /dev:/dev \
        microros/micro-ros-agent:jazzy \
        serial --dev /dev/ttyACM0 -b 115200 -v6 \
        > /dev/null 2>&1

    log "Agent container started"

    log "Sourcing ROS2 environment"
    source /opt/ros/humble/setup.bash

    log "Starting heartbeat publisher"
    ros2 topic pub /heartbeat std_msgs/msg/Header \
        "{stamp: {sec: 0, nanosec: 0}, frame_id: 'test'}" -r 10 \
        >> $LOG_FILE 2>&1 &

    PUB_PID=$!
    log "Publisher PID: $PUB_PID"

    log "Running for ${RUN_DURATION} seconds..."
    sleep $RUN_DURATION

    log "Stopping processes"

    docker stop $AGENT_NAME >> $LOG_FILE 2>&1 || true
    docker rm $AGENT_NAME >> $LOG_FILE 2>&1 || true

    kill $PUB_PID 2>/dev/null || true
    wait $PUB_PID 2>/dev/null || true

    log "Processes stopped"

    log "Sleep ${REST_DURATION} seconds before restart"
    sleep $REST_DURATION

    log "===== ROUND $i END ====="
done

log "✅ DONE"

echo "📄 Log saved to: $LOG_FILE"