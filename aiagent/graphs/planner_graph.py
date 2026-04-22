from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.cognition.planner_normalizer import PlannerNormalizer
from aiagent.cognition.planner_prompt import PlannerPromptBuilder
from aiagent.cognition.planner_reply import ReplyPlanner
from aiagent.graphs.graph_model import PlannerGraphInput, PlannerInferenceOutput,PlannerGraphResult
from aiagent.persona.persona_runtime import PersonaRuntime  

class PlannerGraphState(TypedDict,total=False):
    input:PlannerGraphInput
    persona_runtime:PersonaRuntime
    prompt:str
    output:PlannerInferenceOutput
    normalized_output:PlannerInferenceOutput
    metadata:dict[str,str]

class PlannerRunner:
    def __init__(
            self,
            planner_reply:ReplyPlanner,
            planner_normalizer:PlannerNormalizer|None =None
    ) -> None:
        self.planner_reply = planner_reply
        self.planner_normalizer = planner_normalizer or PlannerNormalizer()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(PlannerGraphState)

        graph.add_node("build_prompt",self._build_prompt_node)
        graph.add_node("analyze_plan",self._analyze_plan_node)
        graph.add_node("normalize_plan",self._normalize_plan_node)

        graph.add_edge(START,"build_prompt")
        graph.add_edge("build_prompt","analyze_plan")
        graph.add_edge("analyze_plan","normalize_plan")
        graph.add_edge("normalize_plan",END)

        return graph.compile()
    
    def _build_prompt_node(self,state:PlannerGraphState) -> PlannerGraphState:
        graph_input = state["input"] # type: ignore
        persona_runtime = state["persona_runtime"] # type: ignore

        prompt = PlannerPromptBuilder.build(
            user_text=graph_input.user_text,
            user_name=graph_input.user_name,
            emotion=graph_input.emotion,
            intent=graph_input.intent,
            topic=graph_input.topic,
            motion_hint=graph_input.motion_hint,
            context_summary=graph_input.context_summary,
            persona_runtime=persona_runtime,
        )

        return {
            "prompt":prompt,
            "metadata":{"planner_prompt":"built"}
        }
    
    def _analyze_plan_node(self, state: PlannerGraphState) -> PlannerGraphState:
        graph_input = state["input"] # type: ignore
        prompt = state["prompt"] # type: ignore

        output = self.planner_reply.infer(
            prompt=prompt,
            user_text=graph_input.user_text,
        )

        metadata = dict(state.get("metadata", {}))
        metadata["planner_inference"] = "model"

        return {
            "output": output,
            "metadata": metadata,
        }

    def _normalize_plan_node(self, state: PlannerGraphState) -> PlannerGraphState:
        normalized = self.planner_normalizer.normalize(state["output"]) # type: ignore
        metadata = dict(state.get("metadata", {})) 
        metadata["planner_normalization"] = "hybrid"

        return {
            "normalized_output": normalized,
            "metadata": metadata,
        }

    def run(
        self,
        user_text: str,
        user_name: str,
        state_result,
        persona_runtime: PersonaRuntime,
    ) -> PlannerGraphResult:
        graph_input = PlannerGraphInput(
            user_text=user_text,
            user_name=user_name,
            emotion=state_result.emotion,
            intent=state_result.intent,
            topic=state_result.topic,
            motion_hint=state_result.motion_hint,
            context_summary=state_result.context_summary,
            confidence=state_result.confidence,
            reasoning=state_result.reasoning,
            persona_id=persona_runtime.persona_id,
            persona_name=persona_runtime.name,
            persona_alias=persona_runtime.alias,
        )

        result = self.graph.invoke(
            {
                "input": graph_input,
                "persona_runtime": persona_runtime,
            }
        )

        normalized = result["normalized_output"]

        return PlannerGraphResult(
            user_text=graph_input.user_text,
            user_name=graph_input.user_name,
            strategy=normalized.strategy,
            should_store_memory=normalized.should_store_memory,
            should_speak=normalized.should_speak,
            target_emotion=normalized.target_emotion,
            target_motion=normalized.target_motion,
            target_expression=normalized.target_expression,
            reply_instruction=normalized.reply_instruction,
            reasoning=normalized.reasoning,
            confidence=normalized.confidence,
            persona_id=graph_input.persona_id,
            persona_name=graph_input.persona_name,
            persona_alias=graph_input.persona_alias,
            metadata=result.get("metadata", {}),
        )