"""Unit tests for EmotionEngine."""

from brain.emotion.engine import EmotionEngine
from brain.emotion.models import EmotionType, StimulusType


def test_emotion_baseline_and_stimulus():
    engine = EmotionEngine()
    assert engine.state.current_emotion == EmotionType.CURIOUS

    # User Greet stimulus
    engine.process_stimulus(StimulusType.USER_GREET)
    assert engine.state.current_emotion == EmotionType.HAPPY
    assert engine.state.valence > 0.7

    # Eye expression for HAPPY
    eyes = engine.get_eye_expression()
    assert eyes.expression_name == "happy_squint"

    # Body gesture for HAPPY
    gesture = engine.get_body_gesture()
    assert gesture.head_tilt > 100.0  # looking up happily


def test_obstacle_and_low_battery_stimulus():
    engine = EmotionEngine()

    engine.process_stimulus(StimulusType.OBSTACLE_NEAR)
    assert engine.state.current_emotion == EmotionType.SURPRISED
    assert engine.get_eye_expression().expression_name == "wide_open"

    engine.process_stimulus(StimulusType.LOW_BATTERY)
    assert engine.state.current_emotion == EmotionType.SLEEPY
    assert engine.get_body_gesture().head_tilt < 70.0  # droop head


def test_emotion_decay():
    engine = EmotionEngine()
    engine.process_stimulus(StimulusType.USER_GREET, intensity=1.0)
    high_valence = engine.state.valence

    # Tick decay for 10 seconds
    for _ in range(10):
        engine.tick(dt=1.0)

    # Valence should have decayed towards baseline
    assert engine.state.valence < high_valence


def test_emotion_lock():
    engine = EmotionEngine()
    engine.lock_emotion(EmotionType.HAPPY)
    assert engine.is_locked is True
    assert engine.state.current_emotion == EmotionType.HAPPY

    high_valence = engine.state.valence
    # Tick decay for 10 seconds while locked
    for _ in range(10):
        engine.tick(dt=1.0)

    # When locked, valence must not decay!
    assert engine.state.valence == high_valence
    assert engine.state.current_emotion == EmotionType.HAPPY

    engine.unlock_emotion()
    assert engine.is_locked is False
