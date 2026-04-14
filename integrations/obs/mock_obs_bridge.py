import json

from pathlib import Path
from uuid import uuid4

class MockOBSBridge:
    def __init__(self,output_dir: str|Path = "data/cache/mock_obs") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def push_subtitle(self,subtitle_text:str) ->str:
        payload = {
            "type":"subtitle",
            "text":subtitle_text
        }

        path = self.output_dir / f"{uuid4().hex}.json"
        path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        return str(path)