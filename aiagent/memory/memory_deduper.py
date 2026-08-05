from __future__ import annotations

import re
from difflib import SequenceMatcher

from aiagent.memory.mem0_memory import MemoryHit
from aiagent.schemas.memory import MemoryDedupResult

class MemoryDeduper:
    def __init__(self,duplicate_thresold:float = 0.86) -> None:
        self.duplicate_thresold = duplicate_thresold

    def check(
            self,
            candidate:str,
            hits:list[MemoryHit],
            existing_context:str = "",
    ) -> MemoryDedupResult:
        candidate_norm = self._normalize(candidate)
        if not candidate_norm:
            return MemoryDedupResult(
                duplicate=False,
                reason="empty_candidate",
            )

        best_hit:MemoryHit|None = None
        best_similarity = 0.0

        for hit in hits:
            similarity = self._similarity(candidate_norm,self._normalize(hit.memory))
            if similarity> best_similarity:
                best_hit = hit
                best_similarity = similarity

        if best_hit is not None and best_similarity >=self.duplicate_thresold:
            return MemoryDedupResult(
                duplicate = True,
                reason = "similar_existing_memory",
                matched_memory_id = best_hit.id,
                matched_memory = best_hit.memory,
                similarity = round(best_similarity,4)
            )

        if existing_context:
            context_similarity = self._context_similarity(candidate_norm,existing_context)
            if context_similarity >= self.duplicate_thresold:
                return MemoryDedupResult(
                    duplicate = True,
                    reason = "similar_existing_context",
                    similarity = round(context_similarity,4)
                )
            
        return MemoryDedupResult(
            duplicate = False,
            reason = "not_duplicate",
            similarity=round(best_similarity,4)
        )

    def _normalize(self, text: str) -> str:
        normalized = text.strip().lower()
        normalized = normalized.replace("阿绫", "乐正绫")
        normalized = normalized.replace("阿綾", "乐正绫")
        normalized = normalized.replace("天依", "洛天依")
        normalized = re.sub(r"\s+", "", normalized)
        normalized = re.sub(r"[，。！？、,.!?;；：:（）()\[\]【】\"'“”‘’]", "", normalized)
        return normalized

    def _similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        if left in right or right in left:
            shorter = min(len(left), len(right))
            longer = max(len(left), len(right))
            return shorter / max(longer, 1)
        return SequenceMatcher(None, left, right).ratio()

    def _context_similarity(self, candidate_norm: str, existing_context: str) -> float:
        best = 0.0
        for line in existing_context.splitlines():
            line = line.strip()
            if not line:
                continue
            best = max(best, self._similarity(candidate_norm, self._normalize(line)))
        return best