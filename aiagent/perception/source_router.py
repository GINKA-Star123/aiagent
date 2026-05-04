from __future__ import annotations

from aiagent.perception.input_normalizer import InputNormalizer
from aiagent.schemas.inputs import EventPriority, InputAttachment, InputEvent, InputSource


class SourceRouter:
    def __init__(self, input_normalizer: InputNormalizer) -> None:
        self.input_normalizer = input_normalizer

    def route(self, source: str, payload: dict) -> InputEvent:
        normalized_source = self._normalize_source(source)
        priority = self.input_normalizer.parse_priority(payload.get("priority", EventPriority.NORMAL))

        text = str(payload.get("text", "") or "")
        user_id = str(payload.get("user_id") or "guest")
        username = str(payload.get("username") or payload.get("user_name") or "guest")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        attachments = [
            InputAttachment(**item)
            for item in payload.get("attachments", [])
            if isinstance(item, dict)
        ]

        modality = str(payload.get("modality") or self._infer_modality(text, attachments))

        if normalized_source == InputSource.CHAT and not attachments:
            event = self.input_normalizer.normalize_chat(
                text=text,
                user_id=user_id,
                username=username,
                priority=priority,
                metadata=metadata,
            )
            event.modality = modality
            event.attachments = attachments
            return event

        if normalized_source == InputSource.ASR and not attachments:
            event = self.input_normalizer.normalize_asr_text(
                text=text,
                user_id=user_id,
                username=username,
                asr_mode=str(metadata.get("asr_mode", "text")),
                priority=priority,
            )
            event.modality = modality
            event.attachments = attachments
            return event

        if normalized_source == InputSource.SYSTEM and not attachments:
            event = self.input_normalizer.normalize_system(
                text=text,
                user_id=user_id,
                username=username,
                priority=priority,
            )
            event.modality = modality
            event.attachments = attachments
            return event

        return InputEvent(
            source=normalized_source,
            text=text,
            user_id=user_id,
            user_name=username,
            priority=priority,
            modality=modality,
            attachments=attachments,
            metadata=metadata,
        )

    def _normalize_source(self, source: str) -> InputSource:
        value = (source or "").strip().lower()

        if value == "chat":
            return InputSource.CHAT
        if value == "asr":
            return InputSource.ASR
        if value == "vision":
            return InputSource.VISION
        if value == "multimodal":
            return InputSource.MULTIMODAL
        if value == "system":
            return InputSource.SYSTEM

        return InputSource.CHAT

    def _infer_modality(self, text: str, attachments: list[InputAttachment]) -> str:
        has_text = bool(text.strip())
        has_image = any(item.type == "image" for item in attachments)

        if has_text and has_image:
            return "mixed"
        if has_image:
            return "image"
        return "text"
