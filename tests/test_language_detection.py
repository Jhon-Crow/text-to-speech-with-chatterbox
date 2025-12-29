"""Tests for language detection utilities."""

import pytest

from tts_app.utils.language_detection import (
    detect_script,
    detect_primary_language,
    is_mixed_language_text,
    get_language_name,
)


class TestDetectScript:
    """Tests for detect_script function."""

    def test_english_text(self):
        """Test detecting Latin script in English text."""
        text = "Hello, this is a test."
        result = detect_script(text)

        assert result['latin'] > 0
        assert result['cyrillic'] == 0

    def test_russian_text(self):
        """Test detecting Cyrillic script in Russian text."""
        text = "Привет, это тест."
        result = detect_script(text)

        assert result['cyrillic'] > 0
        assert result['latin'] == 0

    def test_chinese_text(self):
        """Test detecting CJK script in Chinese text."""
        text = "你好世界"
        result = detect_script(text)

        assert result['cjk'] > 0

    def test_mixed_text(self):
        """Test detecting multiple scripts in mixed text."""
        text = "Hello Привет 你好"
        result = detect_script(text)

        assert result['latin'] > 0
        assert result['cyrillic'] > 0
        assert result['cjk'] > 0

    def test_punctuation_ignored(self):
        """Test that punctuation is not counted."""
        text = "...!!???..."
        result = detect_script(text)

        # All should be zero since punctuation is ignored
        assert result['latin'] == 0
        assert result['cyrillic'] == 0


class TestDetectPrimaryLanguage:
    """Tests for detect_primary_language function."""

    def test_english_detection(self):
        """Test detecting English as primary language."""
        text = "This is an English text about programming."
        result = detect_primary_language(text)

        assert result == "en"

    def test_russian_detection(self):
        """Test detecting Russian as primary language."""
        text = "Это текст на русском языке о программировании."
        result = detect_primary_language(text)

        assert result == "ru"

    def test_chinese_detection(self):
        """Test detecting Chinese as primary language."""
        text = "这是一段关于编程的中文文本。"
        result = detect_primary_language(text)

        assert result == "zh"

    def test_japanese_detection_hiragana(self):
        """Test detecting Japanese (hiragana)."""
        text = "これはテストです"
        result = detect_primary_language(text)

        assert result == "ja"

    def test_korean_detection(self):
        """Test detecting Korean."""
        text = "이것은 테스트입니다"
        result = detect_primary_language(text)

        assert result == "ko"

    def test_mixed_with_dominant_russian(self):
        """Test mixed text where Russian is dominant."""
        text = "Привет мир! Hello! Это тест на русском языке с английскими словами."
        result = detect_primary_language(text)

        # Russian should be dominant
        assert result == "ru"

    def test_empty_text(self):
        """Test empty text defaults to English."""
        text = ""
        result = detect_primary_language(text)

        assert result == "en"

    def test_punctuation_only(self):
        """Test punctuation-only text defaults to English."""
        text = "...!!!???"
        result = detect_primary_language(text)

        assert result == "en"


class TestIsMixedLanguageText:
    """Tests for is_mixed_language_text function."""

    def test_pure_english(self):
        """Test pure English text is not mixed."""
        text = "This is a pure English text with no other languages."
        result = is_mixed_language_text(text)

        assert result is False

    def test_pure_russian(self):
        """Test pure Russian text is not mixed."""
        text = "Это чистый русский текст без других языков."
        result = is_mixed_language_text(text)

        assert result is False

    def test_mixed_english_russian(self):
        """Test mixed English and Russian text is detected."""
        # Roughly 50-50 split
        text = "Привет мир Hello world Это тест This is test"
        result = is_mixed_language_text(text, threshold=0.1)

        assert result is True

    def test_minor_mixed_below_threshold(self):
        """Test that minor mixing below threshold is not detected."""
        # Mostly Russian with very little English
        text = "Это очень длинный русский текст о программировании и технологиях. x"
        result = is_mixed_language_text(text, threshold=0.1)

        # The single 'x' should be below 10% threshold
        assert result is False


class TestGetLanguageName:
    """Tests for get_language_name function."""

    def test_known_languages(self):
        """Test getting names of known languages."""
        assert get_language_name("en") == "English"
        assert get_language_name("ru") == "Russian"
        assert get_language_name("zh") == "Chinese"
        assert get_language_name("ja") == "Japanese"
        assert get_language_name("ko") == "Korean"
        assert get_language_name("ar") == "Arabic"

    def test_unknown_language(self):
        """Test unknown language code returns uppercase code."""
        assert get_language_name("xx") == "XX"
