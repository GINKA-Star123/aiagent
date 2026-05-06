from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aiagent.live2d.models import  (
    Live2DCharacterProfile,
    Live2DBackgroundProfile,
)

class Live2DRegistry:
    def __init__(
            self,
            character_root:str|Path = "data/live2d/characters",
            background_root:str|Path = "data/live2d/backgrounds",
    ) ->None:
        self.character_root = Path(character_root)
        self.background_root = Path(background_root)

        self.character_root.mkdir(parents=True, exist_ok=True)
        self.background_root.mkdir(parents=True, exist_ok=True)

        self._characters:dict[str,Live2DCharacterProfile] = {}
        self._backgrounds:dict[str,Live2DBackgroundProfile] = {}

    def load(self)->None:
        self._characters = self._load_characters()
        self._backgrounds = self._load_backgrounds()

    def get_character(self,character_id:str) ->Live2DCharacterProfile:
        if not self._characters:
            self.load()

        profile = self._characters.get(character_id)
        if profile is not None:
            return profile
        
        fallback = self._characters.get("yzl")
        if fallback is not None:
            return fallback

        raise RuntimeError(f"Character {character_id} not found")
    
    def get_background(self,background_id:str) ->Live2DBackgroundProfile:
        if not self._backgrounds:
            self.load()

        profile = self._backgrounds.get(background_id)
        if profile is not None:
            return profile
        
        fallback = self._backgrounds.get("room_default")
        if fallback is not None:
            return fallback

        raise RuntimeError(f"Background {background_id} not found")
    
    def all_characters(self) ->list[Live2DCharacterProfile]:
        if not self._characters:
            self.load()

        return list(self._characters.values())
    
    def all_backgrounds(self) ->list[Live2DBackgroundProfile]:
        if not self._backgrounds:
            self.load()

        return list(self._backgrounds.values())
    
    def stats(self) ->dict[str,Any]:
        if not self._characters or not self._backgrounds:
            self.load()

        return {
            "character_count": len(self._characters),
            "background_count": len(self._backgrounds),
            "characters": list(self._characters.keys()),
            "backgrounds": list(self._backgrounds.keys()),
        }
    
    def _load_characters(self) ->dict[str,Live2DCharacterProfile]:
        result:dict[str,Live2DCharacterProfile] = {}

        for profile_path in self.character_root.glob("*/profile.yaml"):
            raw = self._read_yaml(profile_path)
            if not raw:
                continue
            profile = Live2DCharacterProfile(**raw)
            result[profile.character_id] = profile

        return result
    
    def _load_backgrounds(self) ->dict[str,Live2DBackgroundProfile]:
        result:dict[str,Live2DBackgroundProfile] = {}

        for profile_path in self.background_root.glob("*.yaml"):
            raw = self._read_yaml(profile_path)
            if not raw:
                continue
            profile = Live2DBackgroundProfile(**raw)
            result[profile.background_id] = profile

        for profile_path in self.background_root.glob("*/profile.yaml"):
            raw = self._read_yaml(profile_path)
            if not raw:
                continue
            profile = Live2DBackgroundProfile(**raw)
            result[profile.background_id] = profile

        return result
    
    def _read_yaml(self,path:Path) ->dict[str,Any]:
        if not path.exists():
            return {}

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
