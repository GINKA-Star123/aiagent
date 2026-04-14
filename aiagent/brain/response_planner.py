"""High-level response planning."""

from aiagent.schemas.outputs import EmotionLabel,ResponsePacket

class ResponsePlanner:
    def plan(self,final_reply_text:str,base_reply_text :str|None=None) -> ResponsePacket :
        emotion = self._infer_emotion(final_reply_text)
        motion = self._infer_motion(emotion)
        expression=self._infer_expression(emotion)

        return ResponsePacket(
            reply_text=final_reply_text,
            base_reply_text=base_reply_text,
            emotion=emotion,
            should_speak=True,
            should_store_memory=False,
            motion=motion,
            expression=expression,
            subtitle_text = final_reply_text,
            metadata={"planner":"week5-expression-ready"}
        )
    
    def _infer_emotion(self,text:str)->EmotionLabel:
        if "!" in text or "好耶" in text or "太棒" in text:
            return EmotionLabel.EXCITED
        if "喜欢" in text or "开心" in text:
            return EmotionLabel.HAPPY
        if "别担心" in text or "慢慢来" in text:
            return EmotionLabel.CALM
        return EmotionLabel.NEUTRAL
    
    def _infer_motion(self,emotion:EmotionLabel) -> str|None:
        if emotion == EmotionLabel.EXCITED:
            return "excited_wave"
        if emotion == EmotionLabel.HAPPY:
            return "smile_nod"
        if emotion == EmotionLabel.CALM:
            return "soft_idle"
        return "idle"
    
    def _infer_expression(self,emotion:EmotionLabel) -> str|None:
        if emotion == EmotionLabel.EXCITED:
            return "bright_smile"
        if emotion == EmotionLabel.HAPPY:
            return "happy_smile"
        if emotion == EmotionLabel.CALM:
            return "gentle"
        if emotion == EmotionLabel.ANGRY:
            return "angry"
        return "neutral"
            