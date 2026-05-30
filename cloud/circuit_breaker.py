from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

class CircuitState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    HALF_OPEN = "half_open"

@dataclass
class CircuitSnapshot:
    name:str
    state:str
    failure_count:int
    success_count:int
    opened_at:float |None
    last_error:str
    allow_request:bool

class CircuitBreaker:
    def __init__(
            self,
            *,
            name:str,
            failure_threshold:int = 3,
            recovery_seconds :int = 30,
            half_open_success_threshold:int =2,
    ) ->None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at :float | None = None
        self._last_error = ""

    def allow_request(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.HALF_OPEN:
            return True
        
        if self._opened_at is None:
            return True
        
        if time.time() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            self._success_count  = 0
            return True
        
        return False
    
    def record_success(self) ->None:
        if self._state ==  CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_success_threshold:
                self._close()
            return 
        
        self._close()

    def record_failure(self,error:str) ->None:
        self._last_error = error
        self._failure_count += 1
        self._success_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._open()
            return
    
        if self._failure_count >= self.failure_threshold:
            self._open()
            return
        
    
    def snapshot(self) -> CircuitSnapshot:
        return CircuitSnapshot(
            name=self.name,
            state = self._state.value,
            failure_count=self._failure_count,
            success_count=self._success_count,
            opened_at=self._opened_at,
            last_error = self._last_error,
            allow_request = self.allow_request(),
        )
    
    def _open(self) ->None:
        self._state = CircuitState.OPEN
        self._opened_at = time.time()

    def _close(self) ->None:
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._success_count = 0
        self._failure_count = 0
        self._last_error = ""