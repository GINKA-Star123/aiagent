from __future__ import annotations

class Live2DSceneMapper:
    def scene_from_context(
        self,
        *,
        background_id: str | None = None,
        image_type: str | None = None,
        daily_scene_type: str | None = None,
        topic: str | None = None,
        emotion: str | None = None,
    ) -> str:
        if background_id:
            return background_id

        scene_type = (daily_scene_type or "").strip().lower()
        image_kind = (image_type or "").strip().lower()
        topic_id = (topic or "").strip().lower()
        emotion_id = (emotion or "").strip().lower()

        if scene_type in {"travel", "street"}:
            return "street_day"

        if scene_type in {"food", "cafe"}:
            return "cafe_table"

        if scene_type in {"desk", "work"}:
            return "desk_work"

        if scene_type in {"landscape"}:
            return "landscape_view"

        if image_kind == "character":
            return "stage_default"

        if topic_id in {"work", "study"}:
            return "desk_work"

        if topic_id == "music":
            return "stage_default"

        if emotion_id in {"calm", "sad"}:
            return "room_night"

        return "room_default"