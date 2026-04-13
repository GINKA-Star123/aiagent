class MockASRClient:
    def transcribe(self,audio_text:str) ->str:
        return audio_text.strip()
    
    