from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel,Field

class MemoryCategory(StrEnum):
    IDENTITY  = 'identity'
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    GOAL = "goal"
    HABIT = "habit"
    BOUNDARY = "boundary"
    EVENT = "event"
    TOPIC = "topic"
    OTHER = "other"

class MemoryLayer(StrEnum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    EPISODE = "episode"
    BOUNDARY = "boundary"
    OTHER = "other"

class MemoryImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MemoryWriteDecision(BaseModel):
    should_store : bool =False
    category : MemoryCategory = MemoryCategory.OTHER
    importance : MemoryImportance = MemoryImportance.MEDIUM
    reason:str =""
    memory_hint : str =""
    facts: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    metadata:dict[str,Any] = Field(default_factory=dict)

class MemorySensitivity(StrEnum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"
    BLOCKED = "blocked"

class MemoryGuardResult(BaseModel):
    allowed: bool = True
    sensitivity: MemorySensitivity = MemorySensitivity.NONE
    flags: list[str] = Field(default_factory=list)
    reason: str = ""
    redacted_text: str = ""

class MemoryDedupResult(BaseModel):
    duplicate: bool = False
    reason: str = ""
    matched_memory_id: str = ""
    matched_memory: str = ""
    similarity: float = 0.0

class MemoryStorePlan(BaseModel):
    should_store: bool = False
    status: str = "skipped"
    reason: str = ""
    category: MemoryCategory = MemoryCategory.OTHER
    importance: MemoryImportance = MemoryImportance.MEDIUM
    memory_text: str = ""
    guard: MemoryGuardResult = Field(default_factory=MemoryGuardResult)
    dedup: MemoryDedupResult = Field(default_factory=MemoryDedupResult)
    source: str = "chat_turn"
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

class MemoryRecord(BaseModel):
    id: str = ""
    memory: str = ""
    layer: MemoryLayer = MemoryLayer.OTHER
    category: MemoryCategory = MemoryCategory.OTHER
    importance: MemoryImportance = MemoryImportance.MEDIUM
    score: float | None = None
    sensitivity: MemorySensitivity = MemorySensitivity.NONE
    pinned: bool = False
    pinned_at: str | None = None
    archived: bool = False
    metadata: dict[str,Any] = Field(default_factory=dict)
    relations: list[dict[str,Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

class MemoryLayerBucket(BaseModel):
    layer: MemoryLayer
    count: int = 0
    memories: list[MemoryRecord] = Field(default_factory=list)

class MemorySnapshot(BaseModel):
    user_id: str
    agent_id: str = "yzl"
    total: int = 0
    layers: list[MemoryLayerBucket] = Field(default_factory=list)

class MemoryControlResult(BaseModel):
    ok: bool = True
    status: str = "ok"
    user_id: str = ""
    agent_id: str = "yzl"
    memory_id: str = ""
    layer: MemoryLayer = MemoryLayer.OTHER
    deleted_count:int = 0
    deleted_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    errors: list[dict[str,Any]] = Field(default_factory=list)

class MemoryEditRequest(BaseModel):
    memory: str = Field(min_length=1)
    category: MemoryCategory | None = None
    importance: MemoryImportance | None = None
    layer: MemoryLayer | None = None
    pinned: bool | None = None
    reason: str = ""
    metadata: dict[str,Any] = Field(default_factory=dict)

class MemoryPinRequest(BaseModel):
    reason: str = ""
    pinned: bool = True

class MemoryMergeRequest(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    merged_memory: str = Field(min_length=1)
    category: MemoryCategory | None = None
    importance: MemoryImportance | None = None
    layer: MemoryLayer | None = None
    pinned: bool | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryPreferenceUpdate(BaseModel):
    long_term_enabled: bool = True
    reason: str = ""


class MemoryPreferenceState(BaseModel):
    user_id: str
    agent_id: str = "yzl"
    long_term_enabled: bool = True
    source: str = "default"
    updated_at: str | None = None
    reason: str = ""

class MemoryPromptSource(StrEnum):
    PINNED = "pinned"
    RETRIEVED = "retrieved"

class MemoryPromptItem(BaseModel):
    id: str = ""
    memory: str = ""
    source: MemoryPromptSource = MemoryPromptSource.PINNED
    layer: MemoryLayer = MemoryLayer.OTHER
    category: MemoryCategory = MemoryCategory.OTHER
    importance: MemoryImportance = MemoryImportance.MEDIUM
    score: float | None = None
    pinned: bool = False
    reason: str = ""
    metadata: dict[str,Any] = Field(default_factory=dict)

class MemoryPromptContext(BaseModel):
    text: str = "无长期记忆"
    items: list[MemoryPromptItem] = Field(default_factory=list)
    total_count: int = 0
    pinned_count: int = 0
    retrieved_count: int = 0
    char_count: int = 0
    max_chars: int = 1200
    truncated: bool = False

    layer_counts: dict[str, int] = Field(default_factory=dict)
    selected_ids: list[str] = Field(default_factory=list)
    selected_layers: list[str] = Field(default_factory=list)
    compression_reason: str = ""

class MemoryWriteAudit(BaseModel):
    """一次记忆写入决策的审计记录(JSONL 落盘，可被用户查看)"""

    audit_id: str = ""
    user_id: str =""
    agent_id: str = "yzl"
    session_id: str = ""
    turn_id: str = ""
    status: str = "skipped"
    category: MemoryCategory = MemoryCategory.OTHER
    importance: MemoryImportance = MemoryImportance.MEDIUM
    layer: MemoryLayer = MemoryLayer.OTHER
    reason: str = ""
    source: str = "chat_turn"
    memory_text: str = ""
    sensitivity: MemorySensitivity = MemorySensitivity.NONE
    flags: list[str] = Field(default_factory=list)
    created_at: str = ""