"""Faster Whisper client placeholder."""
import logging
from pathlib import Path

from faster_whisper import WhisperModel

class FasterWhisperClient:
    def __init__(
            self,
            model_size : str = "small",
            model_path : str = "",
            device: str ="cpu",
            compute_type = "int8",
            language : str= "zh"
    ) ->None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.language = language

        model_source = model_path.strip() or model_size

        if model_path.strip():
            local_path = Path(model_path)
            if not local_path.exists():
                raise FileNotFoundError(f"Local ASR model path not found: {local_path}")
            self.logger.info("Using local faster-whisper model path: %s", local_path)
        else:
            self.logger.info("Using remote faster-whisper model name: %s", model_size)

        self.model = WhisperModel(
            model_source,
            device=device,
            compute_type=compute_type,
        )
    def transcribe(self,audio_path:str) ->str :
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found:{path}")
        
        self.logger.info("Transcribing audio with faster-whisper %s",path)

        segments, info = self.model.transcribe(
            str(path),
            language=self.language,
            vad_filter=True
        )

        text_parts: list[str] = []
        for segment in segments:
            if segment.text.strip():
                text_parts.append(segment.text.strip())

        transcript = "".join(text_parts).strip()

        self.logger.info(
            "ASR finished. language=%s duration=%s text=%s",
            info.language,
            getattr(info, "duration", "unknown"),
            transcript,
        )
        
        return transcript