#!/usr/bin/env bash
# ==============================================================================
# Smart Launcher for ESP32-S3 Hardware Controller Simulator
# - Preferred: Runs via Docker (zero host dependencies needed)
# - Fallback: Runs via Host Python (auto-creates venv if needed)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

echo "=========================================================="
echo " ESP32-S3 Hardware Controller Simulator Launcher"
echo "=========================================================="

# Check if Docker is available and preferred
if command -v docker &> /dev/null; then
    echo "[MODE: DOCKER] Starting supporting services (MQTT broker & Brain Core)..."
    cd "$ROOT_DIR/docker"
    docker compose up -d mqtt-broker brain-core 2>/dev/null || docker compose up -d mqtt-broker
    echo "[MODE: DOCKER] Running simulator inside Docker..."
    exec docker compose run --rm -v "$ROOT_DIR/brain:/app/brain" -v "$ROOT_DIR/schemas:/app/schemas" esp32-simulator
fi

# Fallback: Host Python
echo "[MODE: HOST PYTHON] Docker not active, checking host Python environment..."
cd "$ROOT_DIR"

if ! python3 -c "import paho.mqtt, pydantic" 2>/dev/null; then
    echo "Installing required packages (paho-mqtt, pydantic)..."
    if command -v apt-get &> /dev/null && [ "$EUID" -eq 0 ]; then
        apt-get install -y python3-paho-mqtt python3-pydantic
    else
        if [ ! -d ".venv" ]; then
            python3 -m venv .venv || sudo apt-get install -y python3-venv python3-pip
            python3 -m venv .venv
        fi
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install paho-mqtt pydantic
        exec .venv/bin/python run_simulator.py "$@"
    fi
fi

exec python3 run_simulator.py "$@"
