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

    def rebuild_knowledge(self, force_rebuild: bool = True) -> dict[str, Any]:
        return self._request(
            "POST",
            "/knowledge/rebuild",
            json_body={"force_rebuild": force_rebuild},
        )

    def get_runtime_snapshot(self, user_id: str) -> dict[str, Any]:
        health = self.get_health()
        control = self.get_control_status()
        voice = self.get_voice_state()
        memory = self.get_user_memory(user_id)
        memory_stats = self.get_memory_stats(user_id)
        knowledge = self.get_knowledge_stats()

        return {
            "health": health,
            "control": control,
            "voice": voice,
            "memory": memory,
            "memory_stats": memory_stats,
            "knowledge": knowledge,
        }

    def run_startup_check(self, user_id: str) -> dict[str, Any]:
        checks: dict[str, Any] = {
            "backend_health": {"ok": False},
            "control_status": {"ok": False},
            "voice_state": {"ok": False},
            "memory_stats": {"ok": False},
            "knowledge_stats": {"ok": False},
        }

        overall_ok = True

        try:
            checks["backend_health"] = self.get_health()
        except Exception as exc:
            overall_ok = False
            checks["backend_health"] = {"ok": False, "error": str(exc)}

        try:
            checks["control_status"] = self.get_control_status()
        except Exception as exc:
            overall_ok = False
            checks["control_status"] = {"ok": False, "error": str(exc)}

        try:
            checks["voice_state"] = self.get_voice_state()
        except Exception as exc:
            overall_ok = False
            checks["voice_state"] = {"ok": False, "error": str(exc)}

        try:
            checks["memory_stats"] = self.get_memory_stats(user_id)
        except Exception as exc:
            overall_ok = False
            checks["memory_stats"] = {"ok": False, "error": str(exc)}

        try:
            checks["knowledge_stats"] = self.get_knowledge_stats()
        except Exception as exc:
            overall_ok = False
            checks["knowledge_stats"] = {"ok": False, "error": str(exc)}

        return {
            "ok": overall_ok,
            "checks": checks,
        }

    @staticmethod
    def pretty_json(data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
