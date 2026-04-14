"""Dispatch motion and expression commands to Live2D."""
from aiagent.schemas.outputs import ResponsePacket
from integrations.live2d.mock_live2d_client import MockLive2DClient

class Live2DDispatcher:
    def __init__(self,client:MockLive2DClient) -> None:
        self.client = client

    def dispatch(self,packet:ResponsePacket) -> ResponsePacket:
        command_path = self.client.dispatch(
            expression=packet.expression,
            motion = packet.motion,
            text = packet.reply_text
        )

        packet.live2d_command_path = command_path
        packet.metadata["live2d"] = "mock"
        return packet