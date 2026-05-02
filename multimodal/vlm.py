"""
VLM (Vision Language Model) providers for multimodal analysis.

Supports:
- QwenVL (Alibaba DashScope)
- OpenAI Vision (GPT-4V)
- OpenRouter (Google Gemma 4, and other multimodal models via OpenRouter)

Advanced capabilities per provider:
- Image analysis (all)
- Video analysis (OpenRouter/Gemma 4)
- Function calling (OpenRouter/Gemma 4)
- Structured output (all, provider-dependent)
- Thinking mode (OpenRouter/Gemma 4)
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Templates (per-VLM optimized)
# =============================================================================

class VLMPrompts:
    """Curated prompts optimized for different VLM providers and tasks."""
    
    # -------------------------------------------------------------------------
    # Image Analysis Prompts
    # -------------------------------------------------------------------------
    IMAGE_ANALYSIS = {
        "qwen": (
            "分析这张图片。提取所有关键信息，用中文详细描述图中元素及其关系。\n\n"
            "要求：\n"
            "1. 列出图中所有可识别对象\n"
            "2. 说明各对象的作用和属性\n"
            "3. 标注对象之间的关系\n"
            "4. 如果是架构图，标注数据流向"
        ),
        "openai": (
            "Analyze this image thoroughly. You are an expert at extracting "
            "structured information from diagrams, screenshots, and documents.\n\n"
            "Extract:\n"
            "1. All identifiable objects and their properties\n"
            "2. Relationships between objects\n"
            "3. Any text or labels present\n"
            "4. Data flows if applicable"
        ),
        "openrouter": (
            "You are an expert diagram and image analyzer. Your task is to extract "
            "complete structured information from any visual input.\n\n"
            "Follow these steps:\n"
            "1. Identify all visual elements (objects, text, labels)\n"
            "2. Classify each element by type and function\n"
            "3. Map relationships and dependencies\n"
            "4. Note any metadata or attributes\n"
            "5. Output your findings in clear, structured format"
        ),
    }
    
    # -------------------------------------------------------------------------
    # Text Extraction Prompts
    # -------------------------------------------------------------------------
    TEXT_EXTRACTION = {
        "qwen": "识别并提取图片中的所有文字内容。保持原始格式，只返回文字。",
        "openai": "Extract all readable text from this image. Preserve the original spelling and formatting.",
        "openrouter": "Extract ALL text from this image with perfect accuracy. Include every word, number, and symbol. Preserve formatting.",
    }
    
    # -------------------------------------------------------------------------
    # Diagram Extraction Prompts
    # -------------------------------------------------------------------------
    DIAGRAM_EXTRACTION = {
        "qwen": (
            "这是一个架构图。请提取所有组件和它们之间的关系。\n"
            "按以下JSON格式输���：\n"
            '{"nodes": [{"id": "名称", "type": "类型", "description": "描述"}], '
            '"edges": [{"from": "源", "to": "目标", "label": "关系"}]}'
        ),
        "openai": (
            "Extract the complete structure from this architecture diagram.\n\n"
            "Identify:\n"
            "1. All components (services, databases, APIs, clients)\n"
            "2. Their connections and data flows\n"
            "3. Technologies and protocols used\n"
            "4. Return as structured JSON with nodes and edges"
        ),
        "openrouter": (
            "解析此架构图。完全提取所有组件、连接和数据流。\n\n"
            "JSON output required:\n"
            "{\n"
            '  "nodes": [{"id": "unique_id", "label": "Component Name", "type": "service|database|api|client|gateway|queue", "technology": "optional tech stack", "description": "what it does"}],\n'
            '  "edges": [{"source": "node_id", "target": "node_id", "label": "HTTP|REST|gRPC|WebSocket|MQ", "description": "data flow description"}]\n'
            "}\n\n"
            "Be precise. Use consistent IDs. Include all visible connections."
        ),
    }
    
    # -------------------------------------------------------------------------
    # UI Element Extraction Prompts
    # -------------------------------------------------------------------------
    UI_EXTRACTION = {
        "qwen": "分析这个UI界面。列出所有UI组件（按钮、输入框、菜单等）及其位置和功能。",
        "openai": (
            "Analyze this user interface screenshot.\n\n"
            "Extract all UI elements with:\n"
            "1. Element type (button, input, menu, etc.)\n"
            "2. Position/bounds\n"
            "3. Text or label\n"
            "4. Apparent function\n"
            "5. State if identifiable"
        ),
        "openrouter": (
            "You are a UI/UX expert analyzing a screenshot.\n\n"
            "For each visible element provide:\n"
            '  {"type": "button|input|menu|header|sidebar|modal|text|icon|image", "label": "visible text", '
            '"bounds": {"x": 0, "y": 0, "width": 100, "height": 50}, '
            '"function": "what it does", "state": "default|active|disabled"}'
        ),
    }
    
    # -------------------------------------------------------------------------
    # Structured Output Prompts (for JSON schema enforcement)
    # -------------------------------------------------------------------------
    STRUCTURED_OUTPUT = {
        "qwen": (
            "按以下JSON Schema生成准确输出：\n{schema}\n\n"
            "只返回有效的JSON，不要其他解释。"
        ),
        "openai": (
            "Output valid JSON conforming to this schema:\n{schema}\n\n"
            "Respond with ONLY valid JSON, no additional text."
        ),
        "openrouter": (
            "Output STRICT JSON matching this schema exactly:\n{schema}\n\n"
            "Your response will be parsed directly - no wrapper text, no markdown."
        ),
    }
    
    # -------------------------------------------------------------------------
    # Video Analysis Prompts (OpenRouter only)
    # -------------------------------------------------------------------------
    VIDEO_ANALYSIS = {
        "openrouter": (
            "分析此视频。逐帧提取关键信息：\n"
            "1. 视频中的主要对象和动作\n"
            "2. 时间序列事件\n"
            "3. 任何文字或标签\n"
            "4. 总结视频内容\n"
            "帧率：1fps抽样"
        ),
    }
    
    # -------------------------------------------------------------------------
    # Thinking Mode Prompts (for models that support it)
    # -------------------------------------------------------------------------
    THINKING_MODE = {
        "openrouter": (
            "Think step-by-step about your analysis. Show your reasoning process.\n"
            "Consider multiple perspectives before finalizing your response."
        ),
    }
    
    @classmethod
    def get(cls, task: str, provider: str) -> str:
        """Get prompt for task/provider combination."""
        prompts = getattr(cls, task.upper(), {})
        return prompts.get(provider.lower(), prompts.get("openrouter", ""))


# =============================================================================
# VLM Provider Interface (Extended)
# =============================================================================

class VLMProvider(ABC):
    """Abstract base for VLM providers."""
    
    # Provider capabilities (override in subclasses)
    supports_video: bool = False
    supports_function_calling: bool = False
    supports_structured_output: bool = False
    supports_thinking: bool = False
    
    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """Analyze an image with a custom prompt."""
        ...
    
    @abstractmethod
    async def extract_text(self, image_url: str) -> str:
        """Extract all text from an image."""
        ...
    
    async def analyze_diagram(self, image_url: str) -> Dict[str, Any]:
        """Extract structured diagram information."""
        prompt = VLMPrompts.get("DIAGRAM_EXTRACTION", self.provider_name)
        return await self.analyze_image(image_url, prompt)
    
    async def analyze_ui(self, image_url: str) -> Dict[str, Any]:
        """Extract UI elements from screenshot."""
        prompt = VLMPrompts.get("UI_EXTRACTION", self.provider_name)
        return await self.analyze_image(image_url, prompt)
    
    async def analyze_video(self, video_url: str) -> Dict[str, Any]:
        """Analyze a video (if supported)."""
        if not self.supports_video:
            return {"error": f"Video analysis not supported by {self.provider_name}"}
        return {"error": "Not implemented"}
    
    async def call_function(
        self, prompt: str, functions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use function calling (if supported)."""
        if not self.supports_function_calling:
            return {"error": f"Function calling not supported by {self.provider_name}"}
        return {"error": "Not implemented"}
    
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate JSON conforming to a schema."""
        if not self.supports_structured_output:
            # Fall back to prompt-based extraction
            schema_prompt = VLMPrompts.get("STRUCTURED_OUTPUT", self.provider_name)
            full_prompt = f"{prompt}\n\n{schema_prompt.format(schema=json.dumps(schema))}"
            result = await self.analyze_image("", full_prompt)
            return self._parse_structured(result, schema)
        return {"error": "Not implemented"}
    
    def _parse_structured(
        self, result: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse result into structured format."""
        text = result.get("output", {}).get("text", "")
        try:
            # Try direct JSON parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {"raw": text, "error": "Failed to parse structured output"}
    
    @property
    def provider_name(self) -> str:
        """Provider identifier for prompt selection."""
        return "openrouter"


