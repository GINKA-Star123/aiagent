from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import faiss
import numpy as np
from PIL import Image

from aiagent.graphs.graph_model import CharacterCandidate
from aiagent.vision.character_registry import CharacterRegistry

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class CharacterRetriever:
    """基于 FAISS 的角色图片检索器。

    embedding 模型按需加载，避免 health/chat/RAG 等后端路由在启动时就导入
    torch、sklearn、scipy 等重依赖。
    """

    def __init__(
        self,
        registry: CharacterRegistry,
        embedding_model_name: str = "clip-ViT-B-32",
        embedding_model_path: str = "",
        device: str = "cpu",
        local_files_only: bool = False,
        cache_dir: str | Path = "data/cache/vision/character_index",
        confident_score: float = 0.78,
    ) -> None:
        self.registry = registry
        self.embedding_model_name = embedding_model_name
        self.embedding_model_path = embedding_model_path
        self.device = device
        self.local_files_only = local_files_only
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.cache_dir / "faiss.index"
        self.records_path = self.cache_dir / "records.json"
        self.confident_score = confident_score

        self._model: SentenceTransformer | None = None
        self._index: faiss.IndexFlatIP | None = None
        self._records: list[dict[str, Any]] = []

    def build_index(self, force_rebuild: bool = False) -> dict[str, Any]:
        """根据角色 profile 和图片目录构建参考图索引。"""
        if not force_rebuild and self.index_path.exists() and self.records_path.exists():
            self._load_index()
            return self.stats()

        model: SentenceTransformer | None = None
        records: list[dict[str, Any]] = []
        vectors: list[np.ndarray] = []

        for profile in self.registry.all_profiles():
            for image_path in profile.image_paths:
                # 空图库不需要模型；模型加载失败仍应明确上报，不能当作坏图片忽略。
                if model is None:
                    model = self._get_model()
                try:
                    vector = self._embed_image(model=model, image_path=image_path)
                except Exception as exc:
                    logger.warning("Failed to embed character image %s: %s", image_path, exc)
                    continue

                records.append(
                    {
                        "character_id": profile.character_id,
                        "name": profile.name,
                        "aliases": profile.aliases,
                        "visual_traits": profile.visual_traits,
                        "related_characters": profile.related_characters,
                        "image_path": str(image_path),
                        "metadata": profile.metadata,
                    }
                )
                vectors.append(vector)

        if not vectors:
            self._records = []
            self._index = faiss.IndexFlatIP(1)
            self._save_records()
            faiss.write_index(self._index, str(self.index_path))
            return self.stats()

        matrix = np.vstack(vectors).astype("float32")
        faiss.normalize_L2(matrix)

        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)

        self._records = records
        self._index = index
        self._save_records()
        faiss.write_index(index, str(self.index_path))

        return self.stats()

    def retrieve(self, image_path: str | Path, top_k: int = 5) -> list[CharacterCandidate]:
        """为上传图片返回最匹配的角色候选。"""
        self._ensure_loaded()

        if self._index is None or not self._records or self._index.ntotal == 0:
            return []

        model = self._get_model()
        query = self._embed_image(model=model, image_path=image_path).reshape(1, -1).astype("float32")
        faiss.normalize_L2(query)

        k = min(max(top_k * 4, top_k), self._index.ntotal)
        scores, indices = self._index.search(query, k)

        best_by_character: dict[str, dict[str, Any]] = {}

        for score, index in zip(scores[0].tolist(), indices[0].tolist(), strict=True):
            if index < 0 or index >= len(self._records):
                continue

            record = self._records[index]
            character_id = record["character_id"]
            current = best_by_character.get(character_id)

            if current is None or score > current["score"]:
                best_by_character[character_id] = {
                    "score": float(score),
                    "record": record,
                }

        ranked = sorted(best_by_character.values(), key=lambda item: item["score"], reverse=True)
        output: list[CharacterCandidate] = []

        for item in ranked[:top_k]:
            record = item["record"]
            score = float(item["score"])
            visual_traits = record.get("visual_traits") or []

            evidence = [
                f"图像向量相似度 {score:.3f}",
                f"最相似参考图: {Path(record['image_path']).name}",
            ]
            if visual_traits:
                evidence.append("角色视觉特征: " + "、".join(visual_traits[:6]))

            output.append(
                CharacterCandidate(
                    character_id=record["character_id"],
                    name=record["name"],
                    aliases=record.get("aliases", []),
                    score=score,
                    confidence=score,
                    evidence=evidence,
                    metadata={
                        "matched_image_path": record["image_path"],
                        "method": "clip_faiss",
                    },
                )
            )

        return output

    def stats(self) -> dict[str, Any]:
        if self._index is not None:
            vector_count = int(self._index.ntotal)
        elif self.index_path.exists():
            try:
                vector_count = int(faiss.read_index(str(self.index_path)).ntotal)
            except Exception:
                vector_count = 0
        else:
            vector_count = 0

        character_count = len({item.get("character_id") for item in self._records})

        return {
            "embedding_model_name": self.embedding_model_name,
            "embedding_model_path": self.embedding_model_path,
            "device": self.device,
            "cache_dir": str(self.cache_dir),
            "index_path": str(self.index_path),
            "records_path": str(self.records_path),
            "reference_image_count": len(self._records),
            "vector_count": vector_count,
            "character_count": character_count,
            "confident_score": self.confident_score,
        }

    def _ensure_loaded(self) -> None:
        if self._index is not None:
            return

        if self.index_path.exists() and self.records_path.exists():
            self._load_index()
            return

        self.build_index(force_rebuild=True)

    def _load_index(self) -> None:
        self._index = faiss.read_index(str(self.index_path))
        self._records = json.loads(self.records_path.read_text(encoding="utf-8"))

    def _save_records(self) -> None:
        self.records_path.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_model(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model

        # 本地导入可以让 API 启动更轻。即使加载失败，也只影响视觉角色检索，
        # 文本聊天和 RAG 仍可启动。
        from sentence_transformers import SentenceTransformer

        model_name = self.embedding_model_path.strip() or self.embedding_model_name.strip()
        if not model_name:
            raise RuntimeError("Vision character embedding model is not configured.")

        logger.info(
            "Loading vision character embedding model: model=%s device=%s local_files_only=%s",
            model_name,
            self.device,
            self.local_files_only,
        )

        self._model = SentenceTransformer(
            model_name,
            device=self.device,
            local_files_only=self.local_files_only,
        )
        return self._model

    def _embed_image(self, model: SentenceTransformer, image_path: str | Path) -> np.ndarray:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            vector = model.encode(
                image,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        vector = np.asarray(vector, dtype="float32")
        if vector.ndim != 1:
            vector = vector.reshape(-1)

        return vector
