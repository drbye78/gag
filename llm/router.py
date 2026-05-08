import asyncio
import json
from collections.abc import AsyncGenerator
from enum import Enum
from functools import lru_cache
from typing import Any

import httpx

from core.cache.llm import get_llm_cache
from core.config import get_settings
from core.prometheus_metrics import record_llm


class LLMProvider(str, Enum):
    OPENROUTER = "openrouter"
    QWEN = "qwen"
    GLM = "glm"


class LLMModel(str, Enum):
    QWEN_MAX = "qwen-max"
    QWEN_TURBO = "qwen-turbo"
    GLM_4 = "glm-4"
    GLM_4_FLASH = "glm-4-flash"


LLM_PROVIDER_URLS = {
    LLMProvider.OPENROUTER: "https://openrouter.ai/api/v1",
    LLMProvider.QWEN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    LLMProvider.GLM: "https://open.bigmodel.cn/api/paas/v4",
}


class ChatCompletionResponse:
    def __init__(
        self, id: str, model: str, choices: list[dict[str, Any]], usage: dict[str, int]
    ):
        self.id = id
        self.model = model
        self.choices = choices
        self.usage = usage

    @property
    def text(self) -> str:
        if self.choices and len(self.choices) > 0:
            choice = self.choices[0]
            if "message" in choice:
                return choice["message"].get("content", "")
            if "delta" in choice:
                return choice["delta"].get("content", "")
        return ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatCompletionResponse":
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            choices=data.get("choices", []),
            usage=data.get("usage", {}),
        )


class LLMRouter:
    _circuit_state: str = "closed"
    _failure_count: int = 0

    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: LLMModel | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.provider = provider or LLMProvider(settings.llm_provider)
        self.model = model or LLMModel(settings.llm_model)
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or LLM_PROVIDER_URLS.get(self.provider, "")
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    @property
    def circuit_state(self) -> str:
        return LLMRouter._circuit_state

    def record_failure(self):
        LLMRouter._failure_count += 1
        if LLMRouter._failure_count >= 5:
            LLMRouter._circuit_state = "open"

    def record_success(self):
        LLMRouter._failure_count = 0
        if LLMRouter._circuit_state == "open":
            LLMRouter._circuit_state = "half-open"

    def get_client(self) -> httpx.AsyncClient:
        if LLMRouter._circuit_state == "open":
            raise Exception("Circuit breaker OPEN - LLM provider unavailable")
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60))
        return self._client

    async def close_client(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> ChatCompletionResponse:
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ValueError("temperature must be a number")
            if temperature < 0 or temperature > 2.0:
                raise ValueError("temperature must be between 0 and 2.0")

        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                raise ValueError("max_tokens must be an integer")
            if max_tokens < 1 or max_tokens > 32000:
                raise ValueError("max_tokens must be between 1 and 32000")

        cache = None
        if use_cache:
            cache = get_llm_cache()
            cached = await cache.get(prompt, system_prompt)
            if cached:
                return ChatCompletionResponse.from_dict(cached)

        messages = self._build_messages(prompt, system_prompt)
        payload = {"model": self.model.value, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        for attempt in range(self.max_retries):
            try:
                client = self.get_client()
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                )
                response.raise_for_status()
                self.record_success()
                result = ChatCompletionResponse.from_dict(response.json())
                if cache is not None:
                    await cache.set(prompt, {
                        "id": result.id,
                        "model": result.model,
                        "choices": result.choices,
                        "usage": result.usage,
                    }, system_prompt)
                if result.usage:
                    total_tokens = result.usage.get("total_tokens", 0)
                    if total_tokens > 0:
                        record_llm(self.model.value, 0.0, total_tokens, "success")
                return result
            except Exception:
                self.record_failure()
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        raise RuntimeError("Max retries exceeded")

    async def embed(self, text: str) -> list[float]:
        from embeddings import get_embedding_service
        service = get_embedding_service()
        return await service.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        from embeddings import get_embedding_service
        service = get_embedding_service()
        return await service.embed_batch(texts)

    async def chat_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(prompt, system_prompt)
        payload = {"model": self.model.value, "messages": messages, "stream": True}
        if temperature is not None:
            payload["temperature"] = temperature

        client = self.get_client()
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._build_headers(),
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if chunk.get("choices"):
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


@lru_cache(maxsize=1)
def get_router() -> LLMRouter:
    return LLMRouter()


def get_llm_router() -> LLMRouter:
    return get_router()
