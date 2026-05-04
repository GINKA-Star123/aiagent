from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

NO_LONG_TERM_MEMORY_TEXT = "无长期记忆。"

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

class VisionSafetyResult(BaseModel):
    has_sentitive_content: bool = False
    risk_level: str =  "none"
    reason:str = ""

class VisionMemoryCandidate(BaseModel):
    should_consider: bool = False
    reason: str = ""

class VisionLive2DSuggestion(BaseModel):
    suggested_emotion : str = "neutral"
    suggested_expression : str ="neutral"
    suggested_motion : str = "idle"
    suggested_background : str = "room_default"

class CharacterCandidate(BaseModel):
    character_id : str
    name:str
    aliases:list[str] = Field(default_factory=list)
    confidence:float = 0.0
    score:float = 0.0
    evidence:list[str] = Field(default_factory=list)
    metadata: dict[str,Any] = Field(default_factory=dict)

class DailySceneResult(BaseModel):
    scene_type : str ="unknown"
    location_hint : str = ""
    activity: str = ""
    food:list[str] = Field(default_factory=list)
    landmarks:list[str] = Field(default_factory=list)
    objects:list[str] = Field(default_factory=list)
    people_count:int | None =None
    time_hint : str =""
    weather_hint : str = ""
    notable_details:list[str] = Field(default_factory=list)

class VisionAnalyzeResult(BaseModel):
    image_id:str
    image_path:str
    image_url :str = ""
    width:int = 0
    height:int = 0
    format:str = ""

    image_type:str ="unknown"
    user_intent:str = "unknown"

    summary:str = ""
    objects : list[str] = Field(default_factory=list)
    scene:str = ""
    daily_scene:DailySceneResult = Field(default_factory=DailySceneResult)
    ocr_text : list[str] = Field(default_factory=list)
    mood:str = ""

    recognized_characters :list[CharacterCandidate] = Field(default_factory=list)
    is_confident:bool = False
    confidence:float = 0.0

    safety:VisionSafetyResult = Field(default_factory=VisionSafetyResult)
    memory:VisionMemoryCandidate = Field(default_factory=VisionMemoryCandidate)
    live2d:VisionLive2DSuggestion = Field(default_factory=VisionLive2DSuggestion)

    raw_model_output : str =""
    metadata:dict[str,Any] = Field(default_factory=dict)

    

class LLMGraphInput(BaseModel):
    thread_id: str
    user_text: str
    user_name: str = "guest"
    internal_context: str = ""

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
    long_term_memory_context: str = NO_LONG_TERM_MEMORY_TEXT

class LLMGraphResult(BaseModel):
    thread_id: str
    user_text: str
    user_name: str
    internal_context: str = ""

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
    long_term_memory_context: str = NO_LONG_TERM_MEMORY_TEXT
    
    metadata: dict[str, str] = Field(default_factory=dict)
