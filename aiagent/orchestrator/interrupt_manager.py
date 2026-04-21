"""Handle interruptions and speaking preemption."""

class InterruptManager:
    def __init__(self) -> None:
        self.pending_interrupt: bool =False
        self.last_reason : str = ""
        self.interrupt_count : int =0

    def request_interrupt(self,reason:str = "manual_interrupt")->None:
        self.pending_interrupt = True
        self.last_reason = reason
        self.interrupt_count += 1

    def consume_interrupt(self) ->str | None:
        if not self.pending_interrupt:
            return None

        self.pending_interrupt = False
        return self.last_reason
    
    def snapshot(self) -> dict:
        return {
            "pending_interrupt": self.pending_interrupt,
            "last_reason": self.last_reason,
            "interrupt_count": self.interrupt_count
        }