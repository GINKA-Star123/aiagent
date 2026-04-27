from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StateGraphInput(BaseModel):
    user_text: str
    user_name: str = "guest"
    history: list[str] = Field(default_factory=list)
    persona_id: str = ""
    persona_name: str = ""
    persona_alias: str = ""


class StateInferenceOutput(BaseModel):
    emotion: str
    intent: str
    topic: str
    motion_hint: str
    context_summary: str
    confidence: float = 0.0
    reasoning: str = ""


class StateGraphResult(BaseModel):
    user_text: str
    user_name: str
    emotion: str
    intent: str
    topic: str
    motion_hint: str
    context_summary: str
    confidence: float = 0.0
    reasoning: str = ""
    persona_id: str = ""
    persona_name: str = ""
    persona_alias: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class PlannerGraphInput(BaseModel):
    user_text: str
    user_name: str = "guest"

    emotion: str
    intent: str
    topic: str
    motion_hint: str
    context_summary: str
    confidence: float = 0.0
    reasoning: str = ""

    persona_id: str = ""
    persona_name: str = ""
    persona_alias: str = ""


class PlannerInferenceOutput(BaseModel):
    strategy: str
    should_store_memory: bool = False
    should_speak: bool = True
    target_emotion: str = ""
    target_motion: str = ""
    target_expression: str = ""
    reply_instruction: str = ""
    reasoning: str = ""
    confidence: float = 0.0

    should_retrieve: bool = False
    retrieval_query: str = ""
    retrieval_reason: str = ""


class PlannerGraphResult(BaseModel):
    user_text: str
    user_name: str

    strategy: str
    should_store_memory: bool
    should_speak: bool
    target_emotion: str
    target_motion: str
    target_expression: str
    reply_instruction: str
    reasoning: str
    confidence: float

    should_retrieve: bool = False
    retrieval_query: str = ""
    retrieval_reason: str = ""

    persona_id: str
    persona_name: str
    persona_alias: str
    metadata: dict[str, str] = Field(default_factory=dict)


class RAGGraphInput(BaseModel):
    user_text: str
    state_intent: str = ""
    state_topic: str = ""
    planner_query: str = ""
    planner_should_retrieve: bool = False


class RAGGraphResult(BaseModel):
    query: str = ""
    should_inject: bool = False
    context: list[str] = Field(default_factory=list)
    debug_chunks: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class LLMGraphInput(BaseModel):
    thread_id: str
    user_text: str
    user_name: str = "guest"

    persona_id: str = ""
    persona_name: str = ""
    persona_alias: str = ""

    state_emotion: str = ""
    state_intent: str = ""
    state_topic: str = ""
    state_motion_hint: str = ""
    state_context_summary: str = ""
    state_confidence: float = 0.0
    state_reasoning: str = ""

    strategy: str = "chat"
    should_store_memory: bool = False
    should_speak: bool = True
    target_emotion: str = ""
    target_motion: str = ""
    target_expression: str = ""
    reply_instruction: str = ""
    planner_reasoning: str = ""
    planner_confidence: float = 0.0

    retrieved_context: list[str] = Field(default_factory=list)


class LLMGraphResult(BaseModel):
    thread_id: str
    user_text: str
    user_name: str

    persona_id: str
    persona_name: str
    persona_alias: str

    reply_text: str
    validation_issues: list[str] = Field(default_factory=list)

    should_store_memory: bool = False
    should_speak: bool = True
    target_emotion: str = ""
    target_motion: str = ""
    target_expression: str = ""

    retrieved_context: list[str] = Field(default_factory=list)
    short_term_messages: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
