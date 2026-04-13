"""Memory storage adapter."""

from aiagent.schemas.inputs import  InputEvent
from aiagent.schemas.memory import MemoryItem,MemoryKind

class MemoryStore:
    def should_store_user_profile(self,event:InputEvent) -> bool:
        keywords = ["我叫", "我喜欢", "我是", "我明天", "我今天", "记住", "我最近"]
        return any(keyword in event.text for keyword in keywords)
    
    def build_user_profile_memory(self,event:InputEvent) -> MemoryItem:
        
        return MemoryItem(
            user_id = event.user_id,
            username = event.user_name,
            content =event.text,
            kind = MemoryKind.USER_PORFILE,
            importance = 0.7,
        )