from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class DesktopIdentity(BaseModel):
    user_id: str
    username: str
    profile_version: int = Field(default=1)


class DesktopIdentityStore:
    def __init__(self, file_path: str | Path = "data/app_state/desktop_user.json") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_identity(self) -> DesktopIdentity | None:
        if not self.file_path.exists():
            return None

        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        return DesktopIdentity(**data)

    def create_identity(self, username: str) -> DesktopIdentity:
        normalized_username = username.strip() or "Guest"
        safe_name = self._normalize_username(normalized_username)
        identity = DesktopIdentity(
            user_id=f"desktop_{safe_name}_{uuid4().hex[:12]}",
            username=normalized_username,
        )
        self.save_identity(identity)
        return identity

    def save_identity(self, identity: DesktopIdentity) -> None:
        self.file_path.write_text(
            identity.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def update_username(self, username: str) -> DesktopIdentity:
        identity = self.load_identity()
        if identity is None:
            return self.create_identity(username)

        new_name = username.strip() or identity.username
        identity.username = new_name
        self.save_identity(identity)
        return identity

    def rebuild_identity(self, username: str) -> DesktopIdentity:
        identity = self.create_identity(username)
        return identity

    def clear_identity(self) -> None:
        if self.file_path.exists():
            self.file_path.unlink()

    def _normalize_username(self, username: str) -> str:
        chars: list[str] = []
        for char in username.lower():
            if char.isalnum() or "\u4e00" <= char <= "\u9fff":
                chars.append(char)
            elif char in {" ", "-", "_"}:
                chars.append("_")

        normalized = "".join(chars).strip("_")
        return normalized or "guest"
