from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


class APIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def close(self) -> None:
        pass

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(timeout=120, trust_env=False) as client:
            response = client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json_body,
                files=files,
            )
        return self._parse_response(response, f"{method} {path}")

    def _parse_response(self, response: httpx.Response, api_name: str) -> dict[str, Any]:
        try:
            data = response.json()
        except Exception:
            data = {
                "ok": False,
                "error": response.text or f"http {response.status_code}",
            }

        if response.is_error or data.get("ok") is False:
            raise RuntimeError(
                f"{api_name} failed: {response.status_code}\n"
                f"{data.get('error', '')}\n\n"
                f"{data.get('traceback', '')}"
            )

        return data

    def get_health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def send_chat(self, user_id: str, username: str, text: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/chat",
            json_body={
                "user_id": user_id,
                "username": username,
                "text": text,
            },
        )

    def transcribe_audio(self, audio_path: str) -> dict[str, Any]:
        path = Path(audio_path)
        with path.open("rb") as file_obj:
            files = {
                "file": (path.name, file_obj, "audio/wav"),
            }
            return self._request("POST", "/voice/transcribe", files=files)

    def get_voice_state(self) -> dict[str, Any]:
        return self._request("GET", "/voice/state")

    def interrupt_voice(self, reason: str = "desktop_interrupt") -> dict[str, Any]:
        return self._request(
            "POST",
            "/voice/interrupt",
            json_body={"reason": reason},
        )

    def get_user_memory(self, user_id: str) -> dict[str, Any]:
        return self._request("GET", f"/memory/user/{user_id}")

    def get_memory_stats(self, user_id: str) -> dict[str, Any]:
        return self._request("GET", f"/memory/user/{user_id}/stats")

    def search_user_memory(self, user_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        encoded_query = quote(query, safe="")
        return self._request(
            "GET",
            f"/memory/user/{user_id}/search?query={encoded_query}&limit={limit}",
        )


    def send_multimodal_chat(
        self,
        user_id: str,
        username: str,
        text: str,
        image_path: str | None = None,
    ) -> dict[str, Any]:
        if not image_path:
            return self.send_chat(
                user_id=user_id,
                username=username,
                text=text,
            )

        path = Path(image_path)
        with path.open("rb") as file_obj:
            files = {
                "file": (path.name, file_obj, self._guess_image_mime(path)),
            }
            data = {
                "user_id": user_id,
                "username": username,
                "text": text,
            }

            with httpx.Client(timeout=240, trust_env=False) as client:
                response = client.post(
                    f"{self.base_url}/chat/multimodal",
                    data=data,
                    files=files,
                )

            return self._parse_response(response, "POST /chat/multimodal")

    def _guess_image_mime(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".png":
            return "image/png"
        if suffix == ".webp":
            return "image/webp"
        return "application/octet-stream"

    def clear_user_memory(self, user_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/memory/user/{user_id}")

    def get_control_status(self) -> dict[str, Any]:
        return self._request("GET", "/control/status")

    def pause_dialogue(self) -> dict[str, Any]:
        return self._request("POST", "/control/pause", json_body={"paused": True})

    def resume_dialogue(self) -> dict[str, Any]:
        return self._request("POST", "/control/resume")

    def reset_context(self) -> dict[str, Any]:
        return self._request("POST", "/control/reset-context")

    def get_knowledge_stats(self) -> dict[str, Any]:
        return self._request("GET", "/knowledge/stats")

    def get_knowledge_rebuild_status(self) -> dict[str, Any]:
        return self._request("GET", "/knowledge/rebuild/status")

    def get_runtime_diagnostics(self) -> dict[str, Any]:
        return self._request("GET", "/runtime/diagnostics")

    def search_knowledge(self, query: str, top_k: int = 4) -> dict[str, Any]:
        return self._request(
            "POST",
            "/knowledge/search",
            json_body={
                "query": query,
                "top_k": top_k,
                "include_prompt_context": True,
            },
        )

    def rebuild_knowledge(self, force_rebuild: bool = True, async_rebuild: bool = True) -> dict[str, Any]:
        return self._request(
            "POST",
            "/knowledge/rebuild",
            json_body={
                "force_rebuild": force_rebuild,
                "async_rebuild": async_rebuild,
            },
        )

    def get_runtime_snapshot(self, user_id: str) -> dict[str, Any]:
        return {
            "health": self.get_health(),
            "diagnostics": self.get_runtime_diagnostics(),
            "control": self.get_control_status(),
            "voice": self.get_voice_state(),
            "memory": self.get_user_memory(user_id),
            "memory_stats": self.get_memory_stats(user_id),
            "knowledge": self.get_knowledge_stats(),
            "knowledge_rebuild": self.get_knowledge_rebuild_status(),
        }

    def run_startup_check(self, user_id: str) -> dict[str, Any]:
        checks: dict[str, Any] = {
            "backend_health": {"ok": False},
            "runtime_diagnostics": {"ok": False},
            "control_status": {"ok": False},
            "voice_state": {"ok": False},
            "memory_stats": {"ok": False},
            "knowledge_stats": {"ok": False},
            "knowledge_rebuild_status": {"ok": False},
        }

        overall_ok = True

        for name, fn in {
            "backend_health": self.get_health,
            "runtime_diagnostics": self.get_runtime_diagnostics,
            "control_status": self.get_control_status,
            "voice_state": self.get_voice_state,
            "memory_stats": lambda: self.get_memory_stats(user_id),
            "knowledge_stats": self.get_knowledge_stats,
            "knowledge_rebuild_status": self.get_knowledge_rebuild_status,
        }.items():
            try:
                checks[name] = fn()
                if name == "runtime_diagnostics" and checks[name].get("status") == "failed":
                    overall_ok = False
            except Exception as exc:
                overall_ok = False
                checks[name] = {"ok": False, "error": str(exc)}

        return {
            "ok": overall_ok,
            "checks": checks,
        }

    @staticmethod
    def pretty_json(data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
