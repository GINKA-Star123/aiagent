from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.brain.context_builder import ContextBuilder
from aiagent.brain.response_planner import ResponsePlanner
from aiagent.brain.safety_guard import SafetyGuard
from aiagent.persona.style_rewriter import StyleRewriter
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import ResponsePacket
from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService
from aiagent.state.agent_state import AgentRuntimeState, AgentStatus
from aiagent.state.conversation_state import ConversationState
from aiagent.state.emotion_state import EmotionState


class BrainGraphState(TypedDict, total=False):
    input_event: InputEvent
    persona: PersonaConfig
    system_prompt: str
    raw_reply: str
    safe_reply: str
    styled_reply: str
    response_packet: ResponsePacket


class AgentCore:
    def __init__(
        self,
        llm_service: LLMService,
        context_builder: ContextBuilder,
        response_planner: ResponsePlanner,
        safety_guard: SafetyGuard,
        style_rewriter: StyleRewriter,
        agent_state: AgentRuntimeState,
        conversation_state: ConversationState,
        emotion_state: EmotionState,
    ) -> None:
        self.llm_service = llm_service
        self.context_builder = context_builder
        self.response_planner = response_planner
        self.safety_guard = safety_guard
        self.style_rewriter = style_rewriter
        self.agent_state = agent_state
        self.conversation_state = conversation_state
        self.emotion_state = emotion_state
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(BrainGraphState)

        graph.add_node("build_context", self._build_context_node)
        graph.add_node("call_llm", self._call_llm_node)
        graph.add_node("rewrite_style", self._rewrite_style_node)
        graph.add_node("plan_response", self._plan_response_node)

        graph.add_edge(START, "build_context")
        graph.add_edge("build_context", "call_llm")
        graph.add_edge("call_llm", "rewrite_style")
        graph.add_edge("rewrite_style", "plan_response")
        graph.add_edge("plan_response", END)

        return graph.compile()

    def _build_context_node(self, state: BrainGraphState) -> BrainGraphState:
        event = state["input_event"] # type: ignore
        persona = state["persona"] # type: ignore

        system_prompt = self.context_builder.build_system_prompt(
            persona=persona,
            conversation_state=self.conversation_state,
            event=event,
        )
        return {"system_prompt": system_prompt}

    def _call_llm_node(self, state: BrainGraphState) -> BrainGraphState:
        event = state["input_event"] # type: ignore
        prompt = state["system_prompt"] # type: ignore

        raw_reply = self.llm_service.generate_reply(
            system_prompt=prompt,
            user_text=event.text,
        )
        safe_reply = self.safety_guard.filter_text(raw_reply)
        return {
            "raw_reply": raw_reply,
            "safe_reply": safe_reply,
        }

    def _rewrite_style_node(self, state: BrainGraphState) -> BrainGraphState:
        persona = state["persona"] # type: ignore
        safe_reply = state["safe_reply"] # type: ignore

        styled_reply = self.style_rewriter.rewrite(
            base_reply=safe_reply,
            persona=persona,
        )
        styled_reply = self.safety_guard.filter_text(styled_reply)

        return {"styled_reply": styled_reply}

    def _plan_response_node(self, state: BrainGraphState) -> BrainGraphState:
        packet = self.response_planner.plan(
            final_reply_text=state["styled_reply"], # type: ignore
            base_reply_text=state["safe_reply"], # type: ignore
        )
        return {"response_packet": packet}

    def process(self, event: InputEvent, persona: PersonaConfig) -> ResponsePacket:
        self.agent_state.status = AgentStatus.THINKING
        self.agent_state.last_input_id = event.event_id

        result = self.graph.invoke(
            {
                "input_event": event,
                "persona": persona,
            }
        )

        packet = result["response_packet"]
        self.emotion_state.current_emotion = packet.emotion
        self.agent_state.status = AgentStatus.IDLE
        return packet
