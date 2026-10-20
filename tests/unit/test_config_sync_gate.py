import pytest

from scripts import check_config_sync as sync


@pytest.mark.parametrize("relative,expected", [
    ("apps/api/probe.py", True),
    ("tests/probe.py", False),
    (".github/probe.py", False),
    ("apps/api/__pycache__/probe.py", False),
])
def test_scan_scope_contrast(tmp_path, monkeypatch, relative, expected):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('os.getenv("SYNTHETIC_CONFIG_KEY")\n', encoding="utf-8")
    monkeypatch.setattr(sync, "PROJECT_ROOT", tmp_path)
    assert ("SYNTHETIC_CONFIG_KEY" in sync.collect_scanned_env()) is expected


@pytest.mark.parametrize("missing", [None, "ENV_EXAMPLE", "CLOUD_ENV_EXAMPLE", "CONFIG_REFERENCE"])
def test_template_exit_code_contrast(tmp_path, monkeypatch, missing):
    monkeypatch.setattr(sync, "collect_settings_env", lambda: {"SYNTHETIC_CONFIG_KEY": "fixture"})
    monkeypatch.setattr(sync, "collect_scanned_env", dict)
    for name in ("ENV_EXAMPLE", "CLOUD_ENV_EXAMPLE", "CONFIG_REFERENCE"):
        path = tmp_path / name
        content = "" if name == missing else "SYNTHETIC_CONFIG_KEY=example\n"
        path.write_text(content, encoding="utf-8")
        monkeypatch.setattr(sync, name, path)
    assert sync.main([]) == (0 if missing is None else 1)
