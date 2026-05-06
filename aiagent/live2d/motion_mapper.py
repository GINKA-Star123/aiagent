from __future__ import annotations

from aiagent.live2d.models import Live2DCharacterProfile, Live2DExpressionAsset, Live2DMotionAsset

class Live2DMotionMapper:
    def resolve_expression(
            self,
            profile:Live2DCharacterProfile,
            emotion:str,
            expression:str|None = None
    )->Live2DExpressionAsset |None:
        expression_id = (expression or "").strip()
        emotion_id = (emotion or "").strip().lower()

        if not expression_id:
            expression_id=profile.emotion_expression_map.get(emotion_id,"")
        
        if not expression_id:
            expression_id=profile.default_expression

        return self._find_expression(profile,expression_id)
    
    def resolve_motion(
            self,
            profile:Live2DCharacterProfile,
            emotion:str,
            motion:str|None = None
    ) ->Live2DMotionAsset|None:
        motion_id = (motion or "").strip()
        emotion_id = (emotion or "").strip().lower()

        if not motion_id:
            motion_id = profile.emotion_motion_map.get(emotion_id, "")

        if not motion_id:
            motion_id = profile.default_motion

        return self._find_motion(profile, motion_id)
    
    def _find_expression(
            self,
            profile:Live2DCharacterProfile,
            expression_id:str
    )->Live2DExpressionAsset|None:
        target = expression_id.strip().lower()

        for item in profile.expressions:
            if item.expression_id.strip().lower() == target:
                return item
            if target in [alias.lower() for alias in item.aliases]:
                return item
        return None
    
    def _find_motion(
            self,
            profile:Live2DCharacterProfile,
            motion_id:str
    )->Live2DMotionAsset|None:
        target = motion_id.strip().lower()

        for item in profile.motions:
            if item.motion_id.strip().lower() == target:
                return item
            if target in [alias.lower() for alias in item.aliases]:
                return item
        return None