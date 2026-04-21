import logging
from pathlib import Path
from uuid import uuid4

import httpx


class GPTSoVITSClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        ref_audio_path: str,
        prompt_lang: str,
        prompt_text: str,
        text_lang: str,
        output_dir: str | Path = "data/cache/tts_real",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.ref_audio_path = ref_audio_path.strip().strip('"').strip("'")
        self.prompt_lang = prompt_lang
        self.prompt_text = prompt_text
        self.text_lang = text_lang
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def synthesize(self, text: str) -> str:
        if not self.ref_audio_path:
            raise RuntimeError("GPT_SOVITS_REF_AUDIO_PATH is not configured.")

        if not Path(self.ref_audio_path).exists():
            raise RuntimeError(f"Reference audio not found: {self.ref_audio_path}")

        payload = {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_lang": self.prompt_lang,
            "prompt_text": self.prompt_text,
            "text_split_method": "cut0",
            "batch_size": 10,
            "media_type": "wav",
            "streaming_mode": False,
            "parallel_infer": False,
            "seed": -1,
        }

        url = f"{self.base_url}/tts"
        self.logger.info("Calling GPT-SoVITS endpoint: %s", url)
        self.logger.info(
            "GPT-SoVITS request summary: ref_audio=%s prompt_lang=%s text_lang=%s prompt_text=%s",
            self.ref_audio_path,
            self.prompt_lang,
            self.text_lang,
            self.prompt_text,
        )

        with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
            response = client.post(url, json=payload)

            if response.status_code != 200:
                raise RuntimeError(
                    f"GPT-SoVITS request failed: {response.status_code} {response.text}"
                )

            content_type = response.headers.get("content-type", "").lower()
            audio_bytes = response.content

        if "application/json" in content_type or "text/plain" in content_type:
            raise RuntimeError(
                f"GPT-SoVITS returned non-audio response: {response.text[:300]}"
            )

        if not audio_bytes:
            raise RuntimeError("GPT-SoVITS returned empty audio content.")

        if not self._looks_like_wav(audio_bytes):
            preview = audio_bytes[:120].decode("utf-8", errors="ignore")
            raise RuntimeError(f"GPT-SoVITS did not return a valid wav stream: {preview}")

        file_path = self.output_dir / f"{uuid4().hex}.wav"
        file_path.write_bytes(audio_bytes)
        return str(file_path)

    @staticmethod
    def _looks_like_wav(audio_bytes: bytes) -> bool:
        return len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"
