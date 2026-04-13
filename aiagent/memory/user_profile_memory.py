"""Per-user memory and profile aggregation."""
from collections import defaultdict

from aiagent.schemas.memory import MemoryItem,MemoryKind


class UserProfileMemory:

    def __init__(self) ->None:
        self._profiles : dict[str,list[MemoryItem]] = defaultdict(list) 
        
    def add_memory(self, item:MemoryItem) ->None:

        self._profiles[item.user_id].append(item)

    def recall_for_user(self, user_id:str,limit: int = 5)->list[MemoryItem]:
        """Recall recent memories for a user."""
        
        items= self._profiles.get(user_id, [])
        return items[-limit:]
    
    def summarize_for_prompt(self,user_id:str,limit:int = 5) -> str:

        items = self.recall_for_user(user_id, limit)
        if not items:
            return "No memories found for this user."
        
        lines = [f"{item.kind.value}: {item.content}" for item in items]

        return "\n".join(lines)