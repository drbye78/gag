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
    from langdetect import LangDetectException, detect

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None
    LangDetectException = Exception


class TextLanguage(str, Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
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


GERMAN_STOP_WORDS = {
    "der",
    "die",
    "das",
    "und",
    "in",
    "den",
    "von",
    "zu",
    "das",
    "mit",
    "ist",
    "ein",
    "eine",
    "nicht",
    "auf",
    "f\u00fcr",
    "an",
    "dem",
    "es",
    "sich",
    "auch",
    "als",
    "nach",
    "wie",
    "oder",
}

FRENCH_STOP_WORDS = {
    "le",
    "la",
    "les",
    "de",
    "des",
    "un",
    "une",
    "du",
    "et",
    "en",
    "est",
    "que",
    "qui",
    "dans",
    "ce",
    "il",
    "ne",
    "sur",
    "se",
    "pas",
    "plus",
    "par",
    "ce",
    "avec",
    "son",
    "cette",
}

SPANISH_STOP_WORDS = {
    "el",
    "la",
    "los",
    "las",
    "de",
    "en",
    "y",
    "que",
    "un",
    "una",
    "es",
    "no",
    "por",
    "con",
    "para",
    "como",
    "pero",
    "su",
    "m\u00e1s",
    "este",
    "ya",
    "entre",
    "cuando",
    "muy",
    "sin",
}


# Unicode ranges for Latin-script language detection
_german_chars = set("\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df")
_french_chars = set(
    "\u00e0\u00e2\u00e7\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f9\u00fb\u00fc\u00c0\u00c2\u00c7\u00c9\u00ca\u00cb\u00ce\u00cf\u00d4\u00d9\u00db\u00dc"
)
_spanish_chars = set(
    "\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\u00bf\u00a1\u00c1\u00c9\u00cd\u00d3\u00da\u00d1"
)


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
        if lang in ("de",):
            return TextLanguage.GERMAN
        if lang in ("fr",):
            return TextLanguage.FRENCH
        if lang in ("es",):
            return TextLanguage.SPANISH
        return TextLanguage.UNKNOWN
    except LangDetectException:
        return _detect_by_script(text)


def _detect_by_script(text: str) -> TextLanguage:
    cyrillic_count = 0
    latin_count = 0
    german_count = 0
    french_count = 0
    spanish_count = 0

    for char in text:
        if "\u0400" <= char <= "\u04ff" or "\u0500" <= char <= "\u052f":
            cyrillic_count += 1
        elif char.isalpha() and ("a" <= char.lower() <= "z" or "A" <= char.upper() <= "Z"):
            latin_count += 1
        if char in _german_chars:
            german_count += 1
        if char in _french_chars:
            french_count += 1
        if char in _spanish_chars:
            spanish_count += 1

    if cyrillic_count > latin_count * 2:
        return TextLanguage.RUSSIAN
    if latin_count > cyrillic_count * 2:
        # Use diacritical markers to distinguish Latin-script languages
        if german_count > french_count and german_count > spanish_count:
            return TextLanguage.GERMAN
        if french_count > german_count and french_count > spanish_count:
            return TextLanguage.FRENCH
        if spanish_count > german_count and spanish_count > french_count:
            return TextLanguage.SPANISH
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
    if language == TextLanguage.GERMAN:
        return word_lower in GERMAN_STOP_WORDS
    if language == TextLanguage.FRENCH:
        return word_lower in FRENCH_STOP_WORDS
    if language == TextLanguage.SPANISH:
        return word_lower in SPANISH_STOP_WORDS

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
        TextLanguage.GERMAN: "German",
        TextLanguage.FRENCH: "French",
        TextLanguage.SPANISH: "Spanish",
        TextLanguage.UNKNOWN: "Unknown",
    }
    return mapping.get(code, "Unknown")
