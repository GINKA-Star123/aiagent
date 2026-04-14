"""OpenAI-compatible client placeholder."""
import logging

import httpx


class OpenAIClient:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, messages) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": self._message_role(msg), "content": self._message_content(msg)}
                for msg in messages
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"
        self.logger.info("Calling OpenAI-compatible endpoint: %s", url)

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    def _message_role(self, msg) -> str:
        return getattr(msg, "type", "user").replace("human", "user")

    def _message_content(self, msg) -> str:
        content = getattr(msg, "content", "")
        return content if isinstance(content, str) else str(content)
