from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from aiagent.graphs.graph_model import VisionAnalyzeResult, VisionLive2DSuggestion
from aiagent.services.vision_service import VisionService


class VisionGraphState(TypedDict, total=False):
    file_obj: Any
    filename: str
    image_path: str
    user_id: str
    user_prompt: str

    vision_result: VisionAnalyzeResult
    chat_context: str
    memory_hint: str
    live2d_suggestion: dict[str, Any]
    metadata: dict[str, Any]


class VisionRunner:
    def __init__(self, vision_service: VisionService) -> None:
        self.vision_service = vision_service
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(VisionGraphState)

        graph.add_node("analyze_image", self._analyze_image_node)
        graph.add_node("build_chat_context", self._build_chat_context_node)
        graph.add_node("build_memory_hint", self._build_memory_hint_node)
        graph.add_node("build_live2d_suggestion", self._build_live2d_suggestion_node)

        graph.add_edge(START, "analyze_image")
        graph.add_edge("analyze_image", "build_chat_context")
        graph.add_edge("build_chat_context", "build_memory_hint")
        graph.add_edge("build_memory_hint", "build_live2d_suggestion")
        graph.add_edge("build_live2d_suggestion", END)

        return graph.compile()

    def analyze_upload(
        self,
        file_obj,
        filename: str,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionGraphState:
        return self.graph.invoke(  # type: ignore
            {
                "file_obj": file_obj,
                "filename": filename,
                "user_prompt": user_prompt,
                "user_id": user_id,
            }
        )

    def analyze_path(
        self,
        image_path: str,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionGraphState:
        return self.graph.invoke(  # type: ignore
            {
                "image_path": image_path,
                "user_prompt": user_prompt,
                "user_id": user_id,
            }
        )

    def _analyze_image_node(self, state: VisionGraphState) -> VisionGraphState:
        user_prompt = state.get("user_prompt", "")
        user_id = state.get("user_id", "guest")

        if state.get("file_obj") is not None:
            result = self.vision_service.analyze_upload(
                file_obj=state.get("file_obj"),
                filename=state.get("filename", "upload.png"),
                user_prompt=user_prompt,  # type: ignore
                user_id=user_id,  # type: ignore
            )
        else:
            image_path = state.get("image_path", "")
            if not image_path:
                raise RuntimeError("image path is not configured")

            result = self.vision_service.analyze_local_path(
                image_path=image_path,
                user_id=user_id,  # type: ignore
                user_prompt=user_prompt,  # type: ignore
            )

        profile = result.confidence_report
        policy = result.low_confidence_policy

        return {
        "vision_result": result,
        "metadata": {
            "vision_graph": "analyzed",
            "vision_image_id": result.image_id,
            "vision_image_type": result.image_type,
            "vision_user_intent": result.user_intent,
            "vision_confidence": result.confidence,
            "vision_confidence_level": profile.level,
            "vision_confidence_reason": profile.reason,
            "vision_is_confident": result.is_confident,
            "vision_low_confidence_active": policy.active,
            "vision_avoid_identity_assertion": policy.avoid_identity_assertion,
            "vision_defer_memory_hint": policy.defer_memory_hint,
            "vision_suppress_live2d_override": policy.suppress_live2d_override,
            "vision_confirmed_character_count": len(result.recognized_characters),
            "vision_candidate_character_count": len(result.character_candidates),
            "vision_character_names": ", ".join(
                item.name for item in result.recognized_characters[:3]
            ),
        },
    }

    def _build_chat_context_node(self, state: VisionGraphState) -> VisionGraphState:
        result = state.get("vision_result")
        if not result:
            raise RuntimeError("Vision result is not configured.")
        profile = result.confidence_report
        policy = result.low_confidence_policy

        confirmed_lines: list[str] = []
        for item in result.recognized_characters[:3]:
            evidence = "；".join(item.evidence[:4])
            confirmed_lines.append(
                f"- 已确认：{item.name} ({item.character_id})，confidence={item.confidence:.3f}，evidence={evidence}"
            )
        candidate_lines: list[str] = []
        if policy.expose_candidates:
            for item in result.character_candidates[:3]:
                evidence = "；".join(item.evidence[:3])
                candidate_lines.append(
                    f"- 候选但未确认：{item.name} ({item.character_id})，confidence={item.confidence:.3f}，evidence={evidence}"
                )

        character_text = "\n".join(confirmed_lines) if confirmed_lines else "没有达到确认阈值的角色。"
        if candidate_lines:
            character_text = character_text + "\n\n候选角色（仅供保守参考，不可强行确认）：\n" + "\n".join(candidate_lines)

        confidence_text = f"""
        - score: {profile.score:.3f}
        - level: {profile.level}
        - threshold: {profile.threshold:.3f}
        - source: {profile.source}
        - reason: {profile.reason}
        - low_confidence_active: {policy.active}
        - avoid_identity_assertion: {policy.avoid_identity_assertion}
        - reply_instruction: {policy.reply_instruction}
        """.strip()
        
        daily = result.daily_scene
        daily_text = f"""
- scene_type: {daily.scene_type}
- location_hint: {daily.location_hint or "无"}
- activity: {daily.activity or "无"}
- food: {"、".join(daily.food) if daily.food else "无"}
- landmarks: {"、".join(daily.landmarks) if daily.landmarks else "无"}
- objects: {"、".join(daily.objects) if daily.objects else "无"}
- people_count: {daily.people_count if daily.people_count is not None else "未知"}
- time_hint: {daily.time_hint or "无"}
- weather_hint: {daily.weather_hint or "无"}
- notable_details: {"；".join(daily.notable_details) if daily.notable_details else "无"}
""".strip()

        objects_text = "、".join(result.objects) if result.objects else "无明确物体列表"
        ocr_text = "\n".join(result.ocr_text) if result.ocr_text else "无 OCR 文本"

        chat_context = f"""
[视觉上下文]
图片ID: {result.image_id}
图片类型: {result.image_type}
用户可能意图: {result.user_intent}
图片尺寸: {result.width}x{result.height}
图片格式: {result.format}

图片摘要:
{result.summary or "无摘要"}

识别到的角色:
{character_text}

日常场景信息:
{daily_text}

通用场景:
{result.scene or "未知"}

物体:
{objects_text}

OCR:
{ocr_text}

氛围:
{result.mood or "未知"}

视觉可信度策略:
{confidence_text}

使用规则：
1. 你可以根据视觉上下文回答用户关于图片的问题。
2. 如果 image_type 是 daily、food、travel、landscape、object、screenshot 或 document，要优先自然描述图片内容，不要强行往角色识别上带。
3. 如果存在“已确认角色”，可以正常引用角色名。
4. 如果只有“候选角色”，必须使用“可能像是、看起来有点像、我不完全确定”这类保守表达。
5. 如果 low_confidence_active=true，不要把候选角色说成已经确认。
6. 不要编造图片里没有的信息。
7. 不要推断真实人物身份。
""".strip()

        metadata = dict(state.get("metadata", {}))
        metadata.update(
            {
                "vision_chat_context_built": True,
                "vision_character_count": len(result.recognized_characters),
                "vision_character_names": ", ".join(
                    item.name for item in result.recognized_characters[:3]
                ),
                "vision_daily_scene_type": result.daily_scene.scene_type,
            }
        )

        return {
            "chat_context": chat_context,
            "metadata": metadata,
        }

    def _build_memory_hint_node(self, state: VisionGraphState) -> VisionGraphState:
        result = state["vision_result"]  # type: ignore
        if result.low_confidence_policy.defer_memory_hint:
            metadata = dict(state.get("metadata", {}))
            metadata.update(
                {
                    "vision_memory_should_consider": False,
                    "vision_memory_deferred_by_confidence": True,
                    "vision_memory_reason": result.low_confidence_policy.reason,
                }
            )
            return {
                "memory_hint": "",
                "metadata": metadata,
            }
        if not result.memory.should_consider:
            memory_hint = ""
        else:
            character_names = "、".join([item.name for item in result.recognized_characters]) or "无"
            memory_hint = (
                f"视觉记忆候选：{result.memory.reason}\n"
                f"图片类型：{result.image_type}\n"
                f"图片摘要：{result.summary}\n"
                f"场景：{result.scene}\n"
                f"日常场景：{result.daily_scene.scene_type}\n"
                f"识别角色：{character_names}"
            )

        metadata = dict(state.get("metadata", {}))
        metadata.update(
            {
                "vision_memory_should_consider": result.memory.should_consider,
                "vision_memory_reason": result.memory.reason,
            }
        )

        return {
            "memory_hint": memory_hint,
            "metadata": metadata,
        }

    def _build_live2d_suggestion_node(self, state: VisionGraphState) -> VisionGraphState:
        result = state["vision_result"]  # type: ignore
        if result.low_confidence_policy.suppress_live2d_override:
            suggestion = VisionLive2DSuggestion().model_dump(mode="json")
        else:
            suggestion = result.live2d.model_dump(mode="json")


        metadata = dict(state.get("metadata", {}))
        metadata.update(
            {
                "vision_live2d_background": result.live2d.suggested_background,
                "vision_live2d_emotion": result.live2d.suggested_emotion,
                "vision_live2d_expression": result.live2d.suggested_expression,
                "vision_live2d_motion": result.live2d.suggested_motion,
                "vision_live2d_suppressed_by_confidence": result.low_confidence_policy.suppress_live2d_override,
            }
        )

        return {
            "live2d_suggestion": suggestion,
            "metadata": metadata,
        }
