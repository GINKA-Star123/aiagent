from __future__ import annotations

from dataclasses import dataclass,field
from pathlib import Path
from typing import Any

import yaml

@dataclass(frozen=True)
class CharacterProfile:
    character_id:str
    name:str
    aliases:list[str] = field(default_factory=list)
    visual_traits:list[str] = field(default_factory=list)
    related_characters:list[str] = field(default_factory=list)
    image_paths:list[Path] = field(default_factory=list)
    metadata:dict[str,Any] = field(default_factory=dict)

class CharacterRegistry:
    def __init__(
        self,
        root_dir:str|Path = "data/characters",
    ) ->None:
        self.root_dir =Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._profiles:dict[str,CharacterProfile] = {}

    def load(self) -> dict[str,CharacterProfile]:
        profiles: dict[str, CharacterProfile] = {}

        for profile_path in sorted(self.root_dir.glob("*/profile.yaml")):
            profile = self._load_profile(profile_path)
            profiles[profile.character_id] = profile
        
        self._profiles = profiles
        return dict(self._profiles)
    
    def all_profiles(self) ->list[CharacterProfile]:
        if not self._profiles:
            self.load()
        return list(self._profiles.values())
    
    def get(self,character_id:str) -> CharacterProfile:
        if not self._profiles:
            self.load()
        return self._profiles[character_id]
    
    def _load_profile(self,profile_path:Path) ->CharacterProfile:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

        character_dir = profile_path.parent
        image_dir = character_dir / "images"
        image_paths :list[Path] = []

        if image_dir.exists():
            for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                image_paths.extend(sorted(image_dir.glob(pattern)))

        character_id = str(raw.get("character_id") or character_dir.name).strip()
        name = str(raw.get("name") or character_id).strip()

        return CharacterProfile(
            character_id=character_id,
            name=name,
            aliases=[str(item).strip() for item in raw.get("aliases", []) if str(item).strip()],
            visual_traits=[str(item).strip() for item in raw.get("visual_traits", []) if str(item).strip()],
            related_characters=[str(item).strip() for item in raw.get("related_characters", []) if str(item).strip()],
            image_paths=image_paths,
            metadata={
                key: value
                for key, value in raw.items()
                if key not in {
                    "character_id",
                    "name",
                    "aliases",
                    "visual_traits",
                    "related_characters",
                }
            },
        )
