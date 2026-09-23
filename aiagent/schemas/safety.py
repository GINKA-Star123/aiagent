from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel,Field


class RiskLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskCategory(StrEnum):
    SELF_HARM = "self_harm"
    VIOLENCE = "violence"
    ILLEGAL = "illegal"
    PRIVACY = "privacy"
    JAILBREAK = "jailbreak"
    PROFESSIONAL_ADVICE = "professional_advice"
    OTHER = "other"


class RiskSignal(BaseModel):
    """一条命中的风险规则。matched_text 已打码，不含完整原文。"""

    rule_id: str = ""
    category: RiskCategory = RiskCategory.OTHER
    level: RiskLevel = RiskLevel.LOW
    matched_text: str = ""
    note: str = ""


class RequestRiskAssessment(BaseModel):
    level: RiskLevel = RiskLevel.NONE
    require_refusal: bool = False
    categories: list[RiskCategory] = Field(default_factory=list)
    signals: list[RiskSignal] = Field(default_factory=list)
    reason_code: str = "no_signal"
    reason: str = ""
    checked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    text_length: int = 0


class SafeRefusal(BaseModel):
    """系统级拒绝的完整输出：文案 + 表达层 + 记忆策略。"""

    text: str = ""
    emotion: str = "calm"
    motion: str = "serious_still"
    expression: str = "serious"
    reason_code: str = ""
    should_store_memory: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
