"""Persona schema definitions."""

from pydantic import BaseModel

class PersonaConfig(BaseModel):
    name :str
    description :str
    style : str
    rules : str

    def to_system_prompt(self) -> str:
        return (
            f"你现在扮演角色：{self.name}\n"
            f"角色描述：{self.description}\n"
            f"说话风格：{self.style}\n"
            f"规则：{self.rules}\n"
            "请用自然、简短、适合直播互动的方式回复。"
        )