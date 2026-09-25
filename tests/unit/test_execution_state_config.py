import pytest

from apps.core.bootstrap import build_shared_state_store
from cloud.config import cloud_settings


def test_redis_mode_without_url_fails_closed(monkeypatch):
    monkeypatch.setattr(cloud_settings, "execution_state_mode", "redis")
    monkeypatch.setattr(cloud_settings, "redis_url", "")
    monkeypatch.setattr(cloud_settings, "execution_state_fail_closed", True)

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        build_shared_state_store()