# =============================================================================
# Qwen VL Provider
# =============================================================================

class QwenVLProvider(VLMProvider):
    """Alibaba Qwen Vision model via DashScope."""
    
    supports_video = False
    supports_function_calling = False
    supports_structured_output = False
    supports_thinking = False
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-vl-plus",
    ):
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/multimodal"
    
    @property
    def provider_name(self) -> str:
        return "qwen"
    
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
        except Exception as e:
            logger.warning("Error analyzing image with Qwen: %s", e)
            return {"error": "Failed to analyze image"}
    
    async def extract_text(self, image_url: str) -> str:
        prompt = VLMPrompts.get("TEXT_EXTRACTION", self.provider_name)
        result = await self.analyze_image(image_url, prompt)
        return result.get("output", {}).get("text", "")


# =============================================================================
# OpenAI Vision Provider
# =============================================================================

class OpenAIVisionProvider(VLMProvider):
    """OpenAI GPT-4V via OpenAI API."""
    
    supports_video = False
    supports_function_calling = False
    supports_structured_output = True  # Supports response_format
    supports_thinking = False
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
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
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {"output": {"text": content}}
        except Exception as e:
            logger.warning("Error analyzing image with OpenAI: %s", e)
            return {"error": "Failed to analyze image"}
    
    async def extract_text(self, image_url: str) -> str:
        prompt = VLMPrompts.get("TEXT_EXTRACTION", self.provider_name)
        result = await self.analyze_image(image_url, prompt)
        return result.get("output", {}).get("text", "")
    
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate JSON with OpenAI's response_format parameter."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_schema", "json_schema": schema},
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {"output": {"text": content}}
        except Exception as e:
            logger.warning("Error with structured output: %s", e)
            return await super().generate_structured(prompt, schema)


