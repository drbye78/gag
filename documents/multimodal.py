"""
Multimodal Parser - Vision-based document understanding.

Uses:
- LlamaIndex multimodal for GPT-4O
- Docling for advanced PDF/OCR (shared with parse.py)
- ColPali for visual embeddings
- Vision APIs (Qwen-VL, Claude)
"""

import base64
import logging
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# LlamaIndex multimodal (optional - may not be installed)
try:
    from llama_index.core.multi_modal_llms.base import MultiModalLLM as OpenAIMultiModal

    LLAMA_MULTIMODAL_AVAILABLE = True
except ImportError:
    OpenAIMultiModal = None
    LLAMA_MULTIMODAL_AVAILABLE = False

# Shared Docling parser (OCR-enabled for multimodal use)
from documents.parse import DoclingParser as _SharedDoclingParser


class VisionModel(str, Enum):
    """Available vision models."""

    GPT4O = "gpt-4o"
    GPT4V = "gpt-4v"
    QWEN_VL = "qwen_vl"
    CLAUDE_VISION = "claude_vision"
    DOCLING = "docling"
    COLPAL = "colpal"
    LLAMA = "llama_index"
    COL_PAL = "col_pal"  # Alias


@dataclass
class VisualElement:
    """Detected visual element."""

    element_id: str
    type: str
    label: Optional[str] = None
    bbox: Optional[List[float]] = None
    confidence: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagramComponent:
    """Parsed diagram component."""

    component_id: str
    component_type: str
    label: str
    bbox: List[float]
    connections: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIComponent:
    """Parsed UI component."""

    component_id: str
    component_type: str
    label: Optional[str] = None
    position: Dict[str, int] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)


@dataclass
class MultimodalResult:
    """Result of multimodal parsing."""

    text: str
    elements: List[VisualElement] = field(default_factory=list)
    diagram_components: List[DiagramComponent] = field(default_factory=list)
    ui_components: List[UIComponent] = field(default_factory=list)
    tables: List[List[str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    used_llama: bool = False
    used_docling: bool = False
    used_vision_api: bool = False
    error: Optional[str] = None


class LlamaIndexMultimodalParser:
    """LlamaIndex multimodal parser for images."""

    def __init__(self):
        self._model = None

    @property
    def available(self) -> bool:
        return LLAMA_MULTIMODAL_AVAILABLE

    def _get_model(self):
        if not self.available:
            return None

        if self._model is None:
            try:
                self._model = OpenAIMultiModal(
                    model="gpt-4o",
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                )
            except Exception as e:
                logger.error("Failed to initialize LlamaIndex OpenAI multimodal model: %s", e)

        return self._model

    async def parse(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail.",
    ) -> MultimodalResult:
        model = self._get_model()

        if not model:
            return MultimodalResult(text="", error="LlamaIndex multimodal not available")

        try:
            response = model.complete(
                prompt=prompt,
                image_path=image_path,
            )

            return MultimodalResult(
                text=str(response),
                metadata={"model": "llama_index_gpt4o"},
                used_llama=True,
            )
        except Exception as e:
            return MultimodalResult(text="", error=str(e))

    async def extract_diagram(
        self,
        image_path: str,
    ) -> MultimodalResult:
        prompt = """Analyze this architecture diagram. Identify and extract:
1. All components (services, databases, APIs, clients)
2. All connections/arrows between components
3. Data flow direction
4. Technologies used
Return structured information about each component and connection."""

        return await self.parse(image_path, prompt)

    async def extract_ui(
        self,
        image_path: str,
    ) -> MultimodalResult:
        prompt = """Analyze this UI screenshot. Return ONLY JSON:
{
  "source_type": "sketch|screenshot|wireframe|diagram",
  "page_type": "object-page|list-report|worklist|overview|custom",
  "layout": {"type": "single-column|two-column|header-content-footer|free-form", "regions": []},
  "elements": [
    {"id": "e1", "type": "table|form|button|input|select|chart|navigation|tab|card",
     "label": "text", "position": {}, "attributes": {}, "interactions": [], "confidence": 0.85}
  ],
  "user_actions": [{"trigger": "action", "expected_result": "result"}]
}"""

        return await self.parse(image_path, prompt)


class VisionAPIParser:
    """Vision API parsers (GPT-4O, Qwen, Claude)."""

    def __init__(
        self,
        model: VisionModel = VisionModel.GPT4O,
    ):
        self.model = model
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def parse(
        self,
        image_url: str,
        prompt: Optional[str] = None,
    ) -> MultimodalResult:
        if self.model == VisionModel.GPT4O or self.model == VisionModel.GPT4V:
            return await self._parse_openai(image_url, prompt)
        elif self.model == VisionModel.QWEN_VL:
            return await self._parse_qwen(image_url, prompt)
        elif self.model == VisionModel.CLAUDE_VISION:
            return await self._parse_claude(image_url, prompt)
        else:
            return MultimodalResult(text="", error=f"Unsupported: {self.model}")

    async def _parse_openai(
        self,
        image_url: str,
        prompt: Optional[str],
    ) -> MultimodalResult:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return MultimodalResult(text="", error="No API key")

        default_prompt = prompt or "Describe this image in detail."

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": default_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "max_tokens": 4096,
        }

        try:
            client = self._get_client()
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]

            return MultimodalResult(
                text=text,
                metadata={"model": self.model.value},
                used_vision_api=True,
            )
        except Exception as e:
            return MultimodalResult(text="", error=str(e))

    async def _parse_qwen(
        self,
        image_url: str,
        prompt: Optional[str],
    ) -> MultimodalResult:
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not api_key:
            return MultimodalResult(error="No API key")

        default_prompt = prompt or "Describe this image in detail."

        payload = {
            "model": "qwen-vl-plus",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_url},
                            {"text": default_prompt},
                        ],
                    }
                ]
            },
        }

        try:
            client = self._get_client()
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["output"]["text"]

            return MultimodalResult(
                text=text,
                metadata={"model": self.model.value},
                used_vision_api=True,
            )
        except Exception as e:
            return MultimodalResult(text="", error=str(e))

    async def _parse_claude(
        self,
        image_url: str,
        prompt: Optional[str],
    ) -> MultimodalResult:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return MultimodalResult(text="", error="No API key")

        default_prompt = prompt or "Describe this image in detail."

        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "url", "url": image_url}},
                        {"type": "text", "text": default_prompt},
                    ],
                }
            ],
        }

        try:
            client = self._get_client()
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]

            return MultimodalResult(
                text=text,
                metadata={"model": self.model.value},
                used_vision_api=True,
            )
        except Exception as e:
            return MultimodalResult(text="", error=str(e))

    async def extract_diagram(self, image_url: str) -> MultimodalResult:
        prompt = """Analyze this architecture diagram. Extract into JSON format:
{
  "components": [{"id", "type", "label", "technology"}],
  "connections": [{"from", "to", "protocol"}],
  "data_flow": [{"source", "target", "description"}]
}"""
        return await self.parse(image_url, prompt)

    async def extract_ui(self, image_url: str) -> MultimodalResult:
        prompt = """Analyze this UI screenshot. Return ONLY JSON:
{
  "source_type": "sketch|screenshot|wireframe|diagram",
  "page_type": "object-page|list-report|worklist|overview|custom",
  "layout": {"type": "single-column|two-column|header-content-footer|free-form", "regions": []},
  "elements": [
    {"id": "e1", "type": "table|form|button|input|select|chart|navigation|tab|card",
     "label": "text", "position": {}, "attributes": {}, "interactions": [], "confidence": 0.85}
  ],
  "user_actions": [{"trigger": "action", "expected_result": "result"}]
}"""
        return await self.parse(image_url, prompt)


