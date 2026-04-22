from __future__ import annotations

from pydantic import BaseModel,Field


class PersonaIdentity(BaseModel):
    name:str
    alias:str = ""
    description:str = ""
    background: str = ""
    core_traits: list[str] = Field(default_factory=list)

class PersonaStyle(BaseModel):
    tone:str
    speaking_habits:list[str] = Field(default_factory=list)
    vocabulary_preferences:list[str] = Field(default_factory=list)
    avoid_phrase:list[str] = Field(default_factory=list)
    sentence_length_preferences: str = ""
    rhythm:str = "natural"

class PersonaRules(BaseModel):
    must: list[str] = Field(default_factory=list)
    must_not : list[str] = Field(default_factory=list)
    safety:list[str] = Field(default_factory=list)

class PersonaBehavior(BaseModel):
    comfort_strategy : str =""
    chat_strategy : str = ""
    question_strategy : str = ""
    conflict_strategy : str = ""
    continuation_strategy : str = ""

class PersonaExpression(BaseModel):
    default_emotion: str ="neutral"
    emotion_bias:dict[str,str] = Field(default_factory=dict)
    motion_bias:dict[str,str] = Field(default_factory=dict)
    default_motion: str = "idle"
    default_expression: str = "neutral"

class PersonaVoice(BaseModel):
    provider: str = "indextts2"
    ref_audio_path : str = ""
    emo_alpha:float = 0.6
    use_emo_text:bool = True

class PersonaPrompts(BaseModel):
    system_identity_prefix:str = "你就是如下角色"
    planner_task_prefix:str = "请先决定这一轮应该如何回应，再给出回复约束。"

class PersonaConfig(BaseModel):
    persona_id :str
    version: str = "1.0.0"
    identity: PersonaIdentity
    style: PersonaStyle
    rules: PersonaRules
    behavior: PersonaBehavior
    expression: PersonaExpression = Field(default_factory=PersonaExpression)
    voice: PersonaVoice = Field(default_factory=PersonaVoice)
    prompts: PersonaPrompts = Field(default_factory=PersonaPrompts)

    @property
    def name(self) -> str:
        return self.identity.name
    
    @property
    def alias(self) -> str:
        return self.identity.alias