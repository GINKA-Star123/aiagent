"""Build model context from state, memory, and knowledge."""

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.persona import PersonaConfig
from aiagent.state.conversation_state import ConversationState


class ContextBuilder:
    def build_system_prompt(
            self,
            persona : PersonaConfig,
            conversation_state : ConversationState,
            event: InputEvent,
    ) ->str:
        recent_lines : list[str] = []

        for item in conversation_state.recent_inputs[-3:]:
            recent_lines.append(f"观众{item.user_name}:{item.text}")

        for item in conversation_state.recent_outputs[-3:]:
            recent_lines.append(f"主播:{item.packet.reply_text}")

        recent_context = "\n".join(recent_lines ) if recent_lines else "无"

        return (
            f"{persona.to_system_prompt()}\n\n"
            f"最近对话：\n{recent_context}\n\n"
            f"当前发言用户：{event.user_name}\n"
            "请给出一条简短、自然、适合直播的回复。"
        )