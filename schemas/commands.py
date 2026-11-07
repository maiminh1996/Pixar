from pydantic import BaseModel, Field

class DriveCommand(BaseModel):
    """
    Tank track differential drive command.
    Topic: robot/cmd/drive
    """
    linear_x: float = Field(..., description="Linear velocity forward (+)/backward (-) in m/s or normalized [-1.0, 1.0]")
    angular_z: float = Field(..., description="Angular velocity left (+)/right (-) in rad/s or normalized [-1.0, 1.0]")

class ServoCommand(BaseModel):
    """
    Servo actuation command for head/arms.
    Topic: robot/cmd/servo
    Joint IDs:
      0: Head Pan (0-180 deg, center 90)
      1: Head Tilt (0-180 deg, center 90)
      2: Left Arm (0-180 deg)
      3: Right Arm (0-180 deg)
    """
    joint_id: int = Field(..., description="Hardware ID of the servo motor")
    angle: float = Field(..., ge=0, le=180, description="Target angle in degrees")
    easing_duration_ms: int = Field(0, description="Time to reach target angle for smooth easing")

class EyeCommand(BaseModel):
    """
    Eye animation UI command for round/IPS LCD displays.
    Topic: robot/cmd/eyes
    """
    expression: str = Field(..., description="Expression name, e.g., 'happy', 'sad', 'blink', 'curious', 'sleepy'")
    brightness: int = Field(255, ge=0, le=255, description="Eye display brightness (0-255)")
    pupil_x: float = Field(0.0, ge=-1.0, le=1.0, description="Pupil horizontal gaze offset [-1.0 left, +1.0 right]")
    pupil_y: float = Field(0.0, ge=-1.0, le=1.0, description="Pupil vertical gaze offset [-1.0 down, +1.0 up]")
