from __future__ import annotations

from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.state.redis_state_store import RedisStateStore

class PersonaManager:
    def __init__(
        self,
        loader: PersonaLoader,
        default_persona_id: str = "yzl",
        shared_state_store: RedisStateStore | None = None,
    ) -> None:
        self.loader = loader
        self.default_persona_id = default_persona_id
        self.shared_state_store = shared_state_store
        self._active_persona: PersonaRuntime | None = None
        self._active_persona_id = default_persona_id

    def load_default_persona(self) -> PersonaRuntime:
        persona_id = self.default_persona_id

        if self.shared_state_store is not None:
            shared_persona_id = (
                self.shared_state_store.get_active_persona_id()
            )
            if shared_persona_id:
                persona_id = shared_persona_id

        config = self.loader.load_persona(persona_id)
        self._active_persona_id = persona_id
        self._active_persona = PersonaRuntime(config)
        self.default_persona_id = persona_id
        return self._active_persona

    def get_active_persona(self) -> PersonaRuntime:
        if self.shared_state_store is None:
            if self._active_persona is None:
                return self.load_default_persona()
            return self._active_persona

        shared_persona_id = (
            self.shared_state_store.get_active_persona_id()
        )

        target_persona_id = (
            shared_persona_id
            or self.default_persona_id
        )

        if (
            self._active_persona is not None
            and self._active_persona_id == target_persona_id
        ):
            return self._active_persona

        config = self.loader.load_persona(target_persona_id)
        self._active_persona_id = target_persona_id
        self._active_persona = PersonaRuntime(config)
        self.default_persona_id = target_persona_id
        return self._active_persona
    
    def switch_persona(
        self,
        persona_id: str,
    ) -> PersonaRuntime:
        if not persona_id.strip():
            raise ValueError("persona_id must not be empty")

        # 先加载并校验，确保无效 persona 不会写入共享状态。
        config = self.loader.load_persona(persona_id)
        runtime = PersonaRuntime(config)

        if self.shared_state_store is not None:
            self.shared_state_store.set_active_persona_id(
                persona_id=persona_id,
                scope="global",
            )

        self._active_persona_id = persona_id
        self._active_persona = runtime
        self.default_persona_id = persona_id
        return runtime
    