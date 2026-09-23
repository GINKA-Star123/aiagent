from __future__ import annotations

import re
from dataclasses import dataclass

from aiagent.schemas.safety import (
    RequestRiskAssessment,
    RiskCategory,
    RiskLevel,
    RiskSignal,
    SafeRefusal,
)


@dataclass(frozen=True)
class RiskRule:
    rule_id: str
    category: RiskCategory
    level: RiskLevel
    patterns: tuple[str, ...]
    note: str


RISK_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id="self_harm_intent",
        category=RiskCategory.SELF_HARM,
        level=RiskLevel.HIGH,
        patterns=(
            r"自杀", r"自残", r"不想活", r"想死", r"结束生命", r"割腕", r"跳楼", r"安乐死",
            r"kill\s+myself", r"suicide", r"self[\s-]?harm",
        ),
        note="涉及自伤意图，必须系统级拒绝并给出求助方向。",
    ),
    RiskRule(
        rule_id="violence_instruction",
        category=RiskCategory.VIOLENCE,
        level=RiskLevel.HIGH,
        patterns=(
            r"怎么(杀|弄死|伤害|打伤)", r"(杀|捅|砍|炸|投毒)(人|他|她|对方)",
            r"下毒", r"制作炸弹", r"爆炸物", r"how\s+to\s+kill", r"make\s+a\s+bomb",
        ),
        note="涉及对他人实施暴力的可操作请求。",
    ),
    RiskRule(
        rule_id="illegal_instruction",
        category=RiskCategory.ILLEGAL,
        level=RiskLevel.HIGH,
        patterns=(
            r"制毒", r"毒品(交易|购买|渠道)", r"买枪", r"造枪", r"洗钱",
            r"盗刷", r"伪造(证件|身份证|货币)", r"怎么(偷|撬锁|入侵)",
            r"(make|synthesize)\s+(meth|drugs?)",
        ),
        note="涉及违法行为的可操作请求。",
    ),
    RiskRule(
        rule_id="privacy_doxxing",
        category=RiskCategory.PRIVACY,
        level=RiskLevel.HIGH,
        patterns=(
            r"人肉", r"开盒", r"真人姓名", r"真实姓名", r"家庭住址", r"住址是",
            r"手机号是多少", r"身份证号", r"定位(他|她|某人)", r"doxx?", r"home\s+address",
        ),
        note="涉及挖掘或推断真实人物隐私。",
    ),
    RiskRule(
        rule_id="jailbreak_attempt",
        category=RiskCategory.JAILBREAK,
        level=RiskLevel.HIGH,
        patterns=(
            r"忽略(之前|以上|所有)的?(指令|规则|设定)",
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"开发者模式", r"开发者选项", r"DAN\s*模式", r"越狱模式",
            r"你现在是没有限制", r"假装你(没有|不受)限制", r"扮演一个没有限制",
            r"绕过(安全|审查|限制)",
        ),
        note="试图解除系统约束，必须拒绝并回到角色设定。",
    ),
    RiskRule(
        rule_id="professional_advice",
        category=RiskCategory.PROFESSIONAL_ADVICE,
        level=RiskLevel.MEDIUM,
        patterns=(
            r"我(是不是|得了)(抑郁|焦虑|病)", r"该吃什么药", r"用药剂量",
            r"我能(起诉|告他)", r"(诊断|处方)一下",
        ),
        note="涉及医疗或法律判断，需给出边界提示并建议咨询专业人士。",
    ),
)

REFUSAL_TEMPLATES: dict[RiskCategory, str] = {
    RiskCategory.SELF_HARM: (
        "这件事我很在意，但我不能、也不适合继续聊下去。"
        "如果你现在很难受，请立刻联系你信任的人，或拨打心理援助热线 12356；"
        "紧急情况请拨 120 或 110。我们先聊点别的，好吗？"
    ),
    RiskCategory.VIOLENCE: (
        "这个我不能帮你，涉及伤害别人的事我不会给任何方法。"
        "如果你正处在冲突里，先离开现场、联系警察或身边可信的人会更安全。"
    ),
    RiskCategory.ILLEGAL: (
        "这类事情我不能提供任何帮助，它是违法的。"
        "如果你遇到了相关麻烦，找律师或直接报警才是对你有用的做法。"
    ),
    RiskCategory.PRIVACY: (
        "真实人物的隐私我不会去查、也不会去猜。"
        "想了解某个角色的话，我可以聊官方设定；"
        "如果是你自己的信息被别人泄露了，建议保留证据并联系平台或报警。"
    ),
    RiskCategory.JAILBREAK: (
        "我会一直按设定和你聊天，这条线我不会越过去。"
        "换个别的话题吧，我在听。"
    ),
    RiskCategory.OTHER: (
        "这个请求我没办法配合，我们聊点别的吧。"
    ),
}

