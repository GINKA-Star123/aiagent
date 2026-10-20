from __future__ import annotations

from pathlib import Path

import pytest

KNOWLEDGE_DIR = Path("data/knowledge/public")


@pytest.fixture(scope="session")
def rag_eval_pipeline(tmp_path_factory):
    if not KNOWLEDGE_DIR.exists():
        pytest.skip("data/knowledge/public is missing")

    from aiagent.knowledge.evaluation.pipeline import build_eval_pipeline

    root = tmp_path_factory.mktemp("rag_eval_v2")
    return build_eval_pipeline(
        knowledge_dir=KNOWLEDGE_DIR,
        docs_index_path=root / "split_docs.json",
        faiss_dir=root / "faiss",
    )
