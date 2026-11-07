"""Unit tests for HardwareBridge and ESP32Simulator."""

import pytest
import time
from brain.hardware.mqtt_bridge import HardwareBridge
from brain.hardware.simulator import ESP32Simulator
from schemas.telemetry import SensorTelemetry


def test_collision_avoidance_clamp():
    bridge = HardwareBridge()

    # Case 1: No telemetry, drive passes unmodified
    cmd = bridge.send_drive(linear_x=0.8, angular_z=0.1)
    assert cmd.linear_x == 0.8

    # Case 2: Front obstacle at 12cm (< 20cm threshold), forward motion clamped to 0
    bridge.last_telemetry = SensorTelemetry(
        battery_voltage=12.0,
        tof_front_cm=12.0,
        tof_rear_cm=80.0,
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
    )
    cmd = bridge.send_drive(linear_x=0.5, angular_z=0.2)
    assert cmd.linear_x == 0.0  # Clamped!
    assert cmd.angular_z == 0.2  # Rotation allowed to steer away

    # Reverse should still be allowed if rear is clear
    cmd_reverse = bridge.send_drive(linear_x=-0.5, angular_z=0.0)
    assert cmd_reverse.linear_x == -0.5

    # Case 3: Rear obstacle at 10cm, reverse motion clamped
    bridge.last_telemetry.tof_rear_cm = 10.0
    cmd_reverse_clamped = bridge.send_drive(linear_x=-0.5, angular_z=0.0)
    assert cmd_reverse_clamped.linear_x == 0.0


def test_hardware_estop():
    bridge = HardwareBridge()
    bridge.send_estop(trigger=True, reason="Unit test E-Stop")
    assert bridge.is_estop_active is True

    # When E-Stop is active, drive is forced to 0
    cmd = bridge.send_drive(0.8, 0.5)
    assert cmd.linear_x == 0.0
    assert cmd.angular_z == 0.0

    bridge.send_estop(trigger=False)
    assert bridge.is_estop_active is False


def test_esp32_simulator_watchdog():
    sim = ESP32Simulator()
    sim.linear_x = 0.5
    sim.angular_z = 0.2
    sim.last_heartbeat_time = time.time() - 1.2  # 1200ms ago (> 1000ms timeout)

    sim.update_step(dt=0.1)
    assert sim.watchdog_tripped is True
    assert sim.linear_x == 0.0
    assert sim.angular_z == 0.0
