from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict,dataclass
from threading import Lock
from typing import Any

@dataclass 
class RequestMetric:
    request_id:str
    method:str
    path:str
    status_code:int
    latency_ms:float
    created_at:float

class MetricsStore:
    def __init__(self,max_items:int = 300) -> None:
        self._lock = Lock()
        self._requests :deque[RequestMetric] = deque(maxlen=max_items)
        self._started_at=time.time()
    
    def record_request(
            self,
            *,
            request_id:str,
            method:str,
            path:str,
            status_code:int,
            latency_ms:float,
    ) ->None:
        item = RequestMetric(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            created_at=time.time(),
        )
        with self._lock:
            self._requests.appendleft(item)
    
    def snapshot(self) ->dict[str,Any]:
        with self._lock:
            requests = list(self._requests)

        total = len(requests)
        errors = sum(1 for item in requests if item.status_code>=500)
        limited = sum(1 for item in requests if item.status_code in {429,503})
        avg_latency = (
            round(sum(item.latency_ms for item in requests) / total, 2) if total else 0
        )

        route_counts : dict[str,int] = {}
        for item in requests:
            key = f"{item.method} {item.path}"
            route_counts[key] = route_counts.get(key,0) + 1

        return {
            "uptime_seconds":round(time.time()-self._started_at,),
            "recent_total":total,
            "recent_errors":errors,
            "recent_limited":limited,
            "avg_latency_ms":avg_latency,
            "route_counts":route_counts,
            "recent_requests":[asdict(item) for item in requests[:80]],
        }
    
metrics_store = MetricsStore()