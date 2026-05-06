from __future__ import annotations

import json
import traceback
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.payload_builder import Live2DPayloadBuilder
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper
from integrations.live2d.live2d_py_runtime import Live2DPyRuntime
from integrations.live2d.model_scanner import Live2DModelScanner
from integrations.live2d.profile_generator import Live2DProfileGenerator
from integrations.live2d.renderer import HeadlessLive2DRenderer

router = APIRouter()


class Live2DPreviewRequest(BaseModel):
    character_id: str = "yzl"
    emotion: str = "neutral"
    expression: str | None = None
    motion: str | None = None
    background_id: str | None = None
    image_type: str | None = None
    daily_scene_type: str | None = None
    topic: str | None = None
    audio_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Live2DInspectRequest(BaseModel):
    character_id: str = "yzl"
    model3_json: str | None = None


class Live2DLoadRequest(BaseModel):
    character_id: str = "yzl"
    model3_json: str | None = None


class Live2DApplyPayloadRequest(BaseModel):
    character_id: str = "yzl"
    model3_json: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Live2DScanRequest(BaseModel):
    root: str = "data/live2d/characters"


class Live2DGenerateProfileRequest(BaseModel):
    character_id: str = "yzl"
    model_id: str = "yzl_v1"
    display_name: str = "乐正绫"
    model3_json: str
    output_path: str = "data/live2d/characters/yzl/profile.yaml"
    overwrite: bool = False


@router.get("/live2d/stats")
def live2d_stats():
    try:
        registry = _build_registry()
        return _json_response(
            {
                "ok": True,
                "stats": registry.stats(),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/preview")
def live2d_preview(request: Live2DPreviewRequest):
    try:
        builder = _build_payload_builder()
        payload = builder.build(
            character_id=request.character_id,
            emotion=request.emotion,
            expression=request.expression,
            motion=request.motion,
            background_id=request.background_id,
            image_type=request.image_type,
            daily_scene_type=request.daily_scene_type,
            topic=request.topic,
            audio_url=request.audio_url,
            metadata=request.metadata,
        )

        return _json_response(
            {
                "ok": True,
                "payload": payload,
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.get("/live2d/runtime/status")
def live2d_runtime_status():
    try:
        runtime = Live2DPyRuntime()
        return _json_response(
            {
                "ok": True,
                "runtime": runtime.status(),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/runtime/inspect")
def live2d_runtime_inspect(request: Live2DInspectRequest):
    try:
        runtime = Live2DPyRuntime()
        model3_json = _resolve_model3_json(
            character_id=request.character_id,
            model3_json=request.model3_json,
        )
        return _json_response(
            {
                "ok": True,
                "inspection": runtime.prepare_model(model3_json),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/runtime/load")
def live2d_runtime_load(request: Live2DLoadRequest):
    try:
        runtime = Live2DPyRuntime()
        model3_json = _resolve_model3_json(
            character_id=request.character_id,
            model3_json=request.model3_json,
        )
        result = runtime.load_model_session(model3_json)
        return _json_response(
            {
                "ok": bool(result.get("ok")),
                "result": result,
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/runtime/apply-payload")
def live2d_runtime_apply_payload(request: Live2DApplyPayloadRequest):
    try:
        model3_json = _resolve_model3_json(
            character_id=request.character_id,
            model3_json=request.model3_json,
        )

        renderer = HeadlessLive2DRenderer()
        load_result = renderer.load(model3_json)
        if not load_result.get("ok"):
            return _json_response(
                {
                    "ok": False,
                    "stage": "load",
                    "load_result": load_result,
                }
            )

        apply_result = renderer.apply_payload(request.payload)
        return _json_response(
            {
                "ok": bool(apply_result.get("ok")),
                "load_result": load_result,
                "apply_result": apply_result,
                "snapshot": renderer.snapshot(),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/models/scan")
def live2d_models_scan(request: Live2DScanRequest):
    try:
        scanner = Live2DModelScanner()
        return _json_response(
            {
                "ok": True,
                "result": scanner.scan_root(request.root),
            }
        )
    except Exception as exc:
        return _error_response(exc)


@router.post("/live2d/profile/generate")
def live2d_profile_generate(request: Live2DGenerateProfileRequest):
    try:
        generator = Live2DProfileGenerator()
        profile = generator.generate_character_profile(
            character_id=request.character_id,
            model_id=request.model_id,
            display_name=request.display_name,
            model3_json=request.model3_json,
            output_path=request.output_path,
            overwrite=request.overwrite,
        )
        return _json_response(
            {
                "ok": True,
                "profile": profile,
                "output_path": request.output_path,
            }
        )
    except Exception as exc:
        return _error_response(exc)


def _resolve_model3_json(*, character_id: str, model3_json: str | None) -> str:
    if model3_json:
        return model3_json

    registry = _build_registry()
    profile = registry.get_character(character_id)
    return profile.model3_json


def _build_registry() -> Live2DRegistry:
    registry = Live2DRegistry(
        character_root="data/live2d/characters",
        background_root="data/live2d/backgrounds",
    )
    registry.load()
    return registry


def _build_payload_builder() -> Live2DPayloadBuilder:
    return Live2DPayloadBuilder(
        registry=_build_registry(),
        motion_mapper=Live2DMotionMapper(),
        scene_mapper=Live2DSceneMapper(),
    )


def _json_response(body: dict, status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(body, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
    )


def _error_response(exc: Exception, status_code: int = 500) -> Response:
    body = {
        "ok": False,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
    return _json_response(body, status_code=status_code)
