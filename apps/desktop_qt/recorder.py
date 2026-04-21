from pathlib import Path
from uuid import uuid4

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        output_dir: str | Path = "data/cache/desktop_recordings",
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self) -> None:
        if self._is_recording:
            raise RuntimeError("当前已经在录音中。")

        self._frames = []

        def callback(indata, frames, time, status) -> None:
            if status:
                pass
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()
        self._is_recording = True

    def stop_recording(self) -> str:
        if not self._is_recording or self._stream is None:
            raise RuntimeError("当前没有正在进行的录音。")

        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._is_recording = False

        if not self._frames:
            raise RuntimeError("没有录到音频数据，请检查麦克风。")

        audio = np.concatenate(self._frames, axis=0)
        file_path = self.output_dir / f"{uuid4().hex}.wav"
        write(str(file_path), self.sample_rate, audio)

        self._frames = []
        return str(file_path)

    def record(self, seconds: int = 5) -> str:
        recording = sd.rec(
            int(seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16,
        )
        sd.wait()

        file_path = self.output_dir / f"{uuid4().hex}.wav"
        write(str(file_path), self.sample_rate, recording)
        return str(file_path)
