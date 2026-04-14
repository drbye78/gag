"""Structured VLM extraction with JSON enforcement, retry logic, and GPT-4o integration."""

import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, model_validator


# ── Constants ──────────────────────────────────────────────────────────────

VALID_SOURCE_TYPES = {"sketch", "screenshot", "wireframe", "diagram"}

VALID_ELEMENT_TYPES = {
    "table", "form", "button", "input", "select", "chart", "navigation",
    "tab", "card", "dropdown", "checkbox", "radio", "textarea", "link",
    "image", "icon", "divider", "toolbar", "sidebar", "header", "footer",
    "modal", "toast", "breadcrumb", "pagination", "filter",
}


# ── Pydantic Schema Models ────────────────────────────────────────────────

class UIElementSchema(BaseModel):
    id: str = Field(..., description="Unique element identifier")
    type: str = Field(..., description="Element type (e.g., table, button, form)")
    label: Optional[str] = Field(None, description="Display label")
    position: Dict[str, Any] = Field(default_factory=dict, description="Bounding box {x, y, width, height}")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")
    interactions: List[str] = Field(default_factory=list, description="Supported interactions")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score 0-1")


class UserActionSchema(BaseModel):
    trigger: str = Field(..., description="User trigger (e.g., 'click Save')")
    expected_result: str = Field(..., description="Expected system response")


class LayoutRegionSchema(BaseModel):
    name: str = Field(..., description="Region name (e.g., 'sidebar', 'content')")
    elements: List[UIElementSchema] = Field(default_factory=list, description="Elements in this region")


class LayoutSchema(BaseModel):
    type: str = Field(..., description="Layout type (e.g., single-column, two-column)")
    regions: List[LayoutRegionSchema] = Field(default_factory=list, description="Layout regions")


class UIExtractionSchema(BaseModel):
    source_type: str = Field(..., description="Must be one of: sketch, screenshot, wireframe, diagram")
    page_type: Optional[str] = Field(None, description="Page classification")
    layout: LayoutSchema = Field(..., description="Structural layout")
    elements: List[UIElementSchema] = Field(default_factory=list, description="Extracted UI elements")
    user_actions: List[UserActionSchema] = Field(default_factory=list, description="User actions")

    @model_validator(mode="after")
    def validate_source_type(self):
        if self.source_type not in VALID_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(sorted(VALID_SOURCE_TYPES))}")
        return self


# ── VLMUIExtractor Class ──────────────────────────────────────────────────

class VLMUIExtractor:
    """Extracts structured UI data from images using a VLM (GPT-4o)."""

    def __init__(self, model: str = "gpt-4o", api_key_env: str = "OPENAI_API_KEY"):
        self.model = model
        self.api_key_env = api_key_env

    def build_extraction_prompt(self) -> str:
        """Returns a prompt string enforcing JSON output with full schema description."""
        return (
            "Analyze the provided UI image and extract structured data as JSON. "
            "Respond ONLY with valid JSON matching this schema:\n\n"
            "{\n"
            '  "source_type": "sketch|screenshot|wireframe|diagram",\n'
            '  "page_type": "string|null",\n'
            '  "layout": {\n'
            '    "type": "layout type (e.g., single-column, two-column)",\n'
            '    "regions": [\n'
            '      {"name": "region name", "elements": []}\n'
            "    ]\n"
            "  },\n"
            '  "elements": [{"id": "e1", "type": "table", "label": "Orders", "position": {}, '
            '"attributes": {}, "interactions": [], "confidence": 0.85}],\n'
            '  "user_actions": [{"trigger": "click Save", "expected_result": "form-submitted"}]\n'
            "}\n\n"
            "Valid element types: table, form, button, input, select, chart, navigation, tab, card, "
            "dropdown, checkbox, radio, textarea, link, image, icon, divider, toolbar, sidebar, "
            "header, footer, modal, toast, breadcrumb, pagination, filter.\n\n"
            "Return ONLY valid JSON. No explanations, no markdown."
        )

    def parse_vlm_response(self, response_text: str) -> Optional[UIExtractionSchema]:
        """Strip markdown code blocks, parse JSON, return UIExtractionSchema or None."""
        if not response_text or not response_text.strip():
            return None

        text = response_text.strip()

        # Strip markdown code blocks (with or without language tag)
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

        try:
            return UIExtractionSchema(**data)
        except (ValueError, TypeError):
            return None

    async def _call_vlm(self, image_url: str, prompt: str) -> str:
        """Call OpenAI GPT-4o API via httpx with image_url and response_format json_object."""
        api_key = os.environ.get(self.api_key_env, "")

        payload = {
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
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            raise RuntimeError(f"VLM API error {response.status_code}: {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def extract(self, image_url: str, max_retries: int = 2) -> Optional[UIExtractionSchema]:
        """Extract UI structure from image with retry logic. Returns UIExtractionSchema or None."""
        prompt = self.build_extraction_prompt()

        attempts = 0
        max_attempts = max_retries + 1  # initial + retries

        while attempts < max_attempts:
            attempts += 1
            try:
                response_text = await self._call_vlm(image_url, prompt)
                result = self.parse_vlm_response(response_text)
                if result is not None:
                    return result
            except Exception:
                pass  # Retry on any exception

        return None
