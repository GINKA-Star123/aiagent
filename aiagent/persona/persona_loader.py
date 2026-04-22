"""人格载入"""

from __future__ import annotations

from pathlib import Path

import yaml

from aiagent.persona.persona_models import PersonaConfig

class PersonaLoader:
    def __init__(self, base_dir: str | Path = "data/characters") -> None:
        self.base_dir = Path(base_dir)

    def load_from_file(self, file_path: str | Path) -> PersonaConfig:
        path = Path(file_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Persona yaml must be a mapping: {path}")
        return PersonaConfig(**data)

    def load_persona(self, persona_id: str) -> PersonaConfig:
        persona_file = self.base_dir / persona_id / "persona.yaml"
        if not persona_file.exists():
            raise FileNotFoundError(f"Persona file not found: {persona_file}")
        return self.load_from_file(persona_file)

    def load_all(self) -> dict[str, PersonaConfig]:
        personas: dict[str, PersonaConfig] = {}
        if not self.base_dir.exists():
            return personas

        for child in self.base_dir.iterdir():
            if not child.is_dir():
                continue

            persona_file = child / "persona.yaml"
            if not persona_file.exists():
                continue

            config = self.load_from_file(persona_file)
            personas[config.persona_id] = config

        return personas