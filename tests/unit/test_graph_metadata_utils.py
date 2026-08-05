from aiagent.graphs.metadata_utils import (
    mark_stage_done,
    mark_stage_failed,
    mark_stage_skipped,
    metadata_strings,
    now_perf,
)


def test_mark_stage_done_adds_status_and_latency():
    started_at = now_perf()

    metadata = mark_stage_done(
        {"existing": "value"},
        "unit_stage",
        started_at,
        count=3,
    )

    assert metadata["existing"] == "value"
    assert metadata["unit_stage_status"] == "done"
    assert "unit_stage_latency_ms" in metadata
    assert metadata["count"] == 3


def test_mark_stage_skipped_adds_reason():
    metadata = mark_stage_skipped(
        {},
        "vision_graph",
        "no_image_attachment",
    )

    assert metadata["vision_graph_status"] == "skipped"
    assert metadata["vision_graph_skip_reason"] == "no_image_attachment"


def test_mark_stage_failed_adds_error():
    started_at = now_perf()

    metadata = mark_stage_failed(
        {},
        "rag_graph",
        started_at,
        RuntimeError("boom"),
    )

    assert metadata["rag_graph_status"] == "failed"
    assert metadata["rag_graph_error"] == "boom"
    assert "rag_graph_latency_ms" in metadata


def test_metadata_strings_converts_values():
    metadata = metadata_strings(
        {
            "bool_true": True,
            "bool_false": False,
            "number": 12,
            "none": None,
        }
    )

    assert metadata["bool_true"] == "true"
    assert metadata["bool_false"] == "false"
    assert metadata["number"] == "12"
    assert metadata["none"] == ""