from aiagent.live2d.payload_contract import normalize_live2d_payload


def test_normalize_empty_live2d_payload_has_v1_contract():
    payload = normalize_live2d_payload({})

    assert payload["version"] == "1.0"
    assert payload["character"]["character_id"] == "yzl"
    assert payload["character"]["model_id"] == "yzl_v1"
    assert payload["character"]["expression"] == "neutral"
    assert payload["character"]["motion"] == "idle"
    assert payload["character"]["motion_group"] == "default"
    assert payload["character"]["mouth"]["mode"] == "idle"
    assert payload["scene"]["background_id"] == "room_default"


def test_normalize_live2d_payload_preserves_existing_fields():
    payload = normalize_live2d_payload(
        {
            "character": {
                "character_id": "yzl",
                "model_id": "yzl_v1",
                "emotion": "happy",
                "expression": "smile",
                "motion": "wave",
                "motion_priority": 3,
                "mouth": {
                    "mode": "audio",
                    "audio_url": "/audio/unit.wav",
                },
            },
            "scene": {
                "background_id": "stage_default",
                "lighting": "bright",
            },
            "metadata": {
                "source": "unit",
            },
        }
    )

    assert payload["character"]["emotion"] == "happy"
    assert payload["character"]["expression"] == "smile"
    assert payload["character"]["motion"] == "wave"
    assert payload["character"]["motion_priority"] == 3
    assert payload["character"]["mouth"]["audio_url"] == "/audio/unit.wav"
    assert payload["scene"]["background_id"] == "stage_default"
    assert payload["scene"]["lighting"] == "bright"
    assert payload["metadata"]["source"] == "unit"


def test_normalize_live2d_payload_uses_audio_url_hint():
    payload = normalize_live2d_payload(
        {},
        audio_url="/audio/reply.wav",
    )

    assert payload["character"]["mouth"]["mode"] == "audio"
    assert payload["character"]["mouth"]["audio_url"] == "/audio/reply.wav"