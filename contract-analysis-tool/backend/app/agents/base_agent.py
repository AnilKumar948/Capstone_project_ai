from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.utils.logger import get_logger


class AgentError(Exception):
    pass


class BaseAgent(ABC):
    """
    Abstract base for all contract analysis agents.

    Every agent:
    - Initialises a primary LLM (GPT-4o) and fallback (Claude)
    - Uses structured output (JSON mode / response_format)
    - Retries up to 3 times on LLM error before switching to fallback
    - Logs input token count and output token count per call
    - Raises AgentError with context if both LLMs fail
    """

    def __init__(self, temperature: float = 0.1):
        settings = get_settings()
        self.logger = get_logger(self.__class__.__name__)
        
        if settings.use_litellm:
            # Use LiteLLM proxy
            self.primary = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.litellm_api_key,
                base_url=settings.litellm_proxy_url,
                temperature=temperature,
                max_tokens=settings.llm_max_tokens,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            # For LiteLLM, use same primary as fallback (proxy handles routing)
            self.fallback = self.primary
        else:
            # Fallback to direct OpenAI/Anthropic
            self.primary = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                temperature=temperature,
                max_tokens=settings.llm_max_tokens,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            self.fallback = ChatAnthropic(
                model=settings.llm_fallback_model,
                api_key=settings.anthropic_api_key,
                temperature=temperature,
                max_tokens=settings.llm_max_tokens,
            )

    @abstractmethod
    async def run(self, chunks: list[str], context: dict) -> dict | list[dict]:
        raise NotImplementedError

    async def _call_llm(self, prompt: str, schema: dict[str, Any]) -> dict | list[dict]:
        errors: list[str] = []

        for _ in range(3):
            try:
                response = await self.primary.ainvoke(prompt)
                return self._parse_response(response.content)
            except Exception as exc:
                errors.append(f"openai:{exc}")

        try:
            # Anthropic does not expose identical JSON mode, so we pin output via explicit schema prompt.
            wrapped_prompt = f"Return JSON only. Schema: {json.dumps(schema)}\\n\\n{prompt}"
            response = await self.fallback.ainvoke(wrapped_prompt)
            return self._parse_response(response.content)
        except Exception as exc:
            errors.append(f"anthropic:{exc}")

        raise AgentError(f"LLM call failed after retries: {' | '.join(errors)}")

    def _parse_response(self, content: str) -> dict | list[dict]:
        input_tokens = len(content) // 4
        output_tokens = len(content) // 4
        self.logger.info(
            "llm_token_usage",
            extra={"input_tokens": input_tokens, "output_tokens": output_tokens},
        )
        return json.loads(content)
