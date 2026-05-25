from __future__ import annotations

import json
from datetime import datetime,timezone

from cloud.config import cloud_settings
from cloud.redis_client import get_redis_client
from aiagent.presence.models import SessionSnapshot

class PresenceStore:
    def __init__(self,prefix:str|None = None) ->None:
        self.prefix = prefix or cloud_settings.redis_prefix

    def _key(self,user_id:str) ->str:
        safe_user_id = user_id.replace("","_")[:128]
        return f"{self.prefix}:presence:session:{safe_user_id}"
    
    async def get_snapshot(self,user_id:str,username:str ="guest") -> SessionSnapshot:
        redis = get_redis_client()
        if redis is None:
            return SessionSnapshot(user_id=user_id,username=username)
        
        raw = await redis.get(self._key(user_id)) # type: ignore
        if not raw:
            return SessionSnapshot(user_id=user_id,username=username)   
        
        try:
            data = json.loads(raw)
            snapshot = SessionSnapshot.model_validate(data)
            snapshot.username = username or snapshot.username
            return snapshot
        
        except:
            return SessionSnapshot(user_id=user_id,username=username)   
        
    async def save_snapshot(self,snapshot:SessionSnapshot,ttl_seconds: int = 60 * 60 * 24 * 90) ->None:
        redis = await get_redis_client()
        if redis is None:
            return
        
        payload = snapshot.model_dump(mode="json")
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await redis.set(self._key(snapshot.user_id),json.dumps(payload,ensure_ascii=False),ex=ttl_seconds)