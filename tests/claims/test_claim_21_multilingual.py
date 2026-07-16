"""
README claim: "Multilingual: Language detection (Russian, English, and 20+ languages);
Russian text normalization (Cyrillic, yo-ye equivalence)"
Source: README.md lines 113-116
"""
import pytest


@pytest.mark.claim
@pytest.mark.parametrize("text,expected", [
    ("\u041a\u0430\u043a \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0430\u0443\u0442\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f?", "russian"),
    ("How does authentication work?", "english"),
])
def test_language_detection_russian_english(text, expected):
    from core.text_utils import detect_language, TextLanguage
    lang = detect_language(text)
    if expected == "russian":
        assert lang == TextLanguage.RUSSIAN, f"Expected Russian, got {lang}"
    elif expected == "english":
        assert lang == TextLanguage.ENGLISH, f"Expected English, got {lang}"


@pytest.mark.claim
def test_russian_yo_ye_normalization():
    from core.text_utils import normalize_text, TextLanguage
    text1 = "\u0451\u043b\u043a\u0430"
    text2 = "\u0435\u043b\u043a\u0430"
    norm1 = normalize_text(text1, language=TextLanguage.RUSSIAN)
    norm2 = normalize_text(text2, language=TextLanguage.RUSSIAN)
    assert norm1 == norm2, f"Russian normalization failed: '{norm1}' != '{norm2}'"


@pytest.mark.claim
def test_language_detection_multiple_languages():
    from core.text_utils import detect_language
    texts = [
        "Comment fonctionne l'authentification?",
        "Wie funktioniert die Authentifizierung?",
        "\u00bfC\u00f3mo funciona la autenticaci\u00f3n?",
        "\u8a8d\u8a3c\u306f\u3069\u306e\u3088\u3046\u306b\u6a5f\u80fd\u3057\u307e\u3059\u304b\uff1f",
        "\uc778\uc99d\uc740 \uc5b4\ub5bb\uac8c \uc791\ub3d9\ud569\ub2c8\uae4c?",
        "\u0643\u064a\u0641 \u062a\u0639\u0645\u0644 \u0627\u0644\u0645\u0635\u0627\u062f\u0642\u0629\u061f",
        "\u8ba4\u8bc1\u662f\u5982\u4f55\u5de5\u4f5c\u7684\uff1f",
    ]
    for text in texts:
        lang = detect_language(text)
        assert lang is not None, f"Language detection returned None for: {text}"
