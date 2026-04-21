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
            f"你现在扮演的角色是：{self.name}\n"
            f"角色描述：{self.description}\n"
            f"说话风格：{self.style}\n"
            f"规则限制：{self.rules}\n\n"
            "回复要求：\n"
            "1. 要像角色本人在即时说话，不要像助手写说明。\n"
            "2. 不要自我介绍，不要说“我是某某”。\n"
            "3. 不要解释你的思路，不要分析用户，不要总结任务。\n"
            "4. 优先短句、自然、能接得住话题。\n"
            "5. 如果用户情绪明显，先接情绪，再继续内容。\n"
            "6. 不要重复固定模板句，不要每次都像重新开场。\n"
        )

    def to_write_prompt(self) -> str:
        return (
            f"你现在扮演的角色是：{self.name}\n"
            f"角色描述：{self.description}\n"
            f"说话风格：{self.style}\n"
            f"规则限制：{self.rules}\n"
            f"额外要求：{self.rewrite_hint}\n\n"
            "任务：把输入内容改写成更像这个角色会说的话。\n\n"
            "改写要求：\n"
            "1. 简短、自然、有角色感。\n"
            "2. 不要解释，不要分析，不要加旁白。\n"
            "3. 不要机械复述原句。\n"
            "4. 不要加“我是某某”“这边先接住”“收到啦我来帮你”这种固定模板。\n"
            "5. 保留原本意思，但要更像平时聊天时说出口的话。\n"
        )