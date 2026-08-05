from __future__ import annotations

from aiagent.memory.mem0_memory import MemoryHit
from aiagent.memory.memory_deduper import MemoryDeduper
from aiagent.memory.memory_safety import MemorySafetyFilter
from aiagent.schemas.memory import MemoryStorePlan,MemoryWriteDecision

class MemoryIntakeService:
    def __init__(
            self,
            safety_filter: MemorySafetyFilter | None = None,
            deduper: MemoryDeduper | None = None,
    ) ->None:
        self.safety_filter = safety_filter or MemorySafetyFilter()
        self.deduper = deduper or MemoryDeduper()

    def build_store_plan(
            self,
            *,
            decision: MemoryWriteDecision | None,
            memory_hits: list[MemoryHit],
            existing_memory_context:str,
            user_text:str,
            assistant_text:str,
    ) -> MemoryStorePlan:
        if decision is None:
            return MemoryStorePlan(
                should_store=False,
                status="skipped",
                reason="missing_write_decision",
            )
        if not decision.should_store:
            return MemoryStorePlan(
                should_store=False,
                status="skipped",
                reason=decision.reason or "policy_should_store_false",
                category=decision.category,
                importance=decision.importance,
                metadata={
                    "policy_confidence":decision.confidence,
                },
            )

        candidate = self._select_candidate(decision)
        if not candidate:
            return MemoryStorePlan(
                should_store=False,
                status="skipped",
                reason="empty_memory_candidate",
                category=decision.category,
                importance=decision.importance,
            )

        guard = self.safety_filter.evaluate(candidate)
        if not guard.allowed:
            return MemoryStorePlan(
                should_store=False,
                status="blocked",
                reason=guard.reason,
                category=decision.category,
                importance=decision.importance,
                memory_text=guard.redacted_text,
                guard=guard,
                metadata={
                    "policy_reason": decision.reason,
                    "policy_confidence": decision.confidence,
                },
            )

        dedup = self.deduper.check(
            candidate=guard.redacted_text,
            hits=memory_hits,
            existing_context=existing_memory_context,
        )
        if dedup.duplicate:
            return MemoryStorePlan(
                should_store=False,
                status="duplicate",
                reason=dedup.reason,
                category=decision.category,
                importance=decision.importance,
                memory_text=guard.redacted_text,
                guard=guard,
                dedup=dedup,
                metadata={
                    "policy_reason": decision.reason,
                    "policy_confidence": decision.confidence,
                },
            )
        return MemoryStorePlan(
            should_store=True,
            status="ready",
            reason=decision.reason or "policy_allowed",
            category=decision.category,
            importance=decision.importance,
            memory_text=guard.redacted_text,
            guard=guard,
            dedup=dedup,
            metadata={
                "policy_reason": decision.reason,
                "policy_confidence": decision.confidence,
                "source_facts_count": len(decision.facts),
            },
        )
    def _select_candidate(self,decision: MemoryWriteDecision) -> str:
        facts = [item.strip() for item in decision.facts if item.strip()]
        if facts:
            return ";".join(facts)
        return decision.memory_hint.strip()