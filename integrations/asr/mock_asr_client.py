class MockASRClient:
    def transcribe(self,audio_text:str) ->str:
        return "这是来自mock ASR 的测试文本"
    
    