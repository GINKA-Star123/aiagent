from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Live2DSessionState:
    model3_json: str
    loaded: bool = False
    model_class: str = ""
    canvas_size: list[float] = field(default_factory=list)
    canvas_size_pixel: list[float] = field(default_factory=list)
    expression_ids: list[str] = field(default_factory=list)
    motion_groups: list[str] = field(default_factory=list)
    parameter_ids: list[str] = field(default_factory=list)
    drawable_ids: list[str] = field(default_factory=list)
    part_ids: list[str] = field(default_factory=list)
    current_expression: str = ""
    current_motion_group: str = ""
    current_motion_index: int = -1
    last_error: str = ""


class Live2DModelSession:
    def __init__(self, live2d_module: Any) -> None:
        self.live2d = live2d_module
        self.model: Any | None = None
        self.state = Live2DSessionState(model3_json="")

    def load(self, model3_json: str | Path, prefer_lapp_model: bool = True) -> dict[str, Any]:
        model_path = Path(model3_json)
        self.state = Live2DSessionState(model3_json=str(model_path))

        if not model_path.exists():
            self.state.last_error = f"model3_json not found: {model_path}"
            return self.snapshot()

        try:
            model_cls = self._select_model_class(prefer_lapp_model=prefer_lapp_model)
            self.model = model_cls()
            self.state.model_class = getattr(model_cls, "__name__", str(model_cls))

            load_fn = getattr(self.model, "LoadModelJson", None)
            if not callable(load_fn):
                raise RuntimeError("Live2D model object has no LoadModelJson method.")

            load_fn(str(model_path))
            self.state.loaded = True
            self._refresh_static_info()

        except Exception as exc:
            logger.exception("Failed to load Live2D model: %s", exc)
            self.state.loaded = False
            self.state.last_error = str(exc)

        return self.snapshot()

    def update(self) -> dict[str, Any]:
        if self.model is None:
            self.state.last_error = "model is not loaded"
            return self.snapshot()

        update_fn = getattr(self.model, "Update", None)
        if callable(update_fn):
            try:
                update_fn()
            except Exception as exc:
                logger.warning("Live2D model update failed: %s", exc)
                self.state.last_error = str(exc)

        return self.snapshot()

    def set_expression(self, expression_id: str) -> dict[str, Any]:
        if self.model is None:
            self.state.last_error = "model is not loaded"
            return self.snapshot()

        expression_id = expression_id.strip()
        if not expression_id:
            return self.snapshot()

        fn = getattr(self.model, "SetExpression", None)
        if callable(fn):
            try:
                fn(expression_id)
                self.state.current_expression = expression_id
            except Exception as exc:
                logger.warning("SetExpression failed: %s", exc)
                self.state.last_error = str(exc)

        return self.snapshot()

    def start_motion(
        self,
        group: str,
        index: int = 0,
        priority: int | None = None,
    ) -> dict[str, Any]:
        if self.model is None:
            self.state.last_error = "model is not loaded"
            return self.snapshot()

        group = group.strip()
        if not group:
            return self.snapshot()

        fn = getattr(self.model, "StartMotion", None)
        if callable(fn):
            try:
                if priority is None:
                    fn(group, index)
                else:
                    fn(group, index, priority)

                self.state.current_motion_group = group
                self.state.current_motion_index = index
            except TypeError:
                try:
                    fn(group, index)
                    self.state.current_motion_group = group
                    self.state.current_motion_index = index
                except Exception as exc:
                    logger.warning("StartMotion failed: %s", exc)
                    self.state.last_error = str(exc)
            except Exception as exc:
                logger.warning("StartMotion failed: %s", exc)
                self.state.last_error = str(exc)

        return self.snapshot()

    def drag(self, x: float, y: float) -> dict[str, Any]:
        if self.model is None:
            self.state.last_error = "model is not loaded"
            return self.snapshot()

        fn = getattr(self.model, "Drag", None)
        if callable(fn):
            try:
                fn(float(x), float(y))
            except Exception as exc:
                logger.warning("Drag failed: %s", exc)
                self.state.last_error = str(exc)

        return self.snapshot()

    def resize(self, width: int, height: int) -> dict[str, Any]:
        if self.model is None:
            self.state.last_error = "model is not loaded"
            return self.snapshot()

        fn = getattr(self.model, "Resize", None)
        if callable(fn):
            try:
                fn(int(width), int(height))
            except Exception as exc:
                logger.warning("Resize failed: %s", exc)
                self.state.last_error = str(exc)

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "model3_json": self.state.model3_json,
            "loaded": self.state.loaded,
            "model_class": self.state.model_class,
            "canvas_size": self.state.canvas_size,
            "canvas_size_pixel": self.state.canvas_size_pixel,
            "expression_ids": self.state.expression_ids,
            "motion_groups": self.state.motion_groups,
            "parameter_ids": self.state.parameter_ids,
            "drawable_ids": self.state.drawable_ids,
            "part_ids": self.state.part_ids,
            "current_expression": self.state.current_expression,
            "current_motion_group": self.state.current_motion_group,
            "current_motion_index": self.state.current_motion_index,
            "last_error": self.state.last_error,
        }

    def _select_model_class(self, prefer_lapp_model: bool):
        if prefer_lapp_model and hasattr(self.live2d, "LAppModel"):
            return getattr(self.live2d, "LAppModel")

        if hasattr(self.live2d, "Model"):
            return getattr(self.live2d, "Model")

        if hasattr(self.live2d, "LAppModel"):
            return getattr(self.live2d, "LAppModel")

        raise RuntimeError("No supported Live2D model class found.")

    def _refresh_static_info(self) -> None:
        if self.model is None:
            return

        self.state.canvas_size = self._safe_list("GetCanvasSize")
        self.state.canvas_size_pixel = self._safe_list("GetCanvasSizePixel")
        self.state.expression_ids = self._safe_list("GetExpressionIds")
        self.state.motion_groups = self._safe_list("GetMotionGroups")
        self.state.parameter_ids = self._safe_list("GetParamIds")
        self.state.drawable_ids = self._safe_list("GetDrawableIds")
        self.state.part_ids = self._safe_list("GetPartIds")

        if not self.state.parameter_ids:
            self.state.parameter_ids = self._safe_list("GetParameterIds")

    def _safe_list(self, method_name: str) -> list[Any]:
        if self.model is None:
            return []

        fn = getattr(self.model, method_name, None)
        if not callable(fn):
            return []

        try:
            value = fn()
        except Exception:
            return []

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        try:
            return list(value)
        except TypeError:
            return [value]
