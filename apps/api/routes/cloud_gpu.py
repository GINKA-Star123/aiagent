from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.gpu_client import gpu_client
from config.settings import settings

router = APIRouter()


class LlmSmokeRequest(BaseModel):
    prompt: str = "ping"
    model: str | None = None


@router.get("/cloud/gpu/health")
async def cloud_gpu_health(_: None = Depends(require_cloud_admin)):
    return {
        "ok": True,
        "endpoints": await gpu_client.health_all(),
    }


@router.post("/cloud/gpu/llm-smoke")
async def cloud_gpu_llm_smoke(
    req: LlmSmokeRequest,
    _: None = Depends(require_cloud_admin),
):
    result = await gpu_client.openai_chat(
        base_url=cloud_settings.gpu_llm_base_url or settings.openai_base_url,
        model=req.model or settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a concise health-check assistant."},
            {"role": "user", "content": req.prompt},
        ],
        timeout_seconds=20,
    )

    return {
        "ok": True,
        "result": result,
    }
