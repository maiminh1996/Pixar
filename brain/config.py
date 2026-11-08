from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

CONFIG_FILE_PATH = Path(os.environ.get("ROBOT_CONFIG_FILE", Path(__file__).resolve().parents[1] / "config" / "robot_config.yaml"))

class HardwareConfig(BaseModel):
    broker_url: str = "localhost"
    broker_port: int = 1883
    heartbeat_interval_s: float = 0.20
    watchdog_timeout_ms: int = 1000
    collision_distance_cm: float = 20.0
    max_linear_speed_m_s: float = 1.0
    max_angular_speed_rad_s: float = 2.0

class ServoConfig(BaseModel):
    pan_center: float = 90.0
    pan_min: float = 30.0
    pan_max: float = 150.0
    tilt_center: float = 90.0
    tilt_min: float = 70.0
    tilt_max: float = 120.0

class RobotConfig(BaseModel):
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    servos: ServoConfig = Field(default_factory=ServoConfig)

def load_config(config_path: Optional[Path] = None) -> RobotConfig:
    target = config_path or CONFIG_FILE_PATH
    if target.is_file():
        try:
            import yaml
            data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
            return RobotConfig(**data)
        except Exception:
            pass
    return RobotConfig()

robot_config = load_config()
