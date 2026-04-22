from __future__ import annotations

from aiagent.graphs.graph_model import StateInferenceOutput
from aiagent.services.state_llm_service import StateLLMService

class StateAnalyzer:
    def __init__(self, llm_service: StateLLMService) -> None:
        self.llm_service = llm_service

    def infer(self,user_text:str,prompt:str) -> StateInferenceOutput:
        return self.llm_service.infer_state(
            system_prompt=prompt,
            user_text=user_text
        )