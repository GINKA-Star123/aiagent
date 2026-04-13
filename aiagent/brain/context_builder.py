"""Build model context from state, memory, and knowledge."""
from aiagent.memory.short_term_memory import ShortTermMemory
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.persona import PersonaConfig
from aiagent.state.conversation_state import ConversationState


class ContextBuilder:
    def __init__(
            self,
            short_term_memory:ShortTermMemory,
            user_profile_memory:UserProfileMemory
    )-> None:
        self.short_term_memory = short_term_memory
        self.user_profile_memory = user_profile_memory

    def build_system_prompt(
        self,
        persona: PersonaConfig,
        conversation_state: ConversationState,
        event: InputEvent,
    ) -> str:
        short_memory_lines = self.short_term_memory.recent_dialogue_lines(limit=6)
        short_memory_text = "\n".join(short_memory_lines) if short_memory_lines else "无"

        user_profile_text = self.user_profile_memory.summarize_for_prompt(
            user_id=event.user_id,
            limit=5,
        )

        return (
            f"{persona.to_system_prompt()}\n\n"
            f"最近对话：\n{short_memory_text}\n\n"
            f"该用户的画像记忆：\n{user_profile_text}\n\n"
            f"当前发言用户：{event.user_name}\n"
            f"当前输入来源：{event.source}\n"
            "请给出一条简短、自然、适合直播的回复。"
        )