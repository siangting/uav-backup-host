# /etc/systemd/system/micro_ros_agent.service
[Unit]
Description=micro-ROS Agent (Serial)
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker run --rm --net=host --privileged \
  -v /dev:/dev \
  microros/micro-ros-agent:jazzy \
  serial --dev /dev/ttyACM0 -b 115200 -v6
Restart=always
RestartSec=2
User=siangting

[Install]
WantedBy=multi-user.target