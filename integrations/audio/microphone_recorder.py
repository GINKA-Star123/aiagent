import logging
from pathlib import Path
from uuid import uuid4

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

class MicrophoneRecorder:
    def __init__(
            self,
            sample_rate:int = 16000,
            channels:int =1,
            output_dir : str|Path = "data/cache/recordings"
    ) -> None:
        self.sample_rate = sample_rate,
        self.channels = channels,
        self.output_dir =Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def record(self,seconds:int) ->str:
        self.logger.info(
            "Start recording from microphone. seconds=%s sample_rate=%s",
            seconds,
            self.sample_rate,
        )

        recording = sd.rec(
            int(seconds*self.sample_rate), #type:ignore
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16,
        )
        sd.wait()

        file_path = self.output_dir/f"{uuid4().hex}.wav"
        write(str(file_path),self.sample_rate,recording)

        self.logger.info("Microphone recording saved: %s", file_path)
        return str(file_path)