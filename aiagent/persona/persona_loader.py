"""Load persona configuration from data files."""
from pathlib import Path

import yaml

from aiagent.schemas.persona import PersonaConfig


class PersonaLoader:
    """Load persona configuration from data files."""

    def load_from_file(self,file_path: Path|str) -> PersonaConfig:
        """Load persona configuration from a YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Persona file not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return PersonaConfig(**data)
