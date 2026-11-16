"""
Central Robot Orchestrator for NiPoGi AM02 Brain.
Coordinates the master state machine, Emotion Engine,
Hardware Bridge (ESP32-S3), safety monitoring, and lifelike Pixar behaviors.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Optional

from brain.config import robot_config
from brain.hardware.mqtt_bridge import HardwareBridge
from brain.emotion.engine import EmotionEngine
from brain.emotion.models import StimulusType, EmotionType
from schemas.telemetry import SensorTelemetry

logger = logging.getLogger(__name__)


class RobotState(str, Enum):
    IDLE = "IDLE"
    SLEEPING = "SLEEPING"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class RobotOrchestrator:
    """
    Master Coordinator for NiPoGi AM02.
    Integrates Hardware Bridge, Emotion Engine, and Safety Watchdog.
    """

    HEARTBEAT_INTERVAL_S = 0.20
    LOW_BATTERY_VOLTAGE = 6.80
    COLLISION_DISTANCE_CM = 20.0

    def __init__(self, broker_url: Optional[str] = None, broker_port: Optional[int] = None):
        url = broker_url or robot_config.hardware.broker_url
        port = broker_port or robot_config.hardware.broker_port
        logger.info(f"Initializing RobotOrchestrator connecting to MQTT at {url}:{port}...")

        self.hardware = HardwareBridge(broker_host=url, broker_port=port)
        self.emotion = EmotionEngine()

        self.state = RobotState.IDLE
        self._running = False
        self._background_tasks: list[asyncio.Task] = []

        self.last_exchange: dict = {
            "user": "Ready for conversation.",
            "robot": "Hello! I am your companion robot.",
            "emotion": "neutral",
            "time": time.strftime("%H:%M:%S"),
        }
        self.conversation_logs: list[dict] = []

        # Wire hardware telemetry callback
        self.hardware.on_telemetry = self._on_sensor_telemetry

    def log_dialogue_event(self, speaker: str, message: str) -> None:
        turn = {
            "speaker": speaker,
            "message": message,
            "time": time.strftime("%H:%M:%S"),
        }
        self.conversation_logs.append(turn)
        if len(self.conversation_logs) > 50:
            self.conversation_logs.pop(0)

    def _on_sensor_telemetry(self, telemetry: SensorTelemetry) -> None:
        """Real-time telemetry analysis and proactive safety triggers."""
        # 1. Low battery safety check
        if telemetry.battery_voltage < self.LOW_BATTERY_VOLTAGE and self.state != RobotState.SLEEPING:
            logger.warning(f"Low battery warning: {telemetry.battery_voltage:.2f}V! Entering SLEEPING state.")
            self.state = RobotState.SLEEPING
            self.emotion.process_stimulus(StimulusType.LOW_BATTERY)
            self.sync_expression_and_posture()
            self.hardware.send_drive(0.0, 0.0)

        # 2. Collision avoidance safety check
        if telemetry.tof_front_cm < self.COLLISION_DISTANCE_CM and self.state != RobotState.EMERGENCY_STOP:
            logger.warning(f"Obstacle detected ({telemetry.tof_front_cm:.1f} cm)! Halting motion.")
            self.hardware.send_drive(0.0, 0.0)
            self.emotion.process_stimulus(StimulusType.OBSTACLE_NEAR)
            self.sync_expression_and_posture()

    def sync_expression_and_posture(self) -> None:
        """Synchronizes current PAD emotion with LCD eyes and head/arm servos."""
        if self.state == RobotState.EMERGENCY_STOP:
            return

        eye_expr = self.emotion.get_eye_expression()
        self.hardware.send_eyes(
            expression=eye_expr.expression_name,
            brightness=eye_expr.brightness,
            pupil_x=eye_expr.pupil_x,
            pupil_y=eye_expr.pupil_y,
        )

        # Send articulated servo joint positions
        gesture = self.emotion.get_body_gesture()
        self.hardware.send_servo(0, gesture.head_pan, easing_duration_ms=gesture.easing_ms)
        self.hardware.send_servo(1, gesture.head_tilt, easing_duration_ms=gesture.easing_ms)
        self.hardware.send_servo(2, gesture.left_arm, easing_duration_ms=gesture.easing_ms)
        self.hardware.send_servo(3, gesture.right_arm, easing_duration_ms=gesture.easing_ms)

    async def start(self) -> None:
        """Start background safety heartbeat and lifelike idle behaviors."""
        logger.info("Starting RobotOrchestrator core loops...")
        self._running = True
        self.hardware.start()

        # Initial wake-up animation
        self.emotion.process_stimulus(StimulusType.TOUCH_PET)
        self.sync_expression_and_posture()

        self._background_tasks = [
            asyncio.create_task(self._heartbeat_loop(), name="safety_heartbeat"),
            asyncio.create_task(self._lifelike_idle_loop(), name="idle_fidget"),
            asyncio.create_task(self._emotion_decay_loop(), name="decay_loop"),
        ]

    async def stop(self) -> None:
        """Gracefully terminate all orchestrator tasks and stop hardware."""
        logger.info("Stopping RobotOrchestrator...")
        self._running = False
        for task in self._background_tasks:
            task.cancel()
        self.hardware.stop()

    def emergency_stop(self, reason: str = "Operator Triggered E-Stop") -> None:
        """Engage hardware and software E-Stop."""
        self.state = RobotState.EMERGENCY_STOP
        self.hardware.send_estop(trigger=True, reason=reason)
        self.hardware.send_eyes("tremble_small", brightness=255)
        logger.critical(f"Orchestrator engaged EMERGENCY STOP: {reason}")

    def release_emergency_stop(self) -> None:
        """Release E-Stop and return to IDLE."""
        self.hardware.send_estop(trigger=False, reason="E-Stop reset")
        self.state = RobotState.IDLE
        self.emotion.set_emotion_explicit(EmotionType.CURIOUS)
        self.sync_expression_and_posture()
        logger.info("Orchestrator released EMERGENCY STOP. Back to IDLE.")

    def send_drive(self, linear_x: float, angular_z: float) -> None:
        """Direct locomotion control passing through active safety estop."""
        if self.state == RobotState.EMERGENCY_STOP:
            logger.warning("Motion rejected: E-Stop is active.")
            return
        self.hardware.send_drive(linear_x, angular_z)

    async def _heartbeat_loop(self) -> None:
        """Periodic 200ms safety pulse ensuring ESP32 watchdog does not trigger."""
        seq = 0
        while self._running:
            try:
                self.hardware.send_heartbeat(seq)
                seq = (seq + 1) % 65536
                await asyncio.sleep(self.HEARTBEAT_INTERVAL_S)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in heartbeat loop: {exc}")
                await asyncio.sleep(1.0)

    async def _lifelike_idle_loop(self) -> None:
        """Lifelike idle behaviors: subtle head tilts, eye blinks, and micro-fidgets."""
        while self._running:
            try:
                delay = random.uniform(3.0, 5.0)
                await asyncio.sleep(delay)

                if self.state == RobotState.IDLE and not self.emotion.is_locked:
                    self.sync_expression_and_posture()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Idle fidget loop exception: {exc}")

    async def _emotion_decay_loop(self) -> None:
        """Pulls PAD emotional state back toward baseline over time."""
        last_time = time.time()
        while self._running:
            try:
                await asyncio.sleep(0.5)
                now = time.time()
                dt = now - last_time
                last_time = now

                if not self.emotion.is_locked:
                    self.emotion.step_decay(dt)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Emotion decay loop exception: {exc}")
