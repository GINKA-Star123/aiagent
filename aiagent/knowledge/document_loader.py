"""Document loader placeholder."""

from pathlib import Path

class KnowledgeDocumentLoader:
    def load_markdown(self,file_path: Path|str) -> str:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")

        return  path.read_text(encoding="utf-8")