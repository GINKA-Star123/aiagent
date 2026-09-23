from __future__ import annotations

import uuid
import logging
from typing import Any,TypedDict
from datetime import datetime, timezone

from aiagent.memory.memory_write_audit import MemoryWriteAuditLog
from aiagent.memory.memory_write_dispatcher import MemoryWriteDispatcher
from aiagent.schemas.memory import (
    MemoryCategory,
    MemoryImportance,
    MemorySensitivity,
    MemoryWriteAudit,
)
from langgraph.graph import START,END,StateGraph

from aiagent.memory.memory_preferences import MemoryPreferenceStore
from aiagent.memory.mem0_memory import Mem0LongTermMemory,MemoryHit
from aiagent.memory.memory_intake import MemoryIntakeService
from aiagent.memory.memory_prompt import MemoryPromptBuilder
from aiagent.schemas.memory import MemoryWriteDecision,MemoryStorePlan,MemoryRecord
from aiagent.services.memory_policy_llm_service import MemoryPolicyLLMService
from aiagent.memory.memory_layers import infer_memory_layer
from aiagent.graphs.degradation import (
    build_degraded_memory_retrieve_state,
    build_degraded_memory_store_state,
)
from aiagent.graphs.metadata_utils import (
    mark_stage_done,
    mark_stage_failed,
    mark_stage_skipped,
    now_perf,
)

logger = logging.getLogger(__name__)

class MemoryGraphState(TypedDict,total=False):
    user_id:str
    user_name:str
    agent_id:str
    session_id:str
    turn_id:str
    user_text:str
    assistant_text:str
    retrieval_query:str
    planner_should_store_memory:bool
    memory_hits:list[MemoryHit]
    memory_prompt_context:str
    write_decision:MemoryWriteDecision
    memory_store_plan:MemoryStorePlan
    memory_pinned_records: list[MemoryRecord]
    memory_prompt_context_data:dict[str,Any]
    store_result:dict[str,Any]
    metadata:dict[str,Any]

