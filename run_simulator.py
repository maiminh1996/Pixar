#!/usr/bin/env python3
"""
Convenience launcher for the ESP32-S3 Hardware Controller Simulator.
Can be run from anywhere:
    python3 run_simulator.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from brain.hardware.simulator import main

if __name__ == "__main__":
    main()
