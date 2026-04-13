from pathlib import Path
from uuid import uuid4

class MockTTSClient:
    def __init__(self, output_dir: str|Path = "data/cache/mock_tts") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def synthesize(self, text: str) -> str:
        file_path = self.output_dir / f"{uuid4()}.txt"
        file_path.write_text(text, encoding="utf-8")
        return str(file_path)