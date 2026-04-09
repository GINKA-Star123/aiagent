"""Manage sessions, rooms, and runtime contexts."""

from aiagent.schemas.inputs import InputEvent

class SessionManager:
    def resolve_session_id(self,event:InputEvent) ->str:
        return f"{event.source}:{event.user_id}"
    