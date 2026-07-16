"""Shared LLM response extraction utilities.

Provides robust text extraction from LLM responses, handling both
real ChatCompletionResponse objects and mock objects used in tests.
"""

from typing import Any


def extract_text(response: Any) -> str:
    """Extract text from an LLM response, handling all response shapes.

    Handles:
    - ChatCompletionResponse (has .text property)
    - Dict with 'content' key
    - Dict with 'choices' list
    - MagicMock (test fixtures)

    Returns empty string if no text can be extracted.
    """
    # ChatCompletionResponse has a .text property
    if hasattr(response, "text"):
        text = response.text
        if isinstance(text, str):
            return text.strip()

    # Try dict-style access (some providers return dicts)
    if hasattr(response, "get"):
        try:
            content = response.get("content", "")
            if isinstance(content, str):
                return content.strip()
        except Exception:
            pass

    # Try choices[0].message.content (OpenAI format)
    if hasattr(response, "choices"):
        try:
            choices = response.choices
            if choices and len(choices) > 0:
                choice = choices[0]
                if isinstance(choice, dict):
                    msg = choice.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        return content.strip()
                elif hasattr(choice, "message"):
                    content = getattr(choice.message, "content", "")
                    if isinstance(content, str):
                        return content.strip()
        except Exception:
            pass

    return ""


def extract_json_from_response(response: Any) -> Any:
    """Extract and parse JSON from an LLM response.

    Handles:
    - Plain JSON string
    - JSON wrapped in markdown code fences (```json ... ```)
    - JSON with leading/trailing prose

    Returns the parsed JSON object, or None if parsing fails.
    """
    import json
    import re

    text = extract_text(response)
    if not text:
        return None

    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array or object in the text
    for pattern in [
        r'\[.*\]',  # JSON array
        r'\{.*\}',  # JSON object
    ]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    return None
