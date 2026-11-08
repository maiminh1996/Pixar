#!/bin/bash
set -e
echo "=========================================================="
echo " RUNNING PYTEST SUITE IN ISOLATED DOCKER ENVIRONMENT"
echo "=========================================================="
docker run --rm -v "$(pwd):/app" -w /app --network host python:3.12-slim bash -c "
    echo '[1/3] Installing system audio/vision runtime libraries...' &&
    apt-get update -yqq && apt-get install -y --no-install-recommends libasound2 libportaudio2 libgomp1 libglib2.0-0 &&
    echo '[2/3] Installing Python dependencies from pyproject.toml...' &&
    pip install -q --upgrade pip &&
    pip install -q -e . &&
    pip install -q pytest pytest-asyncio httpx requests &&
    echo '[3/3] Running automated tests...' &&
    PYTHONPATH=. pytest tests/
"
