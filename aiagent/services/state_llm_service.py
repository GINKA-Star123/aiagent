from __future__ import annotations

import logging
import json
from typing import Any

import httpx

from aiagent.graphs.graph_model import StateInferenceOutput
from config.providers import StateProvider
from config.settings import Settings

class StateLLMService:
    def __init__(self,settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def infer_state(self,system_prompt:str,user_text:str) -> StateInferenceOutput:
        try:
            if self.settings.enable_mock_state or self.settings.state_provider == StateProvider.MOCK:
                return self._fallback_state()
            
            if self.settings.state_provider == StateProvider.LMSTUDIO:
                return self._infer_with_lmstudio(system_prompt,user_text)
            
            return self._infer_with_openai(system_prompt,user_text)
        
        except Exception as e:
            self.logger.error(e)
            return self._fallback_state()
        
    
    def _infer_with_lmstudio(self,system_prompt,user_text) ->StateInferenceOutput:
        payload = {
            "model":self.settings.state_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.1,
        }

        with httpx.Client(timeout=self.settings.llm_timeout_seconds, trust_env=False) as client:
            response = client.post(
                f"{self.settings.lmstudio_base_url}/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.lmstudio_api_key or 'lm-studio'}",
                }
            )

            if response.is_error:
                raise RuntimeError(f"LM Studio request failed: {response.status_code} {response.text}")

            data = response.json()
            content=self._extract_content(data)
            return self._parse_output(content)

    def _infer_with_openai(self, system_prompt: str, user_text: str) ->StateInferenceOutput:
        api_key, base_url = self._resolve_openai_like_config()

        payload = {
            "model": self.settings.state_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.1,
        }

        with httpx.Client(timeout=self.settings.llm_timeout_seconds, trust_env=False) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )

        if response.is_error:
            raise RuntimeError(f"OpenAI-compatible state request failed: {response.status_code} {response.text}")

        data = response.json()
        content = self._extract_content(data)
        return self._parse_output(content)
        
    def _resolve_openai_like_config(self) -> tuple[str,str]:
        if self.settings.state_provider == StateProvider.OPENAI:
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured.")
            return self.settings.openai_api_key, self.settings.openai_base_url

        if self.settings.state_provider == StateProvider.SILICONFLOW:
            if not self.settings.siliconflow_api_key:
                raise RuntimeError("SILICONFLOW_API is not configured.")
            return self.settings.siliconflow_api_key, self.settings.siliconflow_base_url

        raise ValueError(f"Unsupported state provider: {self.settings.state_provider}")
    
    def _extract_content(self,data: dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices found in state response: {data}")
        
        message = choices[0].get("message",{})
        if not message:
            raise RuntimeError(f"No message found in state response: {data}")
        
        content = message.get("content","")
        if not content:
            raise RuntimeError(f"No content found in state response: {data}")
        
        return str(content).strip()

    def _parse_output(self, content: str) -> StateInferenceOutput:
        text = content.strip()

        if text.startswith("```"):
            text = text.strip("`")
            lines = text.splitlines()
            if lines and lines[0].lower().startswith("json"):
                text = "\n".join(lines[1:]).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        try:
            data = json.loads(text)
        except Exception:
            return self._fallback_state()

        return StateInferenceOutput(
            emotion=str(data.get("emotion", "")),
            intent=str(data.get("intent", "")),
            topic=str(data.get("topic", "")),
            motion_hint=str(data.get("motion_hint", "")),
            context_summary=str(data.get("context_summary", "")),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=str(data.get("reasoning", "")),
        )

    def _fallback_state(self) -> StateInferenceOutput:
        return StateInferenceOutput(
            emotion="neutral",
            intent="chat",
            topic="general",
            motion_hint="idle",
            context_summary="当前输入需要常规回复。",
            confidence=0.2,
            reasoning="fallback_state",
        )