"""
Text Utilities - Multilingual text processing.

Provides:
- Language detection (Russian, English, etc.)
- Text normalization (Unicode, case folding)
- Language-aware sentence splitting
- Cyrillic transliteration fallback
"""

import re
import unicodedata
from enum import Enum
from functools import lru_cache
from typing import List, Optional

try:
    from langdetect import detect, LangDetectException

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None
    LangDetectException = Exception


class TextLanguage(str, Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    UNKNOWN = "unknown"


CYRILLIC_RANGE = "\u0400-\u04ff"
CYRILLIC_BLOCKS = [
    (0x0400, 0x04FF),
    (0x0500, 0x052F),
    (0x2DE0, 0x2DFF),
    (0xA640, 0xA69F),
]


RUSSIAN_LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
RUSSIAN_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
RUSSIAN_EQUIVALENTS = {
    "ё": "е",
    "Ё": "Е",
}


RUSSIAN_STOP_WORDS = {
    "и",
    "в",
    "во",
    "не",
    "что",
    "он",
    "на",
    "я",
    "с",
    "со",
    "как",
    "а",
    "то",
    "все",
    "она",
    "так",
    "его",
    "но",
    "да",
    "ты",
    "у",
    "же",
    "вы",
    "за",
    "бы",
    "по",
    "только",
    "ее",
    "мне",
    "было",
    "вот",
    "от",
    "меня",
    "еще",
    "нет",
    "о",
    "из",
    "ему",
    "теперь",
    "когда",
    "уже",
    "вам",
    "ни",
    "быть",
    "был",
    "него",
    "до",
    "нас",
    "для",
}


ENGLISH_STOP_WORDS = {
    "the",
    "is",
    "at",
    "which",
    "on",
    "and",
    "a",
    "an",
    "to",
    "in",
    "of",
    "for",
    "that",
    "by",
    "with",
    "from",
    "as",
    "it",
    "be",
    "are",
    "was",
    "or",
    "have",
    "has",
    "had",
    "were",
    "been",
    "being",
    "this",
    "these",
    "those",
    "can",
    "will",
    "just",
    "should",
    "would",
    "could",
}


@lru_cache(maxsize=1000)
def detect_language(text: str, min_confidence: float = 0.5) -> TextLanguage:
    if not text or not text.strip():
        return TextLanguage.UNKNOWN

    if not LANGDETECT_AVAILABLE:
        return _detect_by_script(text)

    try:
        lang = detect(text)
        if lang in ("ru",):
            return TextLanguage.RUSSIAN
        if lang in ("en",):
            return TextLanguage.ENGLISH
        return TextLanguage.UNKNOWN
    except LangDetectException:
        return _detect_by_script(text)


def _detect_by_script(text: str) -> TextLanguage:
    cyrillic_count = 0
    latin_count = 0

    for char in text:
        if "\u0400" <= char <= "\u04ff" or "\u0500" <= char <= "\u052f":
            cyrillic_count += 1
        elif char.isalpha() and (
            "a" <= char.lower() <= "z" or "A" <= char.upper() <= "Z"
        ):
            latin_count += 1

    if cyrillic_count > latin_count * 2:
        return TextLanguage.RUSSIAN
    if latin_count > cyrillic_count * 2:
        return TextLanguage.ENGLISH

    return TextLanguage.UNKNOWN


def normalize_text(
    text: str,
    language: Optional[TextLanguage] = None,
    lowercase: bool = True,
    remove_accents: bool = True,
) -> str:
    if not text:
        return ""

    result = text

    if lowercase:
        result = result.lower()

    if language == TextLanguage.RUSSIAN:
        result = normalize_cyrillic(result)

    if remove_accents:
        result = remove_diacritics(result)

    result = unicodedata.normalize("NFKC", result)
    result = re.sub(r"\s+", " ", result)
    result = result.strip()

    return result


def normalize_cyrillic(text: str) -> str:
    result = text

    for old, new in RUSSIAN_EQUIVALENTS.items():
        result = result.replace(old, new)

    return result


def remove_diacritics(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    result = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", result)


def split_sentences(
    text: str,
    language: Optional[TextLanguage] = None,
) -> List[str]:
    if not text:
        return []

    if language == TextLanguage.RUSSIAN:
        return _split_russian_sentences(text)

    return _split_english_sentences(text)


def _split_russian_sentences(text: str) -> List[str]:
    sentence_endings = r"[.!?]+[\s]+"
    sentences = re.split(sentence_endings, text)

    result = []
    for sent in sentences:
        sent = sent.strip()
        if sent:
            result.append(sent)

    return result


def _split_english_sentences(text: str) -> List[str]:
    sentence_endings = r"[.!?]+[\s]+"
    sentences = re.split(sentence_endings, text)

    result = []
    for sent in sentences:
        sent = sent.strip()
        if sent:
            result.append(sent)

    return result


def is_stop_word(word: str, language: TextLanguage) -> bool:
    word_lower = word.lower()

    if language == TextLanguage.RUSSIAN:
        return word_lower in RUSSIAN_STOP_WORDS

    return word_lower in ENGLISH_STOP_WORDS


def remove_stop_words(text: str, language: TextLanguage) -> str:
    words = text.split()
    filtered = [w for w in words if not is_stop_word(w, language)]
    return " ".join(filtered)


def truncate_for_embedding(
    text: str,
    max_tokens: int = 8000,
    model: str = "openai",
) -> str:
    if model in ("openai", "qwen"):
        chars_per_token = 4
    elif model == "ollama":
        chars_per_token = 3
    else:
        chars_per_token = 4

    max_chars = max_tokens * chars_per_token

    if len(text) <= max_chars:
        return text

    return text[:max_chars]


def clean_whitespace(text: str) -> str:
    text = re.sub(r"[\t\n\r]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = text.strip()
    return text


def is_cyrillic(text: str) -> bool:
    for char in text:
        if "\u0400" <= char <= "\u04ff":
            return True
    return False


def is_latin(text: str) -> bool:
    for char in text:
        if char.isalpha():
            if "a" <= char.lower() <= "z":
                return True
    return False


def get_language_name(code: TextLanguage) -> str:
    mapping = {
        TextLanguage.RUSSIAN: "Russian",
        TextLanguage.ENGLISH: "English",
        TextLanguage.UNKNOWN: "Unknown",
    }
    return mapping.get(code, "Unknown")
