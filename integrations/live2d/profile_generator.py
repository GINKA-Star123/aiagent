from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class Live2DProfileGenerator:
    def generate_character_profile(
        self,
        *,
        character_id: str,
        model_id: str,
        display_name: str,
        model3_json: str | Path,
        output_path: str | Path,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        model3_path = Path(model3_json)
        output = Path(output_path)

        if output.exists() and not overwrite:
            raise FileExistsError(f"profile already exists: {output}")

        if not model3_path.exists():
            raise FileNotFoundError(f"model3_json not found: {model3_path}")

        raw = json.loads(model3_path.read_text(encoding="utf-8-sig"))
        refs = raw.get("FileReferences") or {}

        expressions = self._extract_expressions(refs)
        motions = self._extract_motions(refs)

        profile = {
            "character_id": character_id,
            "model_id": model_id,
            "display_name": display_name,
            "model3_json": str(model3_path).replace("\\", "/"),
            "default_expression": self._default_expression(expressions),
            "default_motion": self._default_motion(motions),
            "expressions": expressions,
            "motions": motions,
            "emotion_expression_map": self._emotion_expression_map(expressions),
            "emotion_motion_map": self._emotion_motion_map(motions),
            "metadata": {
                "source": "auto_generated",
                "model3_version": raw.get("Version"),
            },
        }

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            yaml.safe_dump(
                profile,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return profile

    def _extract_expressions(self, refs: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        expressions = refs.get("Expressions") or []
        if not isinstance(expressions, list):
            return result

        for item in expressions:
            if not isinstance(item, dict):
                continue

            name = str(item.get("Name") or "").strip()
            file = str(item.get("File") or "").strip()

            if not file:
                continue

            expression_id = self._normalize_id(name or Path(file).stem)

            result.append(
                {
                    "expression_id": expression_id,
                    "file": file.replace("\\", "/"),
                    "aliases": self._expression_aliases(expression_id),
                }
            )

        return result

    def _extract_motions(self, refs: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        motions = refs.get("Motions") or {}
        if not isinstance(motions, dict):
            return result

        for group, items in motions.items():
            if not isinstance(items, list):
                continue

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue

                file = str(item.get("File") or "").strip()
                if not file:
                    continue

                motion_id = self._normalize_id(Path(file).stem or f"{group}_{index}")

                result.append(
                    {
                        "motion_id": motion_id,
                        "group": str(group),
                        "file": file.replace("\\", "/"),
                        "priority": self._motion_priority(group, motion_id),
                        "aliases": self._motion_aliases(group, motion_id),
                    }
                )

        return result

    def _default_expression(self, expressions: list[dict[str, Any]]) -> str:
        if not expressions:
            return "neutral"

        for candidate in ("neutral", "normal", "default", "idle"):
            for item in expressions:
                if item["expression_id"] == candidate or candidate in item.get("aliases", []):
                    return item["expression_id"]

        return expressions[0]["expression_id"]

    def _default_motion(self, motions: list[dict[str, Any]]) -> str:
        if not motions:
            return "idle"

        for candidate in ("idle", "normal", "default"):
            for item in motions:
                if item["motion_id"] == candidate or candidate in item.get("aliases", []):
                    return item["motion_id"]

        return motions[0]["motion_id"]

    def _emotion_expression_map(self, expressions: list[dict[str, Any]]) -> dict[str, str]:
        ids = {item["expression_id"] for item in expressions}

        def choose(*candidates: str, fallback: str = "neutral") -> str:
            for item in candidates:
                if item in ids:
                    return item
            if fallback in ids:
                return fallback
            return next(iter(ids), fallback)

        return {
            "neutral": choose("neutral", "normal", "default"),
            "calm": choose("gentle", "calm", "neutral", "normal"),
            "happy": choose("happy_smile", "happy", "smile", "joy"),
            "excited": choose("bright_smile", "excited", "happy", "smile"),
            "angry": choose("serious", "angry", "mad", "neutral"),
            "sad": choose("sad", "gentle", "calm", "neutral"),
        }

    def _emotion_motion_map(self, motions: list[dict[str, Any]]) -> dict[str, str]:
        ids = {item["motion_id"] for item in motions}

        def choose(*candidates: str, fallback: str = "idle") -> str:
            for item in candidates:
                if item in ids:
                    return item
            if fallback in ids:
                return fallback
            return next(iter(ids), fallback)

        return {
            "neutral": choose("idle", "normal", "default"),
            "calm": choose("soft_idle", "idle", "normal"),
            "happy": choose("smile_nod", "happy", "tapbody", "idle"),
            "excited": choose("excited_wave", "wave", "happy", "tapbody"),
            "angry": choose("serious_still", "serious", "idle"),
            "sad": choose("soft_idle", "sad", "idle"),
        }

    def _expression_aliases(self, expression_id: str) -> list[str]:
        aliases: list[str] = []

        if expression_id in {"normal", "default"}:
            aliases.append("neutral")
        if "smile" in expression_id:
            aliases.extend(["happy", "smile"])
        if "happy" in expression_id:
            aliases.append("joy")
        if "angry" in expression_id:
            aliases.append("serious")
        if "sad" in expression_id:
            aliases.append("calm")

        return sorted(set(aliases))

    def _motion_aliases(self, group: str, motion_id: str) -> list[str]:
        aliases: list[str] = []
        group_id = self._normalize_id(group)

        if group_id:
            aliases.append(group_id)
        if "idle" in motion_id:
            aliases.append("default")
        if "tap" in group_id:
            aliases.append("tapbody")
        if "wave" in motion_id:
            aliases.append("excited")
        if "nod" in motion_id:
            aliases.append("happy")

        return sorted(set(aliases))

    def _motion_priority(self, group: str, motion_id: str) -> int:
        text = f"{group} {motion_id}".lower()

        if "idle" in text:
            return 1
        if "tap" in text:
            return 2
        if "special" in text or "wave" in text:
            return 3

        return 2

    def _normalize_id(self, value: str) -> str:
        text = value.strip().lower()
        text = text.replace(" ", "_")
        text = text.replace("-", "_")
        text = text.replace(".", "_")

        allowed = []
        for char in text:
            if char.isalnum() or char == "_":
                allowed.append(char)

        normalized = "".join(allowed).strip("_")
        return normalized or "default"