# =============================================================================
# OpenRouter VLM Provider (Gemma 4 + others)
# =============================================================================

class OpenRouterVLMProvider(VLMProvider):
    """OpenRouter-hosted models including Google Gemma 4.
    
    Supports:
    - Text + images (all models)
    - Video input (models that support it)
    - Function calling (when available)
    - Structured output (via schema prompt)
    - Thinking mode (when enabled)
    
    Models via OpenRouter:
    - google/gemma-4-31b-it:free: Text, images, video (60s), function calling, structured output, thinking
    - google/gemma-3-it: Text, images, video
    - Other multimodal models
    """
    
    supports_video = True
    supports_function_calling = True
    supports_structured_output = True
    supports_thinking = True
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "google/gemma-4-31b-it:free",
    ):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
    
    @property
    def provider_name(self) -> str:
        return "openrouter"
    
    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using OpenRouter API."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
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
                    timeout=90.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {"output": {"text": content}}
        except Exception as e:
            logger.warning("Error analyzing image with OpenRouter: %s", e)
            return {"error": f"Failed to analyze image: {e}"}
    
    async def extract_text(self, image_url: str) -> str:
        """Extract text with high accuracy prompt."""
        prompt = VLMPrompts.get("TEXT_EXTRACTION", self.provider_name)
        result = await self.analyze_image(image_url, prompt)
        return result.get("output", {}).get("text", "")
    
    async def analyze_video(self, video_url: str) -> Dict[str, Any]:
        """Analyze video frame-by-frame."""
        if not self.supports_video:
            return {"error": f"Video not supported by {self.model}"}
        
        prompt = VLMPrompts.get("VIDEO_ANALYSIS", self.provider_name)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "video_url",
                                        "video_url": {"url": video_url},
                                    },
                                ],
                            }
                        ],
                    },
                    timeout=120.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {"output": {"text": content}}
        except Exception as e:
            logger.warning("Error analyzing video with OpenRouter: %s", e)
            return {"error": f"Failed to analyze video: {e}"}
    
    async def call_function(
        self, prompt: str, functions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use function calling with OpenRouter."""
        if not self.supports_function_calling:
            return {"error": f"Function calling not supported by {self.model}"}
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "tools": [{"type": "function", "function": f} for f in functions],
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("Error with function calling: %s", e)
            return {"error": f"Function call failed: {e}"}
    
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON using schema prompt."""
        schema_prompt = VLMPrompts.STRUCTURED_OUTPUT["openrouter"].format(
            schema=json.dumps(schema)
        )
        full_prompt = f"{prompt}\n\n{schema_prompt}"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": full_prompt}],
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                # Parse JSON from response
                return self._parse_structured({"output": {"text": content}}, schema)
        except Exception as e:
            logger.warning("Error with structured output: %s", e)
            return {"error": f"Structured output failed: {e}"}
    
    async def analyze_with_thinking(
        self, image_url: str, prompt: str
    ) -> Dict[str, Any]:
        """Analyze with thinking/reasoning enabled."""
        if not self.supports_thinking:
            return await self.analyze_image(image_url, prompt)
        
        thinking_prompt = f"{prompt}\n\n{VLMPrompts.THINKING_MODE['openrouter']}"
        return await self.analyze_image(image_url, thinking_prompt)


# =============================================================================
# VLM Processor (Router)
# =============================================================================

class VLMProcessor:
    """Routes to appropriate VLM provider."""
    
    def __init__(self, provider: Optional[VLMProvider] = None):
        self.provider = provider or self._create_provider()
    
    @staticmethod
    def _create_provider() -> VLMProvider:
        provider_type = os.getenv("VLM_PROVIDER", "").lower()
        
        if provider_type == "qwen":
            return QwenVLProvider()
        elif provider_type == "openai":
            return OpenAIVisionProvider()
        elif provider_type == "openrouter":
            model = os.getenv("VLM_MODEL", "google/gemma-4-31b-it:free")
            return OpenRouterVLMProvider(model=model)
        elif provider_type == "gemma":
            return OpenRouterVLMProvider(model="google/gemma-4-31b-it:free")
        else:
            # Default to OpenRouter with Gemma 4
            return OpenRouterVLMProvider()
    
    @property
    def provider_name(self) -> str:
        return self.provider.provider_name
    
    @property
    def supports_video(self) -> bool:
        return self.provider.supports_video
    
    @property
    def supports_function_calling(self) -> bool:
        return self.provider.supports_function_calling
    
    @property
    def supports_structured_output(self) -> bool:
        return self.provider.supports_structured_output
    
    @property
    def supports_thinking(self) -> bool:
        return self.provider.supports_thinking
    
    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        return await self.provider.analyze_image(image_url, prompt)
    
    async def extract_text(self, image_url: str) -> str:
        return await self.provider.extract_text(image_url)
    
    async def analyze_diagram(self, image_url: str) -> Dict[str, Any]:
        return await self.provider.analyze_diagram(image_url)
    
    async def analyze_ui(self, image_url: str) -> Dict[str, Any]:
        return await self.provider.analyze_ui(image_url)
    
    async def analyze_video(self, video_url: str) -> Dict[str, Any]:
        return await self.provider.analyze_video(video_url)
    
    async def call_function(
        self, prompt: str, functions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return await self.provider.call_function(prompt, functions)
    
    async def generate_structured(
        self, prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.provider.generate_structured(prompt, schema)
    
    async def extract_for_ir(
        self, image_url: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        text = await self.provider.extract_text(image_url)
        return {"content": text, "title": title, "type": "image_extraction"}


# =============================================================================
# Factory Function
# =============================================================================

def get_vlm_processor() -> VLMProcessor:
    """Get configured VLM processor."""
    return VLMProcessor()


def get_vlm_provider() -> VLMProvider:
    """Get configured VLM provider."""
    return VLMProcessor().provider