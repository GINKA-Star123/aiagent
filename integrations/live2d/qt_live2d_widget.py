from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget

logger = logging.getLogger(__name__)


class QtLive2DWidget(QOpenGLWidget):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        self.live2d: Any | None = None
        self.model: Any | None = None
        self.model3_json = ""
        self.loaded = False
        self.last_error = ""

        self.setMouseTracking(True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def load_model(self, model3_json: str | Path) -> dict:
        self.model3_json = str(model3_json)
        self.loaded = False
        self.last_error = ""

        path = Path(model3_json)
        if not path.exists():
            self.last_error = f"model3_json not found: {path}"
            return self.snapshot()

        try:
            self.makeCurrent()
            self._ensure_live2d_ready()

            model_cls = getattr(self.live2d, "LAppModel", None) or getattr(self.live2d, "Model", None)
            if model_cls is None:
                raise RuntimeError("No supported Live2D model class found.")

            self.model = model_cls()
            load_fn = getattr(self.model, "LoadModelJson", None)
            if not callable(load_fn):
                raise RuntimeError("Live2D model object has no LoadModelJson method.")

            load_fn(str(path))
            self.loaded = True
            self._resize_model()
            self.update()

        except Exception as exc:
            logger.exception("Failed to load Live2D model: %s", exc)
            self.last_error = str(exc)
            self.loaded = False

        return self.snapshot()

    def set_expression(self, expression_id: str) -> dict:
        if not self.model:
            self.last_error = "model is not loaded"
            return self.snapshot()

        expression_id = expression_id.strip()
        if not expression_id:
            return self.snapshot()

        try:
            self.model.SetExpression(expression_id)
            self.update()
        except Exception as exc:
            logger.warning("SetExpression failed: %s", exc)
            self.last_error = str(exc)

        return self.snapshot()

    def start_motion(self, group: str, index: int = 0, priority: int = 2) -> dict:
        if not self.model:
            self.last_error = "model is not loaded"
            return self.snapshot()

        try:
            try:
                self.model.StartMotion(group, index, priority)
            except TypeError:
                self.model.StartMotion(group, index)

            self.update()
        except Exception as exc:
            logger.warning("StartMotion failed: %s", exc)
            self.last_error = str(exc)

        return self.snapshot()

    def apply_payload(self, payload: dict) -> dict:
        character = payload.get("character") or {}

        expression = str(character.get("expression") or "").strip()
        motion_group = str(character.get("motion_group") or "").strip()
        motion_index = int(character.get("motion_index") or 0)
        motion_priority = int(character.get("motion_priority") or 2)

        if expression:
            self.set_expression(expression)

        if motion_group:
            self.start_motion(
                group=motion_group,
                index=motion_index,
                priority=motion_priority,
            )

        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "loaded": self.loaded,
            "model3_json": self.model3_json,
            "last_error": self.last_error,
            "canvas": {
                "width": self.width(),
                "height": self.height(),
            },
        }

    def initializeGL(self) -> None:
        try:
            self._ensure_live2d_ready()
        except Exception as exc:
            logger.exception("Live2D OpenGL init failed: %s", exc)
            self.last_error = str(exc)

    def resizeGL(self, width: int, height: int) -> None:
        self._resize_model(width=width, height=height)

    def paintGL(self) -> None:
        if not self.live2d:
            return

        clear = getattr(self.live2d, "clearBuffer", None)
        if callable(clear):
            try:
                clear()
            except Exception:
                pass

        if not self.model or not self.loaded:
            return

        try:
            update = getattr(self.model, "Update", None)
            draw = getattr(self.model, "Draw", None)

            if callable(update):
                update()
            if callable(draw):
                draw()
        except Exception as exc:
            logger.debug("Live2D paint failed: %s", exc)
            self.last_error = str(exc)

    def mouseMoveEvent(self, event) -> None:
        if not self.model:
            return

        x = event.position().x()
        y = event.position().y()
        nx = (x / max(self.width(), 1)) * 2.0 - 1.0
        ny = -((y / max(self.height(), 1)) * 2.0 - 1.0)

        drag = getattr(self.model, "Drag", None)
        if callable(drag):
            try:
                drag(float(nx), float(ny))
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        try:
            if self.live2d is not None:
                release = getattr(self.live2d, "glRelease", None)
                if callable(release):
                    release()
        except Exception:
            pass

        super().closeEvent(event)

    def _ensure_live2d_ready(self) -> None:
        if self.live2d is None:
            self.live2d = importlib.import_module("live2d.v3")

        init = getattr(self.live2d, "init", None)
        if callable(init):
            init()

        gl_init = getattr(self.live2d, "glInit", None)
        if callable(gl_init):
            gl_init()

    def _resize_model(self, width: int | None = None, height: int | None = None) -> None:
        if not self.model:
            return

        resize = getattr(self.model, "Resize", None)
        if not callable(resize):
            return

        try:
            resize(int(width or self.width()), int(height or self.height()))
        except Exception as exc:
            logger.debug("Live2D Resize failed: %s", exc)

    def _tick(self) -> None:
        if self.loaded:
            self.update()
