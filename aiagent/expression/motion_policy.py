"""Map emotions and intent to avatar motion."""
from aiagent.schemas.outputs import EmotionLabel, ResponsePacket


class MotionPolicy:
    def refine(self, packet: ResponsePacket) -> ResponsePacket:
        if packet.motion:
            return packet

        if packet.emotion == EmotionLabel.EXCITED:
            packet.motion = "excited_wave"
            packet.expression = packet.expression or "bright_smile"
        elif packet.emotion == EmotionLabel.HAPPY:
            packet.motion = "smile_nod"
            packet.expression = packet.expression or "happy_smile"
        elif packet.emotion == EmotionLabel.CALM:
            packet.motion = "soft_idle"
            packet.expression = packet.expression or "gentle"
        else:
            packet.motion = "idle"
            packet.expression = packet.expression or "neutral"

        return packet
