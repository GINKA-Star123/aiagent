"""Streaming-style microphone turn recorder."""

import queue
from pathlib import Path
from uuid import uuid4

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

from integrations.asr.vad import VoiceActivityDetector


class StreamingMicrophone:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_seconds: float = 0.25,
        output_dir: str | Path = "data/cache/voice_turns",
        vad: VoiceActivityDetector | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_seconds = chunk_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vad = vad or VoiceActivityDetector()

    def record_until_silence(
        self,
        max_seconds: float = 8.0,
        silence_seconds: float = 1.2,
    ) -> str:
        audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        frames: list[np.ndarray] = []

        chunk_size = int(self.sample_rate * self.chunk_seconds)
        max_chunks = max(1, int(max_seconds / self.chunk_seconds))
        required_silent_chunks = max(1, int(silence_seconds / self.chunk_seconds))

        has_speech = False
        silent_chunks = 0
        total_chunks = 0

        def callback(indata, frames_count, time_info, status) -> None:
            if status:
                pass
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_size,
            callback=callback,
        ):
            while total_chunks < max_chunks:
                chunk = audio_queue.get()
                total_chunks += 1
                frames.append(chunk)

                if self.vad.is_speech(chunk):
                    has_speech = True
                    silent_chunks = 0
                elif has_speech:
                    silent_chunks += 1

                if has_speech and silent_chunks >= required_silent_chunks:
                    break

        if not has_speech:
            raise RuntimeError("No speech detected from microphone.")

        merged = np.concatenate(frames, axis=0)

        file_path = self.output_dir / f"{uuid4().hex}.wav"
        write(str(file_path), self.sample_rate, merged)

        return str(file_path)
