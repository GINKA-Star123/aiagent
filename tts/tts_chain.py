from tts_tools import TTSTools

import threading

class TTSChain:
    def __init__(self):
        self.tts = TTSTools()
        self.player_thread = threading.Thread(target=self.tts.player_worker, daemon=True)
        self.player_thread.start()