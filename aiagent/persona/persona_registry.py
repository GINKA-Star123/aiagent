from __future__ import annotations

from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime


class PersonaRegistry:
    def __init__(self, loader: PersonaLoader, default_persona_id: str = "yzl") -> None:
        self.loader = loader
        self.default_persona_id = default_persona_id
        self._personas: dict[str, PersonaRuntime] = {}
        self._active_persona_id: str = default_persona_id

    def load_all(self) -> None:
        configs = self.loader.load_all()
        self._personas = {
            persona_id: PersonaRuntime(config)
            for persona_id, config in configs.items()
        }

        if self.default_persona_id not in self._personas and self._personas:
            self.default_persona_id = next(iter(self._personas.keys()))

        self._active_persona_id = self.default_persona_id

    def register_from_id(self, persona_id: str) -> PersonaRuntime:
        runtime = PersonaRuntime(self.loader.load_persona(persona_id))
        self._personas[persona_id] = runtime
        return runtime

    def get(self, persona_id: str) -> PersonaRuntime:
        if persona_id not in self._personas:
            return self.register_from_id(persona_id)
        return self._personas[persona_id]

    def get_active(self) -> PersonaRuntime:
        return self.get(self._active_persona_id)

    def set_active(self, persona_id: str) -> PersonaRuntime:
        runtime = self.get(persona_id)
        self._active_persona_id = persona_id
        return runtime

    def list_personas(self) -> list[str]:
        return list(self._personas.keys())
