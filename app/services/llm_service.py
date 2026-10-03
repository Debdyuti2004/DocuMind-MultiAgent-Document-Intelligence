"""Pluggable model providers with an explicit non-generative offline fallback."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

from app.utils.config import settings
from app.utils.logging import logger


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        """Generate text or report that generation is unavailable."""


class MockRuleBasedProvider(LLMProvider):
    """An explicit unavailable response for offline tests; it never invents analysis."""

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        if json_mode:
            return "{}"
        return "No generative model response is available in rule-based fallback mode."


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        payload: Dict[str, Any] = {"model": self.model, "prompt": prompt, "stream": False}
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except Exception as exc:
            logger.warning("Ollama is unavailable; returning explicit offline result: %s", exc)
            return MockRuleBasedProvider().generate(prompt, system_prompt, json_mode)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = settings.OPENAI_API_KEY, base_url: str = settings.OPENAI_BASE_URL, model: str = settings.OPENAI_MODEL):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        if not self.api_key:
            logger.warning("OpenAI API key is not configured; generation is unavailable.")
            return MockRuleBasedProvider().generate(prompt, system_prompt, json_mode)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
            messages.append({"role": "user", "content": prompt})
            kwargs: Dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0.1}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("OpenAI generation failed; returning explicit offline result: %s", exc)
            return MockRuleBasedProvider().generate(prompt, system_prompt, json_mode)


class LLMFactory:
    @staticmethod
    def get_provider(provider_type: Optional[str] = None) -> LLMProvider:
        provider = (provider_type or settings.LLM_PROVIDER).lower()
        if provider == "ollama":
            return OllamaProvider()
        if provider == "openai":
            return OpenAIProvider()
        return MockRuleBasedProvider()


llm_service = LLMFactory.get_provider()
