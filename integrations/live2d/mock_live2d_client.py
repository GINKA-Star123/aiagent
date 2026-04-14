import json
from pathlib import Path
from uuid import uuid4


class MockLive2DClient:
    def __init__(self,output_dit:str|Path = "data/cache/mock_live2d") ->None:
        self.output_dir = Path(output_dit)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def dispatch(self,expression:str|None,motion:str|None,text:str|None) -> str:
        payload = {
            "expression":expression,
            "motion":motion,
            "text":text
        }

        path = self.output_dir / f"{uuid4().hex}.json"
        path.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
        return str(path)