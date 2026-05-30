from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
import time


import httpx

from cloud.config import cloud_settings
from apps.api.metrics_store import metrics_store
from cloud.circuit_breaker import CircuitBreaker


_llm_breaker = CircuitBreaker(name="llm", failure_threshold=3, recovery_seconds=30)
_tts_breaker = CircuitBreaker(name="tts", failure_threshold=3, recovery_seconds=30)
_asr_breaker = CircuitBreaker(name="asr", failure_threshold=3, recovery_seconds=30)

def _breaker_for(name:str) ->CircuitBreaker:
    if name.strip().lower() == "tts":
        return _tts_breaker
    if name.strip().lower() == "llm":
        return _llm_breaker
    return _asr_breaker

@dataclass(frozen=True)
class GpuEndpointHealth:
    name: str
    configured: bool
    ok: bool
    status_code: int | None = None
    error: str = ""

class GpuCircuitOpenError(RuntimeError):
    pass


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _auth_headers() -> dict[str, str]:
    token = os.getenv("GPU_API_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


class GpuServiceClient:
    async def health(self, name: str, base_url: str) -> GpuEndpointHealth:
        if not base_url:
            return GpuEndpointHealth(name=name, configured=False, ok=False)

        async with httpx.AsyncClient(timeout=5) as client:
            for path in ("health", "ready", ""):
                try:
                    response = await client.get(
                        _join_url(base_url, path),
                        headers=_auth_headers(),
                    )
                    if response.status_code < 500:
                        return GpuEndpointHealth(
                            name=name,
                            configured=True,
                            ok=response.status_code < 400,
                            status_code=response.status_code,
                        )
                except Exception as exc:
                    last_error = str(exc)

        return GpuEndpointHealth(
            name=name,
            configured=True,
            ok=False,
            error=last_error,
        )

    async def health_all(self) -> dict[str, Any]:
        llm = await self.health("llm", cloud_settings.gpu_llm_base_url)
        tts = await self.health("tts", cloud_settings.gpu_tts_base_url)
        asr = await self.health("asr", cloud_settings.gpu_asr_base_url)

        return {
            "llm": llm.__dict__,
            "tts": tts.__dict__,
            "asr": asr.__dict__,
            "circuit": self.circuit_snapshot_all(),
        }

    async def openai_chat(
        self,
        *,
        base_url: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 128,
        timeout_seconds: float = 30,
    ) -> dict[str, Any]:
        breaker = _breaker_for("llm")
        if not breaker.allow_request():
            raise GpuCircuitOpenError(
                f"GPU LLM circuit breaker is open. Last error: {breaker._last_error}"
            )
        
        if not base_url:
            raise RuntimeError("GPU LLM base url is not configured.")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    _join_url(base_url, "chat/completions"),
                    headers={
                        "Content-Type": "application/json",
                        **_auth_headers(),
                    },
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
            
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_success()
            metrics_store.record_external_service(
                service="llm",
                ok=True,
                latency_ms=latency_ms,
            )
            return result
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_failure(str(exc))
            metrics_store.record_external_service(
                service="llm",
                ok=False,
                latency_ms=latency_ms,
                error=str(exc),
            )
            raise

    def circuit_snapshot_all(self) ->dict[str,dict]:
        return {
            "llm":_llm_breaker.snapshot().__dict__,
            "tts":_tts_breaker.snapshot().__dict__,
            "asr":_asr_breaker.snapshot().__dict__,
        }

    async def tts(
            self,
            *,
            text:str,
            voice:str = "default",
            emotion:str = "neutral",
            speed:float = 1.0,
            timeout_seconds: float = 120,
    ) ->dict[str,Any]:
        if not cloud_settings.gpu_tts_base_url:
            raise RuntimeError("GPU TTS base url is not configured.")

        breaker = _breaker_for("tts")
        if not breaker.allow_request():
            raise GpuCircuitOpenError(
                f"GPU TTS circuit breaker is open. Last error: {breaker._last_error}"
            )

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    _join_url(cloud_settings.gpu_tts_base_url, "tts"),
                    headers={
                        "Content-Type": "application/json",
                        **_auth_headers(),
                    },
                    json={
                        "text": text,
                        "voice": voice,
                        "emotion": emotion,
                        "speed": speed,
                        "format":"wav",
                    },
                )
                response.raise_for_status()
                result = response.json()
            
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_success()
            metrics_store.record_external_service(
                service="tts",
                ok=True,
                latency_ms=latency_ms,
            )
            return result
        
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_failure(str(exc))
            metrics_store.record_external_service(
                service="tts",
                ok=False,
                latency_ms=latency_ms,
                error=str(exc),
            )
            raise

    async def asr(
        self,
        *,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        timeout_seconds: float = 120,
    ) -> dict[str, Any]:
        if not cloud_settings.gpu_asr_base_url:
            raise RuntimeError("GPU ASR base url is not configured.")

        breaker = _breaker_for("asr")
        if not breaker.allow_request():
            raise GpuCircuitOpenError("GPU ASR circuit is open.")

        started = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    _join_url(cloud_settings.gpu_asr_base_url, "asr"),
                    headers=_auth_headers(),
                    files={
                        "file": (filename, audio_bytes, "audio/wav"),
                    },
                )
                response.raise_for_status()
                result = response.json()

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_success()
            metrics_store.record_external_service(
                service="asr",
                ok=True,
                latency_ms=latency_ms,
            )
            return result

        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            breaker.record_failure(str(exc))
            metrics_store.record_external_service(
                service="asr",
                ok=False,
                latency_ms=latency_ms,
                error=str(exc),
            )
            raise
gpu_client = GpuServiceClient()