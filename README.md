# Pixar-Style Autonomous AI Companion Robot

An autonomous Pixar-style companion robot featuring tank-track differential drive, articulated head and arms, and expressive eyes.

## Hardware Roles & Specifications
- **Central Brain (NiPoGi AM02)**: AMD Ryzen 7 5800U (8C/16T), 16GB DDR4, Ubuntu 24.04 LTS, Docker.
  - 100% Local AI inference (faster-whisper, Qwen2.5-3B-Instruct GGUF via llama.cpp, Piper TTS, YOLOv11-nano).
- **Hardware Controller (ESP32-S3 DevKitC-1 N16R8)**:
  - Real-time actuation: Dual DC tank drive (TB6612FNG), head/arm servos, dual round LCDs (GC9A01), ToF sensors (VL53L0X), IMU (MPU6050).
  - Real-time communication via MQTT with Pydantic JSON schemas.
  - Hard safety watchdog: 1000ms heartbeat timeout cuts motor power immediately if AM02 stops sending heartbeats.

## Engineering Roadmap
- [x] Project charter, Pydantic schemas, Mosquitto MQTT, and hardware simulator.
- [ ] 3D PAD emotion engine and lifelike state machine.
- [ ] Local voice pipeline with faster-whisper, Qwen2.5, and Piper TTS.
- [ ] Vision tracking (YOLOv11) and persistent long-term memory (SQLite).
- [ ] Mission control web dashboard and ESP32-S3 FreeRTOS C++ firmware.
