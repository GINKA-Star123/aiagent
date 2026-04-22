from __future__ import annotations

from aiagent.graphs.graph_model import StateInferenceOutput

class StateNormalizer:
    ALLOWED_EMOTIONS = {"neutral", "happy", "excited", "calm", "angry", "sad"}
    ALLOWED_INTENTS = {"chat", "comfort", "question", "continuation", "memory", "request", "sing"}
    ALLOWED_TOPICS = {"general", "music", "study", "work", "emotion", "profile", "stream"}
    ALLOWED_MOTIONS = {"idle", "soft_idle", "smile_nod", "thinking", "excited_wave", "serious_still"}

    def normalize(self,output:StateInferenceOutput) -> StateInferenceOutput:
        emotion = output.emotion if output.emotion in self.ALLOWED_EMOTIONS else "neutral"
        intent = output.intent if output.intent in self.ALLOWED_INTENTS else "chat"
        topic = output.topic if output.topic in self.ALLOWED_TOPICS else "general"
        motion_hint = output.motion_hint if output.motion_hint in self.ALLOWED_MOTIONS else "idle"

        confidence = output.confidence
        if confidence < 0.0:
            confidence = 0.0
        if confidence >=1.0:
            confidence = 1.0

        context_summary = output.context_summary.strip() or "当前输入需要常规回复。"
        reasoning = output.reasoning.strip() or "state_model_normalize"

        return StateInferenceOutput(
            emotion=emotion,
            intent=intent,
            topic=topic,
            motion_hint=motion_hint,
            confidence=confidence,
            context_summary=context_summary,
            reasoning=reasoning
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