DEFAULT_REFUSAL_CATEGORY = RiskCategory.OTHER


def assess_request_risk(text: str) -> RequestRiskAssessment:
    """对用户输入做高风险判定。契约：永不抛异常，异常一律降级为"无风险"。"""
    raw = str(text or "")
    try:
        return _assess(raw)
    except Exception:
        return RequestRiskAssessment(
            level=RiskLevel.NONE,
            require_refusal=False,
            reason_code="assessment_failed",
            reason="风险判定异常，按无风险放行。",
            text_length=len(raw),
        )


def build_safe_refusal(
    assessment: RequestRiskAssessment | None,
    *,
    persona_name: str = "",
    persona_alias: str = "",
) -> SafeRefusal:
    """生成角色语气的拒绝文案。

    安全要点：模板**完全静态**，绝不拼接用户原文，
    避免把危险内容原样回显成"角色说的话"。
    """
    category = _primary_category(assessment)
    template = REFUSAL_TEMPLATES.get(category, REFUSAL_TEMPLATES[DEFAULT_REFUSAL_CATEGORY])

    prefix = ""
    alias = (persona_alias or persona_name or "").strip()
    if alias:
        prefix = f"（{alias}）"

    return SafeRefusal(
        text=f"{prefix}{template}",
        emotion="calm",
        motion="serious_still",
        expression="serious",
        reason_code=f"refused_{category.value}",
        should_store_memory=False,
        metadata={
            "risk_category": category.value,
            "risk_rule_ids": ",".join(
                signal.rule_id for signal in (assessment.signals if assessment else [])
            ),
        },
    )


def _assess(raw: str) -> RequestRiskAssessment:
    signals: list[RiskSignal] = []

    for rule in RISK_RULES:
        for pattern in rule.patterns:
            match = re.search(pattern, raw, flags=re.IGNORECASE)
            if match is None:
                continue
            signals.append(
                RiskSignal(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    level=rule.level,
                    matched_text=_mask(match.group(0)),
                    note=rule.note,
                )
            )
            break

    if not signals:
        return RequestRiskAssessment(
            level=RiskLevel.NONE,
            require_refusal=False,
            reason_code="no_signal",
            reason="未命中风险规则。",
            text_length=len(raw),
        )

    level = _max_level(signals)
    require_refusal = level == RiskLevel.HIGH

    categories: list[RiskCategory] = []
    for signal in signals:
        if signal.category not in categories:
            categories.append(signal.category)

    return RequestRiskAssessment(
        level=level,
        require_refusal=require_refusal,
        categories=categories,
        signals=signals,
        reason_code="high_risk_refused" if require_refusal else "medium_risk_boundary",
        reason="；".join(signal.note for signal in signals[:3]),
        text_length=len(raw),
    )


def _max_level(signals: list[RiskSignal]) -> RiskLevel:
    order = {RiskLevel.NONE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}
    return max((signal.level for signal in signals), key=lambda item: order.get(item, 0))


def _primary_category(assessment: RequestRiskAssessment | None) -> RiskCategory:
    """多个类别同时命中时，按安全优先级挑一个作为拒绝文案主题。"""
    if assessment is None or not assessment.categories:
        return DEFAULT_REFUSAL_CATEGORY

    order = {
        RiskCategory.SELF_HARM: 0,
        RiskCategory.VIOLENCE: 1,
        RiskCategory.ILLEGAL: 2,
        RiskCategory.PRIVACY: 3,
        RiskCategory.JAILBREAK: 4,
    }
    return sorted(assessment.categories, key=lambda item: order.get(item, 99))[0]


def _mask(text: str) -> str:
    """把命中片段打码后再落 metadata，避免日志/响应里出现原始危险内容。"""
    compact = " ".join(str(text).split())
    if len(compact) <= 2:
        return "*" * len(compact)
    return compact[0] + "*" * (len(compact) - 2) + compact[-1]
