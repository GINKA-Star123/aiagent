"""Memory storage adapter."""
from __future__ import annotations

from aiagent.memory.long_term_memory import LongTermMemory
from aiagent.memory.user_profile_memory import UserProfileMemory
from aiagent.schemas.memory import MemoryItem


class MemoryStore:
    def store_profile_memories(
        self,
        user_profile_memory: UserProfileMemory,
        items: list[MemoryItem],
    ) -> int:
        if not items:
            return 0

        user_profile_memory.add_memories(items)
        return len(items)

    def store_long_term_memories(
        self,
        long_term_memory: LongTermMemory,
        items: list[MemoryItem],
    ) -> int:
        if not items:
            return 0

        return long_term_memory.add_memories(items)
