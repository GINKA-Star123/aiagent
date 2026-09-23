from __future__ import annotations

import base64
import json
import logging
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from aiagent.vision.confidence_policy import VisionConfidencePolicy
from aiagent.vision.character_retriever import CharacterRetriever
from aiagent.vision.image_store import ImageStore, StoredImage
from aiagent.graphs.graph_model import (
    CharacterCandidate,
    DailySceneResult,
    VisionAnalyzeResult,
    VisionLive2DSuggestion,
    VisionMemoryCandidate,
    VisionSafetyResult,
    VisionImageType,
    VisionConfidenceLevel,
    VISION_ANALYZE_SCHEMA_VERSION,
)
from aiagent.vision.confidence_policy import (
    MODEL_CONFIRMED_SOURCE,
    RETRIEVAL_ONLY_SOURCE,
    VisionConfidencePolicy,
)
from aiagent.vision.character_retriever import CharacterRetriever
from aiagent.vision.image_store import ImageStore, StoredImage
from aiagent.vision.vision_memory_policy import decide_memory
from aiagent.vision.vision_payload_guard import (
    build_channels,
    describe_violations,
    normalize_payload,
)
from aiagent.graphs.graph_model import (
    CharacterCandidate,
    DailySceneResult,
    VisionAnalyzeResult,
    VisionLive2DSuggestion,
    VisionMemoryCandidate,
    VisionModelPayload,
    VisionSafetyResult,
    VisionImageType,
    VisionConfidenceLevel,
    VISION_ANALYZE_SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)


