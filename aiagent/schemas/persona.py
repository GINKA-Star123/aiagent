"""Persona schema definitions."""

from pydantic import BaseModel

class PersonaConfig(BaseModel):
    name :str
    description :str
    style : str
    rules : str
    greeting: str = ""
    rewrite_hint : str=""

    def to_system_prompt(self) -> str:
        return (
            f"你现在扮演角色：{self.name}\n"
            f"角色描述：{self.description}\n"
            f"说话风格：{self.style}\n"
            f"规则：{self.rules}\n"
            "请用自然、简短、符合角色性格的方式回复。"
        )
    

    def to_write_prompt(self) ->str:
        return (
            f"你现在扮演角色：{self.name}\n"
            f"角色描述：{self.description}\n"
            f"说话风格：{self.style}\n"
            f"规则：{self.rules}\n"
            f"额外要求：{self.rewrite_hint}\n"
            "请把输入内容改写成更像角色说的话。\n"
            "要求：简短、自然、有角色感，不要解释，不要分析。"
        )