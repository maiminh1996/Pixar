"""
Emotion and personality data structures for Pixar-style AI companion robot.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EmotionType(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    CURIOUS = "curious"
    PLAYFUL = "playful"
    SURPRISED = "surprised"
    SLEEPY = "sleepy"
    SAD = "sad"
    SCARED = "scared"
    ALERT = "alert"
    PROUD = "proud"
    ANGRY = "angry"
    COMFORTABLE = "comfortable"
    CONFUSED = "confused"


class StimulusType(str, Enum):
    WAKE_WORD = "wake_word"
    USER_GREET = "user_greet"
    USER_COMPLIMENT = "user_compliment"
    OBSTACLE_NEAR = "obstacle_near"
    LOW_BATTERY = "low_battery"
    USER_INTERRUPT = "user_interrupt"
    TOUCH_PET = "touch_pet"
    IDLE_TIMEOUT = "idle_timeout"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"


class EyeExpression(BaseModel):
    """Visual presentation for the round/IPS eye displays."""
    expression_name: str
    brightness: int = 255
    pupil_x: float = 0.0  # -1.0 to +1.0
    pupil_y: float = 0.0  # -1.0 to +1.0


class BodyGesture(BaseModel):
    """Articulated head and arm servo angles."""
    head_pan: float = 90.0   # 0 to 180 degrees, 90 is straight
    head_tilt: float = 90.0  # 0 to 180 degrees, 90 is level
    left_arm: float = 90.0
    right_arm: float = 90.0
    easing_ms: int = 400


class VocalProsody(BaseModel):
    """Voice modification and audio chime hints for Piper TTS / audio."""
    pitch_scale: float = 1.0   # 0.8 to 1.3
    rate_scale: float = 1.0    # 0.8 to 1.3
    chime_effect: Optional[str] = None  # e.g., 'happy_chirp.wav', 'curious_whistle.wav'


class EmotionState(BaseModel):
    """Snapshot of current emotional and mood state."""
    current_emotion: EmotionType = EmotionType.NEUTRAL
    valence: float = Field(0.2, ge=-1.0, le=1.0, description="Negative (-1.0) to Positive (+1.0)")
    arousal: float = Field(0.2, ge=-1.0, le=1.0, description="Calm (-1.0) to Excited (+1.0)")
    dominance: float = Field(0.0, ge=-1.0, le=1.0, description="Submissive (-1.0) to Assertive (+1.0)")
    intensity: float = Field(0.5, ge=0.0, le=1.0, description="Emotion strength")
