from __future__ import annotations

from pathlib import Path
from typing import Any

from integrations.live2d.live2d_py_runtime import Live2DPyRuntime
from integrations.live2d.model_session import Live2DModelSession


class HeadlessLive2DRenderer:
    def __init__(self, runtime: Live2DPyRuntime | None = None) -> None:
        self.runtime = runtime or Live2DPyRuntime()
        self.session: Live2DModelSession | None = None

    def load(self, model3_json: str | Path) -> dict[str, Any]:
        prepared = self.runtime.prepare_model(model3_json)
        if not prepared.get("prepared"):
            return {
                "ok": False,
                "stage": "prepare_model",
                "prepared": prepared,
                "session": None,
            }

        self.session = self.runtime.create_session()
        session_state = self.session.load(model3_json=model3_json)
        return {
            "ok": bool(session_state.get("loaded")),
            "stage": "load",
            "prepared": prepared,
            "session": session_state,
        }

    def apply_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.session is None:
            return {
                "ok": False,
                "stage": "apply_payload",
                "error": "model session is not loaded",
            }

        character = payload.get("character") or {}
        expression = str(character.get("expression") or "").strip()
        motion_group = str(character.get("motion_group") or "").strip()
        motion_priority = character.get("motion_priority")
        motion_index = int(character.get("motion_index") or 0)

        result: dict[str, Any] = {
            "ok": True,
            "stage": "apply_payload",
            "steps": [],
        }

        if expression:
            result["steps"].append(
                {
                    "type": "expression",
                    "value": expression,
                    "state": self.session.set_expression(expression),
                }
            )

        if motion_group:
            result["steps"].append(
                {
                    "type": "motion",
                    "group": motion_group,
                    "index": motion_index,
                    "state": self.session.start_motion(
                        group=motion_group,
                        index=motion_index,
                        priority=motion_priority,
                    ),
                }
            )

        result["state"] = self.session.update()
        return result

    def drag(self, x: float, y: float) -> dict[str, Any]:
        if self.session is None:
            return {
                "ok": False,
                "stage": "drag",
                "error": "model session is not loaded",
            }

        return {
            "ok": True,
            "state": self.session.drag(x=x, y=y),
        }

    def resize(self, width: int, height: int) -> dict[str, Any]:
        if self.session is None:
            return {
                "ok": False,
                "stage": "resize",
                "error": "model session is not loaded",
            }

        return {
            "ok": True,
            "state": self.session.resize(width=width, height=height),
        }

    def update(self) -> dict[str, Any]:
        if self.session is None:
            return {
                "ok": False,
                "stage": "update",
                "error": "model session is not loaded",
            }

        return {
            "ok": True,
            "state": self.session.update(),
        }

    def snapshot(self) -> dict[str, Any]:
        if self.session is None:
            return {
                "loaded": False,
                "session": None,
            }

        return {
            "loaded": True,
            "session": self.session.snapshot(),
        }
