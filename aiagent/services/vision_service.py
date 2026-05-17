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

from aiagent.vision.character_retriever import CharacterRetriever
from aiagent.vision.image_store import ImageStore, StoredImage
from aiagent.graphs.graph_model import (
    CharacterCandidate,
    DailySceneResult,
    VisionAnalyzeResult,
    VisionLive2DSuggestion,
    VisionMemoryCandidate,
    VisionSafetyResult,
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
    ) -> None:
        self.image_store = image_store
        self.character_retriever = character_retriever
        self.provider = provider.strip().lower()
        self.model = model.strip()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.confident_score = confident_score

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

用户附加说明：
{user_prompt or "无"}

候选角色：
{candidate_text}

请输出 JSON：
{{
  "image_type": "character|daily|screenshot|document|food|travel|landscape|object|unknown",
  "user_intent": "用户可能想让你做什么，例如识别角色、描述照片、分析食物、读图中文字、判断场景等",
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

        return {
            "image_type": "character" if recognized else "unknown",
            "user_intent": "mock vision 仅验证角色图库召回，不做通用图片理解",
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
        recognized = self._normalize_model_characters(
            raw_items=model_data.get("recognized_characters", []),
            retrieved_candidates=candidates,
        )

        best_confidence = max([item.confidence for item in recognized], default=0.0)
        is_confident = best_confidence >= self.confident_score

        if not is_confident:
            recognized = [
                item
                for item in recognized
                if item.confidence >= max(self.confident_score - 0.12, 0.0)
            ]

        return VisionAnalyzeResult(
            image_id=stored.image_id,
            image_path=str(stored.path),
            width=stored.width,
            height=stored.height,
            format=stored.format,
            image_type=str(model_data.get("image_type", "unknown")).strip() or "unknown",
            user_intent=str(model_data.get("user_intent", "unknown")).strip() or "unknown",
            summary=str(model_data.get("summary", "")).strip(),
            objects=[str(item).strip() for item in model_data.get("objects", []) if str(item).strip()],
            scene=str(model_data.get("scene", "")).strip(),
            daily_scene=DailySceneResult(**(model_data.get("daily_scene") or {})),
            ocr_text=[str(item).strip() for item in model_data.get("ocr_text", []) if str(item).strip()],
            mood=str(model_data.get("mood", "")).strip(),
            recognized_characters=recognized,
            is_confident=is_confident,
            confidence=best_confidence,
            safety=VisionSafetyResult(**(model_data.get("safety") or {})),
            memory=VisionMemoryCandidate(**(model_data.get("memory") or {})),
            live2d=VisionLive2DSuggestion(**(model_data.get("live2d") or {})),
            raw_model_output=str(model_data.get("_raw_model_output", "")),
            metadata={
                "user_id": user_id,
                "user_prompt": user_prompt,
                "character_retrieval_candidates": [
                    item.model_dump(mode="json")
                    for item in candidates
                ],
                "vision_provider": self.provider,
                "vision_model": self.model,
                "confident_score": self.confident_score,
            },
        )

    def _normalize_model_characters(
        self,
        raw_items: Any,
        retrieved_candidates: list[CharacterCandidate],
    ) -> list[CharacterCandidate]:
        if not isinstance(raw_items, list):
            raw_items = []

        retrieved_by_id = {
            item.character_id: item
            for item in retrieved_candidates
        }

        output: list[CharacterCandidate] = []

        for raw in raw_items:
            if not isinstance(raw, dict):
                continue

            character_id = str(raw.get("character_id", "")).strip()
            if not character_id:
                continue

            base = retrieved_by_id.get(character_id)

            try:
                model_confidence = float(raw.get("confidence", 0.0))
            except (TypeError, ValueError):
                model_confidence = 0.0

            model_confidence = min(max(model_confidence, 0.0), 1.0)
            retrieval_score = base.score if base else 0.0

            if base:
                final_confidence = round(model_confidence * 0.62 + retrieval_score * 0.38, 6)
            else:
                final_confidence = round(model_confidence * 0.55, 6)

            evidence: list[str] = []
            if base:
                evidence.extend(base.evidence)
            evidence.extend([str(item).strip() for item in raw.get("evidence", []) if str(item).strip()])

            output.append(
                CharacterCandidate(
                    character_id=character_id,
                    name=str(raw.get("name") or (base.name if base else character_id)).strip(),
                    aliases=base.aliases if base else [],
                    score=retrieval_score,
                    confidence=final_confidence,
                    evidence=evidence,
                    metadata={
                        "model_confidence": model_confidence,
                        "retrieval_score": retrieval_score,
                    },
                )
            )

        if output:
            return sorted(output, key=lambda item: item.confidence, reverse=True)

        return retrieved_candidates[:3]

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
