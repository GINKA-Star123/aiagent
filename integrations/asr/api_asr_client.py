from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

class ApiASRClient:
    def __init__(
            self,
            *,
            base_url:str,
            api_key:str|None = None,
            model:str = "whisper-large-v3",
            language:str = "zh",
            timeout_seconds:float=60.0
    )-> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.language = language
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(self.__class__.__name__)

        if not self.base_url:
            raise RuntimeError("ASR_API_BASE_URL is not configured.")
    
    def transcribe(self,audio_path:str) ->str:
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found:{path}")
        
        self.logger.info("Transcribing audio with api-asr %s",path)

        headers = self._headers()

        with path.open("rb") as file_obj:
            files = {
                "file":(
                    path.name,
                    file_obj,
                    self._guess_content_type(path),
                )
            }
            data = {
                "model": self.model,
                "language": self.language,
            }

            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    self._join_url("asr"),
                    headers=headers,
                    data=data,
                    files=files
                )

        response.raise_for_status()
        payload = response.json()
        transcript = self._extract_text(payload)

        self.logger.info(
            "ASR finished.  text=%s",transcript)
        
        return transcript
    
    def _headers(self) -> dict[str,str]:
        if not self.api_key:
            return {}
        return {"Authorization":f"Bearer {self.api_key}"}
    
    def _join_url(self,path:str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"
    
    def _guess_content_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".mp3":
            return "audio/mpeg"
        if suffix == ".m4a":
            return "audio/mp4"
        if suffix == ".webm":
            return "audio/webm"
        if suffix == ".ogg":
            return "audio/ogg"
        return "audio/wav"
    
    def _extract_text(self, payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("text", "transcript", "result"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            data = payload.get("data")
            if isinstance(data, dict):
                for key in ("text", "transcript", "result"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

            segments = payload.get("segments")
            if isinstance(segments, list):
                parts = []
                for item in segments:
                    if isinstance(item, dict):
                        text = str(item.get("text") or "").strip()
                        if text:
                            parts.append(text)
                if parts:
                    return "".join(parts).strip()

        raise RuntimeError(f"ASR response does not contain transcript text: {payload}")