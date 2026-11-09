"""
Pixar-style Emotion Engine for autonomous AI Companion Robot.
Maintains continuous affective state (Valence, Arousal, Dominance)
and outputs coordinated eye animations, head/arm gestures, and vocal prosody.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional

from brain.config import robot_config
from brain.emotion.models import (
    EmotionType,
    StimulusType,
    EmotionState,
    EyeExpression,
    BodyGesture,
    VocalProsody,
)

logger = logging.getLogger(__name__)


class EmotionEngine:
    """
    Simulates emotional personality inspired by Wall-E / Baymax:
    warm, inquisitive, slightly clumsy, and highly expressive.
    """

    # Baseline resting state (Pixar persona: warm and curious)
    BASELINE_VALENCE = 0.25
    BASELINE_AROUSAL = 0.20
    BASELINE_DOMINANCE = 0.05
    DECAY_RATE = 0.08  # Per second pull toward baseline

    def __init__(self, config=None):
        cfg = config or getattr(robot_config, "emotion", None)
        self.decay_rate = cfg.decay_rate_per_second if cfg else self.DECAY_RATE
        self.baseline_valence = cfg.resting_valence if cfg else self.BASELINE_VALENCE
        self.baseline_arousal = cfg.resting_arousal if cfg else self.BASELINE_AROUSAL
        self.baseline_dominance = cfg.resting_dominance if cfg else self.BASELINE_DOMINANCE

        self.state = EmotionState(
            current_emotion=EmotionType.CURIOUS,
            valence=self.baseline_valence,
            arousal=self.baseline_arousal,
            dominance=self.baseline_dominance,
            intensity=0.6,
        )
        self.is_locked: bool = False

    def lock_emotion(self, emotion: Optional[EmotionType] = None) -> None:
        """Lock current or specified emotion so it does not decay."""
        if emotion:
            self.set_emotion_explicit(emotion)
        self.is_locked = True
        logger.info(f"Emotion locked to: {self.state.current_emotion.value}")

    def unlock_emotion(self) -> None:
        """Unlock emotion and resume natural decay."""
        self.is_locked = False
        logger.info("Emotion unlocked, natural decay resumed.")

    def process_stimulus(self, stimulus: StimulusType, intensity: float = 0.8) -> EmotionState:
        """Trigger emotional shift based on sensory/dialogue events."""
        logger.info(f"Emotion stimulus received: {stimulus.value} (intensity={intensity:.2f})")

        if stimulus == StimulusType.WAKE_WORD:
            self.state.current_emotion = EmotionType.CURIOUS
            self.state.valence = max(self.state.valence, 0.4)
            self.state.arousal = 0.6
            self.state.intensity = intensity

        elif stimulus == StimulusType.USER_GREET:
            self.state.current_emotion = EmotionType.HAPPY
            self.state.valence = 0.8
            self.state.arousal = 0.7
            self.state.intensity = intensity

        elif stimulus == StimulusType.USER_COMPLIMENT:
            self.state.current_emotion = EmotionType.PROUD
            self.state.valence = 0.9
            self.state.arousal = 0.5
            self.state.intensity = intensity

        elif stimulus == StimulusType.OBSTACLE_NEAR:
            self.state.current_emotion = EmotionType.SURPRISED
            self.state.valence = -0.3
            self.state.arousal = 0.9
            self.state.intensity = 1.0

        elif stimulus == StimulusType.LOW_BATTERY:
            self.state.current_emotion = EmotionType.SLEEPY
            self.state.valence = -0.2
            self.state.arousal = -0.7
            self.state.intensity = 0.9

        elif stimulus == StimulusType.USER_INTERRUPT:
            self.state.current_emotion = EmotionType.SURPRISED
            self.state.valence = 0.1
            self.state.arousal = 0.7
            self.state.intensity = 0.7

        elif stimulus == StimulusType.TOUCH_PET:
            self.state.current_emotion = EmotionType.PLAYFUL
            self.state.valence = 0.85
            self.state.arousal = 0.6
            self.state.intensity = intensity

        elif stimulus == StimulusType.IDLE_TIMEOUT:
            self.state.current_emotion = EmotionType.SLEEPY
            self.state.valence = 0.1
            self.state.arousal = -0.5
            self.state.intensity = 0.5

        return self.state

    def set_emotion_explicit(self, emotion: EmotionType, intensity: float = 0.7) -> None:
        """Allow direct override, e.g., when LLM dialogue outputs an emotion tag [happy]."""
        self.state.current_emotion = emotion
        self.state.intensity = intensity
        if emotion in (EmotionType.HAPPY, EmotionType.PLAYFUL, EmotionType.PROUD, EmotionType.COMFORTABLE):
            self.state.valence = 0.7
            self.state.arousal = 0.4 if emotion == EmotionType.COMFORTABLE else 0.6
        elif emotion in (EmotionType.SAD, EmotionType.SLEEPY):
            self.state.valence = -0.4
            self.state.arousal = -0.5
        elif emotion == EmotionType.ANGRY:
            self.state.valence = -0.6
            self.state.arousal = 0.85
            self.state.dominance = 0.8
        elif emotion in (EmotionType.SURPRISED, EmotionType.ALERT):
            self.state.arousal = 0.8
        elif emotion == EmotionType.CONFUSED:
            self.state.valence = 0.0
            self.state.arousal = 0.3

    def step_decay(self, dt: float) -> None:
        self.tick(dt)

    def tick(self, dt: float) -> None:
        """Decay affective state smoothly toward baseline unless locked."""
        if self.is_locked:
            return  # Emotion is locked by user command

        factor = self.decay_rate * dt
        self.state.valence += (self.baseline_valence - self.state.valence) * factor
        self.state.arousal += (self.baseline_arousal - self.state.arousal) * factor
        self.state.dominance += (self.baseline_dominance - self.state.dominance) * factor
        self.state.intensity = max(0.2, self.state.intensity - (factor * 0.5))

        # Transition back to neutral or curious if intensity is low
        if self.state.intensity <= 0.3:
            self.state.current_emotion = EmotionType.CURIOUS if self.state.valence >= 0.2 else EmotionType.NEUTRAL

    # ==================== Expressive Mappings ====================

    def get_eye_expression(self) -> EyeExpression:
        """Map emotional state to eye screen presentation."""
        e = self.state.current_emotion

        if e == EmotionType.HAPPY:
            return EyeExpression(expression_name="happy_squint", brightness=255, pupil_x=0.0, pupil_y=0.1)
        elif e == EmotionType.CURIOUS:
            return EyeExpression(expression_name="curious_tilt", brightness=240, pupil_x=0.2, pupil_y=0.2)
        elif e == EmotionType.PLAYFUL:
            return EyeExpression(expression_name="playful_sparkle", brightness=255, pupil_x=-0.2, pupil_y=0.2)
        elif e == EmotionType.SURPRISED:
            return EyeExpression(expression_name="wide_open", brightness=255, pupil_x=0.0, pupil_y=0.3)
        elif e == EmotionType.SLEEPY:
            return EyeExpression(expression_name="droopy_sleepy", brightness=120, pupil_x=0.0, pupil_y=-0.3)
        elif e == EmotionType.SAD:
            return EyeExpression(expression_name="sad_down", brightness=180, pupil_x=0.0, pupil_y=-0.2)
        elif e == EmotionType.SCARED:
            return EyeExpression(expression_name="tremble_small", brightness=255, pupil_x=0.0, pupil_y=0.0)
        elif e == EmotionType.ALERT:
            return EyeExpression(expression_name="alert_focused", brightness=255, pupil_x=0.0, pupil_y=0.1)
        elif e == EmotionType.PROUD:
            return EyeExpression(expression_name="proud_puff", brightness=255, pupil_x=0.1, pupil_y=0.2)
        elif e == EmotionType.ANGRY:
            return EyeExpression(expression_name="angry_narrow", brightness=255, pupil_x=0.0, pupil_y=-0.1)
        elif e == EmotionType.COMFORTABLE:
            return EyeExpression(expression_name="gentle_warm", brightness=200, pupil_x=0.0, pupil_y=0.0)
        elif e == EmotionType.CONFUSED:
            return EyeExpression(expression_name="one_big_one_small", brightness=240, pupil_x=-0.2, pupil_y=0.1)
        else:
            return EyeExpression(expression_name="neutral_open", brightness=220, pupil_x=0.0, pupil_y=0.0)

    def get_body_gesture(self) -> BodyGesture:
        """Map emotional state to head/arm servo angles."""
        e = self.state.current_emotion

        if e == EmotionType.HAPPY:
            # Head up slightly, arms raised joyfully
            return BodyGesture(head_pan=90.0, head_tilt=110.0, left_arm=135.0, right_arm=135.0, easing_ms=300)
        elif e == EmotionType.CURIOUS:
            # Inquisitive head tilt, one arm slightly lifted
            return BodyGesture(head_pan=105.0, head_tilt=100.0, left_arm=90.0, right_arm=110.0, easing_ms=500)
        elif e == EmotionType.PLAYFUL:
            # Wiggle head pan, arms out
            return BodyGesture(head_pan=75.0, head_tilt=105.0, left_arm=120.0, right_arm=120.0, easing_ms=250)
        elif e == EmotionType.SURPRISED:
            # Head snaps up high, arms pull back
            return BodyGesture(head_pan=90.0, head_tilt=125.0, left_arm=45.0, right_arm=45.0, easing_ms=150)
        elif e == EmotionType.SLEEPY:
            # Head droops forward, arms down
            return BodyGesture(head_pan=90.0, head_tilt=65.0, left_arm=45.0, right_arm=45.0, easing_ms=800)
        elif e == EmotionType.SAD:
            # Head tilted down, arms limp
            return BodyGesture(head_pan=85.0, head_tilt=70.0, left_arm=50.0, right_arm=50.0, easing_ms=600)
        elif e == EmotionType.ANGRY:
            # Head thrust forward/down, arms firmly positioned
            return BodyGesture(head_pan=90.0, head_tilt=78.0, left_arm=125.0, right_arm=125.0, easing_ms=200)
        elif e == EmotionType.COMFORTABLE:
            # Soft posture
            return BodyGesture(head_pan=92.0, head_tilt=92.0, left_arm=80.0, right_arm=80.0, easing_ms=500)
        else:
            # Neutral / attentive
            return BodyGesture(head_pan=90.0, head_tilt=90.0, left_arm=90.0, right_arm=90.0, easing_ms=400)

    def get_prosody(self) -> VocalProsody:
        """Map emotional state to voice synthesis modulation."""
        e = self.state.current_emotion

        if e in (EmotionType.HAPPY, EmotionType.PLAYFUL):
            return VocalProsody(pitch_scale=1.15, rate_scale=1.1, chime_effect="happy_chirp.wav")
        elif e == EmotionType.CURIOUS:
            return VocalProsody(pitch_scale=1.08, rate_scale=1.0, chime_effect="curious_whistle.wav")
        elif e == EmotionType.ANGRY:
            return VocalProsody(pitch_scale=0.88, rate_scale=1.2, chime_effect="grumpy_buzz.wav")
        elif e == EmotionType.SURPRISED:
            return VocalProsody(pitch_scale=1.08, rate_scale=1.0, chime_effect="curious_whistle.wav")
        elif e == EmotionType.SURPRISED:
            return VocalProsody(pitch_scale=1.25, rate_scale=1.2, chime_effect="surprise_beep.wav")
        elif e in (EmotionType.SLEEPY, EmotionType.SAD):
            return VocalProsody(pitch_scale=0.90, rate_scale=0.85, chime_effect="sleepy_sigh.wav")
        else:
            return VocalProsody(pitch_scale=1.0, rate_scale=1.0, chime_effect=None)
