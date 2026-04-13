import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx


class VLMProvider(ABC):
    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def extract_text(self, image_url: str) -> str:
        pass


class QwenVLProvider(VLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-vl-plus"):
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/multimodal"

    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/generation",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "input": {
                            "image_url": image_url,
                            "text": prompt,
                        },
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return {"error": "Failed to analyze image"}

    async def extract_text(self, image_url: str) -> str:
        result = await self.analyze_image(image_url, "Extract all text from this image")
        return result.get("output", {}).get("text", "")


class OpenAIVisionProvider(VLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": image_url},
                                    },
                                ],
                            }
                        ],
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return {"output": {"text": content}}
        except Exception:
            return {"error": "Failed to analyze image"}

    async def extract_text(self, image_url: str) -> str:
        result = await self.analyze_image(
            image_url, "Extract all readable text from this image"
        )
        return result.get("output", {}).get("text", "")


class VLMProcessor:
    def __init__(self, provider: Optional[VLMProvider] = None):
        self.provider = provider or self._create_provider()

    @staticmethod
    def _create_provider() -> VLMProvider:
        provider_type = os.getenv("VLM_PROVIDER", "").lower()
        if provider_type == "qwen":
            return QwenVLProvider()
        elif provider_type == "openai":
            return OpenAIVisionProvider()
        else:
            return QwenVLProvider()

    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        return await self.provider.analyze_image(image_url, prompt)

    async def extract_for_ir(
        self, image_url: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        text = await self.provider.extract_text(image_url)
        return {"content": text, "title": title, "type": "image_extraction"}


def get_vlm_processor() -> VLMProcessor:
    return VLMProcessor()
