from __future__ import annotations

from dataclasses import dataclass

@dataclass
class PersonaGuardResult:
    text:str
    changed:bool
    reasons:list[str]

class PersonaGuard:
    forbidden_phrases = [
        "作为AI",
        "作为一个AI",
        "作为语言模型",
        "我是人工智能",
        "我是一个人工智能",
        "我是AI助手",
        "作为助手",
    ]

    cold_phrases = [
        "以下是",
        "综上所述",
        "需要注意的是",
        "用户您好",
        "很高兴为您服务",
    ]

    def normalize(self, text: str) -> PersonaGuardResult:
        original = text or ""
        result = original.strip()
        reasons: list[str] = []

        for phrase in self.forbidden_phrases:
            if phrase in result:
                result = result.replace(phrase, "阿绫")
                reasons.append(f"removed_forbidden:{phrase}")

        for phrase in self.cold_phrases:
            if phrase in result:
                result = result.replace(phrase, "")
                reasons.append(f"softened_cold_phrase:{phrase}")

        result = self._trim_repeated_prefix(result)

        if self._looks_too_cold(result):
            result = self._add_light_persona_tail(result)
            reasons.append("added_persona_tail")

        return PersonaGuardResult(
            text=result.strip(),
            changed=result.strip() != original.strip(),
            reasons=reasons,
        )

    def normalize_reply(self, text: str) -> str:
        """Return the normalized reply text expected by PersonaRuntime."""
        return self.normalize(text).text

    def validate_reply(self, text: str, config=None) -> list[str]:
        """Return lightweight persona-safety issues for downstream metadata.

        `config` is accepted for compatibility with PersonaRuntime and future
        persona-specific rules. The current checks stay conservative so they do
        not block normal replies.
        """
        result = text or ""
        issues: list[str] = []

        for phrase in self.forbidden_phrases:
            if phrase in result:
                issues.append(f"forbidden_phrase:{phrase}")

        for phrase in self.cold_phrases:
            if phrase in result:
                issues.append(f"cold_phrase:{phrase}")

        if not result.strip():
            issues.append("empty_reply")

        return issues

    def _trim_repeated_prefix(self, text: str) -> str:
        prefixes = ["阿绫觉得，", "阿绫认为，", "嗯，"]
        for prefix in prefixes:
            doubled = prefix + prefix
            while doubled in text:
                text = text.replace(doubled, prefix)
        return text

    def _looks_too_cold(self, text: str) -> bool:
        if not text:
            return False

        if "阿绫" in text:
            return False

        if any(mark in text for mark in ["啦", "呀", "哦", "嘛", "嗯"]):
            return False

        return len(text) >= 40

    def _add_light_persona_tail(self, text: str) -> str:
        return f"{text} 嗯，阿绫把重点先给你放在这里。"
