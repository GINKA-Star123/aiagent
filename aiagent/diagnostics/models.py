from __future__ import annotations

from datetime import datetime,timezone
from typing import Any,Literal

from pydantic import BaseModel,Field

DiagnosticStatus = Literal["ok","degraded","failed","skipped"]

class DiagnosticCheck(BaseModel):
    name:str
    status:DiagnosticStatus
    summary:str
    details:dict[str,Any] = Field(default_factory=dict)
    action:str = ""

class DiagnosticReport(BaseModel):
    ok:bool
    status:DiagnosticStatus
    generated_at :str
    checks:list[DiagnosticCheck]
    summary:dict[str,int]

    @classmethod
    def from_checks(cls,checks:list[DiagnosticCheck]) ->"DiagnosticReport":
        counts = {
            "ok":0,
            "degraded":0,
            "failed":0,
            "skipped":0,
        }
        
        for check in checks:
            counts[check.status] += 1

        if counts["failed"]>0:
            status:DiagnosticStatus = "failed"
        elif counts["degraded"]>0:
            status:DiagnosticStatus = "degraded"
        elif counts["ok"]>0:
            status:DiagnosticStatus = "ok"
        else:
            status:DiagnosticStatus = "skipped"

        return cls(
            ok=status in {"ok","degraded"},
            status=status,
            generated_at=datetime.now(timezone.utc).isoformat(),
            checks=checks,
            summary=counts,
        )