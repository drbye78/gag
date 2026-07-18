import asyncio
import json
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from core.config import get_settings


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
        self, id: str, model: str, choices: List[Dict[str, Any]], usage: Dict[str, int]
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
    def from_dict(cls, data: Dict[str, Any]) -> "ChatCompletionResponse":
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            choices=data.get("choices", []),
            usage=data.get("usage", {}),
        )


class LLMRouter:
    _embed_pipeline: Optional[Any] = None

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[LLMModel] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
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
        self._client: Optional[httpx.AsyncClient] = None
        # Circuit breaker
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0  # Unix timestamp when circuit resets
        self._circuit_threshold = 5  # Trip after 5 consecutive failures
        self._circuit_reset_seconds = 30.0  # Half-open after 30s

    def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60))
        return self._client

    async def close_client(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _circuit_is_open(self) -> bool:
        """Check if circuit breaker is tripped."""
        import time as _time
        if self._consecutive_failures >= self._circuit_threshold:
            if _time.time() < self._circuit_open_until:
                return True
            # Half-open: reset and try again
            self._consecutive_failures = 0
        return False

    def _record_success(self):
        """Record a successful call — resets circuit breaker."""
        self._consecutive_failures = 0

    def _record_failure(self):
        """Record a failed call — may trip circuit breaker."""
        import time as _time
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._circuit_threshold:
            self._circuit_open_until = _time.time() + self._circuit_reset_seconds

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResponse:
        if self._circuit_is_open():
            raise RuntimeError("LLM circuit breaker is open — fast-failing after consecutive failures")
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
                self._record_success()
                return ChatCompletionResponse.from_dict(response.json())
            except Exception as e:
                self._record_failure()
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        raise RuntimeError("Max retries exceeded")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text using configured embedding provider."""
        if LLMRouter._embed_pipeline is None:
            from ingestion.embedder import EmbeddingPipeline
            LLMRouter._embed_pipeline = EmbeddingPipeline()
        return await LLMRouter._embed_pipeline.embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using configured embedding provider."""
        if LLMRouter._embed_pipeline is None:
            from ingestion.embedder import EmbeddingPipeline
            LLMRouter._embed_pipeline = EmbeddingPipeline()
        return await LLMRouter._embed_pipeline.embed_batch(texts)

    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
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
                    if "choices" in chunk and chunk["choices"]:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]


from functools import lru_cache


@lru_cache(maxsize=1)
def get_router() -> LLMRouter:
    return LLMRouter()


def get_llm_router() -> LLMRouter:
    """Alias for get_router() for backwards compatibility."""
    return get_router()
