import logging
import threading
import time
import wave
from pathlib import Path

import pygame


class AudioPlayer:
    SUPPORTED_SUFFIXES = {".wav", ".mp3", ".ogg"}

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._mixer_ready = False
        self._playback_thread : threading.Thread | None = None
        self._stop_event= threading.Event()
        self._lock = threading.Lock()
        self._current_audio_path:str = ""

        self._ensure_mixer()

    def _ensure_mixer(self)->None:
        if self._mixer_ready:
            return
        
        try : 
            if not pygame.mixer.get_init():
                pygame.mixer.get_init()
            self._mixer_ready = True
        except Exception:
            self.logger.exception("初始化失败")
            self._mixer_ready=False
            raise

    def play(self, audio_file: str) -> None:
        self._ensure_mixer()

        path = Path(audio_file)
        self._validate_audio_file(path)

        with self._lock:
            self._stop_event.clear()
            self._current_audio_path = str(Path)
        
        self.logger.info("Playing audio file: %s", path)
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if self._stop_event.is_set():
                self.logger.info("Stopping audio playback")
                pygame.mixer.music.stop()
                break
            time.sleep(0.05)

        with self._lock:
            self._current_audio_path =""

    def play_async(self,audio_file:str) -> None:
        self.stop(wait=True)

        def runner() -> None:
            try:
                self.play(audio_file)
            except Exception:
                self.logger.exception("Audio playback failed")


        thread = threading.Thread(target=runner, daemon=True,name="audio-playback-thread")
        self._playback_thread = thread
        thread.start()

    def stop(self,wait:bool = False)->None:
        with self._lock:
            self._stop_event.set()
        
        try:
            if self._mixer_ready and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            self.logger.exception("Failed to stop audio playback")

        if wait and self._playback_thread is not None and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)

    def is_busy(self) -> bool:
        try:
            if not self._mixer_ready:
                return False
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            self.logger.exception("Failed to check audio playback status")
            return False
        
    def get_current_audio_path(self)->str:
        return self._current_audio_path
    
    def get_duration_seconds(self,audio_file:str) ->float:
        path =Path(audio_file)
        self._validate_audio_file(path)

        if path.suffix.lower() == ".wav":
            with wave.open(str(path), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                frame_rate = wav_file.getframerate() or 1
                return round(frame_count / frame_rate, 3)

        return 0.0
        
    def _validate_audio_file(self,path:Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported audio format for playback: {path.suffix}")

        if path.stat().st_size == 0:
            raise ValueError(f"Audio file is empty: {path}")

        if path.suffix.lower() == ".wav":
            self._validate_wav(path)

    def _validate_wav(self, path: Path) -> None:
        try:
            with wave.open(str(path), "rb") as wav_file:
                wav_file.getparams()
        except wave.Error as exc:
            raise ValueError(f"Invalid wav file: {path}") from exc
