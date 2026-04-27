from __future__ import annotations

from aiagent.graphs.graph_model import PlannerInferenceOutput


class PlannerNormalizer:
    ALLOWED_STRATEGIES = {
        "chat",
        "comfort",
        "answer",
        "continuation",
        "memory_ack",
        "request_handle",
        "sing",
    }

    ALLOWED_EMOTIONS = {
        "neutral",
        "happy",
        "excited",
        "calm",
        "angry",
        "sad",
    }

    ALLOWED_MOTIONS = {
        "idle",
        "soft_idle",
        "smile_nod",
        "thinking",
        "excited_wave",
        "serious_still",
    }

    ALLOWED_EXPRESSIONS = {
        "neutral",
        "happy_smile",
        "bright_smile",
        "gentle",
        "serious",
    }

    def normalize(self, output: PlannerInferenceOutput) -> PlannerInferenceOutput:
        strategy = output.strategy if output.strategy in self.ALLOWED_STRATEGIES else "chat"
        target_emotion = output.target_emotion if output.target_emotion in self.ALLOWED_EMOTIONS else "neutral"
        target_motion = output.target_motion if output.target_motion in self.ALLOWED_MOTIONS else self._default_motion_for_emotion(target_emotion)
        target_expression = output.target_expression if output.target_expression in self.ALLOWED_EXPRESSIONS else self._default_expression_for_emotion(target_emotion)

        confidence = output.confidence
        if confidence < 0.0:
            confidence = 0.0
        if confidence > 1.0:
            confidence = 1.0

        reply_instruction = output.reply_instruction.strip() or "自然接住当前输入，给出符合角色口吻的实时回复。"
        reasoning = output.reasoning.strip() or "planner_model_normalized"

        return PlannerInferenceOutput(
            strategy=strategy,
            should_store_memory=bool(output.should_store_memory),
            should_speak=bool(output.should_speak),
            target_emotion=target_emotion,
            target_motion=target_motion,
            target_expression=target_expression,
            reply_instruction=reply_instruction,
            reasoning=reasoning,
            confidence=confidence,
            should_retrieve=bool(output.should_retrieve),
            retrieval_query=output.retrieval_query.strip(),
            retrieval_reason=output.retrieval_reason.strip(),

        )

    def _default_motion_for_emotion(self, emotion: str) -> str:
        if emotion == "happy":
            return "smile_nod"
        if emotion == "excited":
            return "excited_wave"
        if emotion == "calm":
            return "soft_idle"
        if emotion == "angry":
            return "serious_still"
        return "idle"

    def _default_expression_for_emotion(self, emotion: str) -> str:
        if emotion == "happy":
            return "happy_smile"
        if emotion == "excited":
            return "bright_smile"
        if emotion == "calm":
            return "gentle"
        if emotion == "angry":
            return "serious"
        return "neutral"