from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from aiagent.schemas.memory import MemoryPreferenceState
from config.paths import MEMORY_PREFERENCES_FILE


class MemoryPreferenceStore:
    def __init__(
        self,
        path: str | Path | None = None,
        default_long_term_enabled: bool = True,
    ) -> None:
        self.path = Path(path) if path else MEMORY_PREFERENCES_FILE
        self.default_long_term_enabled = default_long_term_enabled
        self._lock = RLock()

    def get(self, user_id: str, agent_id: str = "yzl") -> MemoryPreferenceState:
        user_id = user_id.strip() or "guest"
        agent_id = agent_id.strip() or "yzl"
        key = self._key(user_id=user_id, agent_id=agent_id)

        with self._lock:
            data = self._load()
            raw = data.get(key)

        if not isinstance(raw, dict):
            return MemoryPreferenceState(
                user_id=user_id,
                agent_id=agent_id,
                long_term_enabled=self.default_long_term_enabled,
                source="default",
            )

        return MemoryPreferenceState(
            user_id=user_id,
            agent_id=agent_id,
            long_term_enabled=bool(raw.get("long_term_enabled", self.default_long_term_enabled)),
            source="user",
            updated_at=str(raw.get("updated_at") or ""),
            reason=str(raw.get("reason") or ""),
        )

    def set(
        self,
        *,
        user_id: str,
        long_term_enabled: bool,
        agent_id: str = "yzl",
        reason: str = "",
    ) -> MemoryPreferenceState:
        user_id = user_id.strip() or "guest"
        agent_id = agent_id.strip() or "yzl"
        key = self._key(user_id=user_id, agent_id=agent_id)

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "user_id": user_id,
            "agent_id": agent_id,
            "long_term_enabled": bool(long_term_enabled),
            "updated_at": now,
            "reason": reason.strip() or "user_memory_preference_update",
        }

        with self._lock:
            data = self._load()
            data[key] = record
            self._save(data)

        return MemoryPreferenceState(
            user_id=user_id,
            agent_id=agent_id,
            long_term_enabled=bool(long_term_enabled),
            source="user",
            updated_at=now,
            reason=record["reason"],
        )

    def is_enabled(self, user_id: str, agent_id: str = "yzl") -> bool:
        return self.get(user_id=user_id, agent_id=agent_id).long_term_enabled

    def _key(self, *, user_id: str, agent_id: str) -> str:
        return f"{agent_id}:{user_id}"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        return data if isinstance(data, dict) else {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)