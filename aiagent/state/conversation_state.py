"""Conversation continuity state."""

from __future__ import annotations

from pydantic import BaseModel,Field

from aiagent.schemas.inputs import InputEvent
from aiagent.schemas.outputs import OutputEvent

class ConversationState(BaseModel):
    recent_inputs : list[InputEvent] = Field(default_factory=list)
    recent_outputs : list[OutputEvent] = Field(default_factory=list)
    max_turns : int = 10

    current_topic : str ="general"
    topic_history: list[str] = Field(default_factory=list)
    recent_keywords: list[str] = Field(default_factory=list)
    last_user_goal: str = ""
    last_user_emotion_hint : str ="neutral"
    last_strategy: str = ""
    last_topic_shift : bool = False
    
    def add_input(self,event:InputEvent) -> None:
        self.recent_inputs.append(event)
        self.recent_inputs = self.recent_inputs[-self.max_turns:]

        inferred_topic = self._infer_topic(event.text)
        previous_topic = self.current_topic
        self.last_topic_shift = inferred_topic != previous_topic

        self.current_topic = inferred_topic
        self.topic_history.append(inferred_topic)
        self.topic_history = self.topic_history[-8:]

        self.last_user_goal = self._infer_user_goal(event.text)
        self.last_user_emotion_hint = self._infer_user_emotion(event.text)

        keywords = self._extract_keywords(event.text)
        merged_keywords = self.recent_keywords + keywords
        deduped: list[str] = []
        for item in merged_keywords:
            if item not in deduped:
                deduped.append(item)
        self.recent_keywords = deduped[-10:]

    
    def add_output(self,event:OutputEvent) -> None:
        self.recent_outputs.append(event)
        self.recent_outputs = self.recent_outputs[-self.max_turns:]

        planner_strategy = event.packet.metadata.get("strategy","")
        if planner_strategy:
            self.last_strategy = planner_strategy

    
    def recent_dialogue_pairs(self, limit: int = 4, session_id: str = "") -> list[dict]:
        """最近若干轮"用户输入 + 助手回复"配对。

        roadmap 5.3：

        - ``session_id`` 非空时只统计该会话的轮次，避免不同会话互相污染；
        - 优先按 ``turn_id`` 配对（当前轮尚未产生回复时会被自然跳过，
          不会像按位置配对那样把上一轮回复错配给本轮）；
        - 没有 ``turn_id`` 的旧数据退回按出现顺序配对，保持兼容。
        """

        inputs = [
            event
            for event in self.recent_inputs
            if self._session_matches(getattr(event, "session_id", ""), session_id)
        ]
        outputs = [
            event
            for event in self.recent_outputs
            if self._session_matches(
                (event.packet.metadata or {}).get("session_id", ""),
                session_id,
            )
        ]

        replies_by_turn = self._replies_by_turn(outputs)
        if replies_by_turn:
            pairs = self._pairs_by_turn_id(inputs, replies_by_turn)
            if pairs:
                return pairs[-limit:]

        return self._pairs_in_order(inputs, outputs, limit)

    @staticmethod
    def _session_matches(entry_session_id: str, session_id: str) -> bool:
        """session_id 为空表示"不过滤"，保持旧调用方行为。"""

        if not session_id:
            return True

        return str(entry_session_id or "") == session_id

    @staticmethod
    def _replies_by_turn(outputs: list[OutputEvent]) -> dict[str, str]:
        replies: dict[str, str] = {}

        for event in outputs:
            turn_id = str((event.packet.metadata or {}).get("turn_id", "") or "")
            if turn_id:
                replies[turn_id] = event.packet.reply_text

        return replies

    @staticmethod
    def _pairs_by_turn_id(
        inputs: list[InputEvent],
        replies_by_turn: dict[str, str],
    ) -> list[dict]:
        pairs: list[dict] = []

        for event in inputs:
            turn_id = str(getattr(event, "turn_id", "") or "")
            reply = replies_by_turn.get(turn_id)
            if reply is None:
                continue
            pairs.append(
                {
                    "user": event.user_name,
                    "input": event.text,
                    "reply": reply,
                }
            )

        return pairs

    @staticmethod
    def _pairs_in_order(
        inputs: list[InputEvent],
        outputs: list[OutputEvent],
        limit: int,
    ) -> list[dict]:
        """兼容旧数据：没有 turn_id 时按出现顺序配对（保留原实现语义）。"""

        recent_inputs = inputs[-limit:]
        recent_outputs = outputs[-limit:]
        pair_count = min(len(recent_inputs), len(recent_outputs))

        pairs: list[dict] = []
        for index in range(pair_count):
            pairs.append(
                {
                    "user": recent_inputs[index].user_name,
                    "input": recent_inputs[index].text,
                    "reply": recent_outputs[index].packet.reply_text,
                }
            )

        return pairs
    
    def prompt_summary(self) ->str:
        if not self.recent_inputs:
            return "暂无连续对话上下文"
        
        lines = [
            f"当前话题：{self.current_topic}",
            f"最近关键词：{', '.join(self.recent_keywords) if self.recent_keywords else '无'}",
            f"用户当前诉求：{self.last_user_goal or '未识别'}",
            f"用户情绪倾向：{self.last_user_emotion_hint}",
            f"上一轮回复策略：{self.last_strategy or '无'}",
            f"本轮是否切换话题：{'是' if self.last_topic_shift else '否'}",
        ]
        return "\n".join(lines)
    

    def snapshot(self) -> dict:
        return {
            "当前话题":self.current_topic,
            "对话历史":self.topic_history,
            "最近关键词":self.recent_keywords,
            "用户当前诉求":self.last_user_goal,
            "用户当前情绪":self.last_user_emotion_hint,
            "本轮是否转换话题":self.last_topic_shift,
            "最近轮数":len(self.recent_inputs)
        }
    
    def clear(self) -> None:
        self.recent_inputs.clear()
        self.recent_outputs.clear()
        self.current_topic = "general"
        self.topic_history.clear()
        self.recent_keywords.clear()
        self.last_user_goal = ""
        self.last_user_emotion_hint = "neutral"
        self.last_strategy = ""
        self.last_topic_shift = False

    def _infer_topic(self, text: str) -> str:
        if any(keyword in text for keyword in ["考试", "复习", "成绩", "学校", "作业", "老师"]):
            return "学习"
        if any(keyword in text for keyword in ["唱歌", "音乐", "吉他", "钢琴", "编曲", "歌词"]):
            return "音乐"
        if any(keyword in text for keyword in ["生日", "纪念日", "礼物"]):
            return "庆典"
        if any(keyword in text for keyword in ["工作", "上班", "同事", "老板", "加班"]):
            return "工作"
        if any(keyword in text for keyword in ["喜欢", "讨厌", "我是", "我叫", "请记住"]):
            return "档案"
        if any(keyword in text for keyword in ["紧张", "难过", "焦虑", "压力", "烦"]):
            return "情绪"
        return "正常话题"

    def _infer_user_goal(self, text: str) -> str:
        if any(keyword in text for keyword in ["怎么", "如何", "怎样", "可以吗"]):
            return "寻求建议"
        if any(keyword in text for keyword in ["请记住", "记住我"]):
            return "寻求记忆"
        if "?" in text or "？" in text:
            return "寻求回答"
        if any(keyword in text for keyword in ["紧张", "难过", "焦虑", "压力"]):
            return "渴望安慰"
        if any(keyword in text for keyword in ["喜欢", "最近", "今天", "明天"]):
            return "分享现状"
        return "随意的聊天"

    def _infer_user_emotion(self, text: str) -> str:
        if any(keyword in text for keyword in ["紧张", "焦虑", "压力", "害怕"]):
            return "紧张"
        if any(keyword in text for keyword in ["开心", "高兴", "喜欢", "期待"]):
            return "积极"
        if any(keyword in text for keyword in ["难过", "失落", "烦", "崩溃"]):
            return "低落"
        return "正常"

    def _extract_keywords(self, text: str) -> list[str]:
        seeds = [
            "考试",
            "复习",
            "学校",
            "作业",
            "音乐",
            "唱歌",
            "吉他",
            "生日",
            "工作",
            "上班",
            "紧张",
            "开心",
            "焦虑",
            "礼物",
        ]
        hits = [keyword for keyword in seeds if keyword in text]
        return hits[:5]
