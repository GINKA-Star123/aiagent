from __future__ import annotations

from typing import Any,TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.cognition.state_analyzer import StateAnalyzer
from aiagent.cognition.state_normalizer import StateNormalizer
from aiagent.cognition.state_prompt import StateInferencePromptBuilder
from aiagent.graphs.graph_model import StateGraphInput, StateInferenceOutput,StateGraphResult
from aiagent.persona.persona_runtime import PersonaRuntime

class StateGraphState(TypedDict,total=False):
    input:StateGraphInput
    persona_runtime:PersonaRuntime
    prompt:str
    output:StateInferenceOutput
    normalized_output:StateInferenceOutput
    metadata:dict[str,str]

class StateRunner:
    def __init__(
        self,
        state_analyzer:StateAnalyzer,
        state_normalizer:StateNormalizer |None = None
    )->None:
        self.state_analyzer =state_analyzer
        self.state_normalizer = state_normalizer or StateNormalizer()
        self.graph=self._build_graph()

    def _build_graph(self):
        graph = StateGraph(StateGraphState)

        graph.add_node("build_prompt",self._build_prompt_node)
        graph.add_node("analyze_state",self._analyze_state_node)
        graph.add_node("normalize_state",self._normalize_state_node)

        graph.add_edge(START,"build_prompt")
        graph.add_edge("build_prompt","analyze_state")
        graph.add_edge("analyze_state","normalize_state")
        graph.add_edge("normalize_state",END)

        return graph.compile()
    
    def _build_prompt_node(self,state:StateGraphState) -> StateGraphState:
        graph_input = state["input"] # type: ignore
        persona_runtime = state["persona_runtime"] # type: ignore
        
        prompt = StateInferencePromptBuilder.build(
            user_text = graph_input.user_text, # type: ignore
            user_name=graph_input.user_name, # type: ignore
            history=graph_input.history, # type: ignore
            persona_runtime=persona_runtime
        )

        return {
            "prompt":prompt,
            "metadata":{"state_prompt":"built"}
        }

    def _analyze_state_node(self,state:StateGraphState) -> StateGraphState:
        graph_input = state["input"] # type: ignore
        prompt = state["prompt"] # type: ignore

        output = self.state_analyzer.infer(
            prompt=prompt,
            user_text=graph_input.user_text # type: ignore
        )

        metadata = dict(state.get("metadata",{}))
        metadata["state_inference"] = "model"

        return {
            "output":output,
            "metadata":metadata
        }    
    
    def _normalize_state_node(self,state:StateGraphState) -> StateGraphState:
        normalized = self.state_normalizer.normalize(state["output"]) #type:ignore
        metadata = dict(state.get("metadata",{}))
        metadata["state_normalization"] = "hybrid"
        return {
            "normalized_output":normalized,
            "metadata":metadata
        }
    
    def run(
        self,
        user_text:str,
        user_name:str,
        persona_runtime:PersonaRuntime,
        history:list[str] |None = None
    ) ->  StateGraphResult:
        graph_input = StateGraphInput(
            user_text=user_text,
            user_name=user_name,
            history=history or [],
            persona_id=persona_runtime.persona_id,
            persona_name=persona_runtime.name,
            persona_alias=persona_runtime.alias,
        )

        result = self.graph.invoke(
            {
                "input":graph_input,
                "persona_runtime":persona_runtime,
            }
        )

        normalized = result["normalized_output"]

        return StateGraphResult(
            user_text=graph_input.user_text,
            user_name=graph_input.user_name,
            emotion=normalized.emotion,
            intent=normalized.intent,
            topic=normalized.topic,
            motion_hint=normalized.motion_hint,
            context_summary=normalized.context_summary,
            confidence=normalized.confidence,
            reasoning=normalized.reasoning,
            persona_id=graph_input.persona_id,
            persona_name=graph_input.persona_name,
            persona_alias=graph_input.persona_alias,
            metadata=result.get("metadata", {}),
        )