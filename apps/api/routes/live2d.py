from __future__ import annotations

import json
import traceback
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from apps.api.response_utils import (
    error_message_response,
    error_response,
    ok_response,
)

from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.payload_builder import Live2DPayloadBuilder
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper
from aiagent.live2d.payload_contract import normalize_live2d_payload
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
        return ok_response(
            stats=registry.stats(),
        )
    except Exception as exc:
        return error_response(
            stage="live2d_stats",
            exc=exc,
            status_code=500,
        )


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

        return ok_response(
            payload=payload,
        )

    except Exception as exc:
        return error_response(
            stage="live2d_preview",
            exc=exc,
            status_code=500,
        )


@router.get("/live2d/runtime/status")
def live2d_runtime_status():
    try:
        runtime = Live2DPyRuntime()
        return ok_response(
            runtime=runtime.status(),
        )
    except Exception as exc:
        return error_response(
            stage="live2d_runtime_status",
            exc=exc,
            status_code=500,
        )

@router.post("/live2d/runtime/inspect")
def live2d_runtime_inspect(request: Live2DInspectRequest):
    try:
        runtime = Live2DPyRuntime()
        model3_json = _resolve_model3_json(
            character_id=request.character_id,
            model3_json=request.model3_json,
        )
        return ok_response(
                   model3_json=model3_json,
               )

    except Exception as exc:
        return error_response(
                    stage="live2d_runtime_load",
                    exc=exc,
                    status_code=500,
                )

@router.post("/live2d/runtime/load")
def live2d_runtime_load(request: Live2DLoadRequest):
    try:
        runtime = Live2DPyRuntime()
        model3_json = _resolve_model3_json(
            character_id=request.character_id,
            model3_json=request.model3_json,
        )
        result = runtime.load_model_session(model3_json)

        if not result.get("ok"):
            return error_message_response(
                stage="live2d_runtime_load",
                error=str(result.get("error") or "Live2D model load failed."),
                status_code=500,
                extra={
                    "result": result,
                },
            )

        return ok_response(
            result=result,
        )

    except Exception as exc:
        return error_response(
            stage="live2d_runtime_load",
            exc=exc,
            status_code=500,
        )


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
            return error_message_response(
            stage="live2d_runtime_apply_payload_load",
            error=str(load_result.get("error") or "Live2D model load failed."),
            status_code=500,
            extra={
                "load_result": load_result,
            },
        )

        payload = normalize_live2d_payload(
            request.payload,
            metadata={
                "source": "live2d_runtime_apply_payload",
            },
        )

        apply_result = renderer.apply_payload(payload)
        return ok_response(
            payload=payload,
            load_result=load_result,
            apply_result=apply_result,
            snapshot=renderer.snapshot(),
        )
    except Exception as exc:
        return error_response(
                    stage="live2d_runtime_load",
                    exc=exc,
                    status_code=500,
                )
@router.post("/live2d/models/scan")
def live2d_models_scan(request: Live2DScanRequest):
    try:
        scanner = Live2DModelScanner()
        return ok_response(
            result=scanner.scan_root(request.root),
        )
    except Exception as exc:
        return error_response(
            stage="live2d_models_scan",
            exc=exc,
            status_code=500,
        )


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

        return ok_response(
            profile=profile,
            output_path=request.output_path,
        )

    except Exception as exc:
        return error_response(
            stage="live2d_profile_generate",
            exc=exc,
            status_code=500,
        )

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



