#!/usr/bin/env python3
"""
Live Terminal Dashboard for Pixar AI Companion Robot.
Connects to the FastAPI Brain-Core to display real-time telemetry, 
emotion state, and system resources in a beautiful, non-scrolling UI.
"""

import time
import urllib.request
import json
import sys
import os

API_BASE = "http://localhost:8000"

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(x, y):
    sys.stdout.write(f"\033[{y};{x}H")

def color(text, *codes):
    code_str = ";".join(str(c) for c in codes)
    return f"\033[{code_str}m{text}\033[0m"

# ANSI Colors
CYAN = "36"
GREEN = "32"
YELLOW = "33"
RED = "31"
MAGENTA = "35"
WHITE = "37"
BOLD = "1"

def fetch_json(endpoint):
    try:
        req = urllib.request.Request(f"{API_BASE}{endpoint}")
        with urllib.request.urlopen(req, timeout=1.0) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def draw_bar(percentage, length=20, bar_color=GREEN):
    filled = int((percentage / 100.0) * length)
    empty = length - filled
    bar = color("█" * filled, bar_color) + color("░" * empty, WHITE)
    return f"[{bar}] {percentage:>5.1f}%"

def render_dashboard():
    state = fetch_json("/state")
    telemetry = fetch_json("/telemetry")
    system = fetch_json("/system")
    emotion = fetch_json("/emotion")

    clear_screen()
    move_cursor(1, 1)

    print(color("╔══════════════════════════════════════════════════════════════════════════════╗", CYAN))
    print(color("║               🤖 PIXAR AI COMPANION ROBOT - LIVE DASHBOARD                 ║", CYAN, BOLD))
    print(color("╠══════════════════════════════════════════════════════════════════════════════╣", CYAN))

    if not state or not system:
        print(color("║  [!] Cannot connect to Brain API at localhost:8000                           ║", RED))
        print(color("║      Please ensure 'docker compose up' is running.                           ║", RED))
        print(color("╚══════════════════════════════════════════════════════════════════════════════╝", CYAN))
        return

    # --- Header: State & Safety ---
    status_icon = "[OK]" if not state.get("is_estop") else "[ESTOP]"
    estop_text = color("ACTIVE", RED) if state.get("is_estop") else color("RELEASED", GREEN)
    mqtt_conn = "CONNECTED" if system.get("mqtt_connected") else color("DISCONNECTED", RED)
    
    print(f"║ {status_icon} BRAIN STATE: {color(state.get('state', 'UNKNOWN'), BOLD):<15} │  E-STOP: {estop_text:<16}                 ║")
    print(f"║ MQTT BROKER  : {mqtt_conn:<15} │  UPTIME : {system.get('uptime_seconds', 0):<16} s          ║")
    print(color("╠══════════════════════════════════════════════════════════════════════════════╣", CYAN))

    # --- System Resources ---
    cpu_usage = system.get("cpu_usage_percent", 0)
    ram = system.get("ram_usage", {})
    ram_usage = ram.get("percent", 0)
    
    print(f"║ NI POGI AM02 SYSTEM RESOURCES                                                ║")
    print(f"║   CPU Usage    : {draw_bar(cpu_usage, 25, CYAN)}                               ║")
    print(f"║   RAM Usage    : {draw_bar(ram_usage, 25, MAGENTA)}                               ║")
    print(f"║   LLM Backend  : {system.get('llm_api_base')}                              ║")
    print(color("╠══════════════════════════════════════════════════════════════════════════════╣", CYAN))

    # --- Emotion & Eyes ---
    em = emotion.get("current_emotion", "unknown") if emotion else "unknown"
    val = emotion.get("valence", 0) if emotion else 0
    arousal = emotion.get("arousal", 0) if emotion else 0
    
    eye_art = "( -_- )"
    if em in ("happy", "playful"): eye_art = "( ^_^ )"
    elif em == "curious": eye_art = "( o_O )"
    elif em == "surprised": eye_art = "( O_O )"
    elif em == "sleepy": eye_art = "( u_u )"
    elif em == "scared": eye_art = "( >_< )"
    elif em == "angry": eye_art = "( `o´ )"
    elif em == "sad": eye_art = "( ;_; )"
    elif em == "comfortable": eye_art = "( ˘‿˘ )"

    print(f"║ EMOTION ENGINE (PAD Model)                                                   ║")
    print(f"║   Emotion      : {color(em.upper(), YELLOW, BOLD):<12}      {color(eye_art, CYAN, BOLD)}                                   ║")
    print(f"║   Valence      : {val:>+5.2f}  |  Arousal       : {arousal:>+5.2f}                         ║")
    print(color("╠══════════════════════════════════════════════════════════════════════════════╣", CYAN))

    # --- Hardware Telemetry ---
    print(f"║ HARDWARE TELEMETRY (ESP32-S3)                                                ║")
    if telemetry and telemetry.get("status") != "NO_DATA":
        batt = telemetry.get("battery_voltage", 0.0)
        batt_pct = max(0, min(100, (batt - 10.5) / (12.6 - 10.5) * 100))
        batt_color = GREEN if batt > 11.1 else RED
        
        front_dist = telemetry.get("tof_front_cm", 0.0)
        rear_dist = telemetry.get("tof_rear_cm", 0.0)
        front_warn = color("[CLOSE]", RED) if front_dist < 20 else "Safe"
        rear_warn = color("[CLOSE]", RED) if rear_dist < 20 else "Safe"

        print(f"║   Battery      : {batt:>5.2f}V {draw_bar(batt_pct, 15, batt_color)}                          ║")
        print(f"║   ToF Front    : {front_dist:>6.1f} cm ({front_warn:<15})                               ║")
        print(f"║   ToF Rear     : {rear_dist:>6.1f} cm ({rear_warn:<15})                               ║")
        print(f"║   IMU Angles   : Roll: {telemetry.get('imu_roll',0):>+5.1f}° | Pitch: {telemetry.get('imu_pitch',0):>+5.1f}° | Yaw: {telemetry.get('imu_yaw',0):>+5.1f}°          ║")
    else:
        print(color("║   [!] Waiting for MQTT telemetry from ESP32 Controller...                   ║", YELLOW))

    # --- Live Conversation ---
    dialogue_data = fetch_json("/audio/conversation_logs")
    last_ex = dialogue_data.get("last_exchange", {}) if dialogue_data else {}
    user_txt = last_ex.get("user", "")
    robot_txt = last_ex.get("robot", "")
    robot_em = last_ex.get("emotion", "neutral")

    print(color("╠══════════════════════════════════════════════════════════════════════════════╣", CYAN))
    print(f"║ LATEST SPOKEN DIALOGUE TURN                                                  ║")
    if user_txt:
        u_short = user_txt[:60]
        r_short = robot_txt[:55]
        print(f"║   USER     : {u_short:<63} ║")
        print(f"║   🤖 ROBOT : [{robot_em}] {r_short:<51} ║")
    else:
        print(f"║   (Waiting for spoken turn or message via /dialogue...)                       ║")
    
    print(color("╚══════════════════════════════════════════════════════════════════════════════╝", CYAN))
    print("\nPress Ctrl+C to exit.")


def main():
    try:
        # Hide cursor
        sys.stdout.write("\033[?25l")
        while True:
            render_dashboard()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        # Show cursor
        sys.stdout.write("\033[?25h")
        clear_screen()

if __name__ == "__main__":
    main()
