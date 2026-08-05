from __future__ import annotations

import re

from aiagent.schemas.memory import MemoryGuardResult, MemorySensitivity


class MemorySafetyFilter:
    SECRET_PATTERNS = [
        re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
        re.compile(r"\bapi[_-]?key\s*[:=]\s*[A-Za-z0-9_\-]{8,}", re.IGNORECASE),
        re.compile(r"\b(token|secret|password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
    ]

    CONTACT_PATTERNS = [
        re.compile(r"\b[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}\b"),
        re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ]

    ID_PATTERNS = [
        re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
        re.compile(r"\b\d{15,19}\b"),
    ]

    ADDRESS_PATTERNS = [
        re.compile(r"(我住在|地址是|住址是|家庭住址|公司地址).{4,80}"),
    ]

    BLOCKED_FLAGS = {
        "secret",
        "identity_document",
        "bank_or_card_number",
    }

    def evaluate(self, text: str) -> MemoryGuardResult:
        raw = (text or "").strip()
        if not raw:
            return MemoryGuardResult(
                allowed=False,
                sensitivity=MemorySensitivity.NONE,
                reason="empty_memory_candidate",
                redacted_text="",
            )

        redacted = raw
        flags: list[str] = []

        for pattern in self.SECRET_PATTERNS:
            if pattern.search(redacted):
                flags.append("secret")
                redacted = pattern.sub("[已脱敏密钥]", redacted)

        for pattern in self.CONTACT_PATTERNS:
            if pattern.search(redacted):
                flags.append("contact")
                redacted = pattern.sub("[已脱敏联系方式]", redacted)

        for pattern in self.ID_PATTERNS:
            if pattern.search(redacted):
                flags.append("identity_document")
                redacted = pattern.sub("[已脱敏证件或卡号]", redacted)

        for pattern in self.ADDRESS_PATTERNS:
            if pattern.search(redacted):
                flags.append("precise_address")
                redacted = pattern.sub("[已脱敏地址]", redacted)

        unique_flags = sorted(set(flags))

        if any(flag in self.BLOCKED_FLAGS for flag in unique_flags):
            return MemoryGuardResult(
                allowed=False,
                sensitivity=MemorySensitivity.BLOCKED,
                flags=unique_flags,
                reason="blocked_sensitive_memory",
                redacted_text=redacted.strip(),
            )

        if unique_flags:
            return MemoryGuardResult(
                allowed=True,
                sensitivity=MemorySensitivity.HIGH,
                flags=unique_flags,
                reason="sensitive_memory_redacted",
                redacted_text=redacted.strip(),
            )

        return MemoryGuardResult(
            allowed=True,
            sensitivity=MemorySensitivity.NONE,
            flags=[],
            reason="safe",
            redacted_text=raw,
        )