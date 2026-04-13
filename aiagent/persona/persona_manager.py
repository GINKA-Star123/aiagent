"""Runtime persona management."""

from pathlib import Path

from aiagent.persona.persona_loader import PersonaLoader
from aiagent.schemas.persona import PersonaConfig
from config.paths import CHARACTER_DIR


class PersonaManager:
    """Manages personas for AI agents."""

    def __init__(self, loader: PersonaLoader):
        self.loader = loader
        self._active_persona : PersonaConfig | None = None # type: ignore

    def load_default_persona(self) -> PersonaConfig:

        persona_path = CHARACTER_DIR /"yzl" /"persona.yaml"
        self._active_persona = self.loader.load_from_file(persona_path)
        return self._active_persona

    def get_active_persona(self) -> PersonaConfig:
        if self._active_persona is None:
            return self.load_default_persona()
        return self._active_persona