"""High-level response planning."""

from aiagent.schemas.outputs import EmotionLabel,ResponsePacket

class ResponsePlanner:
    def plan(self,reply_text :str) -> ResponsePacket :
        emotion = self._infer_emotion(reply_text)

        return ResponsePacket(
            reply_text=reply_text,
            emotion=emotion,
            should_speak=False,
            should_store_memory=False,
            motion=None,
            metadata={"planner":"langgraphweek1"}
        )
    
    def _infer_emotion(self,text:str)->EmotionLabel:
        if "!" in text or "好耶" in text:
            return EmotionLabel.EXCITED
        if "喜欢" in text or "开心" in text:
            return EmotionLabel.HAPPY
        return EmotionLabel.NEUTRAL