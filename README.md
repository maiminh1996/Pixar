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
- [x] Sprint 1: Project charter, Pydantic schemas, Mosquitto MQTT, and hardware simulator.
- [x] Sprint 2: 3D PAD emotion engine and lifelike state machine.
- [ ] Sprint 3: Local voice pipeline with faster-whisper, Qwen2.5, and Piper TTS.
- [ ] Sprint 4: Vision tracking (YOLOv11) and persistent long-term memory (SQLite).
- [ ] Sprint 5: Mission control web dashboard and ESP32-S3 FreeRTOS C++ firmware.

## Data Contracts & Communication Protocol (Schemas)
All communication between the Central Brain and Hardware Controller is strictly typed via Pydantic models:
- `DriveCommand`: Differential drive linear and angular velocity (`linear_x`, `angular_z`) in SI units (`m/s`, `rad/s`).
- `ServoCommand`: Smooth articulated joint angles with cosine easing (`joint_id`, `angle`, `easing_duration_ms`).
- `EyeCommand`: LCD screen expressions and pupil coordinates (`expression`, `brightness`, `pupil_x`, `pupil_y`).
- `SensorTelemetry`: Real-time 10Hz readings (`battery_voltage`, `tof_front_cm`, `tof_rear_cm`, `imu_roll`, `imu_pitch`, `imu_yaw`).
- `HeartbeatCommand`: 200ms periodic safety pulse.

## Hardware Abstraction Layer & ESP32 Simulator
To develop and test without physical hardware:
```bash
./run_simulator.sh
```
The simulator emulates ESP32-S3 firmware, prints motor PWM updates, and enforces the 1000ms safety watchdog.

## Pixar 3D PAD Emotion Engine
The robot's psychological state is governed by a Pleasure-Arousal-Dominance (PAD) model:
- Moods: `happy`, `playful`, `curious`, `angry`, `sad`, `comfortable`, `neutral`.
- Continuous emotional decay back to baseline over time.
- Direct mapping to servo body gestures and LCD screen expressions.
