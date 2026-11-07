import os
import time
import asyncio
import paho.mqtt.client as mqtt
import json
import logging

logger = logging.getLogger(__name__)

class RobotMQTTClient:
    def __init__(self):
        self.broker = os.environ.get("MQTT_BROKER_URL", "localhost")
        self.port = int(os.environ.get("MQTT_BROKER_PORT", 1883))
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._running = False

    def _on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker {self.broker}:{self.port} with result {rc}")
        self.client.subscribe("robot/telemetry/sensors")

    def _on_message(self, client, userdata, msg):
        logger.debug(f"Received {msg.topic}: {msg.payload.decode()}")

    def start(self):
        logger.info("Starting MQTT client...")
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self._running = True
        except Exception as e:
            logger.error(f"MQTT Connection failed: {e}")

    def stop(self):
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()

    def publish_command(self, topic: str, payload: dict):
        if self._running:
            self.client.publish(topic, json.dumps(payload))

    async def heartbeat_loop(self, state_engine):
        while self._running:
            # Publish heartbeat every 500ms
            heartbeat = {
                "timestamp_ms": int(time.time() * 1000),
                "brain_status": state_engine.current_state.value
            }
            self.publish_command("robot/safety/heartbeat", heartbeat)
            await asyncio.sleep(0.5)

mqtt_client = RobotMQTTClient()
