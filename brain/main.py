"""
FastAPI Brain Service Entrypoint for NiPoGi AM02.
Provides REST and WebSocket APIs for monitoring, teleoperation,
and software testing of the Pixar AI Companion Robot.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from brain.orchestrator import RobotOrchestrator, RobotState
from brain.emotion.models import EmotionType
from brain.logger_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

orchestrator: Optional[RobotOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    import os
    broker_host = os.environ.get("MQTT_BROKER_URL", "localhost")
    broker_port = int(os.environ.get("MQTT_BROKER_PORT", 1883))
    llm_api_base = os.environ.get("LLM_API_BASE", "http://localhost:8080/v1")

    logger.info(f"Initializing Robot Brain Core (MQTT: {broker_host}:{broker_port}, LLM: {llm_api_base})...")
    orchestrator = RobotOrchestrator(
        broker_host=broker_host,
        broker_port=broker_port,
        llm_api_base=llm_api_base,
    )
    try:
        await orchestrator.start()
    except Exception as exc:
        logger.warning(f"MQTT Broker not reachable during startup ({exc}). Operating in standalone mode.")

    yield

    logger.info("Shutting down Robot Brain Core...")
    if orchestrator:
        await orchestrator.stop()


app = FastAPI(
    title="Pixar AI Companion Robot - Brain Core API",
    description="Central Brain API running on NiPoGi AM02 (Ubuntu 24.04)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def exception_logging_middleware(request, call_next):
    """Global middleware capturing any unhandled exception with full traceback to log."""
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_SERVER_ERROR", "detail": str(exc)},
        )


# ==================== Request Models ====================

class DriveRequest(BaseModel):
    linear_x: float
    angular_z: float


class ServoRequest(BaseModel):
    joint_id: int
    angle: float
    easing_duration_ms: int = 400


class EyeRequest(BaseModel):
    expression: str
    brightness: int = 255
    pupil_x: float = 0.0
    pupil_y: float = 0.0


class DialogueRequest(BaseModel):
    message: str


# ==================== Endpoints ====================


@app.get("/health")
async def health_check():
    return {"status": "ok", "hardware_connected": orchestrator.hardware.is_connected if orchestrator else False}


@app.get("/state")
async def get_state():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    return {
        "state": orchestrator.state.value,
        "emotion": orchestrator.emotion.state.current_emotion.value,
        "valence": orchestrator.emotion.state.valence,
        "arousal": orchestrator.emotion.state.arousal,
        "is_estop": orchestrator.hardware.is_estop_active,
    }


@app.get("/emotion")
async def get_emotion():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    em_val = orchestrator.emotion.state.current_emotion.value
    return {
        "emotion": em_val,
        "current_emotion": em_val,
        **orchestrator.emotion.state.model_dump(),
        "is_locked": orchestrator.emotion.is_locked,
    }


@app.post("/emotion/lock")
async def lock_emotion(emotion: Optional[str] = None):
    """Lock eye expression and body posture, preventing decay to neutral."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    em = EmotionType(emotion) if emotion else None
    orchestrator.emotion.lock_emotion(em)
    orchestrator.sync_expression_and_posture()
    return {"status": "EMOTION_LOCKED", "current_emotion": orchestrator.emotion.state.current_emotion.value}


@app.post("/emotion/unlock")
async def unlock_emotion():
    """Unlock emotion, restoring natural decay dynamics and idle behaviors."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    orchestrator.emotion.unlock_emotion()
    return {"status": "EMOTION_UNLOCKED"}


@app.get("/telemetry")
async def get_telemetry():
    """Fetch real-time sensor telemetry (battery, ToF, IMU) from ESP32."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    if orchestrator.hardware.last_telemetry:
        return orchestrator.hardware.last_telemetry.model_dump()
    return {"status": "NO_DATA", "detail": "No telemetry packets received yet from hardware or simulator."}


@app.get("/system")
async def get_system_status():
    """Monitor host system resources (CPU, RAM) and connection status."""
    import os
    import psutil
    import time

    uptime = time.time() - psutil.boot_time()
    
    return {
        "os": "Ubuntu 24.04 LTS (NiPoGi AM02)",
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "ram_usage": dict(psutil.virtual_memory()._asdict()),
        "uptime_seconds": round(uptime),
        "mqtt_connected": orchestrator.hardware.is_connected if orchestrator else False,
        "llm_api_base": os.environ.get("LLM_API_BASE", "http://localhost:8080/v1")
    }


@app.post("/wake")
async def trigger_wake():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    orchestrator.trigger_wake_word()
    return {"status": "WAKE_TRIGGERED", "state": orchestrator.state.value}


@app.post("/dialogue")
async def talk_to_robot(req: DialogueRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    try:
        result = await orchestrator.handle_user_text(req.message)
        return result
    except Exception as exc:
        logger.error(f"Dialogue processing error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/barge_in")
async def trigger_barge_in():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    orchestrator.trigger_barge_in()
    return {"status": "BARGE_IN_TRIGGERED", "state": orchestrator.state.value}


@app.post("/estop")
async def trigger_estop(reason: str = "REST API emergency stop"):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    orchestrator.emergency_stop(reason=reason)
    return {"status": "EMERGENCY_STOP_ACTIVE", "reason": reason}


@app.post("/estop/release")
async def release_estop():
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    orchestrator.release_emergency_stop()
    return {"status": "EMERGENCY_STOP_RELEASED", "state": orchestrator.state.value}


@app.post("/drive")
async def drive_robot(req: DriveRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    try:
        cmd = orchestrator.hardware.send_drive(req.linear_x, req.angular_z)
        return {"command": cmd.model_dump()}
    except Exception as exc:
        logger.error(f"Drive command error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/servo")
async def move_servo(req: ServoRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    cmd = orchestrator.hardware.send_servo(req.joint_id, req.angle, req.easing_duration_ms)
    return {"command": cmd.model_dump()}


@app.post("/eyes")
async def set_eyes(req: EyeRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Brain not initialized")
    cmd = orchestrator.hardware.send_eyes(req.expression, req.brightness, req.pupil_x, req.pupil_y)
    return {"command": cmd.model_dump()}


