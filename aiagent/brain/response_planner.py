"""High-level response planning."""
from __future__ import annotations

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import EmotionLabel, ResponsePacket
from aiagent.state.conversation_state import ConversationState


class ResponsePlanner:
    def plan(
        self,
        final_reply_text: str,
        base_reply_text: str | None = None,
        input_event: InputEvent | None = None,
        conversation_state: ConversationState | None = None,
    ) -> ResponsePacket:
        merged_reply_text = final_reply_text.strip() or (base_reply_text or "").strip()

        emotion = self._infer_emotion(merged_reply_text, input_event, conversation_state)
        strategy = self._infer_strategy(input_event, conversation_state)
        motion = self._infer_motion(emotion, strategy)
        expression = self._infer_expression(emotion)

        should_store_memory = self._should_store_memory(input_event, conversation_state)

        metadata = {
            "planner": "week20-dialogue-topic-ready",
            "strategy": strategy,
            "topic": conversation_state.current_topic if conversation_state is not None else "general",
            "topic_shift": str(conversation_state.last_topic_shift).lower() if conversation_state is not None else "false",
        }

        return ResponsePacket(
            reply_text=merged_reply_text,
            base_reply_text=merged_reply_text,
            emotion=emotion,
            should_speak=True,
            should_store_memory=should_store_memory,
            motion=motion,
            expression=expression,
            metadata=metadata,
        )

    def _infer_strategy(
        self,
        input_event: InputEvent | None,
        conversation_state: ConversationState | None,
    ) -> str:
        if input_event is None:
            return "default"

        text = input_event.text

        if conversation_state is not None and conversation_state.last_user_goal == "seek_comfort":
            return "comfort"
        if any(keyword in text for keyword in ["怎么", "如何", "怎样"]):
            return "guidance"
        if any(keyword in text for keyword in ["我叫", "我是", "请记住", "记住我"]):
            return "acknowledge_profile"
        if conversation_state is not None and conversation_state.current_topic == "music":
            return "music_engage"
        if "？" in text or "?" in text:
            return "answer_question"
        if conversation_state is not None and not conversation_state.last_topic_shift:
            return "follow_up"
        return "casual_reply"

    def _infer_emotion(
        self,
        text: str,
        input_event: InputEvent | None,
        conversation_state: ConversationState | None,
    ) -> EmotionLabel:
        if conversation_state is not None and conversation_state.last_user_emotion_hint == "nervous":
            return EmotionLabel.CALM
        if "!" in text or "！" in text or "太棒" in text:
            return EmotionLabel.EXCITED
        if "喜欢" in text or "开心" in text or "有趣" in text:
            return EmotionLabel.HAPPY
        if "别担心" in text or "慢慢来" in text or "没关系" in text:
            return EmotionLabel.CALM
        return EmotionLabel.NEUTRAL

    def _infer_motion(self, emotion: EmotionLabel, strategy: str) -> str | None:
        if strategy == "comfort":
            return "soft_idle"
        if strategy == "music_engage":
            return "smile_nod"
        if emotion == EmotionLabel.EXCITED:
            return "excited_wave"
        if emotion == EmotionLabel.HAPPY:
            return "smile_nod"
        if emotion == EmotionLabel.CALM:
            return "soft_idle"
        return "idle"

    def _infer_expression(self, emotion: EmotionLabel) -> str | None:
        if emotion == EmotionLabel.EXCITED:
            return "bright_smile"
        if emotion == EmotionLabel.HAPPY:
            return "happy_smile"
        if emotion == EmotionLabel.CALM:
            return "gentle"
        if emotion == EmotionLabel.ANGRY:
            return "angry"
        return "neutral"

    def _should_store_memory(
        self,
        input_event: InputEvent | None,
        conversation_state: ConversationState | None,
    ) -> bool:
        if input_event is None:
            return False

        text = input_event.text
        if any(keyword in text for keyword in ["请记住", "我叫", "我是", "我喜欢", "生日", "考试", "工作"]):
            return True

        if conversation_state is not None and conversation_state.current_topic in {"profile", "study", "birthday", "work"}:
            return len(text.strip()) >= 12

        return False
