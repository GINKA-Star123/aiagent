"""Primary brain entrypoint."""
from typing import TypedDict

from langgraph.graph import END,START,StateGraph

from aiagent.brain.context_builder import ContextBuilder
from aiagent.brain.response_planner import ResponsePlanner
from aiagent.brain.safety_guard import SafetyGuard
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import ResponsePacket
from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService
from aiagent.state.agent_state import AgentRuntimeState,AgenStatus
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState


class BrainGraphState(TypedDict,total=False):
    input_event: InputEvent
    persona: PersonaConfig
    system_prompt: str
    raw_reply: str
    safe_reply:str
    response_packet: ResponsePacket

class AgentCore:
    def __init(
            self,
            llm_service: LLMService,
            context_builder: ContextBuilder,
            response_planner: ResponsePlanner,
            safety_guard: SafetyGuard,
            agent_state: AgentRuntimeState,
            emotion_state: EmotionState,
            conversation_state: ConversationState,
    ) -> None:
        self.llm_service = llm_service
        self.context_builder = context_builder
        self.response_planner = response_planner
        self.safety_guard = safety_guard
        self.agent_state = agent_state
        self.emotion_state = emotion_state
        self.conversation_state = conversation_state
        self.graph = self._bulid_graph()

    def _bulid_graph(self):
        graph = StateGraph(BrainGraphState)

        graph.add_node("build_context",self._build_context_node)
        graph.add_node("call_llm",self._call_llm_node)
        graph.add_node("plan_response",self._plan_response_node)

        graph.add_edge(START,"bulid_context")
        graph.add_edge("bulid_context","call_llm")
        graph.add_edge("call_llm","plan_response")
        graph.add_edge("plan_response",END)

        return graph.compile()
    
    def _build_context_node(self,state:BrainGraphState) ->BrainGraphState:
        pass

    def _call_llm_node(self,state:BrainGraphState) ->BrainGraphState:
        pass

    def _plan_response_node(self,state:BrainGraphState) ->BrainGraphState:
        pass
    