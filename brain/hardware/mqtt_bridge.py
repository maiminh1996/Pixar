"""
Hardware MQTT Bridge for Central Brain (NiPoGi AM02).
Manages bi-directional communication with ESP32-S3 over MQTT with built-in safety overrides.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from schemas.commands import DriveCommand, ServoCommand, EyeCommand
from schemas.safety import Heartbeat, EStopCommand
from schemas.telemetry import SensorTelemetry

logger = logging.getLogger(__name__)


class HardwareBridge:
    """
    Bridge communicating with ESP32-S3 over MQTT.
    Applies software safety limits (e.g., collision avoidance) before sending drive commands.
    """

    COLLISION_DISTANCE_CM = 20.0
    HEARTBEAT_INTERVAL_S = 0.20  # 200ms interval (5Hz) to keep ESP32 watchdog healthy
    MAX_LINEAR_SPEED_M_S = 1.0   # Max physical tank-track speed (1.0 m/s ~ 3.6 km/h)
    MAX_ANGULAR_SPEED_RAD_S = 2.0  # Max turning speed (2.0 rad/s)

    def __init__(
        self,
        broker_host: Optional[str] = None,
        broker_port: Optional[int] = None,
        client_id: str = "brain_hardware_bridge",
    ):
        import os
        self.broker_host = broker_host or os.environ.get("MQTT_BROKER_URL", "localhost")
        self.broker_port = int(broker_port or os.environ.get("MQTT_BROKER_PORT", 1883))
        self.client_id = client_id

        # Support both paho-mqtt v1 and v2 callback API versions
        if hasattr(mqtt, "CallbackAPIVersion"):
            self._client: mqtt.Client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id=client_id
            )
        else:
            self._client: mqtt.Client = mqtt.Client(client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self.is_connected: bool = False
        self.is_estop_active: bool = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._status_string: str = "OK"

        # Latest telemetry cache
        self.last_telemetry: Optional[SensorTelemetry] = None
        self.last_telemetry_time: float = 0.0

        # Optional callbacks
        self.telemetry_callbacks: list[Callable[[SensorTelemetry], None]] = []

    def register_telemetry_callback(self, callback: Callable[[SensorTelemetry], None]) -> None:
        self.telemetry_callbacks.append(callback)

    def set_status(self, status: str) -> None:
        self._status_string = status

    def start(self) -> None:
        """Connect to MQTT broker and start background loop."""
        logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
        try:
            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
        except Exception as exc:
            logger.error(f"Failed to connect to MQTT broker: {exc}")
            raise

    def stop(self) -> None:
        """Stop heartbeat, disconnect MQTT client."""
        logger.info("Stopping HardwareBridge...")
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._client.loop_stop()
        self._client.disconnect()
        self.is_connected = False

    def _on_connect(self, client: mqtt.Client, userdata: any, flags: any, rc: any, *args, **kwargs) -> None:
        reason_code = getattr(rc, "value", rc)
        if reason_code == 0:
            self.is_connected = True
            logger.info("HardwareBridge successfully connected to MQTT broker.")
            # Subscribe to telemetry from ESP32
            self._client.subscribe("robot/telemetry/sensors", qos=0)
            self._client.subscribe("robot/status/battery", qos=0)
        else:
            self.is_connected = False
            logger.error(f"HardwareBridge MQTT connection rejected with code: {reason_code}")

    def _on_disconnect(self, client: mqtt.Client, userdata: any, rc: any, *args, **kwargs) -> None:
        self.is_connected = False
        reason_code = getattr(rc, "value", rc)
        logger.warning(f"HardwareBridge disconnected from MQTT broker (rc={reason_code})")

    def update_telemetry(self, telemetry: SensorTelemetry) -> None:
        """Update cached telemetry and trigger registered callbacks."""
        self.last_telemetry = telemetry
        self.last_telemetry_time = time.time()
        for cb in self.telemetry_callbacks:
            try:
                cb(telemetry)
            except Exception as err:
                logger.error(f"Error in telemetry callback: {err}")

    def _on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if msg.topic == "robot/telemetry/sensors":
                telemetry = SensorTelemetry(**payload)
                self.update_telemetry(telemetry)
        except Exception as exc:
            logger.warning(f"Failed to parse incoming MQTT message on {msg.topic}: {exc}")

    # ==================== Commands Dispatch ====================

    def send_drive(self, linear_x: float, angular_z: float) -> DriveCommand:
        """
        Send tank-track differential drive command with collision safety override.
        Clamps velocity to safe physical limits and halts if ToF distance is below threshold (<20cm).
        """
        # Clamp velocity to safe physical limits
        linear_x = max(-self.MAX_LINEAR_SPEED_M_S, min(self.MAX_LINEAR_SPEED_M_S, linear_x))
        angular_z = max(-self.MAX_ANGULAR_SPEED_RAD_S, min(self.MAX_ANGULAR_SPEED_RAD_S, angular_z))

        if self.is_estop_active:
            logger.warning("E-Stop active! Drive command suppressed.")
            linear_x = 0.0
            angular_z = 0.0

        # Safety override via ToF sensors
        if self.last_telemetry:
            # Front obstacle check
            if linear_x > 0 and self.last_telemetry.tof_front_cm < self.COLLISION_DISTANCE_CM:
                logger.warning(
                    f"Collision Safety Override: Obstacle front at {self.last_telemetry.tof_front_cm:.1f}cm! Halting forward drive."
                )
                linear_x = 0.0

            # Rear obstacle check
            if linear_x < 0 and self.last_telemetry.tof_rear_cm < self.COLLISION_DISTANCE_CM:
                logger.warning(
                    f"Collision Safety Override: Obstacle rear at {self.last_telemetry.tof_rear_cm:.1f}cm! Halting reverse drive."
                )
                linear_x = 0.0

        cmd = DriveCommand(linear_x=round(linear_x, 3), angular_z=round(angular_z, 3))
        self._publish("robot/cmd/drive", cmd.model_dump())
        return cmd

    def send_servo(self, joint_id: int, angle: float, easing_duration_ms: int = 0) -> ServoCommand:
        """Send joint angle command (head pan/tilt, arms)."""
        cmd = ServoCommand(
            joint_id=joint_id,
            angle=float(angle),
            easing_duration_ms=easing_duration_ms,
        )
        self._publish("robot/cmd/servo", cmd.model_dump())
        return cmd

    def send_eyes(
        self,
        expression: str,
        brightness: int = 255,
        pupil_x: float = 0.0,
        pupil_y: float = 0.0,
    ) -> EyeCommand:
        """Send eye display animation and gaze command."""
        cmd = EyeCommand(
            expression=expression,
            brightness=brightness,
            pupil_x=pupil_x,
            pupil_y=pupil_y,
        )
        self._publish("robot/cmd/eyes", cmd.model_dump())
        return cmd

    def send_estop(self, trigger: bool = True, reason: str = "User or System E-Stop") -> EStopCommand:
        """Trigger or release emergency stop."""
        self.is_estop_active = trigger
        cmd = EStopCommand(trigger=trigger, reason=reason)
        self._publish("robot/safety/estop", cmd.model_dump())
        if trigger:
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            # Ensure immediate zeroing of drive
            self.send_drive(0.0, 0.0)
        else:
            logger.info("Emergency Stop released.")
        return cmd

    def _publish(self, topic: str, payload: dict) -> None:
        if not self.is_connected:
            logger.debug(f"MQTT not connected, skipping publish to {topic}")
            return
        json_str = json.dumps(payload)
        self._client.publish(topic, json_str, qos=0)

    # ==================== Watchdog Heartbeat ====================

    async def start_heartbeat_loop(self) -> None:
        """Async loop to continuously send heartbeats to keep ESP32 watchdog alive."""
        logger.info(f"Starting hardware heartbeat loop ({self.HEARTBEAT_INTERVAL_S * 1000}ms interval)")
        try:
            while True:
                hb = Heartbeat(
                    timestamp_ms=int(time.time() * 1000),
                    brain_status="EMERGENCY_STOP" if self.is_estop_active else self._status_string,
                )
                self._publish("robot/safety/heartbeat", hb.model_dump())
                await asyncio.sleep(self.HEARTBEAT_INTERVAL_S)
        except asyncio.CancelledError:
            logger.info("Heartbeat loop stopped.")
