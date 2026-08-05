from aiagent.memory.memory_preferences import MemoryPreferenceStore


def test_memory_preference_uses_default_when_missing(tmp_path):
    store = MemoryPreferenceStore(
        path=tmp_path / "prefs.json",
        default_long_term_enabled=True,
    )

    pref = store.get(user_id="u1")

    assert pref.long_term_enabled is True
    assert pref.source == "default"


def test_memory_preference_can_disable_and_persist(tmp_path):
    path = tmp_path / "prefs.json"
    store = MemoryPreferenceStore(path=path, default_long_term_enabled=True)

    disabled = store.set(
        user_id="u1",
        long_term_enabled=False,
        reason="user_toggle_off",
    )

    assert disabled.long_term_enabled is False
    assert disabled.source == "user"

    reloaded = MemoryPreferenceStore(path=path, default_long_term_enabled=True)
    assert reloaded.get(user_id="u1").long_term_enabled is False