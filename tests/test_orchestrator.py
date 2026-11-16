"""Unit tests for RobotOrchestrator core state machine."""

import pytest
import asyncio
from brain.orchestrator import RobotOrchestrator, RobotState
from schemas.telemetry import SensorTelemetry


@pytest.mark.asyncio
async def test_orchestrator_init_and_estop():
    orch = RobotOrchestrator()
    assert orch.state == RobotState.IDLE

    # Engage E-Stop
    orch.emergency_stop("Test emergency stop")
    assert orch.state == RobotState.EMERGENCY_STOP
    assert orch.hardware.is_estop_active is True

    # Motion command should be ignored during E-Stop
    orch.send_drive(0.5, 0.0)

    # Release E-Stop
    orch.release_emergency_stop()
    assert orch.state == RobotState.IDLE
    assert orch.hardware.is_estop_active is False


@pytest.mark.asyncio
async def test_orchestrator_low_battery_transition():
    orch = RobotOrchestrator()
    assert orch.state == RobotState.IDLE

    # Telemetry with low voltage (< 6.8V)
    telemetry = SensorTelemetry(
        battery_voltage=6.5,
        tof_front_cm=100.0,
        tof_rear_cm=100.0,
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
    )
    orch._on_sensor_telemetry(telemetry)
    assert orch.state == RobotState.SLEEPING


@pytest.mark.asyncio
async def test_orchestrator_collision_avoidance():
    orch = RobotOrchestrator()
    assert orch.state == RobotState.IDLE

    # Telemetry with obstacle (< 20cm)
    telemetry = SensorTelemetry(
        battery_voltage=7.4,
        tof_front_cm=15.0,
        tof_rear_cm=100.0,
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
    )
    orch._on_sensor_telemetry(telemetry)
    assert orch.emotion.state.current_emotion.value in ("surprised", "scared")
