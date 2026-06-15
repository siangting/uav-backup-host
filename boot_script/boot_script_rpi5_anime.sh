#!/bin/bash
while true
do
# Frame 1: RPi5 prepares
clear
echo ""
echo "                    === NORMAL MODE ==="
echo ""
echo ""
echo "     RPi5                                      Pico"
echo "    ╔══════╗                                  ╔══════╗"
echo "    ║ ◉  ◉ ║                                  ║ ◕  ◕ ║"
echo "    ║  ▽   ║                                  ║  ◡   ║"
echo "    ╚══════╝                                  ╚══════╝"
echo ""
echo "    [preparing msg...]"
sleep 0.4

# Frame 2: Message near RPi5
clear
echo ""
echo "                    === NORMAL MODE ==="
echo ""
echo ""
echo "     RPi5                                      Pico"
echo "    ╔══════╗                                  ╔══════╗"
echo "    ║ ◉  ◉ ║ ▶ heartbeat♥                     ║ ◕  ◕ ║"
echo "    ║  ▿   ║                                  ║  ◡   ║"
echo "    ╚══════╝                                  ╚══════╝"
echo ""
echo "    [sending...]"
sleep 0.4

# Frame 3: Message in middle
clear
echo ""
echo "                    === NORMAL MODE ==="
echo ""
echo ""
echo "     RPi5                                      Pico"
echo "    ╔══════╗                                  ╔══════╗"
echo "    ║ ◉  ◉ ║            ▶ heartbeat♥          ║ ◕  ◕ ║"
echo "    ║  ◡   ║                                  ║  ◡   ║"
echo "    ╚══════╝                                  ╚══════╝"
echo ""
echo "    [sending...]"
sleep 0.4

# Frame 4: Message arriving at Pico
clear
echo ""
echo "                    === NORMAL MODE ==="
echo ""
echo ""
echo "     RPi5                                      Pico"
echo "    ╔══════╗                                  ╔══════╗"
echo "    ║ ◉  ◉ ║                     ▶ heartbeat♥ ║ ◕  ◕ ║"
echo "    ║  ◡   ║                                  ║  ▽   ║"
echo "    ╚══════╝                                  ╚══════╝"
echo ""
echo "    [sending...]"
sleep 0.4

# Frame 5: Pico received message — happy!
clear
echo ""
echo "                    === NORMAL MODE ==="
echo ""
echo ""
echo "     RPi5                                      Pico"
echo "    ╔══════╗                                  ╔══════╗"
echo "    ║ ◉  ◉ ║                                  ║ ^  ^ ║"
echo "    ║  ◡   ║                                  ║  ◡   ║ ♥"
echo "    ╚══════╝                                  ╚══════╝"
echo ""
echo "    [Pico received! ♥]"
sleep 0.6
done