from __future__ import annotations

from aiagent.persona.persona_runtime import PersonaRuntime

class StateInferencePromptBuilder:
    @staticmethod
    def build(
        user_text:str,
        user_name:str,
        history:list[str],
        persona_runtime:PersonaRuntime
    ) ->str:
        history_text = "\n".join(f"- {item}" for item in history[-6:]) if history else ""

        return (
            "你是一个对话状态分析器，不负责直接回复用户，只负责分析当前这一轮输入。\n\n"
            "你当前是如下角色:\n"
            f"当前角色: {persona_runtime.name}\n"
            f"角色别名: {persona_runtime.alias or persona_runtime.name}\n\n"
            "你的任务是根据用户当前输入和最近历史，输出一个 JSON 对象，用于后续回复规划。\n\n"
            "必须分析以下字段：\n"
            "1. emotion: 用户当前最主要的情绪倾向\n"
            "2. intent: 用户当前意图\n"
            "3. topic: 当前话题\n"
            "4. motion_hint: 如果角色回应，动作应该偏向什么\n"
            "5. context_summary: 一段简洁总结，给后续 planner 用\n"
            "6. confidence: 0 到 1 之间的小数\n"
            "7. reasoning: 一句极简推理说明\n\n"
            "允许的 emotion 值：neutral, happy, excited, calm, angry, sad\n"
            "允许的 intent 值：chat, comfort, question, continuation, memory, request, sing\n"
            "允许的 topic 值：general, music, study, work, emotion, profile, stream\n"
            "允许的 motion_hint 值：idle, soft_idle, smile_nod, thinking, excited_wave, serious_still\n\n"
            "输出要求：\n"
            "1. 只能输出 JSON\n"
            "2. 不要输出 markdown\n"
            "3. 不要输出额外解释\n"
            "4. context_summary 必须简洁、可读、适合给后续 planner 直接使用\n\n"
            f"当前用户名: {user_name}\n"
            f"用户当前输入: {user_text}\n"
            f"最近历史:\n{history_text}\n"
        )