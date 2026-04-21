"""Normalize source-specific events into shared schemas."""

from aiagent.schemas.inputs import EventPriority, InputEvent, InputSource

class InputNormalizer:
    def normalize_chat(
            self,
            text:str,
            user_id:str = "guest",
            username :str = "guest",
            priority: EventPriority = EventPriority.NORMAL,
            metadata: dict[str,str] | None = None
    ) -> InputEvent:
        return InputEvent(
            source=InputSource.CHAT,
            text=text,
            user_id=user_id,
            user_name=username,
            priority=priority,
            metadata=metadata or {}
        )
    
    def normalize_danmaku(
            self,
            text:str,
            user_id : str,
            username: str,
            room_id : str ="",
            priority: EventPriority = EventPriority.NORMAL,
        
    ) -> InputEvent:
        metadata = {"room_id": room_id,"source_label":"danmaku"}
        return InputEvent(
            source=InputSource.DNAMUKU,
            text=text,
            user_id=user_id,
            user_name=username,
            priority=priority,
            metadata=metadata
        )
    

    def normalize_asr_text(
            self,
            text:str,
            user_id:str="mic",
            username:str ="麦克风输入",
            asr_mode : str = "text",
            priority: EventPriority = EventPriority.HIGH,
    ) -> InputEvent:
        return InputEvent(
            source=InputSource.ASR,
            text=text,
            user_id=user_id,
            user_name=username,
            priority=priority,
            metadata={"asr_code": asr_mode}
        )
    
    def normalize_system(
            self,
            text:str,
            user_id:str="system",
            username:str="系统",
            priority: EventPriority = EventPriority.LOW,
    ) ->InputEvent:
        return InputEvent(
            source=InputSource.SYSTEM,
            text=text,
            user_id=user_id,
            user_name=username,
            priority=priority,
            metadata={"source_label":"system"}
        )
    
    def parse_priority(self,value) -> EventPriority:
        if isinstance(value,EventPriority):
            return value
        
        if isinstance(value,int):
            if value>=EventPriority.HIGH:
                return EventPriority.HIGH
            elif value>=EventPriority.NORMAL:
                return EventPriority.NORMAL
            elif value>=EventPriority.LOW:
                return EventPriority.LOW
            else:
                return EventPriority.LOW
        
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"high", "10"}:
                return EventPriority.HIGH
            if lowered in {"low", "1"}:
                return EventPriority.LOW

        return EventPriority.NORMAL