from __future__ import annotations 

from typing import Any

from aiagent.memory.mem0_memory import MemoryHit
from aiagent.schemas.memory import MemoryLayer, MemorySnapshot

class NullLongTermMemory:
    def __init__(self,reason:str = "Long-term memory is disabled") ->None:
        self.reason = reason

    def graph_status(self) ->dict[str,Any]:
        return {
            "enabled":False,
            "status":"disabled",
            "reason":self.reason,
        }

    def search(
            self,
            query:str,
            user_id:str,
            agent_id :str ="yzl",
            limit: int =6
    ) ->list[MemoryHit]:
        return []

    def add_turn(
            self,
            user_id:str,
            user_name:str,
            user_text:str,
            assistant_text:str,
            session_id:str,
            turn_id:str,
            agent_id:str = "yzl",
            metadata:dict[str,Any] | None = None
    )->dict[str,Any]:
        return {
            "ok":False,
            "status":"skipped",
            "degraded":True,
            "reason":self.reason,
            "user_id":user_id,
            "agent_id":agent_id,
        }

    def get_all(
            self,
            user_id:str,
            agent_id:str = "yzl",
            limit:int = 20
    ) ->list[dict[str,Any]]:
        return []

    def delete_all(self, user_id: str, agent_id: str = "yzl") -> dict[str, Any]:
        return {
            "ok": True,
            "status": "cleared",
            "degraded": True,
            "reason": self.reason,
            "user_id": user_id,
            "agent_id": agent_id,
        }

    def format_for_prompt(self, hits: list[MemoryHit]) -> str:
        return "无长期记忆。"

    def list_records(
            self,
            user_id: str,
            agent_id: str = "yzl",
            limit: int | None = 200,
    ) -> list[Any]:
        return []

    def list_layer_records(
            self,
            user_id:str,
            layer:MemoryLayer|str,
            agent_id: str = "yzl",
            limit: int | None = 200,
    ) -> list[Any]:
        return []

    def list_profile_memories(
            self,
            user_id: str,
            agent_id: str = "yzl",
            limit: int | None = 200,
    ) -> list[Any]:
        return []

    def get_snapshot(
            self,
            user_id: str,
            agent_id: str ="yzl",
            limit: int | None = 200
    ) -> MemorySnapshot:
        return MemorySnapshot(
            user_id=user_id,
            agent_id=agent_id,
            total=0,
            layers=[],
        )

    def delete_memory(
            self,
            memory_id: str
    ) -> dict[str,Any]:
        return {
            "ok":False,
            "status":"skipped",
            "degraded":True,
            "reason":self.reason,
            "memory_id":memory_id
        }

    def delete_layer(
    self,
    user_id: str,
    layer: MemoryLayer | str,
    agent_id: str = "yzl",
    limit: int | None = 1000,
) -> dict[str, Any]:
        layer_value = layer.value if isinstance(layer, MemoryLayer) else str(layer)
        return {
            "ok": True,
            "status": "skipped",
            "degraded": True,
            "reason": self.reason,
            "user_id": user_id,
            "agent_id": agent_id,
            "layer": layer_value,
            "deleted_count": 0,
            "deleted_ids": [],
            "errors": [],
        }

    def get_memory_record(self, memory_id: str, user_id: str, agent_id: str = "yzl"):
        return None

    def update_memory(self, **kwargs) -> dict[str, Any]:
        user_id = str(kwargs.get("user_id") or "")
        memory_id = str(kwargs.get("memory_id") or "")
        agent_id = str(kwargs.get("agent_id") or "yzl")

        return {
            "ok": False,
            "status": "not_found",
            "degraded": True,
            "reason": "memory_not_found_or_not_owned_by_user",
            "user_id": user_id,
            "agent_id": agent_id,
            "memory_id": memory_id,
            "degraded_reason": self.reason,
        }

    def set_memory_pinned(self, **kwargs) -> dict[str, Any]:
        user_id = str(kwargs.get("user_id") or "")
        memory_id = str(kwargs.get("memory_id") or "")
        agent_id = str(kwargs.get("agent_id") or "yzl")

        return {
            "ok": False,
            "status": "not_found",
            "degraded": True,
            "reason": "memory_not_found_or_not_owned_by_user",
            "user_id": user_id,
            "agent_id": agent_id,
            "memory_id": memory_id,
            "degraded_reason": self.reason,
        }

    def merge_memories(self, **kwargs) -> dict[str, Any]:
        user_id = str(kwargs.get("user_id") or "")
        agent_id = str(kwargs.get("agent_id") or "yzl")
        memory_ids = kwargs.get("memory_ids") or []

        return {
            "ok": False,
            "status": "skipped",
            "degraded": True,
            "reason": "merge_requires_at_least_two_memories",
            "user_id": user_id,
            "agent_id": agent_id,
            "memory_ids": list(memory_ids) if isinstance(memory_ids, list) else [],
            "degraded_reason": self.reason,
        }

    def list_pinned_records(
            self,
            user_id: str,
            agent_id: str = "yzl",
            limit: int | None = 8,
    ) -> list[Any]:
        return []