from __future__ import annotations

from pydantic import BaseModel,Field

#State层

class StateGraphInput(BaseModel):
    user_text :str
    user_name :  str = "guest"
    history: list[str] = Field(default_factory=list)
    persona_id : str =""
    persona_name : str = ""
    persona_alias : str =""

class StateInferenceOutput(BaseModel):
    emotion:str
    intent:str
    topic:str
    motion_hint:str
    context_summary:str
    confidence:float = 0.0
    reasoning:str = ""

class StateGraphResult(BaseModel):
    user_text:str
    user_name:str
    emotion:str
    intent:str
    topic:str
    motion_hint:str
    context_summary:str
    confidence:float =0.0
    reasoning:str = ""
    persona_id : str =""
    persona_name:str = ""
    persona_alias : str =""
    metadata:dict[str,str] = Field(default_factory=dict)

#planner 层

class PlannerGraphInput(BaseModel):
    user_text:str
    user_name:str ="guest"

    emotion:str
    intent:str
    topic:str
    motion_hint:str
    context_summary:str
    confidence:float = 0.0
    reasoning:str = ""

    persona_id :str=""
    persona_name:str=""
    persona_alias:str=""

class PlannerInferenceOutput(BaseModel):
    strategy:str 
    should_store_memory:bool = False
    should_speak:bool =True
    target_emotion:str = ""
    target_motion :str = ""
    target_expression:str = ""
    reply_instruction:str = ""
    reasoning:str =""
    confidence:float = 0.0

class PlannerGraphResult(BaseModel):
    user_text:str
    user_name:str

    strategy:str
    should_store_memory:bool
    should_speak:bool
    target_emotion:str
    target_motion:str
    target_expression:str
    reply_instruction:str
    reasoning:str
    confidence:float

    persona_id:str
    persona_name:str
    persona_alias:str
    metadata:dict[str,str] =Field(default_factory=dict)
    