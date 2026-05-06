from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Live2DModelLoader:
    def inspect_model3(self, model3_json: str | Path) -> dict[str, Any]:
        model_path = Path(model3_json)
        report: dict[str, Any] = {
            "model3_json": str(model_path),
            "exists": model_path.exists(),
            "valid_json": False,
            "version": None,
            "moc": None,
            "textures": [],
            "expressions": [],
            "motions": [],
            "missing_files": [],
            "warnings": [],
        }

        if not model_path.exists():
            report["warnings"].append("model3_json_missing")
            report["summary"] = self._summary(report)
            return report

        try:
            raw = json.loads(model_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            report["warnings"].append(f"model3_json_invalid:{exc}")
            report["summary"] = self._summary(report)
            return report

        if not isinstance(raw, dict):
            report["warnings"].append("model3_json_root_not_object")
            report["summary"] = self._summary(report)
            return report

        report["valid_json"] = True
        report["version"] = raw.get("Version")

        refs = raw.get("FileReferences") or {}
        if not isinstance(refs, dict):
            report["warnings"].append("file_references_missing_or_invalid")
            refs = {}

        base_dir = model_path.parent

        moc = refs.get("Moc")
        if isinstance(moc, str) and moc.strip():
            moc_path = self._resolve(base_dir, moc)
            report["moc"] = self._asset_entry(moc, moc_path)
            self._append_missing(report, moc_path)
        else:
            report["warnings"].append("moc_missing")

        textures = refs.get("Textures") or []
        if isinstance(textures, list):
            for texture in textures:
                if isinstance(texture, str) and texture.strip():
                    texture_path = self._resolve(base_dir, texture)
                    report["textures"].append(self._asset_entry(texture, texture_path))
                    self._append_missing(report, texture_path)
        else:
            report["warnings"].append("textures_not_list")

        expressions = refs.get("Expressions") or []
        if isinstance(expressions, list):
            for expression in expressions:
                if not isinstance(expression, dict):
                    continue

                file_name = expression.get("File")
                expression_path = self._resolve(base_dir, file_name) if isinstance(file_name, str) else None

                report["expressions"].append(
                    {
                        "name": expression.get("Name", ""),
                        "file": file_name or "",
                        "path": str(expression_path) if expression_path else "",
                        "exists": bool(expression_path and expression_path.exists()),
                    }
                )

                if expression_path:
                    self._append_missing(report, expression_path)
        else:
            report["warnings"].append("expressions_not_list")

        motions = refs.get("Motions") or {}
        if isinstance(motions, dict):
            for group, items in motions.items():
                if not isinstance(items, list):
                    continue

                for motion in items:
                    if not isinstance(motion, dict):
                        continue

                    file_name = motion.get("File")
                    motion_path = self._resolve(base_dir, file_name) if isinstance(file_name, str) else None

                    report["motions"].append(
                        {
                            "group": group,
                            "file": file_name or "",
                            "path": str(motion_path) if motion_path else "",
                            "exists": bool(motion_path and motion_path.exists()),
                        }
                    )

                    if motion_path:
                        self._append_missing(report, motion_path)
        else:
            report["warnings"].append("motions_not_object")

        report["summary"] = self._summary(report)
        return report

    def _resolve(self, base_dir: Path, file_name: str) -> Path:
        path = Path(file_name)
        if path.is_absolute():
            return path
        return base_dir / path

    def _asset_entry(self, file_name: str, path: Path) -> dict[str, Any]:
        return {
            "file": file_name,
            "path": str(path),
            "exists": path.exists(),
        }

    def _append_missing(self, report: dict[str, Any], path: Path) -> None:
        if not path.exists():
            report["missing_files"].append(str(path))

    def _summary(self, report: dict[str, Any]) -> dict[str, Any]:
        return {
            "texture_count": len(report.get("textures") or []),
            "expression_count": len(report.get("expressions") or []),
            "motion_count": len(report.get("motions") or []),
            "missing_count": len(report.get("missing_files") or []),
            "loadable": bool(
                report.get("valid_json")
                and report.get("moc")
                and not report.get("missing_files")
            ),
        }
