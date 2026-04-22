from aiagent.persona import PersonaLoader, PersonaRegistry, PersonaRuntime


def test_persona_loader_can_load_yzl() -> None:
    loader = PersonaLoader(base_dir="data/characters")
    persona = loader.load_persona("yzl")

    assert persona.persona_id == "yzl"
    assert persona.identity.name == "乐正绫"
    assert persona.voice.provider == "indextts2"


def test_persona_runtime_builds_prompts() -> None:
    loader = PersonaLoader(base_dir="data/characters")
    config = loader.load_persona("yzl")
    runtime = PersonaRuntime(config)

    system_prompt = runtime.build_system_prompt()
    planner_prompt = runtime.build_planner_prompt()

    assert "乐正绫" in system_prompt
    assert "说话风格" in system_prompt
    assert "回应" in planner_prompt


def test_persona_guard_normalizes_reply() -> None:
    loader = PersonaLoader(base_dir="data/characters")
    config = loader.load_persona("yzl")
    runtime = PersonaRuntime(config)

    raw_reply = "我是乐正绫，我这边先接住你这句。嗯，可以继续说。"
    normalized = runtime.normalize_reply(raw_reply)

    assert normalized


def test_persona_registry_switching() -> None:
    loader = PersonaLoader(base_dir="data/characters")
    registry = PersonaRegistry(loader=loader, default_persona_id="yzl")
    registry.load_all()

    active = registry.get_active()
    assert active.persona_id == "yzl"
