from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from aiagent.graphs.graph_model import PlannerInferenceOutput
from config.providers import PlannerProvider
from config.settings import Settings

class PlannerLLMService:
    def __init__(self,settings:Settings) ->None:
        self.settings =settings
        self.logger = logging.getLogger(self.__class__.__name__)

    def infer_plan(self,system_prompt:str,user_text:str) -> PlannerInferenceOutput:
        try:
            if self.settings.enable_mock_planner or self.settings.planner_provider == PlannerProvider.MOCK:
                return self._fallback_plan()
            
            if self.settings.planner_provider ==PlannerProvider.LMSTUDIO:
                return self._infer_with_lmstudio(system_prompt,user_text)
            
            return self._infer_with_openai(system_prompt,user_text)
        
        except Exception as e:
            self.logger.exception("Planner inference failed: %s", e)
            return self._fallback_plan()
        
    
    def _infer_with_lmstudio(self,system_prompt:str,user_text:str) -> PlannerInferenceOutput:
        payload = {
            "model":self.settings.planner_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.2,
        }

        with httpx.Client(timeout=self.settings.llm_timeout_seconds,trust_env=False) as client:
            response = client.post(
                f"{self.settings.lmstudio_base_url}/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.lmstudio_api_key or 'lm-studio'}",
                },
            )

        if response.is_error:
            raise RuntimeError(f"LM Studio planner request failed: {response.status_code} {response.text}")

        data = response.json()
        content = self._extract_content(data)
        return self._parse_output(content)
    
    def _infer_with_openai(self, system_prompt: str, user_text: str) -> PlannerInferenceOutput:
        api_key, base_url = self._resolve_openai_like_config()

        payload = {
            "model": self.settings.planner_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.2,
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
            raise RuntimeError(f"OpenAI-compatible planner request failed: {response.status_code} {response.text}")

        data = response.json()
        content = self._extract_content(data)
        return self._parse_output(content)

    def _resolve_openai_like_config(self) -> tuple[str, str]:
        if self.settings.planner_provider == PlannerProvider.OPENAI:
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured.")
            return self.settings.openai_api_key, self.settings.openai_base_url

        if self.settings.planner_provider == PlannerProvider.SILICONFLOW:
            if not self.settings.siliconflow_api_key:
                raise RuntimeError("SILICONFLOW_API is not configured.")
            return self.settings.siliconflow_api_key, self.settings.siliconflow_base_url

        raise RuntimeError(f"Unsupported planner provider: {self.settings.planner_provider}")

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices found in planner response: {data}")

        message = choices[0].get("message", {})
        if not message:
            raise RuntimeError(f"No message found in planner response: {data}")

        content = message.get("content", "")
        if not content:
            raise RuntimeError(f"No content found in planner response: {data}")

        return str(content).strip()

    def _parse_output(self, content: str) -> PlannerInferenceOutput:
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
            return self._fallback_plan()

        return PlannerInferenceOutput(
            strategy=str(data.get("strategy", "")),
            should_store_memory=bool(data.get("should_store_memory", False)),
            should_speak=bool(data.get("should_speak", True)),
            target_emotion=str(data.get("target_emotion", "")),
            target_motion=str(data.get("target_motion", "")),
            target_expression=str(data.get("target_expression", "")),
            reply_instruction=str(data.get("reply_instruction", "")),
            reasoning=str(data.get("reasoning", "")),
            confidence=float(data.get("confidence", 0.0)),
        )

    def _fallback_plan(self) -> PlannerInferenceOutput:
        return PlannerInferenceOutput(
            strategy="chat",
            should_store_memory=False,
            should_speak=True,
            target_emotion="neutral",
            target_motion="idle",
            target_expression="neutral",
            reply_instruction="自然接住当前输入，给出符合角色口吻的实时回复。",
            reasoning="fallback_plan",
            confidence=0.2,
        )