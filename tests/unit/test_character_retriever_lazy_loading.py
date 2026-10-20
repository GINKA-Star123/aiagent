from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from aiagent.vision.character_registry import CharacterProfile, CharacterRegistry
from aiagent.vision.character_retriever import CharacterRetriever


@pytest.mark.parametrize("has_profile", [False, True])
def test_empty_reference_library_does_not_load_model(monkeypatch, tmp_path, has_profile):
    registry = CharacterRegistry(root_dir=tmp_path / "characters")
    profiles = [CharacterProfile(character_id="test", name="Test")] if has_profile else []
    monkeypatch.setattr(registry, "all_profiles", lambda: profiles)
    cache_dir = tmp_path / "index"
    retriever = CharacterRetriever(registry=registry, cache_dir=cache_dir)
    get_model = Mock(side_effect=AssertionError("An empty library must not load CLIP"))
    monkeypatch.setattr(retriever, "_get_model", get_model)

    stats = retriever.build_index(force_rebuild=True)

    assert stats["reference_image_count"] == 0
    assert stats["vector_count"] == 0
    assert retriever.retrieve(tmp_path / "unused.png") == []
    get_model.assert_not_called()

    # A second instance must also reuse the persisted empty index without a model.
    reloaded = CharacterRetriever(registry=registry, cache_dir=cache_dir)
    monkeypatch.setattr(reloaded, "_get_model", get_model)
    assert reloaded.retrieve(tmp_path / "unused.png") == []
    get_model.assert_not_called()


def test_reference_images_still_build_and_retrieve(monkeypatch, tmp_path, tiny_png_path):
    registry = CharacterRegistry(root_dir=tmp_path / "characters")
    profile = CharacterProfile(
        character_id="test", name="Test", image_paths=[tiny_png_path]
    )
    monkeypatch.setattr(registry, "all_profiles", lambda: [profile])
    retriever = CharacterRetriever(registry=registry, cache_dir=tmp_path / "index")
    model = object()
    get_model = Mock(return_value=model)
    embed_image = Mock(return_value=np.array([1.0, 0.0], dtype="float32"))
    monkeypatch.setattr(retriever, "_get_model", get_model)
    monkeypatch.setattr(retriever, "_embed_image", embed_image)

    stats = retriever.build_index(force_rebuild=True)
    candidates = retriever.retrieve(tiny_png_path, top_k=1)

    assert stats["vector_count"] == 1
    assert len(candidates) == 1
    assert candidates[0].character_id == "test"
    assert candidates[0].score == pytest.approx(1.0)
    assert get_model.call_count == 2
    assert embed_image.call_count == 2
    embed_image.assert_called_with(model=model, image_path=tiny_png_path)


def test_model_load_failure_is_not_silently_treated_as_empty_library(
    monkeypatch, tmp_path, tiny_png_path
):
    registry = CharacterRegistry(root_dir=tmp_path / "characters")
    profile = CharacterProfile(
        character_id="test", name="Test", image_paths=[tiny_png_path]
    )
    monkeypatch.setattr(registry, "all_profiles", lambda: [profile])
    retriever = CharacterRetriever(registry=registry, cache_dir=tmp_path / "index")
    monkeypatch.setattr(
        retriever, "_get_model", Mock(side_effect=RuntimeError("model unavailable"))
    )

    with pytest.raises(RuntimeError, match="model unavailable"):
        retriever.build_index(force_rebuild=True)

    assert not retriever.index_path.exists()
    assert not retriever.records_path.exists()
