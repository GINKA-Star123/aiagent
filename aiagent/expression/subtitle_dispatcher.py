from pathlib import Path
from uuid import uuid4

from aiagent.schemas.outputs import ResponsePacket
from integrations.obs.mock_obs_bridge import MockOBSBridge


class SubtitleDispatcher:
    def __init__(
        self,
        obs_bridge: MockOBSBridge,
        output_dir: str | Path = "data/cache/mock_subtitle",
    ) -> None:
        self.obs_bridge = obs_bridge
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def dispatch(self, packet: ResponsePacket) -> ResponsePacket:
        subtitle_text = packet.subtitle_text or packet.reply_text

        subtitle_path = self.output_dir / f"{uuid4().hex}.txt"
        subtitle_path.write_text(subtitle_text, encoding="utf-8")
        packet.subtitle_path = str(subtitle_path)

        obs_payload_path = self.obs_bridge.push_subtitle(subtitle_text)
        packet.obs_payload_path = obs_payload_path
        packet.metadata["subtitle"] = "mock"

        return packet
