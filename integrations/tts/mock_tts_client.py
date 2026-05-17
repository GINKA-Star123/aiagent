import math
import struct
import wave
from pathlib import Path
from uuid import uuid4

class MockTTSClient:
    def __init__(self, output_dir: str|Path = "data/cache/tts_real") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def synthesize(self, text: str) -> str:
        file_path = self.output_dir / f"{uuid4().hex}.wav"
        self._write_beep_wav(file_path)
        return str(file_path)

    def _write_beep_wav(self, file_path: Path) -> None:
        sample_rate = 16000
        duration_seconds = 0.35
        frequency = 440.0
        amplitude = 0.18
        total_samples = int(sample_rate * duration_seconds)

        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for index in range(total_samples):
                sample = amplitude * math.sin(2 * math.pi * frequency * index / sample_rate)
                frames.extend(struct.pack("<h", int(sample * 32767)))

            wav_file.writeframes(bytes(frames))
