"""Safety and text normalization layer."""
from __future__ import annotations

import re


class SafetyGuard:
    def filter_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text.strip()

        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 清理常见异常空格
        cleaned = cleaned.replace(" ，", "，").replace(" 。", "。").replace(" ？", "？").replace(" ！", "！")
        cleaned = cleaned.replace("( ", "(").replace(" )", ")")

        # 合并重复标点
        cleaned = re.sub(r"[。]{2,}", "。", cleaned)
        cleaned = re.sub(r"[！!]{2,}", "！", cleaned)
        cleaned = re.sub(r"[？?]{2,}", "？", cleaned)
        cleaned = re.sub(r"[~～]{3,}", "~~", cleaned)

        return cleaned[:180].strip()
