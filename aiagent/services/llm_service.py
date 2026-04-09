"""LLM service facade."""

from config.providers import LLMProvider
from config.settings import settings
from integrations.llm.openai_client import OpenAIClient
from integrations.llm.siliconflow_client import SiliconFlowClient
from integrations.llm.prompt_adapter import build_messages

class LLMService:
    def __init__(self):
        self.settings = settings
        self.openai_client = OpenAIClient(
            api_key = self.settings.openai_api_key,
            model = self.settings.llm_model,
        )
        self.siliconflow_client = SiliconFlowClient(
            api_key = self.settings.siliconflow_api_key,
            model = self.settings.llm_model,
            base_url = self.settings.siliconflow_base_url
        )

    def generate_reply(self,systemprompt:str,user_text:str):
        messages = build_messages(systemprompt,user_text)

        if self.settings.enable_mock_llm or self.settings.llm_provider == LLMProvider.MOCK:
            return self._mock_reply(user_text)
        elif self.settings.llm_provider == LLMProvider.OPENAI:
            return self.openai_client.generate(messages)
        elif self.settings.llm_provider == LLMProvider.SILICONFLOW:
            return self.siliconflow_client.generate(messages)
        raise ValueError(f"Unsupported llm provider: {self.settings.llm_provider}")
    
    def _mock_reply(self,user_text :str) ->str:
        return f"阿绫收到你的消息{user_text}啦"