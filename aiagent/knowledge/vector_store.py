from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable,Any
from urllib.parse import urlparse

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAICompatibleEmbeddings(Embeddings):
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        batch_size: int = 64,
        dimensions: int | None = None,
    ) -> None:
        self.model = model
        self.batch_size = max(batch_size, 1)
        self.dimensions = dimensions
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for batch in self._batches(texts, self.batch_size):
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.replace("\n", " ").strip() for text in texts]
        kwargs = {
            "model": self.model,
            "input": cleaned,
            "encoding_format": "float",
        }
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions

        response = self.client.embeddings.create(**kwargs)
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def _batches(self, items: list[str], size: int) -> Iterable[list[str]]:
        for index in range(0, len(items), size):
            yield items[index : index + size]


class LangChainVectorStore:
    def __init__(
        self,
        embedding_model_name: str,
        embedding_model_path: str = "",
        device: str = "cpu",
        normalize_embeddings: bool = True,
        local_files_only: bool = True,
        embedding_provider: str = "huggingface",
        embedding_api_key: str | None = None,
        embedding_base_url: str | None = None,
        embedding_batch_size: int = 64,
        embedding_dimensions: int | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider.strip().lower()
        self.embedding_model_name = embedding_model_name.strip()
        self.embedding_model_path = embedding_model_path.strip()
        self.embedding_dimensions = embedding_dimensions
        self.embeddings = self._build_embeddings(
            embedding_model_name=embedding_model_name,
            embedding_model_path=embedding_model_path,
            device=device,
            normalize_embeddings=normalize_embeddings,
            local_files_only=local_files_only,
            embedding_api_key=embedding_api_key,
            embedding_base_url=embedding_base_url,
            embedding_batch_size=embedding_batch_size,
            embedding_dimensions=embedding_dimensions,
        )
        self.store: FAISS | None = None

    def build(self, documents: list[Document]) -> None:
        if not documents:
            raise ValueError("Cannot build vector store from empty documents")

        self.store = FAISS.from_documents(documents, self.embeddings)

    def save(self, directory: str | Path) -> None:
        if self.store is None:
            raise RuntimeError("Vector store is not built yet")

        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        self.store.save_local(str(path))

    def load(self, directory: str | Path) -> None:
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Vector store directory not found: {path}")

        self.store = FAISS.load_local(
            str(path),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )

        index_dimension = self.index_dimension()
        if (
            self.embedding_dimensions
            and index_dimension
            and int(self.embedding_dimensions) != int(index_dimension)
        ):
            logger.warning(
                "FAISS index dimension (%s) does not match configured embedding dimension (%s). "
                "The index must be rebuilt.",
                index_dimension,
                self.embedding_dimensions,
            )

    def similarity_search(self, query: str, k: int = 6) -> list[Document]:
        
        if self.store is None:
            raise RuntimeError("Vector store is not loaded")

        return self.store.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 6) -> list[tuple[Document, float]]:
        if self.store is None:
            raise RuntimeError("Vector store is not loaded")

        raw_results = self.store.similarity_search_with_score(query, k=k)
        results: list[tuple[Document, float]] = []

        for doc, distance in raw_results:
            results.append((doc, self._distance_to_similarity(float(distance))))

        return results

    def count(self) -> int:
        if self.store is None:
            return 0

        return self.store.index.ntotal

    def index_dimension(self) -> int | None:
        """返回磁盘上 FAISS 索引的真实向量维度；未加载时返回 None"""
        if self.store is None:
            return None

        try:
            return int(self.store.index.d)
        except Exception:
            return None

    def identity(self) -> dict[str, Any]:
        """索引身份快照，写进索引清单，用于后续"配置变了没有"的比对。"""

        return {
            "provider": self.embedding_provider,
            "model": self.embedding_model_name,
            "model_path": self.embedding_model_path,
            "dimensions": self.embedding_dimensions,
            "faiss_dimension": self.index_dimension(),
            "vector_count": self.count(),
        }

    def _build_embeddings(
        self,
        embedding_model_name: str,
        embedding_model_path: str,
        device: str,
        normalize_embeddings: bool,
        local_files_only: bool,
        embedding_api_key: str | None,
        embedding_base_url: str | None,
        embedding_batch_size: int,
        embedding_dimensions: int | None,
    ) -> Embeddings:
        if self.embedding_provider in {"huggingface", "local"}:
            return self._build_huggingface_embeddings(
                embedding_model_name=embedding_model_name,
                embedding_model_path=embedding_model_path,
                device=device,
                normalize_embeddings=normalize_embeddings,
                local_files_only=local_files_only,
            )

        if self.embedding_provider in {"openai", "siliconflow"}:
            api_key = (embedding_api_key or "").strip()
            if not api_key:
                raise RuntimeError("RAG embedding API key is not configured.")

            if self.embedding_provider == "siliconflow":
                base_url = embedding_base_url or "https://api.siliconflow.cn/v1"
            else:
                base_url = embedding_base_url or "https://api.openai.com/v1"

            self._extend_no_proxy(base_url)

            logger.info(
                "Loading RAG API embedding: provider=%s model=%s base_url=%s batch_size=%s",
                self.embedding_provider,
                embedding_model_name,
                base_url,
                embedding_batch_size,
            )

            return OpenAICompatibleEmbeddings(
                model=embedding_model_name,
                api_key=api_key,
                base_url=base_url,
                batch_size=embedding_batch_size,
                dimensions=embedding_dimensions,
            )

        raise ValueError(f"Unsupported RAG embedding provider: {self.embedding_provider}")

    def _build_huggingface_embeddings(
        self,
        embedding_model_name: str,
        embedding_model_path: str,
        device: str,
        normalize_embeddings: bool,
        local_files_only: bool,
    ) -> HuggingFaceEmbeddings:
        model_name = self._resolve_model_name(
            embedding_model_name=embedding_model_name,
            embedding_model_path=embedding_model_path,
        )

        model_kwargs = {
            "device": device,
            "local_files_only": local_files_only,
        }

        encode_kwargs = {
            "normalize_embeddings": normalize_embeddings,
        }

        logger.info(
            "Loading RAG local embedding model: model=%s device=%s local_files_only=%s",
            model_name,
            device,
            local_files_only,
        )

        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )

    def _resolve_model_name(
        self,
        embedding_model_name: str,
        embedding_model_path: str,
    ) -> str:
        local_path = embedding_model_path.strip()
        remote_name = embedding_model_name.strip()

        if local_path:
            path = Path(local_path)
            if not path.exists():
                raise FileNotFoundError(
                    f"RAG_EMBEDDING_MODEL_PATH does not exist: {path}. "
                    "Please download the embedding model locally first."
                )

            required_files = ["config.json"]
            missing = [name for name in required_files if not (path / name).exists()]
            if missing:
                raise FileNotFoundError(
                    f"Invalid local embedding model directory: {path}. "
                    f"Missing files: {missing}"
                )

            return str(path)

        if remote_name:
            return remote_name

        raise ValueError("RAG embedding model name or local path must be provided")

    def _distance_to_similarity(self, distance: float) -> float:
        score = 1.0 - distance / 2.0

        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

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
