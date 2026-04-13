"""High-level response planning."""

from aiagent.schemas.outputs import EmotionLabel,ResponsePacket

class ResponsePlanner:
    def plan(self,base_reply_text :str,final_reply_text:str) -> ResponsePacket :
        emotion = self._infer_emotion(final_reply_text)
        motion = self._infer_motion(emotion)
        return ResponsePacket(
            reply_text=final_reply_text,
            base_reply_text=base_reply_text,
            emotion=emotion,
            should_speak=True,
            should_store_memory=False,
            motion=motion,
            audio_path=None,
            metadata={"planner":"week2-persona-style"}
        )
    
    def _infer_emotion(self,text:str)->EmotionLabel:
        if "!" in text or "好耶" in text:
            return EmotionLabel.EXCITED
        if "喜欢" in text or "开心" in text:
            return EmotionLabel.HAPPY
        return EmotionLabel.NEUTRAL
    
    def _infer_motion(self,emotion:EmotionLabel) -> str|None:
        if emotion == EmotionLabel.EXCITED:
            return "excited_wave"
        if emotion == EmotionLabel.HAPPY:
            return "smile_nod"
        return "idle"