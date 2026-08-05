from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage

from aiagent.schemas.memory import MemoryCategory, MemoryImportance, MemoryWriteDecision
from aiagent.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MemoryPolicyLLMService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def decide_write(
        self,
        user_text: str,
        assistant_text: str,
        existing_memory_context: str,
        planner_should_store_memory: bool,
    ) -> MemoryWriteDecision:
        raw = self.llm_service.invoke_messages(
            messages=[
                HumanMessage(
                    content=self._build_prompt(
                        user_text=user_text,
                        assistant_text=assistant_text,
                        existing_memory_context=existing_memory_context,
                        planner_should_store_memory=planner_should_store_memory,
                    )
                )
            ],
            fallback_text='{"should_store": false, "reason": "llm_fallback"}',
            mode="memory_policy",
        )

        decision = self._parse(raw)
        rule_decision = self._rule_based_decision(user_text)

        if rule_decision is not None and not decision.should_store:
            decision = rule_decision
            
        decision.metadata["planner_should_store_memory"] = planner_should_store_memory
        return decision

    def _build_prompt(
        self,
        user_text: str,
        assistant_text: str,
        existing_memory_context: str,
        planner_should_store_memory: bool,
    ) -> str:
        planner_signal = (
            "planner 建议写入长期记忆。"
            if planner_should_store_memory
            else "planner 未建议写入长期记忆，但这只是参考信号，不是硬性禁止。"
        )

        return f"""
你是 aiagent 的长期记忆写入控制器。你负责判断本轮对话是否值得写入长期记忆。

重要原则：
- 最终是否写入由你判断，不要简单服从关键词，也不要简单服从 planner。
- 如果用户明确要求“记住/以后别忘/下次提醒/我喜欢/我不喜欢/我的习惯是”，且内容有长期复用价值，通常应该写入。
- 如果内容只是一次性闲聊、临时情绪、当前任务步骤、寒暄、单轮问题答案，则不要写入。
- 如果用户当前表达与已有记忆冲突，但看起来是稳定信息更新，应该写入或更新。

planner 信号：
{planner_signal}

应该写入：
- 用户稳定身份信息
- 用户长期偏好、厌恶、习惯
- 用户重要人物关系
- 用户长期目标、计划、创作方向
- 用户明确表达的边界、禁忌、希望被如何对待
- 与已有长期记忆冲突但需要更新的信息
- 对未来多轮对话有持续帮助的信息

不应该写入：
- 一次性闲聊
- 临时情绪
- 当前任务步骤
- 寒暄
- 单轮问题答案
- 模糊、无法复用的信息
- 助手自己的临时表达
- API key、密码、token、身份证号、银行卡号、精确住址、联系方式等敏感信息
- 用户没有明确要求记住的医疗、财务、法律等高度隐私信息

已有长期记忆：
{existing_memory_context or "无长期记忆。"}

本轮用户输入：
{user_text}

本轮助手回复：
{assistant_text}

只输出 JSON：
{{
  "should_store": true,
  "category": "identity|preference|relationship|goal|habit|boundary|event|other",
  "importance": "low|medium|high",
  "confidence": 0.0,
  "reason": "一句话说明",
  "facts": [
    "每条都是独立、简短、可复用的中文长期事实"
  ],
  "memory_hint": "兼容旧字段：如果 facts 非空，可以用一句话概括；否则为空"
}}
""".strip()

    def _parse(self, raw: str) -> MemoryWriteDecision:
        try:
            data = self._extract_json(raw)
            should_store = bool(data.get("should_store", False))

            facts = self._normalize_facts(data.get("facts"))
            memory_hint = str(data.get("memory_hint", "")).strip()

            if facts and not memory_hint:
                memory_hint = "；".join(facts)

            if should_store and not memory_hint and not facts:
                should_store = False

            return MemoryWriteDecision(
                should_store=should_store,
                category=self._safe_enum(MemoryCategory, data.get("category"), MemoryCategory.OTHER),
                importance=self._safe_enum(MemoryImportance, data.get("importance"), MemoryImportance.MEDIUM),
                reason=str(data.get("reason", "")).strip(),
                memory_hint=memory_hint,
                facts=facts,
                confidence=self._safe_float(data.get("confidence"), 0.0),
                metadata={"raw_policy_response": raw},
            )
        except Exception as exc:
            logger.exception("Failed to parse memory policy response: %s", exc)
            return MemoryWriteDecision(
                should_store=False,
                reason=f"parse_failed: {exc}",
                metadata={"raw_policy_response": raw},
            )

    def _extract_json(self, raw: str) -> dict[str, Any]:
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("No JSON object found.")

        parsed = json.loads(match.group(0))
        
        if not isinstance(parsed, dict):
            raise ValueError("JSON root is not object.")

        return parsed

    def _safe_enum(self, enum_cls, value: Any, fallback):
        try:
            return enum_cls(str(value))
        except Exception:
            return fallback

    def _normalize_facts(self,value:Any) ->list[str]:
        if isinstance(value,list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value,str) and value.strip():
            return [str(value).strip()]
        return []

    def _safe_float(self, value: Any, fallback:float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

    def _rule_based_decision(self,user_text:str) -> MemoryWriteDecision | None:
        text =user_text.strip()
        if not text:
            return None

        explicit_markers = [
        "记住",
        "帮我记",
        "以后别忘",
        "下次提醒",
        "我喜欢",
        "我不喜欢",
        "我讨厌",
        "我的习惯",
        "我希望你",
        "不要再",
        ]

        if not any(marker in text for marker in explicit_markers):
            return None

        category = MemoryCategory.OTHER
        if any(marker in text for marker in ["我喜欢", "我不喜欢", "我讨厌"]):
            category = MemoryCategory.PREFERENCE
        elif any(marker in text for marker in ["我的习惯", "我每天", "我经常"]):
            category = MemoryCategory.HABIT
        elif any(marker in text for marker in ["我希望你", "不要再", "别叫我", "叫我"]):
            category = MemoryCategory.BOUNDARY

        return MemoryWriteDecision(
            should_store=True,
            category=category,
            importance=MemoryImportance.MEDIUM,
            reason="rule_based_explicit_memory_request",
            memory_hint=text,
            facts=[text],
            confidence=0.55,
            metadata={
                "memory_policy_source": "rule_based",
            },
        )