from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("path", "decorator"),
    [
        ("apps/core/runtime.py", '@traceable(name="agent_turn", run_type="chain")'),
        ("aiagent/expression/tts_dispatcher.py", '@traceable(name="tts", run_type="tool")'),
        ("aiagent/expression/live2d_payload_dispatcher.py", '@traceable(name="live2d", run_type="tool")'),
    ],
)
def test_observability_boundaries_are_traceable(path: str, decorator: str):
    assert decorator in (ROOT / path).read_text(encoding="utf-8")