class VisionService:
    def __init__(
        self,
        image_store: ImageStore,
        character_retriever: CharacterRetriever,
        provider: str = "mock",
        model: str = "",
        api_key: str | None = None,
        base_url: str = "",
        timeout_seconds: float = 60.0,
        confident_score: float = 0.78,
        scene_confident_score: float = 0.55,
        low_confidence_margin: float = 0.12,
    ) -> None:
        self.image_store = image_store
        self.character_retriever = character_retriever
        self.provider = provider.strip().lower()
        self.model = model.strip()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.confident_score = confident_score
        self.confidence_policy = VisionConfidencePolicy(
            character_confident_score=confident_score,
            scene_confident_score=scene_confident_score,
            low_margin=low_confidence_margin,
        )

    def analyze_upload(
        self,
        file_obj,
        filename: str,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionAnalyzeResult:
        stored = self.image_store.save_upload(file_obj=file_obj, filename=filename)
        return self.analyze_stored_image(
            stored=stored,
            user_prompt=user_prompt,
            user_id=user_id,
        )

    def analyze_local_path(
        self,
        image_path: str | Path,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionAnalyzeResult:
        stored = self.image_store.save_local_copy(image_path)
        return self.analyze_stored_image(
            stored=stored,
            user_prompt=user_prompt,
            user_id=user_id,
        )

    def analyze_stored_image(
        self,
        stored: StoredImage,
        user_prompt: str = "",
        user_id: str = "guest",
    ) -> VisionAnalyzeResult:
        candidates = self.character_retriever.retrieve(stored.path, top_k=5)
        model_data = self._analyze_with_model(
            stored=stored,
            candidates=candidates,
            user_prompt=user_prompt,
        )

        return self._build_result(
            stored=stored,
            candidates=candidates,
            model_data=model_data,
            user_prompt=user_prompt,
            user_id=user_id,
        )

    def rebuild_character_index(self, force_rebuild: bool = True) -> dict[str, Any]:
        return self.character_retriever.build_index(force_rebuild=force_rebuild)

    def character_index_stats(self) -> dict[str, Any]:
        return self.character_retriever.stats()

    def _analyze_with_model(
        self,
        stored: StoredImage,
        candidates: list[CharacterCandidate],
        user_prompt: str,
    ) -> dict[str, Any]:
        if self.provider in {"", "mock"}:
            return self._mock_model_result(candidates)

        if self.provider in {"openai", "siliconflow", "lmstudio"}:
            return self._openai_compatible_vision(
                stored=stored,
                candidates=candidates,
                user_prompt=user_prompt,
            )

        raise ValueError(f"Unsupported vision provider: {self.provider}")

    def _openai_compatible_vision(
        self,
        stored: StoredImage,
        candidates: list[CharacterCandidate],
        user_prompt: str,
    ) -> dict[str, Any]:
        if self.provider != "lmstudio" and not self.api_key:
            raise RuntimeError("Vision API key is not configured.")

        if not self.base_url:
            raise RuntimeError("Vision base URL is not configured.")

        if not self.model:
            raise RuntimeError("Vision model is not configured.")

        image_data_url = self._image_to_data_url(stored.path)
        candidate_text = self._format_candidates_for_prompt(candidates)

        prompt = f"""
你是 aiagent 的正式版视觉理解模块。你需要同时支持两类图片：

A. 角色/IP 图片：
- 例如洛天依、乐正绫、言和、其他二次元角色、同人图、舞台图、Q版图。
- 这类图片必须结合候选角色图库进行判断。
- 如果候选相似度不足，或者你不确定，不要强行确认角色。

B. 日常图片：
- 例如旅游照片、吃饭照片、风景、城市街景、桌面、宠物、截图、衣服、物品、票据、菜单、聊天截图等。
- 这类图片重点描述场景、活动、物品、文字、氛围，以及用户可能想表达什么。
- 不要为了角色识别而忽略日常图片内容。

通用规则：
1. 不要编造图片里没有的信息。
2. 不要识别或推断真实人物身份。
3. 如果图片里有人，只描述可见行为、服饰、人数和场景，不要做人脸身份识别。
4. 如果是角色图，recognized_characters 可以返回候选角色。
5. 如果是日常图，recognized_characters 可以为空。
6. confidence 必须是 0 到 1 之间的小数。
7. 输出必须是 JSON，不要输出 Markdown，不要输出解释正文。
8. 顶层 confidence 表示你对图片整体理解的把握；角色身份置信度仍写在 recognized_characters 内。
9. 如果你不确定角色身份，recognized_characters 可以为空；不要为了迎合候选角色而强行确认。

用户附加说明：
{user_prompt or "无"}

候选角色：
{candidate_text}

请输出 JSON：
{{
  "image_type": "character|daily|screenshot|document|food|travel|landscape|object|unknown",
  "user_intent": "用户可能想让你做什么，例如识别角色、描述照片、分析食物、读图中文字、判断场景等",
  "confidence": 0.0,
  "confidence_reason": ""说明你对图片类型、摘要、OCR、场景理解的整体把握；不要把它和角色身份置信度混为一谈""
  "summary": "图片总体描述",
  "objects": ["物体1", "物体2"],
  "scene": "简短场景描述",
  "daily_scene": {{
    "scene_type": "travel|food|desk|street|home|landscape|screenshot|document|object|unknown",
    "location_hint": "可见地点线索，没有则为空",
    "activity": "可见活动，没有则为空",
    "food": ["食物"],
    "landmarks": ["地标"],
    "objects": ["日常物品"],
    "people_count": 0,
    "time_hint": "白天/夜晚/黄昏等，没有则为空",
    "weather_hint": "天气线索，没有则为空",
    "notable_details": ["值得聊天时提到的细节"]
  }},
  "ocr_text": ["识别到的文字"],
  "mood": "氛围",
  "recognized_characters": [
    {{
      "character_id": "luotianyi",
      "name": "洛天依",
      "confidence": 0.91,
      "evidence": ["候选图库相似度高", "视觉特征匹配"]
    }}
  ],
  "safety": {{
    "has_sensitive_content": false,
    "risk_level": "none|low|medium|high",
    "reason": ""
  }},
  "memory": {{
    "should_consider": false,
    "reason": "是否值得交给 memory_graph 作为长期记忆候选"
  }},
  "live2d": {{
    "suggested_emotion": "neutral|happy|calm|excited|angry",
    "suggested_expression": "neutral|gentle|happy_smile|bright_smile|serious",
    "suggested_motion": "idle|soft_idle|smile_nod|excited_wave|serious_still",
    "suggested_background": "room_default|room_night|desk_work|travel_day|cafe_table|stage_default|street_day|landscape_view"
  }}
}}
""".strip()

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key or 'lm-studio'}",
        }
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
        }

        timeout = httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=20.0,
            read=self.timeout_seconds,
            write=60.0,
            pool=20.0,
        )

        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = self._extract_json(content)
        parsed["_raw_model_output"] = content
        return parsed

    def _mock_model_result(self, candidates: list[CharacterCandidate]) -> dict[str, Any]:
        recognized = []

        if candidates:
            best = candidates[0]
            if best.confidence >= self.confident_score:
                recognized.append(
                    {
                        "character_id": best.character_id,
                        "name": best.name,
                        "confidence": best.confidence,
                        "evidence": best.evidence,
                    }
                )
        best_confidence = recognized[0]["confidence"] if recognized else 0.2

        return {
            "image_type": "character" if recognized else "unknown",
            "user_intent": "mock vision 仅验证角色图库召回，不做通用图片理解",
            "confidence": best_confidence,
            "confidence_reason": "mock provider 仅根据角色图库检索分数生成置信度",
            "summary": "已完成图片角色图库检索。当前为 mock vision，只根据图像向量候选判断。",
            "objects": [],
            "scene": "unknown",
            "daily_scene": {
                "scene_type": "unknown",
                "location_hint": "",
                "activity": "",
                "food": [],
                "landmarks": [],
                "objects": [],
                "people_count": None,
                "time_hint": "",
                "weather_hint": "",
                "notable_details": [],
            },
            "ocr_text": [],
            "mood": "unknown",
            "recognized_characters": recognized,
            "safety": {
                "has_sensitive_content": False,
                "risk_level": "none",
                "reason": "",
            },
            "memory": {
                "should_consider": False,
                "reason": "mock vision 不自动建议写入长期记忆",
            },
            "live2d": {
                "suggested_emotion": "neutral",
                "suggested_expression": "neutral",
                "suggested_motion": "idle",
                "suggested_background": "room_default",
            },
            "_raw_model_output": "",
        }

    def _build_result(
        self,
        stored: StoredImage,
        candidates: list[CharacterCandidate],
        model_data: dict[str, Any],
        user_prompt: str,
        user_id: str,
    ) -> VisionAnalyzeResult:
        # 第一步：schema 校验与修复（永不抛异常），拿到强类型 payload。
        payload, violations = normalize_payload(model_data)

        character_candidates = self._normalize_model_characters(
        payload=payload,
        retrieved_candidates=candidates,
        )
        model_confidence = payload.confidence
        model_reason = payload.confidence_reason

        image_type, confirmable_candidates, confidence_report, low_policy = self.confidence_policy.evaluate(
        image_type=payload.image_type.value,
        model_confidence=model_confidence,
        model_reason=model_reason,
        character_candidates=character_candidates,
        has_sensitive_content=payload.safety.has_sensitive_content,
        )
        # 只有"模型确认过"的候选才允许进入 recognized_characters。
        recognized = [
            item for item in confirmable_candidates
            if item.source != RETRIEVAL_ONLY_SOURCE
        ][:3]
        identity_confirmed = bool(recognized)

        channels = build_channels(
            payload=payload,
            retrieval_candidate_count=len(candidates),
            identity_confirmed=identity_confirmed,
        )

        # 第二步：策略闸门——视觉结果能不能进长期记忆。
        memory_decision = decide_memory(
            image_type=image_type,
            identity_confirmed=identity_confirmed,
            identity_candidate_exists=bool(character_candidates),
            confidence_level=confidence_report.level,
            confidence_score=confidence_report.score,
            safety=payload.safety,
            model_memory=payload.memory,
            has_ocr_text=bool(payload.ocr_text),
            people_count=payload.daily_scene.people_count,
        )

        memory = payload.memory
        if low_policy.defer_memory_hint and memory.should_consider:
            memory = VisionMemoryCandidate(
                should_consider=False,
                reason=f"low_confidence_deferred: {memory.reason or low_policy.reason}",
            )
        if not memory_decision.allow:
            memory = VisionMemoryCandidate(
                should_consider=False,
                reason=f"policy_denied({memory_decision.reason_code}): {memory_decision.reason}",
            )

        live2d = VisionLive2DSuggestion() if low_policy.suppress_live2d_override else payload.live2d

        return VisionAnalyzeResult(
            schema_version=VISION_ANALYZE_SCHEMA_VERSION,
            image_id=stored.image_id,
            image_path=str(stored.path),
            width=stored.width,
            height=stored.height,
            format=stored.format,
            image_type=image_type,
            user_intent=payload.user_intent or "unknown",
            summary=payload.summary,
            objects=payload.objects,
            scene=payload.scene,
            daily_scene=payload.daily_scene,
            ocr_text=payload.ocr_text,
            mood=payload.mood,
            character_candidates=character_candidates[:5],
            recognized_characters=recognized,
            identity_confirmed=identity_confirmed,
            is_confident=(
                confidence_report.level in {
                    VisionConfidenceLevel.HIGH,
                    VisionConfidenceLevel.MEDIUM,
                }
                and not low_policy.active
            ),
            confidence=confidence_report.score,
            confidence_report=confidence_report,
            low_confidence_policy=low_policy,
            channels=channels,
            schema_violations=violations,
            memory_decision=memory_decision,
            safety=payload.safety,
            memory=memory,
            live2d=live2d,
            raw_model_output=payload.raw_output,
            metadata={
                "vision_schema_version": VISION_ANALYZE_SCHEMA_VERSION,
                "vision_image_type": image_type.value,
                "vision_confidence_score": confidence_report.score,
                "vision_confidence_level": confidence_report.level.value,
                "vision_confidence_source": confidence_report.source,
                "vision_schema_violation_count": len(violations),
                "vision_schema_violation_codes": describe_violations(violations),
                "vision_channel_ocr_status": channels.ocr.status.value,
                "vision_channel_scene_status": channels.scene.status.value,
                "vision_channel_character_status": channels.character.status.value,
                "vision_low_confidence_active": low_policy.active,
                "vision_low_confidence_avoid_identity_assertion": low_policy.avoid_identity_assertion,
                "vision_low_confidence_defer_memory_hint": low_policy.defer_memory_hint,
                "vision_low_confidence_suppress_live2d_override": low_policy.suppress_live2d_override,
                "vision_identity_confirmed": identity_confirmed,
                "vision_memory_decision_allow": memory_decision.allow,
                "vision_memory_decision_reason_code": memory_decision.reason_code,
                "vision_memory_decision_reason": memory_decision.reason,
                "vision_safety_sensitive": payload.safety.has_sensitive_content,
                "vision_confirmed_character_ids": [item.character_id for item in recognized],
                "vision_candidate_character_ids": [item.character_id for item in character_candidates[:5]],
                "vision_candidate_count": len(character_candidates),
                "vision_best_character_id": confidence_report.best_character_id,
                "vision_best_character_name": confidence_report.best_character_name,
                "character_retrieval_candidates": [
                    item.model_dump(mode="json") for item in candidates
                ],
            },
        )

    def _normalize_model_characters(
        self,
        payload: VisionModelPayload,
        retrieved_candidates: list[CharacterCandidate],
    ) -> list[CharacterCandidate]:
        """把模型声明的角色与图库候选合并，并标注候选来源。

        来源语义（决定它能否成为"已确认身份"）：
        - model_confirmed：模型明确列出了该 character_id；
        - model_only：模型列出但图库里没有对应候选；
        - retrieval_only：模型没提、只是图库检索到了 —— 永远不能当作身份确认。
        """
        retrieved_by_id = {
            item.character_id: item
            for item in retrieved_candidates
        }

        output: list[CharacterCandidate] = []

        for raw in payload.characters:
            character_id = raw.character_id.strip()
            if not character_id:
                continue

            base = retrieved_by_id.get(character_id)
            model_confidence = raw.confidence
            retrieval_score = base.score if base else 0.0

            if base:
                final_confidence = round(model_confidence * 0.62 + retrieval_score * 0.38, 6)
                source = MODEL_CONFIRMED_SOURCE
            else:
                final_confidence = round(model_confidence * 0.55, 6)
                source = "model_only"

            evidence: list[str] = []
            if base:
                evidence.extend(base.evidence)
            evidence.extend(raw.evidence)

            output.append(
                CharacterCandidate(
                    character_id=character_id,
                    name=raw.name or (base.name if base else character_id),
                    aliases=base.aliases if base else [],
                    score=retrieval_score,
                    confidence=final_confidence,
                    source=source,
                    model_confidence=model_confidence,
                    evidence=evidence,
                    metadata={
                        "model_confidence": model_confidence,
                        "retrieval_score": retrieval_score,
                        "candidate_source": source,
                    },
                )
            )

        if output:
            return sorted(output, key=lambda item: item.confidence, reverse=True)

        # 模型没有声明任何角色：只把图库候选降级返回，明确标记 retrieval_only。
        return [
            item.model_copy(
                update={
                    "source": RETRIEVAL_ONLY_SOURCE,
                    "model_confidence": 0.0,
                    "metadata": {
                        **(item.metadata or {}),
                        "candidate_source": RETRIEVAL_ONLY_SOURCE,
                    },
                }
            )
            for item in retrieved_candidates[:3]
        ]

    def _format_candidates_for_prompt(self, candidates: list[CharacterCandidate]) -> str:
        if not candidates:
            return "无候选角色。"

        lines: list[str] = []
        for index, item in enumerate(candidates, start=1):
            aliases = "、".join(item.aliases) if item.aliases else "无"
            evidence = "；".join(item.evidence)
            lines.append(
                f"{index}. character_id={item.character_id}, name={item.name}, "
                f"aliases={aliases}, retrieval_score={item.score:.3f}, evidence={evidence}"
            )

        return "\n".join(lines)

    def _image_to_data_url(self, image_path: str | Path) -> str:
        path = Path(image_path)

        with Image.open(path) as image:
            image = image.convert("RGB")

            max_side = 1280
            width, height = image.size
            scale = min(max_side / max(width, height), 1.0)

            if scale < 1.0:
                image = image.resize(
                    (int(width * scale), int(height * scale)),
                    Image.Resampling.LANCZOS,
                )

            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=85, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

        return f"data:image/jpeg;base64,{encoded}"

    def _extract_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start < 0 or end <= start:
            raise ValueError("No JSON object found in vision model output.")

        parsed = json.loads(cleaned[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("Vision model JSON root is not an object.")

        return parsed

    def _safe_float(self,value:Any, fallback:float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

        return min(max(number,0.0),1.0)