class HybridMultimodalParser:
    """Hybrid parser: LlamaIndex → Docling → Vision APIs."""

    def __init__(
        self,
        prefer_llama: bool = True,
        default_model: VisionModel = VisionModel.GPT4O,
    ):
        self.llama_parser = LlamaIndexMultimodalParser()
        self.docling_parser = _SharedDoclingParser(use_ocr=True)
        self.vision_parser = VisionAPIParser(default_model)
        self.prefer_llama = prefer_llama
        self.default_model = default_model

    @property
    def llama_available(self) -> bool:
        return self.llama_parser.available

    @property
    def docling_available(self) -> bool:
        return self.docling_parser.available

    async def parse_image_url(
        self,
        image_url: str,
    ) -> MultimodalResult:
        # Try LlamaIndex if available
        if self.prefer_llama and self.llama_available:
            result = await self.llama_parser.parse(image_url)
            if result.text and not result.error:
                return result

        # Fallback to vision API
        return await self.vision_parser.parse(image_url)

    async def parse_image_bytes(
        self,
        image_bytes: bytes,
    ) -> MultimodalResult:
        # Convert to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            if self.llama_available:
                result = await self.llama_parser.parse(tmp_path)
                if result.text and not result.error:
                    return result

            # Fallback to base64 encoding
            b64 = base64.b64encode(image_bytes).decode()
            return await self.vision_parser.parse(f"data:image/png;base64,{b64}")
        finally:
            os.unlink(tmp_path)

    async def extract_diagram(
        self,
        image_url: str,
        use_specialized: bool = False,
    ) -> MultimodalResult:
        if use_specialized and self.docling_available:
            return await self.docling_parser.parse(await self._get_image_bytes(image_url))

        if self.llama_available:
            return await self.llama_parser.extract_diagram(image_url)

        return await self.vision_parser.extract_diagram(image_url)

    async def extract_ui(
        self,
        image_url: str,
    ) -> MultimodalResult:
        if self.llama_available:
            return await self.llama_parser.extract_ui(image_url)

        return await self.vision_parser.extract_ui(image_url)

    async def _get_image_bytes(self, image_url: str) -> bytes:
        if image_url.startswith("data:"):
            b64 = image_url.split(",")[1]
            return base64.b64decode(b64)

        client = httpx.AsyncClient()
        resp = await client.get(image_url)
        return resp.content


_parser: Optional[HybridMultimodalParser] = None


def get_multimodal_parser() -> HybridMultimodalParser:
    global _parser
    if _parser is None:
        _parser = HybridMultimodalParser()
    return _parser


def is_llama_multimodal_available() -> bool:
    return LLAMA_MULTIMODAL_AVAILABLE


def is_docling_available() -> bool:
    return _SharedDoclingParser().available
