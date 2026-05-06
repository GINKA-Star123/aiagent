from __future__ import annotations

from pathlib import Path
from typing import Any

from integrations.live2d.model_loader import Live2DModelLoader


class Live2DModelScanner:
    def __init__(self, loader: Live2DModelLoader | None = None) -> None:
        self.loader = loader or Live2DModelLoader()

    def scan_root(self, root: str | Path) -> dict[str, Any]:
        root_path = Path(root)

        result: dict[str, Any] = {
            "root": str(root_path),
            "exists": root_path.exists(),
            "model_count": 0,
            "models": [],
        }

        if not root_path.exists():
            return result

        model_paths = sorted(root_path.rglob("*.model3.json"))
        result["model_count"] = len(model_paths)

        for model_path in model_paths:
            inspection = self.loader.inspect_model3(model_path)
            result["models"].append(
                {
                    "model3_json": str(model_path),
                    "directory": str(model_path.parent),
                    "summary": inspection.get("summary", {}),
                    "warnings": inspection.get("warnings", []),
                    "missing_files": inspection.get("missing_files", []),
                }
            )

        return result

    def find_first_model(self, root: str | Path) -> Path | None:
        root_path = Path(root)
        if not root_path.exists():
            return None

        for model_path in sorted(root_path.rglob("*.model3.json")):
            return model_path

        return None
