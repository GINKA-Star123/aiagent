"""Build model context from state, memory, and knowledge."""

from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.memory.long_term_memory import LongTermMemory
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.persona import PersonaConfig
from aiagent.services.llm_service import LLMService
from aiagent.state.conversation_state import ConversationState


class ContextBuilder:
    def __init__(
        self,
        llm_service: LLMService,
        user_profile_memory: UserProfileMemory,
        rag_pipeline: RAGPipeline,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.llm_service = llm_service
        self.user_profile_memory = user_profile_memory
        self.rag_pipeline = rag_pipeline
        self.long_term_memory = long_term_memory

    def build_system_prompt(
        self,
        persona: PersonaConfig,
        conversation_state: ConversationState,
        event: InputEvent,
    ) -> str:
        short_memory_lines = self.llm_service.recent_dialogue_lines(
            thread_id=event.user_id,
            limit=6,
        )
        short_memory_text = "\n".join(short_memory_lines) if short_memory_lines else "暂无最近对话摘要。"

        user_profile_text = self.user_profile_memory.summarize_for_prompt(
            user_id=event.user_id,
            limit=5,
        )

        long_term_text = self.long_term_memory.summarize_for_prompt(
            user_id=event.user_id,
            limit=5,
        )

        knowledge_text = self.rag_pipeline.format_for_prompt(
            query=event.text,
            top_k=4,
        )

        dialogue_state_lines = [
            f"当前话题: {conversation_state.current_topic}",
            f"最近关键词: {', '.join(conversation_state.recent_keywords) if conversation_state.recent_keywords else '无'}",
            f"用户当前诉求: {conversation_state.last_user_goal or '未识别'}",
            f"用户情绪倾向: {conversation_state.last_user_emotion_hint}",
            f"上一轮回复策略: {conversation_state.last_strategy or '无'}",
            f"本轮是否切换话题: {'是' if conversation_state.last_topic_shift else '否'}",
        ]
        dialogue_state_text = "\n".join(dialogue_state_lines)

        return (
            f"{persona.to_system_prompt()}\n\n"
            f"最近对话摘要:\n{short_memory_text}\n\n"
            f"对话连续性状态:\n{dialogue_state_text}\n\n"
            f"用户画像记忆:\n{user_profile_text}\n\n"
            f"用户长期记忆:\n{long_term_text}\n\n"
            f"检索到的知识片段:\n{knowledge_text}\n\n"
            f"当前发言用户: {event.user_name}\n"
            f"当前输入来源: {event.source}\n\n"
            "请结合以上信息回复。\n"
            "要求:\n"
            "1. 优先保证角色口吻自然。\n"
            "2. 如果当前话题在延续，不要像重新开场一样回答。\n"
            "3. 如果用户是在求安慰，就先接情绪，再给建议。\n"
            "4. 如果用户是在闲聊或求接话，就优先自然接住话题。\n"
            "5. 如果知识检索命中明确，就尽量利用知识，但不要机械复述。\n"
            "6. 回复尽量简洁、自然、适合实时互动。"
        )

    def build_user_input_text(
        self,
        event: InputEvent,
        conversation_state: ConversationState,
    ) -> str:
        previous_input = self._find_previous_input(event, conversation_state)
        previous_output = conversation_state.recent_outputs[-1] if conversation_state.recent_outputs else None

        if previous_input is None:
            return event.text

        if not self._is_likely_follow_up(event, conversation_state):
            return event.text

        previous_reply_text = previous_output.packet.reply_text if previous_output is not None else "无"

        return (
            "这是同一段连续对话，请优先承接上一轮话题，不要重新开场。\n"
            f"上一轮用户消息: {previous_input.text}\n"
            f"你上一轮回复: {previous_reply_text}\n"
            f"当前用户消息: {event.text}\n"
            "如果当前这句话是省略式表达，比如“这个”“那首”“继续”“来一段”“再说说”等，"
            "默认它是在延续上一轮主题，回答时请明确接住那个主题。"
        )

    def build_history_messages(self, event: InputEvent, limit_turns: int = 4) -> list:
        return self.llm_service.recent_messages(
            thread_id=event.user_id,
            limit_turns=limit_turns,
            exclude_input_text=event.text,
        )

    def _find_previous_input(
        self,
        event: InputEvent,
        conversation_state: ConversationState,
    ) -> InputEvent | None:
        candidates = [
            item for item in conversation_state.recent_inputs if item.event_id != event.event_id
        ]
        return candidates[-1] if candidates else None

    def _is_likely_follow_up(
        self,
        event: InputEvent,
        conversation_state: ConversationState,
    ) -> bool:
        text = event.text.strip()
        if not text:
            return False

        if not conversation_state.recent_outputs:
            return False

        follow_up_keywords = [
            "这个",
            "那个",
            "那首",
            "这首",
            "它",
            "继续",
            "接着",
            "来一段",
            "唱一段",
            "再说说",
            "然后呢",
            "后面呢",
        ]
        explicit_music_keywords = [
            "歌词",
            "唱",
            "歌",
            "歌曲",
            "音乐",
            "旋律",
            "副歌",
        ]

        if any(keyword in text for keyword in follow_up_keywords):
            return True

        if not conversation_state.last_topic_shift and any(keyword in text for keyword in explicit_music_keywords):
            return True

        return False
