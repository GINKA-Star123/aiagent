from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from mem0 import Memory

logger = logging.getLogger(__name__)

NO_LONG_TERM_MEMORY_TEXT = "无长期记忆。"

@dataclass(frozen=True)
class MemoryHit:
    """返回给图节点和 API 路由的标准化记忆命中。"""

    id: str
    memory: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    relations: list[dict[str, Any]] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class Mem0LongTermMemory:
    """Mem0 长期记忆的安全封装层。

    集中处理 provider 配置、中文记忆抽取 prompt、结果标准化，以及 API
    并发读写时需要的锁。
    """

    def __init__(
        self,
        llm_provider: str,
        llm_model: str,
        llm_api_key_env: str,
        embedder_provider: str,
        embedder_model: str,
        embedder_api_key_env: str | None = None,
        embedder_base_url: str | None = None,
        vector_provider: str = "qdrant",
        vector_collection: str = "aiagent_long_term_memory",
        embedding_dims: int = 1536,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        enable_graph: bool = True,
        graph_provider: str = "neo4j",
        graph_url: str | None = None,
        graph_username: str | None = None,
        graph_password: str | None = None,
        graph_database: str = "neo4j",
        reset_vector_store: bool = False,
    ) -> None:
        self.enable_graph = enable_graph
        self.graph_provider = graph_provider
        self.graph_url = graph_url or ""
        self.graph_username = graph_username or ""
        self.graph_database = graph_database
        self._lock = RLock()

        self._extend_no_proxy(embedder_base_url)

        if llm_provider.strip().lower() == "deepseek":
            self._extend_no_proxy("https://api.deepseek.com")

        llm_api_key = self._resolve_secret(llm_api_key_env, "MEMORY_LLM_API_KEY_ENV")
        if not llm_api_key:
            raise RuntimeError(
                f"{llm_api_key_env} is not configured. "
                "Set MEMORY_LLM_API_KEY_ENV to an env var name, or provide a direct key."
            )

        normalized_embedder_provider = self._normalize_embedder_provider(embedder_provider)
        
        embedder_config: dict[str, Any] = {
            "provider": normalized_embedder_provider,
            "config": {"model": embedder_model},
        }

        if embedder_base_url:
            embedder_config["config"]["openai_base_url"] = embedder_base_url.strip().rstrip("/")

        if embedder_api_key_env:
            embedder_api_key = self._resolve_secret(
                embedder_api_key_env,
                "MEMORY_EMBEDDER_API_KEY_ENV",
            )
            if not embedder_api_key:
                raise RuntimeError(
                    f"{embedder_api_key_env} is not configured. "
                    "Set MEMORY_EMBEDDER_API_KEY_ENV to an env var name, or provide a direct key."
                )
            embedder_config["config"]["api_key"] = embedder_api_key

        config: dict[str, Any] = {
            "version": "v1.1",
            "llm": {
                "provider": llm_provider,
                "config": {
                    "model": llm_model,
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "api_key": llm_api_key,
                },
            },
            "embedder": embedder_config,
            "vector_store": {
                "provider": vector_provider,
                "config": {
                    "collection_name": vector_collection,
                    "embedding_model_dims": embedding_dims,
                    "host": qdrant_host,
                    "port": qdrant_port,
                },
            },
            "reset_vector_store": reset_vector_store,
        }

        if enable_graph:
            if not graph_url or not graph_username or not graph_password:
                raise RuntimeError("Graph memory is enabled but Neo4j config is incomplete.")

            config["graph_store"] = {
                "provider": graph_provider,
                "config": {
                    "url": graph_url,
                    "username": graph_username,
                    "password": graph_password,
                    "database": graph_database,
                },
                "custom_prompt": (
                    "只抽取对长期个性化有价值的实体和关系：用户身份、稳定偏好、长期厌恶、"
                    "重要人物关系、长期目标、习惯、边界、禁忌、沟通方式。"
                    "不要记录临时闲聊、一次性情绪、无意义寒暄、当前任务步骤。"
                    "所有可读文本尽量使用简体中文。"
                ),
            }

        logger.info(
            "Initializing Mem0 memory: vector=%s embedder=%s graph=%s",
            vector_provider,
            normalized_embedder_provider,
            enable_graph,
        )
        self.memory = Memory.from_config(config)

    def graph_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enable_graph,
            "provider": self.graph_provider,
            "url": self.graph_url,
            "username": self.graph_username,
            "database": self.graph_database,
        }

    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 6,
        agent_id: str = "yzl",
    ) -> list[MemoryHit]:
        """按用户范围检索长期记忆，供 prompt 注入使用。"""
        query = query.strip()
        if not query:
            return []

        kwargs: dict[str, Any] = {
            "query": query,
            "top_k": limit,
            "threshold": 0.0,
            "filters": {
                "user_id": user_id,
                "agent_id": agent_id,
            },
        }

        if self.enable_graph:
            kwargs["enable_graph"] = True

        with self._lock:
            raw = self.memory.search(**kwargs)

        return self._normalize_search(raw)

    def add_turn(
        self,
        user_id: str,
        user_name: str,
        user_text: str,
        assistant_text: str,
        session_id: str,
        turn_id: str,
        agent_id: str = "yzl",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """在策略允许时写入一轮完整的用户/助手对话。"""
        if not user_text.strip() or not assistant_text.strip():
            return {"status": "skipped", "reason": "empty_turn"}

        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "user", "content": user_text.strip()},
                {"role": "assistant", "content": assistant_text.strip()},
            ],
            "user_id": user_id,
            "agent_id": agent_id,
            "run_id": session_id,
            "metadata": {
                "source": "chat_turn",
                "user_name": user_name,
                "session_id": session_id,
                "turn_id": turn_id,
                "agent_id": agent_id,
                **(metadata or {}),
            },
            "prompt": self._build_chinese_memory_prompt(metadata or {}),
        }

        if self.enable_graph:
            kwargs["enable_graph"] = True

        with self._lock:
            result = self.memory.add(**kwargs)

        return result if isinstance(result, dict) else {"status": "ok", "result": result}

    def _build_chinese_memory_prompt(self, metadata: dict[str, Any]) -> str:
        """引导 Mem0 保留稳定中文事实，而不是临时闲聊。"""
        memory_hint = str(metadata.get("memory_hint", "")).strip()
        hint_text = f"\n优先参考这条已审核的记忆提示：{memory_hint}\n" if memory_hint else ""

        return f"""
你是长期记忆抽取器。请从本轮对话中抽取对未来长期个性化有价值的记忆。

硬性要求：
1. 记忆正文必须使用简体中文。
2. 不要把中文翻译成英文。
3. 不要输出英文记忆，例如不要写 "User prefers..."。
4. 每条记忆必须是独立、可复用、面向未来的事实。
5. 如果用户明确要求“记住”，并且内容包含长期偏好、习惯、边界、目标或身份信息，应优先写入。
6. 不要记录一次性闲聊、临时情绪、当前任务步骤、寒暄。
7. 不要记录助手自己的临时表达。
{hint_text}
输出格式必须遵循系统要求的 JSON schema。memory 数组中的每个 text 字段必须是中文。
""".strip()

    def get_all(
        self,
        user_id: str,
        agent_id: str = "yzl",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "filters": {
                "user_id": user_id,
                "agent_id": agent_id,
            }
        }
        if limit is not None:
            kwargs["top_k"] = limit

        with self._lock:
            raw = self.memory.get_all(**kwargs)

        items = raw.get("results", []) if isinstance(raw, dict) else raw or []
        return [item for item in items if isinstance(item, dict)]

    def delete_all(self, user_id: str, agent_id: str = "yzl") -> dict[str, Any]:
        with self._lock:
            result = self.memory.delete_all(user_id=user_id, agent_id=agent_id)

        return result if isinstance(result, dict) else {"status": "ok", "result": result}

    def format_for_prompt(self, hits: list[MemoryHit]) -> str:
        if not hits:
            return NO_LONG_TERM_MEMORY_TEXT

        lines: list[str] = []
        for index, hit in enumerate(hits, start=1):
            score = f"; score={hit.score:.4f}" if hit.score is not None else ""
            relations = self._format_relations(hit.relations)
            rel_text = f"; relations={relations}" if relations else ""
            lines.append(f"{index}. {hit.memory}{score}{rel_text}")

        return "\n".join(lines)

    def _normalize_search(self, raw: Any) -> list[MemoryHit]:
        items = raw.get("results", []) if isinstance(raw, dict) else raw or []
        hits: list[MemoryHit] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            memory = str(item.get("memory") or item.get("data") or "").strip()
            if not memory:
                continue

            try:
                score = float(item["score"]) if item.get("score") is not None else None
            except (TypeError, ValueError):
                score = None

            metadata = item.get("metadata") or {}
            relations = item.get("relations") or []

            hits.append(
                MemoryHit(
                    id=str(item.get("id", "")),
                    memory=memory,
                    score=score,
                    metadata=metadata if isinstance(metadata, dict) else {},
                    relations=relations if isinstance(relations, list) else [],
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                )
            )

        return hits

    def _format_relations(self, relations: list[dict[str, Any]]) -> str:
        parts: list[str] = []

        for relation in relations[:3]:
            if not isinstance(relation, dict):
                continue

            source = relation.get("source") or relation.get("source_node")
            rel = relation.get("relationship") or relation.get("relation")
            target = relation.get("target") or relation.get("target_node")

            if source and rel and target:
                parts.append(f"{source}-{rel}-{target}")

        return "; ".join(parts)

    def _resolve_secret(self, value: str | None, setting_name: str) -> str | None:
        if value is None:
            return None

        candidate = value.strip()
        if not candidate:
            return None

        env_value = os.getenv(candidate)
        if env_value:
            return env_value.strip()

        if self._looks_like_secret(candidate):
            logger.warning(
                "%s contains a direct secret value. Prefer setting it to an env var name.",
                setting_name,
            )
            return candidate

        return None

    def _normalize_embedder_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized == "siliconflow":
            logger.warning(
                "Mem0 does not support embedder provider 'siliconflow' directly; "
                "using OpenAI-compatible embedder instead."
            )
            return "openai"
        return normalized

    def _extend_no_proxy(self, url: str | None) -> None:
        if not url:
            return

        host = urlparse(url).hostname
        if not host:
            return

        existing = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
        items = [item.strip() for item in existing.split(",") if item.strip()]
        if host not in items:
            items.append(host)

        value = ",".join(items)
        os.environ["NO_PROXY"] = value
        os.environ["no_proxy"] = value

    def _looks_like_secret(self, value: str) -> bool:
        lowered = value.lower()
        known_prefixes = ("sk-", "sk_", "api-", "pk-", "eyj")
        if lowered.startswith(known_prefixes):
            return True
        return len(value) >= 32 and any(ch.isdigit() for ch in value)
