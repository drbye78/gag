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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatCompletionResponse":
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            choices=data.get("choices", []),
            usage=data.get("usage", {}),
        )


class LLMRouter:
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
        self.timeout = timeout
        self.max_retries = max_retries

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

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResponse:
        messages = self._build_messages(prompt, system_prompt)
        payload = {"model": self.model.value, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    return ChatCompletionResponse.from_dict(response.json())
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        raise RuntimeError("Max retries exceeded")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text using configured embedding provider."""
        from ingestion.embedder import EmbeddingPipeline
        pipeline = EmbeddingPipeline()
        return await pipeline.embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using configured embedding provider."""
        from ingestion.embedder import EmbeddingPipeline
        pipeline = EmbeddingPipeline()
        return await pipeline.embed_batch(texts)

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

        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
