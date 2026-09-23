from __future__ import annotations

from typing import Any

class NullRAGPipeline:
    def __init__(self,reason:str = "RAG pipeline is disabled.") -> None:
        self.reason = reason

    def build_index(self,force_rebuild: bool = False) -> dict[str,Any]:
        return {
            "ok":False,
            "status":"disabled",
            "force_rebuild":force_rebuild,
            "reason":self.reason
        }

    def rebuild_async(self,force_rebuild:bool=True) -> dict[str,Any]:
        return {
            "ok":False,
            "status":"disabled",
            "force_rebuild":force_rebuild,
            "reason":self.reason,
        }

    def build_status(self)->dict[str,Any]:
        return {
            "ok":False,
            "status":"disabled",
            "reason":self.reason,
        }

    def ensure_ready(self) -> None:
        return None

    def retrieve(self,query:str,top_k :int|None =None) ->list[Any]:
        return []

    def search(self, query: str, top_k: int = 4) -> list[str]:
        return []

    def format_for_prompt(self, query: str, top_k: int = 4) -> str:
        return "无外部知识。"

    def debug_retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        return []

    def index_freshness(self, force_refresh: bool = False) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "missing",
            "stale": False,
            "reasons": ["rag_disabled"],
            "hint": "RAG 索引未启用。",
            "manifest_path": "",
            "checked_at": "",
        }
    
    def stats(self) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "disabled",
            "degraded": True,
            "reason": self.reason,
            "document_count": 0,
            "vector_count": 0,
            "index_freshness": self.index_freshness()
        }

    def inspect(self, query: str, top_k: int = 4, min_cosine_score: float = 0.38) -> dict[str, Any]:
        return {
            "ok": False,
            "query": query,
            "top_k": top_k,
            "should_inject": False,
            "confidence": {
                "status": "empty",
                "level": "none",
                "should_inject": False,
                "reason": "rag_disabled",
                "candidate_count": 0,
                "signals": ["rag_disabled"],
            },
            "citations": [],
            "chunks": [],
            "prompt_context": "无外部知识。",
            "reason": self.reason,
        }