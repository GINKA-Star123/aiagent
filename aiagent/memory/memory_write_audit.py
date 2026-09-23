from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from aiagent.schemas.memory import MemoryWriteAudit
from config.paths import MEMORY_WRITE_AUDIT_FILE

logger = logging.getLogger(__name__)


class MemoryWriteAuditLog:
    def __init__(self, path: str | Path | None = None, tail_limit: int = 200) -> None:
        self.path = Path(path) if path else MEMORY_WRITE_AUDIT_FILE
        self.tail_limit = max(tail_limit, 1)
        self._lock = RLock()

    def append(self, record: MemoryWriteAudit) -> MemoryWriteAudit:
        if not record.created_at:
            record = record.model_copy(update={"created_at": self._utc_now()})

        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n"
                    )
            except Exception as exc:
                # 审计失败不能影响记忆写入本身。
                logger.warning("Failed to append memory write audit: %s", exc)
        return record

    def tail(self, *, user_id: str = "", limit: int = 50) -> list[MemoryWriteAudit]:
        """按倒序返回最近的审计记录，可按 user_id 过滤。"""
        records: list[MemoryWriteAudit] = []
        effective_limit = max(min(int(limit), self.tail_limit), 1)

        for payload in reversed(self._iter_payloads()):
            if user_id and str(payload.get("user_id") or "") != user_id:
                continue
            try:
                records.append(MemoryWriteAudit(**payload))
            except Exception:
                continue
            if len(records) >= effective_limit:
                break
        return records

    def count(self, *, user_id: str = "") -> int:
        total = 0
        for payload in self._iter_payloads():
            if user_id and str(payload.get("user_id") or "") != user_id:
                continue
            total += 1
        return total

    def clear(self) -> int:
        """清空审计日志，返回被清除的条数。"""
        with self._lock:
            if not self.path.exists():
                return 0

            removed = len(self._iter_payloads())
            try:
                self.path.unlink()
            except Exception as exc:
                logger.warning("Failed to clear memory write audit: %s", exc)
                return 0
            return removed

    def _iter_payloads(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []

        with self._lock:
            if not self.path.exists():
                return payloads
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except Exception as exc:
                logger.warning("Failed to read memory write audit: %s", exc)
                return payloads

        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                payloads.append(payload)

        return payloads

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()