from __future__ import annotations

from aiagent.persona.persona_loader import PersonaLoader
from aiagent.persona.persona_runtime import PersonaRuntime
from aiagent.services.llm_service import LLMService
from config.settings import settings


def main() -> None:
    loader = PersonaLoader(base_dir="data/characters")
    persona_config = loader.load_persona("yzl")
    persona = PersonaRuntime(persona_config)

    llm = LLMService(settings=settings)

    user_texts = [
        "阿绫，天依是你什么人",
        "阿绫，如果说有一天我们再也不能相见，你会怎么做",
        "阿绫，我喜欢你",
        "阿绫，你真的在现实中存在吗",
    ]

    print("=== PERSONA SUMMARY ===")
    print(persona.summary())
    print()

    print("=== SYSTEM PROMPT ===")
    print(persona.build_system_prompt())
    print()

    for index, user_text in enumerate(user_texts, start=1):
        print(f"=== TEST {index} ===")
        print("USER:", user_text)

        messages = llm.build_messages(
            system_prompt=persona.build_system_prompt(),
            user_text=user_text,
        )

        reply = llm.invoke_messages(
            messages=messages,
            fallback_text=user_text,
            mode="chat",
            persona_name=persona.alias,
        )

        normalized_reply = persona.normalize_reply(reply)
        issues = persona.validate_reply(normalized_reply)

        print("RAW REPLY:", reply)
        print("NORMALIZED REPLY:", normalized_reply)
        print("ISSUES:", issues)
        print()


if __name__ == "__main__":
    main()
