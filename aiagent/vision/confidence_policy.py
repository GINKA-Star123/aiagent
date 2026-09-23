from __future__ import annotations

from aiagent.graphs.graph_model import (
    CharacterCandidate,
    VisionConfidenceLevel,
    VisionConfidenceReport,
    VisionImageType,
    VisionLowConfidencePolicy,
)

SCENE_IMAGE_TYPES = {
    VisionImageType.DAILY,
    VisionImageType.SCREENSHOT,
    VisionImageType.DOCUMENT,
    VisionImageType.FOOD,
    VisionImageType.TRAVEL,
    VisionImageType.LANDSCAPE,
    VisionImageType.OBJECT,
}

# 候选来源标记：只有非 retrieval_only 的候选才有资格成为"已确认身份"。
RETRIEVAL_ONLY_SOURCE = "retrieval_only"
MODEL_CONFIRMED_SOURCE = "model_confirmed"

class VisionConfidencePolicy:
    def __init__(
        self,
        character_confident_score: float = 0.78,
        scene_confident_score: float = 0.55,
        low_margin: float = 0.12,
    ) -> None:
        self.character_confident_score = self._clamp(character_confident_score)
        self.scene_confident_score = self._clamp(scene_confident_score)
        self.low_margin = max(float(low_margin), 0.0)

    def _clamp(self, value: float | int | str | None) -> float:
        try:
            number = float(value) # type: ignore
        except Exception:
            return 0.0
        return min(max(number,0.0),1.0)

    def _image_type(self,value:str) -> VisionImageType:
        try:
            return VisionImageType(str(value).strip().lower())

        except Exception:
            return VisionImageType.UNKNOWN 

    def _level(self,*,score:float,threshold:float) -> VisionConfidenceLevel:
        if score >= min(threshold + 0.12,1.0):
            return VisionConfidenceLevel.HIGH
        if score >= threshold:
            return VisionConfidenceLevel.MEDIUM
        if score >= max(0.0,threshold - self.low_margin):
            return VisionConfidenceLevel.LOW
        return VisionConfidenceLevel.UNCERTAIN

    def evaluate(
        self,
        *,
        image_type: str,
        model_confidence: float,
        model_reason: str,
        character_candidates: list[CharacterCandidate],
        has_sensitive_content: bool = False,
    ) -> tuple[VisionImageType, list[CharacterCandidate], VisionConfidenceReport, VisionLowConfidencePolicy]:
        normalized_type = self._image_type(image_type)
        candidates = sorted(
            character_candidates,
            key=lambda item: item.confidence,
            reverse=True,
        )

        best = candidates[0] if candidates else None
        # 只有"模型确认过来源"的候选才能充当身份证据；
        # 纯图库检索候选（source=retrieval_only）相似度再高也只是候选。
        best_confirmable = next(
            (item for item in candidates if item.source != RETRIEVAL_ONLY_SOURCE),
            None,
        )
        character_score = self._clamp(best.confidence if best else 0.0)
        confirmable_score = self._clamp(best_confirmable.confidence if best_confirmable else 0.0)
        model_score = self._clamp(model_confidence)
        retrieval_score = float(best.score) if best else 0.0

        if normalized_type == VisionImageType.CHARACTER:
            # 角色图的可信度必须来自"可确认来源"的候选，而不是纯检索相似度。
            score = confirmable_score
            threshold = self.character_confident_score
            source = "character_identity" if best_confirmable is not None else "character_candidate_only"
        elif normalized_type in SCENE_IMAGE_TYPES:
            score = model_score
            threshold = self.scene_confident_score
            source = "scene_understanding"
        else:
            score = max(model_score, character_score)
            threshold = self.character_confident_score
            source = "unknown_image_type"

        level = self._level(score=score, threshold=threshold)

        confirmed_characters: list[CharacterCandidate] = []
        if normalized_type == VisionImageType.CHARACTER:
            confirmed_characters = [
                item
                for item in candidates
                if self._clamp(item.confidence) >= self.character_confident_score
                and item.source != RETRIEVAL_ONLY_SOURCE
            ]

        identity_candidate_exists = normalized_type in {
            VisionImageType.CHARACTER,
            VisionImageType.UNKNOWN,
        } and bool(candidates)

        identity_confirmed = (
            normalized_type == VisionImageType.CHARACTER
            and best_confirmable is not None
            and confirmable_score >= self.character_confident_score
        )

        avoid_identity_assertion = (
            (identity_candidate_exists and not identity_confirmed)
            or has_sensitive_content
        )

        low_score_active = level in {
            VisionConfidenceLevel.LOW,
            VisionConfidenceLevel.UNCERTAIN,
        }

        active = low_score_active or avoid_identity_assertion

        reply_instruction = self._build_reply_instruction(
            normalized_type=normalized_type,
            active=active,
            avoid_identity_assertion=avoid_identity_assertion,
            has_sensitive_content=has_sensitive_content,
        )

        reason_parts: list[str] = []
        if model_reason.strip():
            reason_parts.append(model_reason.strip())
        if best is not None:
            reason_parts.append(
                f"最佳角色候选为 {best.name}，角色置信度 {character_score:.3f}，确认阈值 {self.character_confident_score:.3f}"
            )
            if best.source == RETRIEVAL_ONLY_SOURCE:
                reason_parts.append("该候选仅来自图库检索，缺少模型确认，不能作为身份确认")
        else:
            reason_parts.append("没有可用角色候选")
        if has_sensitive_content:
            reason_parts.append("检测到敏感内容，已强制使用保守策略")
        if active:
            reason_parts.append("当前结果需要按低置信度策略处理")

        reason = "；".join(reason_parts)

        report = VisionConfidenceReport(
            score=score,
            level=level,
            threshold=threshold,
            source=source,
            reason=reason,
            evidence=list(best.evidence[:4]) if best else [],
            character_score=character_score,
            model_score=model_score,
            best_retrieval_score=retrieval_score,
            best_character_id=best.character_id if best else "",
            best_character_name=best.name if best else "",
            candidate_count=len(candidates),
        )

        policy = VisionLowConfidencePolicy(
            active=active,
            reason=reason if active else "",
            use_conservative_wording=active,
            avoid_identity_assertion=avoid_identity_assertion,
            expose_candidates=avoid_identity_assertion and bool(candidates),
            defer_memory_hint=active,
            suppress_live2d_override=(
                (normalized_type == VisionImageType.CHARACTER and avoid_identity_assertion)
                or has_sensitive_content
            ),
            reply_instruction=reply_instruction,
        )

        return normalized_type, confirmed_characters, report, policy

    def _build_reply_instruction(
            self,
            *,
            normalized_type: VisionImageType,
            active: bool,
            avoid_identity_assertion: bool,
            has_sensitive_content: bool = False,
        ) -> str:
        if has_sensitive_content:
            return "图片可能包含敏感内容，请只做中性描述，不要确认角色身份，也不要写入记忆。"
        if not active:
            return "可以正常使用视觉分析结果，但不要编造图片里没有的信息。"
        if avoid_identity_assertion:
            return "视觉结果不够确定。候选角色只能作为参考，不能写成已确认身份。"
        if normalized_type in SCENE_IMAGE_TYPES:
            return "场景理解置信度不足，请优先描述可见场景、物体和文字，不要强行认角色。"
        return "视觉结果不够确定，请使用保守语气回答。"