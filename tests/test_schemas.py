"""Unit tests for Pydantic MQTT schemas."""

import pytest
from schemas.commands import DriveCommand, ServoCommand, EyeCommand
from schemas.safety import Heartbeat, EStopCommand
from schemas.telemetry import SensorTelemetry


def test_drive_command():
    cmd = DriveCommand(linear_x=0.5, angular_z=-0.2)
    assert cmd.linear_x == 0.5
    assert cmd.angular_z == -0.2
    dump = cmd.model_dump()
    assert dump["linear_x"] == 0.5


def test_servo_command():
    cmd = ServoCommand(joint_id=0, angle=90.0, easing_duration_ms=300)
    assert cmd.joint_id == 0
    assert cmd.angle == 90.0

    with pytest.raises(ValueError):
        ServoCommand(joint_id=0, angle=200.0)  # > 180 degrees


def test_eye_command():
    cmd = EyeCommand(expression="happy", brightness=200, pupil_x=0.5, pupil_y=-0.2)
    assert cmd.expression == "happy"
    assert cmd.brightness == 200
    assert cmd.pupil_x == 0.5


def test_safety_and_telemetry():
    hb = Heartbeat(timestamp_ms=123456789, brain_status="OK")
    assert hb.brain_status == "OK"

    estop = EStopCommand(trigger=True, reason="Obstacle")
    assert estop.trigger is True

    telemetry = SensorTelemetry(
        battery_voltage=12.2,
        tof_front_cm=45.0,
        tof_rear_cm=110.0,
        imu_roll=0.1,
        imu_pitch=-0.2,
        imu_yaw=1.5,
    )
    assert telemetry.battery_voltage == 12.2
    assert telemetry.tof_front_cm == 45.0
