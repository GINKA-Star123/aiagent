"""Provider selection placeholder."""
from enum import StrEnum

class LLMProvider(StrEnum):
    MOCK = "mock"
    OPENAI = "openai"
    SILICONFLOW = "siliconflow"
    LMSTUDIO = "lmstudio"