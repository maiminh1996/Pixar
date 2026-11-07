"""
ESP32-S3 Hardware Controller Simulator.
Enables 100% full-stack development and testing on the NiPoGi AM02 in Paris
without needing physical hardware. Simulates motor PWM, servos, eye display,
battery discharge, ToF obstacle detection, and the 500ms safety watchdog.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Ensure project root is in sys.path even if executed from another working directory
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt

from schemas.telemetry import SensorTelemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ESP32_Simulator")


class ESP32Simulator:
    """
    Simulates the ESP32-S3 firmware runtime over MQTT.
    """

    WATCHDOG_TIMEOUT_S = 1.000  # 1000ms hardware watchdog timeout (5x heartbeat margin)

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port

        if hasattr(mqtt, "CallbackAPIVersion"):
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id="esp32_s3_hardware_simulator"
            )
        else:
            self._client = mqtt.Client(client_id="esp32_s3_hardware_simulator")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        self.running: bool = False
        self.is_estop: bool = False
        self.watchdog_tripped: bool = False
        self.last_heartbeat_time: float = time.time()

        # Simulated state
        self.linear_x: float = 0.0
        self.angular_z: float = 0.0
        self.servo_angles: Dict[int, float] = {0: 90.0, 1: 90.0, 2: 90.0, 3: 90.0}
        self.eye_expression: str = "neutral"
        self.eye_brightness: int = 255
        self.eye_pupil_x: float = 0.0
        self.eye_pupil_y: float = 0.0

        # Simulated sensors
        self.battery_voltage: float = 12.4
        self.tof_front_cm: float = 120.0
        self.tof_rear_cm: float = 150.0
        self.imu_roll: float = 0.0
        self.imu_pitch: float = 0.0
        self.imu_yaw: float = 0.0

        # Telemetry publish interval
        self.telemetry_interval_s: float = 0.1  # 10Hz

    def start(self) -> None:
        """Connect to broker and start simulated microcontroller loop."""
        logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
        self._client.connect(self.broker_host, self.broker_port, keepalive=60)
        self._client.loop_start()
        self.running = True
        logger.info("ESP32-S3 Simulator initialized and listening for commands.")

    def stop(self) -> None:
        """Stop simulator."""
        self.running = False
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("ESP32-S3 Simulator stopped.")

    def _on_connect(self, client: mqtt.Client, userdata: any, flags: any, rc: any, *args, **kwargs) -> None:
        reason_code = getattr(rc, "value", rc)
        if reason_code == 0:
            logger.info("[ESP32] Connected to MQTT broker. Subscribing to control topics...")
            self._client.subscribe("robot/cmd/drive", qos=0)
            self._client.subscribe("robot/cmd/servo", qos=0)
            self._client.subscribe("robot/cmd/eyes", qos=0)
            self._client.subscribe("robot/safety/heartbeat", qos=0)
            self._client.subscribe("robot/safety/estop", qos=0)
        else:
            logger.error(f"[ESP32] Connection failed with rc={reason_code}")

    def _on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic

            if topic == "robot/safety/heartbeat":
                self.last_heartbeat_time = time.time()
                if self.watchdog_tripped:
                    logger.info("[ESP32 WATCHDOG] Heartbeat recovered! Clearing watchdog fault.")
                    self.watchdog_tripped = False

            elif topic == "robot/safety/estop":
                trigger = payload.get("trigger", False)
                reason = payload.get("reason", "")
                self.is_estop = trigger
                if trigger:
                    self._emergency_cut_motors(f"E-Stop message: {reason}")
                else:
                    logger.info("[ESP32] E-Stop released.")

            elif topic == "robot/cmd/drive":
                if self.is_estop or self.watchdog_tripped:
                    logger.warning("[ESP32] Drive command ignored due to active E-Stop or Watchdog trip!")
                    return
                self.linear_x = float(payload.get("linear_x", 0.0))
                self.angular_z = float(payload.get("angular_z", 0.0))
                logger.info(f"[ESP32 MOTORS] Linear: {self.linear_x:+.2f} m/s | Angular: {self.angular_z:+.2f} rad/s")

            elif topic == "robot/cmd/servo":
                joint_id = int(payload.get("joint_id", 0))
                angle = float(payload.get("angle", 90.0))
                easing = int(payload.get("easing_duration_ms", 0))
                self.servo_angles[joint_id] = angle
                joint_names = {0: "Head Pan", 1: "Head Tilt", 2: "Left Arm", 3: "Right Arm"}
                name = joint_names.get(joint_id, f"Joint {joint_id}")
                logger.info(f"[ESP32 SERVO] {name} -> {angle:.1f}° (easing: {easing}ms)")

            elif topic == "robot/cmd/eyes":
                self.eye_expression = payload.get("expression", "neutral")
                self.eye_brightness = payload.get("brightness", 255)
                self.eye_pupil_x = payload.get("pupil_x", 0.0)
                self.eye_pupil_y = payload.get("pupil_y", 0.0)
                logger.info(
                    f"[ESP32 EYES UI] Expression: '{self.eye_expression}' | Gaze: ({self.eye_pupil_x:+.2f}, {self.eye_pupil_y:+.2f})"
                )

        except Exception as exc:
            logger.error(f"[ESP32] Error parsing command on {msg.topic}: {exc}")

    def _emergency_cut_motors(self, reason: str) -> None:
        self.linear_x = 0.0
        self.angular_z = 0.0
        logger.critical(f"[ESP32 HARDWARE FAILSAFE] MOTORS CUT TO ZERO! Reason: {reason}")

    def update_step(self, dt: float = 0.1) -> None:
        """Simulate hardware sensor dynamics and check watchdog."""
        now = time.time()

        # 1. Watchdog check (500ms timeout)
        time_since_heartbeat = now - self.last_heartbeat_time
        if time_since_heartbeat > self.WATCHDOG_TIMEOUT_S and not self.watchdog_tripped:
            self.watchdog_tripped = True
            self._emergency_cut_motors(
                f"Heartbeat timeout ({time_since_heartbeat * 1000:.0f}ms > {self.WATCHDOG_TIMEOUT_S * 1000:.0f}ms)"
            )

        # 2. Simulate battery discharge
        self.battery_voltage = max(10.0, self.battery_voltage - (0.0001 * dt))

        # 3. Add subtle sensor noise for realism
        noise = random.uniform(-0.2, 0.2)
        front_dist = max(5.0, self.tof_front_cm + noise)
        rear_dist = max(5.0, self.tof_rear_cm + noise)

        # 4. Publish telemetry
        telemetry = SensorTelemetry(
            battery_voltage=round(self.battery_voltage, 2),
            tof_front_cm=round(front_dist, 1),
            tof_rear_cm=round(rear_dist, 1),
            imu_roll=round(self.imu_roll, 2),
            imu_pitch=round(self.imu_pitch, 2),
            imu_yaw=round(self.imu_yaw, 2),
        )
        self._client.publish("robot/telemetry/sensors", json.dumps(telemetry.model_dump()), qos=0)

    async def run_loop(self) -> None:
        """Async loop running telemetry and safety checks at 10Hz."""
        logger.info("[ESP32] Simulator main loop started.")
        while self.running:
            self.update_step(dt=self.telemetry_interval_s)
            await asyncio.sleep(self.telemetry_interval_s)


def main():
    parser = argparse.ArgumentParser(description="ESP32-S3 Hardware Controller Simulator")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = parser.parse_args()

    sim = ESP32Simulator(broker_host=args.host, broker_port=args.port)
    sim.start()
    try:
        asyncio.run(sim.run_loop())
    except KeyboardInterrupt:
        logger.info("Shutting down simulator...")
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
