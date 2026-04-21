"""Voice activity detection placeholder."""

import numpy as np

class VoiceActivityDetector:
    def __init__(self,energy_threshold: float=0.015) -> None:
        self.energy_threshold = energy_threshold

    def is_speech(self, audio_chunk:np.ndarray) ->bool:
        if audio_chunk.size==0:
            return False
        
        chunk = audio_chunk.astype(np.float32)

        if chunk.ndim>1:
            chunk = chunk.mean(axis=1)

        chunk = chunk/32768.0

        rms = float(np.sqrt(np.mean(np.square(chunk))))

        return rms>=self.energy_threshold