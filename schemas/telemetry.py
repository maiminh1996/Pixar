from pydantic import BaseModel, Field

class SensorTelemetry(BaseModel):
    """
    Telemetry reported by the ESP32.
    Topic: robot/telemetry/sensors
    """
    battery_voltage: float = Field(..., description="Battery voltage level")
    tof_front_cm: float = Field(..., description="Front Time-of-Flight sensor distance in cm")
    tof_rear_cm: float = Field(..., description="Rear Time-of-Flight sensor distance in cm")
    imu_roll: float = Field(..., description="IMU Roll angle")
    imu_pitch: float = Field(..., description="IMU Pitch angle")
    imu_yaw: float = Field(..., description="IMU Yaw angle")