class MemoryRunner:
    def __init__(
            self,
            memory:Mem0LongTermMemory,
            policy_service:MemoryPolicyLLMService,
            default_agent_id:str = "yzl",
            retrieval_limit:int =6,
            intake_service: MemoryIntakeService|None = None,
            preference_store: MemoryPreferenceStore|None = None,
            prompt_builder: MemoryPromptBuilder|None = None,
            write_dispatcher: MemoryWriteDispatcher|None = None,
            audit_log: MemoryWriteAuditLog|None = None,
            async_write_enabled: bool = True,
    ) ->None:
        self.memory = memory
        self.policy_service = policy_service
        self.default_agent_id = default_agent_id
        self.retrieval_limit = retrieval_limit
        self.intake_service = intake_service or MemoryIntakeService()
        self.preference_store = preference_store or MemoryPreferenceStore()
        self.prompt_builder = prompt_builder or MemoryPromptBuilder()
        self.write_dispatcher = write_dispatcher or MemoryWriteDispatcher()
        self.audit_log = audit_log or MemoryWriteAuditLog()
        self.async_write_enabled = bool(async_write_enabled)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(MemoryGraphState)
        graph.add_node("retrieve",self._retrieve_node)
        graph.add_node("decide_write",self._decide_write_node)
        graph.add_node("store",self._store_node)
        graph.add_node("guard_write",self._guard_write_node)

        graph.add_edge(START,"retrieve")
        graph.add_edge("retrieve","decide_write")
        graph.add_edge("decide_write","guard_write")
        graph.add_conditional_edges(
            "decide_write",
            self._route_after_decision,
            {"store":"store","end":END}
        )
        graph.add_conditional_edges(
            "guard_write",
            self._route_after_guard,
            {"store": "store", "end": END},
        )
        graph.add_edge("store",END)
        return graph.compile()

    def retrieve_before_reply(
        self,
        user_id:str,
        user_text:str,
        retrieval_query:str = "",
        agent_id:str|None = None
    ) ->MemoryGraphState:
        started_at = now_perf()
        agent = agent_id or self.default_agent_id
        try:
            if not self.preference_store.is_enabled(user_id=user_id,agent_id=agent):
                return {
                    "user_id": user_id,
                    "agent_id": agent,
                    "memory_hits": [],
                    "memory_prompt_context": "无长期记忆。",
                    "metadata": mark_stage_skipped(
                        {},
                        "memory_retrieve",
                        "long_term_memory_disabled_by_user",
                        memory_long_term_enabled=False,
                        memory_error="",
                    ),
                }
            return self._retrieve_node(
                {
                    "user_id":user_id,
                    "user_text":user_text,
                    "retrieval_query":retrieval_query,
                    "agent_id":agent_id or self.default_agent_id
                }
            )
        except Exception as exc:
            # 记忆是可选能力：不可用时返回"无长期记忆"
            return build_degraded_memory_retrieve_state(  #type:ignore
                user_id=user_id,
                agent_id=agent,
                metadata=mark_stage_failed(
                    {},
                    "memory_retrieve",
                    started_at,
                    exc,
                    memory_error=str(exc),
                ),
            )
        
    def run_after_reply(
            self,
            user_id:str,
            user_name:str,
            session_id:str,
            turn_id:str,
            user_text:str,
            assistant_text:str,
            retrieval_query:str,
            planner_should_store_memory:bool,
            memory_prompt_context:str = "",
            metadata:dict[str,Any] |None = None,
            agent_id:str|None = None
    ) ->MemoryGraphState:
        started_at = now_perf()
        agent = agent_id or self.default_agent_id
        try:
            if not self.preference_store.is_enabled(user_id=user_id, agent_id=agent):
                return {
                    "user_id": user_id,
                    "agent_id": agent,
                    "store_result": {
                        "ok": False,
                        "status": "skipped",
                        "reason": "long_term_memory_disabled_by_user",
                    },
                    "metadata": mark_stage_skipped(
                        metadata or {},
                        "memory_store",
                        "long_term_memory_disabled_by_user",
                        memory_long_term_enabled=False,
                        memory_error="",
                    ),
                }
            state = self.graph.invoke( # type: ignore
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "agent_id": agent_id or self.default_agent_id,
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "user_text": user_text,
                    "assistant_text": assistant_text,
                    "retrieval_query": retrieval_query or user_text,
                    "planner_should_store_memory": planner_should_store_memory,
                    "memory_prompt_context": memory_prompt_context,
                    "metadata": metadata or {},
                }
            )
            self._append_audit(state) # type: ignore
            return state # type:ignore 
        except Exception as exc:
            self._append_audit_failure(
                user_id=user_id,
                agent_id=agent,
                session_id=session_id,
                turn_id=turn_id,
                error=str(exc),
            )
            return build_degraded_memory_store_state( # type: ignore
                user_id=user_id, 
                agent_id=agent,
                error=exc,
                metadata=mark_stage_failed(
                    metadata or {},
                    "memory_store",
                    started_at,
                    exc,
                    memory_error=str(exc),
                ),
            )

    def run_after_reply_async(
            self,
            user_id:str,
            user_name:str,
            session_id:str,
            turn_id:str,
            user_text:str,
            assistant_text:str,
            retrieval_query:str,
            planner_should_store_memory:bool,
            memory_prompt_context:str = "",
            metadata:dict[str,Any] |None = None,
            agent_id:str|None = None
    ) ->MemoryGraphState:
        """异步写入入口：立刻返回 queued，真正的策略判断与写盘在后台线程完成。

        失败只体现在 write_status()/审计日志里，永远不会影响本轮回复。
        """
        agent = agent_id or self.default_agent_id

        if not self.async_write_enabled:
            return self.run_after_reply(
                user_id=user_id,
                user_name=user_name,
                session_id=session_id,
                turn_id=turn_id,
                user_text=user_text,
                assistant_text=assistant_text,
                retrieval_query=retrieval_query,
                planner_should_store_memory=planner_should_store_memory,
                memory_prompt_context=memory_prompt_context,
                metadata=metadata,
                agent_id=agent,
            )

        submitted = self.write_dispatcher.submit(
            self.run_after_reply,
            user_id=user_id,
            user_name=user_name,
            session_id=session_id,
            turn_id=turn_id,
            user_text=user_text,
            assistant_text=assistant_text,
            retrieval_query=retrieval_query,
            planner_should_store_memory=planner_should_store_memory,
            memory_prompt_context=memory_prompt_context,
            metadata=metadata or {},
            agent_id=agent,
        )

        return {
            "user_id": user_id,
            "agent_id": agent,
            "store_result": submitted,
            "metadata": mark_stage_done(
                metadata or {},
                "memory_store_dispatch",
                now_perf(),
                memory_write_status=str(submitted.get("status", "")),
                memory_write_task_id=str(submitted.get("task_id", "")),
                memory_write_async=True,
            ),
        }

    def write_status(self) -> dict[str, Any]:
        status = self.write_dispatcher.status()
        status["async_enabled"] = self.async_write_enabled
        return status

    def drain_writes(self, timeout: float = 5.0) -> bool:
        return self.write_dispatcher.drain(timeout=timeout)

    def audit_records(self, *, user_id: str = "", limit: int = 20) -> dict[str, Any]:
        try:
            records = self.audit_log.tail(user_id=user_id, limit=limit)
            total = self.audit_log.count(user_id=user_id)
        except Exception as exc:
            return {
                "enabled": True,
                "count": 0,
                "records": [],
                "reason": "audit_read_failed",
                "error": str(exc),
            }

        return {
            "enabled": True,
            "count": total,
            "records": [record.model_dump(mode="json") for record in records],
        }
    
    def _retrieve_node(self, state: MemoryGraphState) -> MemoryGraphState:
        started_at = now_perf()
        query = state.get("retrieval_query", "") or state.get("user_text", "")
        user_id = state["user_id"]  # type: ignore
        agent_id = state.get("agent_id") or self.default_agent_id

        try:
            hits = self.memory.search(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
                limit=self.retrieval_limit,
            )
        except Exception as exc:
            metadata = mark_stage_failed(
                state.get("metadata") or {},
                "memory_retrieve",
                started_at,
                exc,
                memory_error=str(exc),
                memory_retrieval_query=query,
            )
            return {
                "memory_hits": [],
                "memory_pinned_records": [],
                "memory_prompt_context": "无长期记忆。",
                "memory_prompt_context_data": {},
                "metadata": metadata,
            }

        pinned_records: list[MemoryRecord] = []
        pinned_error = ""
        try:
            pinned_records = self.memory.list_pinned_records(
                user_id=user_id,
                agent_id=agent_id,
                limit=self.prompt_builder.pinned_limit,
            )
        except Exception as exc:
            pinned_error = str(exc)
            pinned_records = []

        combined_hits = self._merge_hits(
            [
                *self._hits_from_pinned_records(pinned_records),
                *hits,
            ]
        )

        prompt_context = self.prompt_builder.build(
            hits=combined_hits,
            pinned_records=pinned_records,
        )

        metadata = mark_stage_done(
            state.get("metadata") or {},
            "memory_retrieve",
            started_at,
            memory_error="",
            memory_retrieval_query=query,
            memory_hit_count=len(combined_hits),
            memory_retrieved_hit_count=len(hits),
            memory_pinned_count=len(pinned_records),
            memory_prompt_chars=prompt_context.char_count,
            memory_prompt_item_count=prompt_context.total_count,
            memory_prompt_truncated=prompt_context.truncated,
            memory_prompt_compressed=True,
            memory_prompt_layer_counts=prompt_context.layer_counts,
            memory_prompt_selected_ids=prompt_context.selected_ids,
            memory_prompt_selected_layers=prompt_context.selected_layers,
            memory_prompt_compression_reason=prompt_context.compression_reason,
            memory_pinned_error=pinned_error,
        )

        return {
            "memory_hits": combined_hits,
            "memory_pinned_records": pinned_records,
            "memory_prompt_context": prompt_context.text,
            "memory_prompt_context_data": prompt_context.model_dump(mode="json"),
            "metadata": metadata,
        }
    def _decide_write_node(self, state: MemoryGraphState) -> MemoryGraphState:
        started_at = now_perf()

        try:
            decision = self.policy_service.decide_write(
                user_text=state.get("user_text", ""),  # type: ignore
                assistant_text=state.get("assistant_text", ""),  # type: ignore
                existing_memory_context=state.get("memory_prompt_context", ""),  # type: ignore
                planner_should_store_memory=bool(
                    state.get("planner_should_store_memory", False)
                ),
            )
        except Exception as exc:
            metadata = mark_stage_failed(
                state.get("metadata") or {},
                "memory_decide_write",
                started_at,
                exc,
                memory_error=str(exc),
            )
            return {
                "metadata": metadata,
            }

        metadata = mark_stage_done(
            state.get("metadata") or {},
            "memory_decide_write",
            started_at,
            memory_write_should_store=decision.should_store,
            memory_write_category=decision.category.value,
            memory_write_importance=decision.importance.value,
            memory_write_reason=decision.reason,
        )

        return {
            "write_decision": decision,
            "metadata": metadata,
        }

    def _guard_write_node(self, state: MemoryGraphState) -> MemoryGraphState:
        started_at = now_perf()

        try:
            plan = self.intake_service.build_store_plan(
                decision=state.get("write_decision"),
                memory_hits=list(state.get("memory_hits", [])),
                existing_memory_context=state.get("memory_prompt_context", ""),
                user_text=state.get("user_text", ""),
                assistant_text=state.get("assistant_text", ""),
            )
        except Exception as exc:
            metadata = mark_stage_failed(
                state.get("metadata") or {},
                "memory_guard_write",
                started_at,
                exc,
                memory_error=str(exc),
            )

            return {
                "memory_store_plan": None, # type: ignore
                "metadata": metadata,
            }

        metadata = mark_stage_done(
            state.get("metadata") or {},
            "memory_guard_write",
            started_at,
            memory_error="",
            memory_store_plan_status=plan.status,
            memory_store_plan_reason=plan.reason,
            memory_guard_sensitivity=plan.guard.sensitivity.value,
            memory_guard_flags=",".join(plan.guard.flags),
            memory_dedup_duplicate=plan.dedup.duplicate,
            memory_dedup_similarity=plan.dedup.similarity,
            memory_store_plan_layer=infer_memory_layer(plan.category).value
        )

        return {
            "memory_store_plan": plan,
            "metadata": metadata,
        }
    
    def _route_after_decision(self,state:MemoryGraphState) ->str:
        decision = state.get("write_decision") # type: ignore
        return "store" if decision and decision.should_store else "end"

    def _route_after_guard(self,state:MemoryGraphState) ->str:
        plan = state.get("memory_store_plan") # type: ignore
        return "store" if plan and plan.should_store else "end"
    
    def _store_node(self, state: MemoryGraphState) -> MemoryGraphState:
        started_at = now_perf()
        plan = state["memory_store_plan"] # type: ignore
        decision = state["write_decision"]  # type: ignore
        memory_layer = infer_memory_layer(decision.category)
        metadata = {
            **(state.get("metadata") or {}),
            "category": decision.category.value,
            "importance": decision.importance.value,
            "policy_reason": decision.reason,
            "memory_hint": decision.memory_hint,
            "memory_guard_status": plan.status,
            "memory_guard_reason": plan.reason,
            "memory_layer": memory_layer.value,
            "source": plan.source or "chat_turn",
            "created_at": plan.created_at or self._utc_now(),
            "dedup_duplicate": plan.dedup.duplicate,
            "dedup_similarity": plan.dedup.similarity,
        }

        try:
            result = self.memory.add_turn(
                user_id=state["user_id"],  # type: ignore
                user_name=state.get("user_name", ""),
                user_text=state.get("user_text", ""),
                assistant_text=state.get("assistant_text", ""),
                session_id=state.get("session_id", ""),
                turn_id=state.get("turn_id", ""),
                agent_id=state.get("agent_id") or self.default_agent_id,
                metadata=metadata,
            )
        except Exception as exc:
            metadata = mark_stage_failed(
                metadata,
                "memory_store",
                started_at,
                exc,
                memory_error=str(exc),
            )
            return {
                "store_result": {
                    "ok": False,
                    "status": "failed",
                    "error": str(exc),
                },
                "metadata": metadata,
            }

        metadata = mark_stage_done(
            metadata,
            "memory_store",
            started_at,
            memory_error="",
            memory_store_status="stored",
            memory_store_layer=memory_layer.value
        )

        return {
            "store_result": result,
            "metadata": metadata,
        }

    def get_user_preference(self, user_id: str, agent_id: str | None = None):
        return self.preference_store.get(
            user_id=user_id,
            agent_id=agent_id or self.default_agent_id,
        )

    def set_user_preference(
        self,
        *,
        user_id: str,
        long_term_enabled: bool,
        reason: str = "",
        agent_id: str | None = None,
    ):
        return self.preference_store.set(
            user_id=user_id,
            agent_id=agent_id or self.default_agent_id,
            long_term_enabled=long_term_enabled,
            reason=reason,
        )

    def _hits_from_pinned_records(self, records: list[MemoryRecord]) -> list[MemoryHit]:
        hits: list[MemoryHit] = []

        for record in records:
            metadata = dict(record.metadata or {})
            metadata["category"] = record.category.value
            metadata["importance"] = record.importance.value
            metadata["memory_layer"] = record.layer.value
            metadata["pinned"] = True
            if record.pinned_at:
                metadata["pinned_at"] = record.pinned_at

            hits.append(
                MemoryHit(
                    id=record.id,
                    memory=record.memory,
                    score=record.score,
                    metadata=metadata,
                    relations=record.relations,
                    pinned=True,
                    pinned_at=record.pinned_at,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

        return hits
    def _append_audit(self, state: MemoryGraphState) -> None:
        """把一次写入决策落进审计日志（stored/duplicate/blocked/skipped 全覆盖）。"""
        try:
            store_result = state.get("store_result") or {}
            if not isinstance(store_result, dict):
                store_result = {"status": str(store_result)}

            plan = state.get("memory_store_plan")
            decision = state.get("write_decision")

            status_value = str(store_result.get("status") or "skipped")
            category = plan.category if plan else (decision.category if decision else MemoryCategory.OTHER)
            importance = plan.importance if plan else (decision.importance if decision else MemoryImportance.MEDIUM)

            reason = ""
            source = "chat_turn"
            memory_text = ""
            sensitivity = MemorySensitivity.NONE
            flags: list[str] = []

            if plan is not None:
                reason = plan.reason
                source = plan.source or source
                memory_text = plan.memory_text
                sensitivity = plan.guard.sensitivity
                flags = list(plan.guard.flags)
            elif decision is not None:
                reason = decision.reason

            self.audit_log.append(
                MemoryWriteAudit(
                    audit_id=uuid.uuid4().hex[:12],
                    user_id=state.get("user_id", "") or "",
                    agent_id=state.get("agent_id") or self.default_agent_id,
                    session_id=state.get("session_id", "") or "",
                    turn_id=state.get("turn_id", "") or "",
                    status=status_value,
                    category=category,
                    importance=importance,
                    layer=infer_memory_layer(category),
                    reason=reason,
                    source=source,
                    memory_text=memory_text,
                    sensitivity=sensitivity,
                    flags=flags,
                )
            )
        except Exception as exc:
            # 审计只是可观测性，绝不能影响记忆写入结果。
            logger.warning("Failed to append memory write audit: %s", exc)

    def _append_audit_failure(
            self,
            *,
            user_id: str,
            agent_id: str,
            session_id: str,
            turn_id: str,
            error: str,
    ) -> None:
        try:
            self.audit_log.append(
                MemoryWriteAudit(
                    audit_id=uuid.uuid4().hex[:12],
                    user_id=user_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    turn_id=turn_id,
                    status="failed",
                    reason="memory_store_failed",
                    source="chat_turn",
                    memory_text="",
                    flags=[],
                )
            )
        except Exception as exc:
            logger.warning("Failed to append memory write audit: %s", exc)

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _merge_hits(self, hits: list[MemoryHit]) -> list[MemoryHit]:
        seen_ids: set[str] = set()
        seen_texts: set[str] = set()
        result: list[MemoryHit] = []

        for hit in hits:
            normalized = self._normalize_memory_text(hit.memory)
            if hit.id and hit.id in seen_ids:
                continue
            if normalized in seen_texts:
                continue

            if hit.id:
                seen_ids.add(hit.id)
            seen_texts.add(normalized)
            result.append(hit)

        return result

    def _normalize_memory_text(self, text: str) -> str:
        return "".join(str(text or "").strip().lower().split())