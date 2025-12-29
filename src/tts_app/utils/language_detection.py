"""Language detection utilities for multilingual text processing."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Unicode ranges for common scripts
SCRIPT_RANGES = {
    'cyrillic': (0x0400, 0x04FF),  # Russian, Ukrainian, etc.
    'latin': (0x0041, 0x007A),     # Basic Latin letters
    'cjk': (0x4E00, 0x9FFF),       # Chinese characters
    'hiragana': (0x3040, 0x309F),  # Japanese Hiragana
    'katakana': (0x30A0, 0x30FF),  # Japanese Katakana
    'hangul': (0xAC00, 0xD7AF),    # Korean
    'arabic': (0x0600, 0x06FF),    # Arabic
    'devanagari': (0x0900, 0x097F), # Hindi/Sanskrit
    'greek': (0x0370, 0x03FF),     # Greek
    'hebrew': (0x0590, 0x05FF),    # Hebrew
}


def detect_script(text: str) -> dict[str, int]:
    """Detect which scripts are present in text and their character counts.

    Args:
        text: The text to analyze.

    Returns:
        Dictionary mapping script names to character counts.
    """
    script_counts = {script: 0 for script in SCRIPT_RANGES}
    script_counts['other'] = 0

    for char in text:
        code_point = ord(char)

        # Skip whitespace and common punctuation
        if char.isspace() or char in '.,!?;:\'"()-[]{}':
            continue

        found = False
        for script, (start, end) in SCRIPT_RANGES.items():
            if start <= code_point <= end:
                script_counts[script] += 1
                found = True
                break

        if not found:
            script_counts['other'] += 1

    return script_counts


def detect_primary_language(text: str) -> str:
    """Detect the primary language of text based on script analysis.

    This is a simple heuristic-based detector that works by analyzing
    the scripts used in the text. For more accurate detection, consider
    using a proper language detection library.

    Args:
        text: The text to analyze.

    Returns:
        Language code (e.g., "en", "ru", "zh", "ja", "ko", "ar", "hi").
        Defaults to "en" if detection fails.
    """
    script_counts = detect_script(text)

    # Remove zero counts and 'other'
    active_scripts = {k: v for k, v in script_counts.items() if v > 0 and k != 'other'}

    if not active_scripts:
        logger.debug("No script detected, defaulting to English")
        return "en"

    # Find the dominant script
    dominant_script = max(active_scripts, key=active_scripts.get)
    total_chars = sum(active_scripts.values())
    dominant_percentage = active_scripts[dominant_script] / total_chars * 100

    logger.debug(f"Script analysis: {active_scripts}")
    logger.debug(f"Dominant script: {dominant_script} ({dominant_percentage:.1f}%)")

    # Map scripts to language codes
    script_to_lang = {
        'cyrillic': 'ru',
        'latin': 'en',  # Default for Latin script
        'cjk': 'zh',
        'hiragana': 'ja',
        'katakana': 'ja',
        'hangul': 'ko',
        'arabic': 'ar',
        'devanagari': 'hi',
        'greek': 'el',
        'hebrew': 'he',
    }

    detected_lang = script_to_lang.get(dominant_script, 'en')
    logger.info(f"Detected primary language: {detected_lang} (from {dominant_script} script)")

    return detected_lang


def is_mixed_language_text(text: str, threshold: float = 0.1) -> bool:
    """Check if text contains significant portions of multiple scripts.

    Args:
        text: The text to analyze.
        threshold: Minimum percentage (0-1) of non-dominant script to be considered mixed.

    Returns:
        True if text contains significant portions of multiple scripts.
    """
    script_counts = detect_script(text)

    # Remove zero counts and 'other'
    active_scripts = {k: v for k, v in script_counts.items() if v > 0 and k != 'other'}

    if len(active_scripts) <= 1:
        return False

    total_chars = sum(active_scripts.values())
    if total_chars == 0:
        return False

    # Sort by count (descending)
    sorted_scripts = sorted(active_scripts.items(), key=lambda x: x[1], reverse=True)

    # Check if second-most-common script exceeds threshold
    if len(sorted_scripts) >= 2:
        second_percentage = sorted_scripts[1][1] / total_chars
        return second_percentage >= threshold

    return False


def get_language_name(code: str) -> str:
    """Get the human-readable name for a language code.

    Args:
        code: ISO 639-1 language code (e.g., "en", "ru").

    Returns:
        Human-readable language name.
    """
    names = {
        "ar": "Arabic",
        "da": "Danish",
        "de": "German",
        "el": "Greek",
        "en": "English",
        "es": "Spanish",
        "fi": "Finnish",
        "fr": "French",
        "he": "Hebrew",
        "hi": "Hindi",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "ms": "Malay",
        "nl": "Dutch",
        "no": "Norwegian",
        "pl": "Polish",
        "pt": "Portuguese",
        "ru": "Russian",
        "sv": "Swedish",
        "sw": "Swahili",
        "tr": "Turkish",
        "zh": "Chinese",
    }
    return names.get(code, code.upper())
