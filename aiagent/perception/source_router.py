"""Route normalized input events by source and priority."""

from aiagent.perception.input_normalizer import InputNormalizer
from aiagent.schemas.inputs import InputEvent, InputSource

class SourceRouter:
    def __init__(self,input_normalizer: InputNormalizer) -> None:
        self.input_normalizer = input_normalizer

    def route(self,source:str| InputSource,payload:dict) -> InputEvent:
        source_enum = self._to_source_enum(source)
        priority = self.input_normalizer.parse_priority(payload.get("priority"))

        if source_enum == InputSource.CHAT:
            return self.input_normalizer.normalize_chat(
                text=str(payload.get("text", "")),
                user_id=str(payload.get("user_id", "guest")),
                username=str(payload.get("username", "guest")),
                priority=priority,
                metadata=self._stringify_metadata(payload.get("metadata", {})),
            )

        if source_enum == InputSource.DNAMUKU:
            return self.input_normalizer.normalize_danmaku(
                text=str(payload.get("text", "")),
                user_id=str(payload.get("user_id", "danmaku-user")),
                username=str(payload.get("username", "弹幕用户")),
                room_id=str(payload.get("room_id", "")),
                priority=priority,
            )

        if source_enum == InputSource.ASR:
            return self.input_normalizer.normalize_asr_text(
                text=str(payload.get("text", "")),
                user_id=str(payload.get("user_id", "mic")),
                username=str(payload.get("username", "麦克风输入")),
                asr_mode=str(payload.get("asr_mode", "text")),
                priority=priority,
            )

        if source_enum == InputSource.SYSTEM:
            return self.input_normalizer.normalize_system(
                text=str(payload.get("text", "")),
                user_id=str(payload.get("user_id", "system")),
                username=str(payload.get("username", "system")),
                priority=priority,
            )

        raise ValueError(f"Unsupported input source: {source}")


    def _to_source_enum(self,source:str|InputSource) -> InputSource:

        if isinstance(source,InputSource):
            return source
        
        normalized = str(source).strip().lower()

        if normalized == "chat":
            return InputSource.CHAT
        elif normalized in {"danmaku","dnamuku"}:
            return InputSource.DNAMUKU
        elif normalized == "asr":
            return InputSource.ASR
        elif normalized == "system":
            return InputSource.SYSTEM
        
        raise ValueError(f"Unknown source: {source}")
    
    def _stringify_metadata(self,metadata) -> dict[str,str]:
        if not isinstance(metadata,dict):
            return {}
        return {str(key):str(value) for key,value in metadata.items()}