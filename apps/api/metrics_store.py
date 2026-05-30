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

@dataclass
class ExternalServiceMetric:
    service:str
    ok:bool
    latency_ms:float
    error:str
    created_at:float

class MetricsStore:
    def __init__(self,max_items:int = 300) -> None:
        self._lock = Lock()
        self._requests :deque[RequestMetric] = deque(maxlen=max_items)
        self._started_at=time.time()
        self._external:deque[ExternalServiceMetric] = deque(maxlen=max_items)
    
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

    def record_external_service(
            self,
            *,
            service:str,
            ok:bool,
            latency_ms:float,
            error:str = "",
    )->None:
        item = ExternalServiceMetric(
            service=service,
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            created_at=time.time(),
        )

        with self._lock:
            self._external.appendleft(item)

    def external_snapshot(self) -> dict[str,Any]:
        with self._lock:
            items = list(self._external)

        services:dict[str,dict[str,Any]] = {}

        for item in items:
            bucket = services.setdefault(item.service,{
                "recent_total": 0,
                "recent_errors": 0,
                "avg_latency_ms": 0.0,
                "last_error": "",
                "last_seen_at": 0.0,
            })

            bucket["recent_total"] += 1
            bucket["last_seen_at"] = max(bucket["last_seen_at"],item.created_at)

            if not item.ok:
                bucket["recent_errors"] += 1
                if not bucket["last_error"]:
                    bucket["last_error"] = item.error

        for service_name, bucket in services.items():
            service_items = [item for item in items if item.service == service_name]
            if service_items:
                bucket["avg_latency_ms"] = round(
                    sum(item.latency_ms for item in service_items) / len(service_items),
                    2,
                )

        return services

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
            "external_services":self.external_snapshot(),
        }
    
metrics_store = MetricsStore()