from __future__ import annotations

from aiagent.persona.persona_guard import PersonaGuard
from aiagent.persona.persona_models import PersonaConfig
from aiagent.persona.persona_prompts import PersonaPromptBuilder


class PersonaRuntime:
    def __init__(self,config:PersonaConfig) ->None:
        self.config = config
        self.safe_guard = PersonaGuard()

    @property
    def persona_id(self) -> str:
        return self.config.persona_id
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def alias(self) -> str:
        return self.config.alias
    
    def build_system_prompt(self)->str:
        return PersonaPromptBuilder.build_system_prompt(self.config)
    
    def build_planner_prompt(self)->str:
        return PersonaPromptBuilder.build_planner_prompt(self.config)
    
    def get_default_emotion(self) ->str:
        return self.config.expression.default_emotion
    
    def get_default_motion(self) ->str:
        return self.config.expression.default_motion
    
    def get_default_expression(self) ->str:
        return self.config.expression.default_expression
    
    def get_motion_for_emotion(self, emotion: str) -> str:
        return self.config.expression.motion_bias.get(emotion, self.get_default_motion())

    def get_expression_for_emotion(self, emotion: str) -> str:
        return self.config.expression.emotion_bias.get(emotion, self.get_default_expression())
    
    def get_voice_config(self) ->dict[str,str|float]:
        voice = self.config.voice
        return {
            "provider":voice.provider,
            "ref_audio_path" : voice.ref_audio_path,
            "emo_alpha": voice.emo_alpha,
            "use_emo_text":voice.use_emo_text
        }
    
    def normalize_reply(self,text:str) ->str:
        return self.safe_guard.normalize_reply(text)
    
    def validate_reply(self,text:str) ->list[str]:
        return self.safe_guard.validate_reply(text,self.config)
    
    def summary(self) ->dict:
         return {
            "persona_id": self.config.persona_id,
            "name": self.name,
            "alias": self.alias,
            "default_emotion": self.get_default_emotion(),
            "default_motion": self.get_default_motion(),
            "default_expression": self.get_default_expression(),
            "voice": self.get_voice_config(),
        }