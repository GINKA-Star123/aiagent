from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from aiagent.live2d.payload_builder import Live2DPayloadBuilder

class FileLive2DClient:
    def __init__(
            self,
            payload_builder:Live2DPayloadBuilder,
            output_dir: str|Path = "data/cache/live2d"
    ) ->None:
        self.payload_builder = payload_builder
        self.output_dir =Path( output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def dispatch(
            self,
            *,
            character_id:str = "yzl",
            emotion:str ="neutral",
            expression:str|None =None,
            motion:str|None = None,
            background_id:str|None =None,
            image_type:str|None = None,
            daily_scene_type:str|None =None,
            topic:str|None =None,
            audio_url:str|None = None,
            metadata:dict|None = None,
    )->str:
        payload = self.payload_builder.build(
            character_id=character_id,
            emotion=emotion,
            expression=expression,
            motion=motion,
            background_id=background_id,
            image_type=image_type,
            daily_scene_type=daily_scene_type,
            topic=topic,
            audio_url=audio_url,
            metadata=metadata
        )

        output_path = self.output_dir / f"{uuid4()}.json"
        output_path.write_text(
            json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"
        )
        return str(output_path)