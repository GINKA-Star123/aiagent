from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from aiagent.schemas.voice import (
    VoiceCallStatus,
    VoiceRealtimeCall,
    VoiceTurnPhase,
)
from cloud.config import cloud_settings
from cloud.redis_client import get_redis_client


logger = logging.getLogger("aiagent.voice.call_store")


class VoiceCallStoreError(RuntimeError):
    stage = "voice_call_store"


class VoiceCallStoreUnavailableError(VoiceCallStoreError):
    stage = "voice_call_store_unavailable"


class VoiceCallStoreConflictError(VoiceCallStoreError):
    stage = "voice_call_store_conflict"


CallMutator = Callable[[VoiceRealtimeCall], None]


class VoiceRealtimeCallStore:
    """
    Voice realtime 通话状态仓储。

    provider 支持：

    - memory：只使用当前 Python 进程内存。
    - redis：强制使用 Redis。
    - auto：配置 REDIS_URL 时使用 Redis，否则使用 memory。

    Redis 模式使用 JSON 保存完整 VoiceRealtimeCall，
    使用 Redis 分布式锁保护所有读改写操作。
    """

    def __init__(
        self,
        *,
        prefix: str,
        provider: str = "auto",
        ttl_seconds: int = 1800,
        ended_ttl_seconds: int = 300,
        lock_ttl_seconds: int = 15,
        lock_wait_seconds: float = 2.0,
        fail_open: bool = False,
    ) -> None:
        normalized_provider = provider.strip().lower()

        if normalized_provider not in {"auto", "memory", "redis"}:
            raise ValueError(
                "voice call store provider must be auto, memory or redis"
            )

        self.prefix = prefix.rstrip(":")
        self.provider = normalized_provider
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.ended_ttl_seconds = max(60, int(ended_ttl_seconds))
        self.lock_ttl_seconds = max(3, int(lock_ttl_seconds))
        self.lock_wait_seconds = max(0.1, float(lock_wait_seconds))
        self.fail_open = bool(fail_open)

        self._calls: dict[str, tuple[VoiceRealtimeCall, float]] = {}
        self._memory_lock = asyncio.Lock()

        self._last_backend = self.effective_provider
        self._last_error = ""

    @property
    def effective_provider(self) -> str:
        if self.provider == "memory":
            return "memory"

        if self.provider == "redis":
            return "redis"

        return "redis" if cloud_settings.redis_url else "memory"

    def _call_key(self, call_id: str) -> str:
        return f"{self.prefix}:voice:call:{call_id}"

    def _lock_key(self, call_id: str) -> str:
        return f"{self.prefix}:voice:call-lock:{call_id}"

    def _ttl_for(self, call: VoiceRealtimeCall) -> int:
        if call.status == VoiceCallStatus.ENDED:
            return self.ended_ttl_seconds
        return self.ttl_seconds

    async def start(
        self,
        *,
        user_id: str,
        username: str,
    ) -> VoiceRealtimeCall:
        call = VoiceRealtimeCall(
            call_id=uuid.uuid4().hex,
            user_id=user_id or "guest",
            username=username or "guest",
        )

        await self.save(call)
        return call.model_copy(deep=True)

    async def get(
        self,
        call_id: str,
        *,
        touch: bool = True,
    ) -> VoiceRealtimeCall | None:
        if touch:
            return await self._mutate(
                call_id,
                lambda call: call.touch(),
            )

        return await self._load(call_id)

    async def save(
        self,
        call: VoiceRealtimeCall,
    ) -> VoiceRealtimeCall:
        redis = await self._resolve_redis()

        if redis is None:
            return await self._memory_save(call)

        try:
            await redis.set(
                self._call_key(call.call_id),
                call.model_dump_json(),
                ex=self._ttl_for(call),
            )
            await self._memory_save(call)
            self._last_backend = "redis"
            self._last_error = ""
            return call.model_copy(deep=True)
        except Exception as exc:
            return await self._handle_redis_save_failure(call, exc)

    async def mark_phase(
        self,
        call_id: str,
        phase: VoiceTurnPhase,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        def mutate(call: VoiceRealtimeCall) -> None:
            call.mark_phase(phase, **metadata)

        return await self._mutate(call_id, mutate)

    async def next_turn(
        self,
        call_id: str,
    ) -> VoiceRealtimeCall | None:
        def mutate(call: VoiceRealtimeCall) -> None:
            call.turn_count += 1
            call.last_turn_id = f"{call.call_id}:{call.turn_count}"
            call.last_error = ""
            call.last_transcript = ""
            call.last_output_id = ""
            call.last_audio_path = ""
            call.last_audio_url = ""
            call.last_interrupt_reason = ""

            call.update_metadata(
                voice_realtime_call_id=call.call_id,
                voice_realtime_turn_id=call.last_turn_id,
                voice_realtime_turn_count=call.turn_count,
            )
            call.mark_phase(VoiceTurnPhase.UPLOADED)

        return await self._mutate(call_id, mutate)

    async def mark_transcript(
        self,
        call_id: str,
        transcript: str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        normalized = transcript.strip()

        def mutate(call: VoiceRealtimeCall) -> None:
            call.last_transcript = normalized

            phase = (
                VoiceTurnPhase.THINKING
                if normalized
                else VoiceTurnPhase.EMPTY_TURN
            )

            call.mark_phase(
                phase,
                **{
                    **metadata,
                    "voice_asr_text_chars": len(normalized),
                    "voice_asr_empty": not bool(normalized),
                },
            )

        return await self._mutate(call_id, mutate)

    async def mark_output(
        self,
        call_id: str,
        *,
        output_id: str,
        audio_path: str = "",
        audio_url: str = "",
        has_audio: bool | None = None,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        output_has_audio = (
            has_audio
            if has_audio is not None
            else bool(audio_path or audio_url)
        )

        def mutate(call: VoiceRealtimeCall) -> None:
            call.last_output_id = output_id
            call.last_audio_path = audio_path or ""
            call.last_audio_url = audio_url or ""

            phase = (
                VoiceTurnPhase.SPEAKING
                if output_has_audio
                else VoiceTurnPhase.COMPLETED
            )

            call.mark_phase(
                phase,
                **{
                    **metadata,
                    "voice_output_id": output_id,
                    "voice_audio_path": audio_path or "",
                    "voice_audio_url": audio_url or "",
                    "voice_output_has_audio": output_has_audio,
                },
            )

        return await self._mutate(call_id, mutate)

    async def interrupt(
        self,
        call_id: str,
        reason: str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        interrupt_reason = reason or "voice_realtime_interrupt"

        def mutate(call: VoiceRealtimeCall) -> None:
            call.interrupt_count += 1
            call.last_interrupt_reason = interrupt_reason
            call.mark_phase(
                VoiceTurnPhase.INTERRUPTED,
                **{
                    **metadata,
                    "voice_interrupt_reason": interrupt_reason,
                    "voice_interrupt_count": call.interrupt_count,
                },
            )

        return await self._mutate(call_id, mutate)

    async def fail(
        self,
        call_id: str,
        error: Exception | str,
        **metadata: Any,
    ) -> VoiceRealtimeCall | None:
        error_text = str(error)

        def mutate(call: VoiceRealtimeCall) -> None:
            call.status = VoiceCallStatus.ERROR
            call.last_error = error_text
            call.mark_phase(
                VoiceTurnPhase.FAILED,
                **{
                    **metadata,
                    "voice_last_error": error_text,
                },
            )

        return await self._mutate(call_id, mutate)

    async def end(
        self,
        call_id: str,
    ) -> VoiceRealtimeCall | None:
        def mutate(call: VoiceRealtimeCall) -> None:
            if call.status == VoiceCallStatus.ENDED:
                return

            call.status = VoiceCallStatus.ENDED
            call.ended_at = datetime.now().isoformat(
                timespec="seconds"
            )
            call.mark_phase(
                VoiceTurnPhase.COMPLETED,
                voice_call_ended=True,
            )

        return await self._mutate(call_id, mutate)

    async def backend_status(self) -> dict[str, Any]:
        effective = self.effective_provider
        redis_configured = bool(cloud_settings.redis_url)

        if effective == "memory":
            return {
                "ok": True,
                "configured_provider": self.provider,
                "effective_provider": "memory",
                "redis_configured": redis_configured,
                "fail_open": self.fail_open,
                "last_backend": self._last_backend,
                "last_error": self._last_error,
            }

        redis = await get_redis_client()
        available = redis is not None

        return {
            "ok": available or self.fail_open,
            "configured_provider": self.provider,
            "effective_provider": (
                "redis"
                if available
                else "memory_fallback"
                if self.fail_open
                else "redis"
            ),
            "redis_configured": redis_configured,
            "redis_available": available,
            "fail_open": self.fail_open,
            "last_backend": self._last_backend,
            "last_error": self._last_error,
        }

    async def clear_for_tests(self) -> None:
        async with self._memory_lock:
            self._calls.clear()

    async def _load(
        self,
        call_id: str,
    ) -> VoiceRealtimeCall | None:
        redis = await self._resolve_redis()

        if redis is None:
            return await self._memory_load(call_id)

        try:
            raw = await redis.get(self._call_key(call_id))
            if not raw:
                return None

            call = VoiceRealtimeCall.model_validate_json(raw)
            self._last_backend = "redis"
            self._last_error = ""
            return call
        except Exception as exc:
            return await self._handle_redis_load_failure(
                call_id,
                exc,
            )

    async def _mutate(
        self,
        call_id: str,
        mutator: CallMutator,
    ) -> VoiceRealtimeCall | None:
        redis = await self._resolve_redis()

        if redis is None:
            return await self._memory_mutate(
                call_id,
                mutator,
            )

        try:
            return await self._redis_mutate(
                redis,
                call_id,
                mutator,
            )
        except VoiceCallStoreError:
            raise
        except Exception as exc:
            self._last_error = str(exc)

            if not self.fail_open:
                raise VoiceCallStoreUnavailableError(
                    "Redis voice call store is unavailable"
                ) from exc

            logger.warning(
                "Redis voice call mutation failed; using memory fallback: %s",
                exc,
            )
            self._last_backend = "memory_fallback"
            return await self._memory_mutate(
                call_id,
                mutator,
            )

    async def _redis_mutate(
        self,
        redis: Any,
        call_id: str,
        mutator: CallMutator,
    ) -> VoiceRealtimeCall | None:
        lock_key = self._lock_key(call_id)
        token = uuid.uuid4().hex
        deadline = time.monotonic() + self.lock_wait_seconds
        acquired = False

        while time.monotonic() < deadline:
            acquired = bool(
                await redis.set(
                    lock_key,
                    token,
                    nx=True,
                    ex=self.lock_ttl_seconds,
                )
            )

            if acquired:
                break

            await asyncio.sleep(0.05)

        if not acquired:
            raise VoiceCallStoreConflictError(
                "voice call state is busy, retry later"
            )

        try:
            raw = await redis.get(self._call_key(call_id))
            if not raw:
                return None

            call = VoiceRealtimeCall.model_validate_json(raw)
            mutator(call)

            await redis.set(
                self._call_key(call_id),
                call.model_dump_json(),
                ex=self._ttl_for(call),
            )

            await self._memory_save(call)
            self._last_backend = "redis"
            self._last_error = ""

            return call.model_copy(deep=True)
        finally:
            release_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            end
            return 0
            """
            try:
                await redis.eval(
                    release_script,
                    1,
                    lock_key,
                    token,
                )
            except Exception as exc:
                logger.warning(
                    "Redis voice call lock release failed: %s",
                    exc,
                )

    async def _resolve_redis(self) -> Any | None:
        if self.effective_provider == "memory":
            self._last_backend = "memory"
            return None

        redis = await get_redis_client()

        if redis is not None:
            return redis

        self._last_error = (
            "Redis is not configured or unavailable"
        )

        if self.fail_open:
            self._last_backend = "memory_fallback"
            return None

        raise VoiceCallStoreUnavailableError(
            "Redis voice call store is required but unavailable"
        )

    async def _memory_save(
        self,
        call: VoiceRealtimeCall,
    ) -> VoiceRealtimeCall:
        expires_at = time.monotonic() + self._ttl_for(call)

        async with self._memory_lock:
            self._cleanup_memory_locked()
            self._calls[call.call_id] = (
                call.model_copy(deep=True),
                expires_at,
            )

        if self.effective_provider == "memory":
            self._last_backend = "memory"

        return call.model_copy(deep=True)

    async def _memory_load(
        self,
        call_id: str,
    ) -> VoiceRealtimeCall | None:
        async with self._memory_lock:
            self._cleanup_memory_locked()
            item = self._calls.get(call_id)

            if item is None:
                return None

            return item[0].model_copy(deep=True)

    async def _memory_mutate(
        self,
        call_id: str,
        mutator: CallMutator,
    ) -> VoiceRealtimeCall | None:
        async with self._memory_lock:
            self._cleanup_memory_locked()
            item = self._calls.get(call_id)

            if item is None:
                return None

            call = item[0].model_copy(deep=True)
            mutator(call)

            self._calls[call_id] = (
                call.model_copy(deep=True),
                time.monotonic() + self._ttl_for(call),
            )

            return call.model_copy(deep=True)

    async def _handle_redis_save_failure(
        self,
        call: VoiceRealtimeCall,
        exc: Exception,
    ) -> VoiceRealtimeCall:
        self._last_error = str(exc)

        if not self.fail_open:
            raise VoiceCallStoreUnavailableError(
                "Redis voice call store write failed"
            ) from exc

        logger.warning(
            "Redis voice call save failed; using memory fallback: %s",
            exc,
        )
        self._last_backend = "memory_fallback"
        return await self._memory_save(call)

    async def _handle_redis_load_failure(
        self,
        call_id: str,
        exc: Exception,
    ) -> VoiceRealtimeCall | None:
        self._last_error = str(exc)

        if not self.fail_open:
            raise VoiceCallStoreUnavailableError(
                "Redis voice call store read failed"
            ) from exc

        logger.warning(
            "Redis voice call load failed; using memory fallback: %s",
            exc,
        )
        self._last_backend = "memory_fallback"
        return await self._memory_load(call_id)

    def _cleanup_memory_locked(self) -> None:
        now = time.monotonic()

        expired = [
            call_id
            for call_id, (_, expires_at) in self._calls.items()
            if expires_at <= now
        ]

        for call_id in expired:
            self._calls.pop(call_id, None)


voice_call_store = VoiceRealtimeCallStore(
    prefix=cloud_settings.redis_prefix,
    provider=cloud_settings.voice_call_store_provider,
    ttl_seconds=cloud_settings.voice_call_ttl_seconds,
    ended_ttl_seconds=cloud_settings.voice_call_ended_ttl_seconds,
    lock_ttl_seconds=cloud_settings.voice_call_lock_ttl_seconds,
    lock_wait_seconds=cloud_settings.voice_call_lock_wait_seconds,
    fail_open=cloud_settings.voice_call_store_fail_open,
)