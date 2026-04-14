"""Broadcast output events to external consumers."""
from aiagent.expression.live2d_dispatcher import Live2DDispatcher
from aiagent.expression.motion_policy  import MotionPolicy
from aiagent.expression.subtitle_dispatcher import SubtitleDispatcher
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.schemas.outputs import OutputEvent
from integrations.bilibili.mock_bilibili_bridge import MockBilibiliBridge   

class OutputBroadcaster:

    def __init__(
            self,
            tts_dispatcher: TTSDispatcher,
            subtitle_dispatcher: SubtitleDispatcher,
            live2d_dispatcher: Live2DDispatcher,
            motion_policy: MotionPolicy,
            bilibili_bridge: MockBilibiliBridge
            ) ->None:
        self.tts_dispatcher = tts_dispatcher
        self.subtitle_dispatcher = subtitle_dispatcher
        self.live2d_dispatcher = live2d_dispatcher
        self.motion_policy = motion_policy
        self.bilibili_bridge = bilibili_bridge

    def broadcast(self,output_event: OutputEvent) -> OutputEvent:

        packet = output_event.packet

        packet = self.motion_policy.refine(packet)
        packet = self.tts_dispatcher.dispatch(packet)
        packet = self.subtitle_dispatcher.dispatch(packet)
        packet = self.live2d_dispatcher.dispatch(packet)

        bilibili_payload_path = self.bilibili_bridge.publish_reply_event(
            reply_text=packet.reply_text,
        )
        packet.bilibili_payload_path = bilibili_payload_path
        packet.metadata["bilibili"] = "mock"

        output_event.packet = packet
        return output_event