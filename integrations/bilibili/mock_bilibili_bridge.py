import json
from pathlib import Path
from uuid import uuid4


class MockBilibiliBridge:
    def __init__(self, output_dir: str | Path = "data/cache/mock_bilibili") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def publish_reply_event(self, reply_text: str, username: str | None = None) -> str:
        payload = {
            "type": "reply_event",
            "username": username or "",
            "reply_text": reply_text,
        }

        path = self.output_dir / f"{uuid4().hex}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
