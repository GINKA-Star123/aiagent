from __future__ import annotations

from aiagent.graphs.graph_model import PlannerInferenceOutput
from aiagent.services.planner_llm_service import PlannerLLMService

class ReplyPlanner:
    def __init__(self,llm_service: PlannerLLMService) -> None:
        self.llm_service = llm_service

    def infer(self,prompt:str,user_text:str) ->PlannerInferenceOutput:
        return self.llm_service.infer_plan(
            system_prompt=prompt,
            user_text=user_text
    )