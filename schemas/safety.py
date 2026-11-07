from pydantic import BaseModel, Field

class Heartbeat(BaseModel):
    """
    Safety watchdog heartbeat from Brain to ESP32.
    Topic: robot/safety/heartbeat
    """
    timestamp_ms: int = Field(..., description="Unix timestamp in milliseconds")
    brain_status: str = Field(..., description="System status, e.g., 'OK', 'FAULT', 'EMERGENCY_STOP'")

class EStopCommand(BaseModel):
    """
    Emergency Stop trigger/release.
    Topic: robot/safety/estop
    """
    trigger: bool = Field(..., description="True to engage E-Stop, False to release")
    reason: str = Field("Manual or software trigger", description="Cause of E-Stop")
