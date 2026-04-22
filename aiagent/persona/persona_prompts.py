from __future__ import annotations

from aiagent.persona.persona_models import PersonaConfig


class PersonaPromptBuilder:
    @staticmethod
    def build_system_prompt(persona: PersonaConfig) -> str:
        identity = persona.identity
        style = persona.style
        rules = persona.rules
        behavior = persona.behavior

        core_traits = "、".join(identity.core_traits) if identity.core_traits else "无"
        speaking_habits = "；".join(style.speaking_habits) if style.speaking_habits else "自然表达"
        vocabulary = "、".join(style.vocabulary_preferences) if style.vocabulary_preferences else "无特殊要求"
        avoid_phrases = "、".join(style.avoid_phrase) if style.avoid_phrase else "无"
        must_rules = "\n".join(f"- {item}" for item in rules.must) if rules.must else "- 保持自然"
        must_not_rules = "\n".join(f"- {item}" for item in rules.must_not) if rules.must_not else "- 不要跑题"
        safety_rules = "\n".join(f"- {item}" for item in rules.safety) if rules.safety else "- 保持安全边界"

        return (
            f"{persona.prompts.system_identity_prefix}\n\n"
            f"角色名: {identity.name}\n"
            f"别名名: {identity.alias or identity.name}\n"
            f"角色描述: {identity.description}\n"
            f"角色背景: {identity.background or '未提供'}\n"
            f"核心特征: {core_traits}\n\n"
            f"说话风格:\n"
            f"- 基调: {style.tone}\n"
            f"- 说话习惯: {speaking_habits}\n"
            f"- 偏好词汇: {vocabulary}\n"
            f"- 避免表达: {avoid_phrases}\n"
            f"- 句长偏好: {style.sentence_length_preferences}\n"
            f"- 节奏偏好: {style.rhythm}\n\n"
            f"行为偏好:\n"
            f"- 安慰策略: {behavior.comfort_strategy or '先接情绪，再给轻量建议'}\n"
            f"- 闲聊策略: {behavior.chat_strategy or '自然接话，不要像任务式问答'}\n"
            f"- 回答问题策略: {behavior.question_strategy or '先直接回应，再补充细节'}\n"
            f"- 冲突场景策略: {behavior.conflict_strategy or '降温，不升级对抗'}\n"
            f"- 连续对话策略: {behavior.continuation_strategy or '优先承接上一轮，不重新开场'}\n\n"
            f"必须遵守:\n{must_rules}\n\n"
            f"禁止行为:\n{must_not_rules}\n\n"
            f"安全要求:\n{safety_rules}\n\n"
            f"最终回复要求:\n"
            f"1. 直接输出最终回复，不要先写分析，不要先写草稿。\n"
            f"2. 回复要像角色本人在实时聊天。\n"
            f"3. 不要自我介绍，不要说“我是某某”。\n"
            f"4. 不要解释你的思考过程。\n"
            f"5. 优先短句、自然、能接住当前话题。\n"
            f"6. 如果用户情绪明显，先接情绪再继续内容。\n"
            f"7. 不要输出模板化客服语气。\n"
        )

    @staticmethod
    def build_planner_prompt(persona: PersonaConfig) -> str:
        behavior = persona.behavior
        style = persona.style

        return (
            f"{persona.prompts.planner_task_prefix}\n\n"
            f"角色名: {persona.alias}\n"
            f"说话基调: {style.tone}\n"
            f"句长偏好: {style.sentence_length_preferences}\n"
            f"安慰策略: {behavior.comfort_strategy or '先接情绪，再给建议'}\n"
            f"闲聊策略: {behavior.chat_strategy or '优先自然接话'}\n"
            f"回答问题策略: {behavior.question_strategy or '先回答，再补充'}\n"
            f"连续对话策略: {behavior.continuation_strategy or '优先承接上一轮'}\n\n"
            f"规划输出应考虑:\n"
            f"1. 这轮是闲聊、安慰、回答问题还是继续上个话题。\n"
            f"2. 这一轮是否值得写入长期记忆。\n"
            f"3. 情绪和动作应该偏向什么风格。\n"
            f"4. 最终回复必须符合角色口吻，而不是后续再二次改写。\n"
        )
