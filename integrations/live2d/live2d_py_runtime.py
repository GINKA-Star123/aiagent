from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from integrations.live2d.model_loader import Live2DModelLoader
from integrations.live2d.model_session import Live2DModelSession

logger = logging.getLogger(__name__)


class Live2DPyRuntime:
    DEFAULT_MODULE_CANDIDATES = (
        "live2d.v3",
        "live2d",
        "live2d_py",
        "pylive2d",
    )

    def __init__(
        self,
        *,
        module_candidates: tuple[str, ...] | None = None,
        model_loader: Live2DModelLoader | None = None,
    ) -> None:
        self.module_candidates = module_candidates or self.DEFAULT_MODULE_CANDIDATES
        self.model_loader = model_loader or Live2DModelLoader()
        self._module: Any | None = None
        self._module_name: str | None = None
        self._last_error: str = ""

    def status(self) -> dict[str, Any]:
        module = self._load_module()
        return {
            "available": module is not None,
            "module": self._module_name or "",
            "candidates": list(self.module_candidates),
            "last_error": self._last_error,
            "mode": "python_binding" if module is not None else "headless_validation",
        }

    def inspect_model(self, model3_json: str | Path) -> dict[str, Any]:
        report = self.model_loader.inspect_model3(model3_json)
        report["runtime"] = self.status()
        return report

    def prepare_model(self, model3_json: str | Path) -> dict[str, Any]:
        report = self.inspect_model(model3_json)
        summary = report.get("summary") or {}
        runtime = report.get("runtime") or {}

        prepared = bool(summary.get("loadable"))
        initialized = False
        warnings = list(report.get("warnings") or [])

        if not prepared:
            warnings.append("model_assets_not_loadable")
        elif runtime.get("available"):
            initialized = self._try_runtime_initialize()
            if not initialized:
                warnings.append("python_binding_detected_but_initialize_not_confirmed")
        else:
            warnings.append("python_binding_not_installed")

        return {
            "ok": prepared,
            "prepared": prepared,
            "initialized": initialized,
            "model3_json": str(model3_json),
            "runtime": runtime,
            "summary": summary,
            "warnings": warnings,
            "asset_report": report,
        }

    def _load_module(self) -> Any | None:
        if self._module is not None:
            return self._module

        errors: list[str] = []

        for module_name in self.module_candidates:
            try:
                self._module = importlib.import_module(module_name)
                self._module_name = module_name
                self._last_error = ""
                return self._module
            except Exception as exc:
                errors.append(f"{module_name}:{exc}")

        self._last_error = "; ".join(errors)
        return None

    def _try_runtime_initialize(self) -> bool:
        module = self._load_module()
        if module is None:
            return False

        for fn_name in ("init", "Init", "initialize", "Initialize"):
            fn = getattr(module, fn_name, None)
            if callable(fn):
                try:
                    fn()
                    return True
                except TypeError:
                    logger.debug("Live2D init function %s requires arguments.", fn_name)
                    return False
                except Exception as exc:
                    logger.warning("Live2D init function %s failed: %s", fn_name, exc)
                    return False

        return True
    

    def create_session(self) ->Live2DModelSession:
        module =self._load_module()
        if module is None:
            raise RuntimeError(f"Python Live2D binding is not available {self._last_error}")
        
        self._try_runtime_initialize()
        return Live2DModelSession(module)
    

    def load_model_session(
            self,
            model3_json:str|Path,
            *,
            prefer_lapp_model: bool = True,
    ) ->dict[str,Any]:
        prepared = self.prepare_model(model3_json)

        if not prepared.get("prepared"):
            return {
                "ok":False,
                "stage":"prepare_model",
                "prepared":prepared,
                "session":None,
            }
        
        try:
            session = self.create_session()
            session_state = session.load(
                model3_json=model3_json,
                prefer_lapp_model=prefer_lapp_model,
            )

            return {
                "ok":bool(session_state.get("loaded")),
                "stage":"load_model_session",
                "prepared":prepared,
                "session":session_state,
            }
        
        except Exception as exc:
            return {
                "ok":False,
                "stage":"load_model_session",
                "prepared":prepared,
                "session":None,
                "error":str(exc),
            }