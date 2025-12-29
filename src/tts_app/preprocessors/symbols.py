"""Symbol and number preprocessing for TTS readability."""

import re
from typing import Optional

from .base import TextPreprocessor, ProcessingContext


class SymbolConverter(TextPreprocessor):
    """Preprocessor that converts symbols and numbered points to readable text.

    This preprocessor handles:
    - Mathematical symbols: =, +, -, *, /, <, >, %, etc.
    - Numbered lists: 1. 2. 3. or 1) 2) 3) patterns
    - Bullet points: -, *, •
    - Special characters: @, #, &, etc.

    The goal is to make the text more natural for TTS synthesis by converting
    symbols that would otherwise be skipped or mispronounced.

    The preprocessor is language-aware and will use localized symbol names
    based on the detected dominant language in the text.
    """

    # English symbol to spoken text mapping (default)
    SYMBOL_MAP_EN = {
        # Mathematical operators
        'equals': ' equals ',
        'plus': ' plus ',
        'minus': ' minus ',
        'times': ' times ',
        'divided_by': ' divided by ',
        'percent': ' percent',
        'less_than': ' less than ',
        'greater_than': ' greater than ',
        'less_or_equal': ' less than or equal to ',
        'greater_or_equal': ' greater than or equal to ',
        'not_equal': ' not equal to ',
        'arrow': ' arrow ',

        # Currency symbols
        'dollars': ' dollars',
        'euros': ' euros',
        'pounds': ' pounds',
        'yen': ' yen',
        'rubles': ' rubles',

        # Common special characters
        'at': ' at ',
        'and': ' and ',
        'number': ' number ',

        # List items
        'point': 'Point ',
    }

    # Russian symbol to spoken text mapping
    SYMBOL_MAP_RU = {
        # Mathematical operators
        'equals': ' равно ',
        'plus': ' плюс ',
        'minus': ' минус ',
        'times': ' умножить на ',
        'divided_by': ' делить на ',
        'percent': ' процентов',
        'less_than': ' меньше ',
        'greater_than': ' больше ',
        'less_or_equal': ' меньше или равно ',
        'greater_or_equal': ' больше или равно ',
        'not_equal': ' не равно ',
        'arrow': ' стрелка ',

        # Currency symbols
        'dollars': ' долларов',
        'euros': ' евро',
        'pounds': ' фунтов',
        'yen': ' иен',
        'rubles': ' рублей',

        # Common special characters
        'at': ' собака ',
        'and': ' и ',
        'number': ' номер ',

        # List items
        'point': 'Пункт ',
    }

    # Language code to symbol map
    LANGUAGE_MAPS = {
        'ru': SYMBOL_MAP_RU,
        'en': SYMBOL_MAP_EN,
    }

    def __init__(self):
        """Initialize the symbol converter."""
        self._current_map = self.SYMBOL_MAP_EN  # Default to English

    @property
    def name(self) -> str:
        """Return the preprocessor name."""
        return "symbol_converter"

    def _get_symbol_map(self, language: Optional[str]) -> dict:
        """Get the appropriate symbol map for the language.

        Args:
            language: Language code (e.g., "en", "ru") or None for auto-detect.

        Returns:
            Dictionary mapping symbol keys to localized spoken text.
        """
        if language and language in self.LANGUAGE_MAPS:
            return self.LANGUAGE_MAPS[language]
        return self.SYMBOL_MAP_EN

    def _detect_text_language(self, text: str) -> str:
        """Detect the dominant language in text based on script.

        Args:
            text: The text to analyze.

        Returns:
            Language code ("en", "ru", etc.).
        """
        from tts_app.utils.language_detection import detect_primary_language
        return detect_primary_language(text)

    def process(self, text: str, context: ProcessingContext) -> str:
        """Process symbols and numbered points in text.

        Args:
            text: The text to process.
            context: Processing context with language information.

        Returns:
            Text with symbols converted to readable words.
        """
        # Determine language: use context language if provided, otherwise detect from text
        language = context.language
        if not language:
            language = self._detect_text_language(text)

        # Get the appropriate symbol map
        self._current_map = self._get_symbol_map(language)

        result = text

        # Convert numbered lists (1. 2. 3. or 1) 2) 3))
        result = self._convert_numbered_lists(result)

        # Convert mathematical expressions
        result = self._convert_math_expressions(result)

        # Convert standalone symbols
        result = self._convert_standalone_symbols(result)

        # Clean up multiple spaces
        result = re.sub(r'  +', ' ', result)

        return result

    def _convert_numbered_lists(self, text: str) -> str:
        """Convert numbered list patterns to speakable text.

        Args:
            text: The text to process.

        Returns:
            Text with numbered lists converted.
        """
        result = text
        point_word = self._current_map.get('point', 'Point ')

        # Convert "1." or "1)" at start of line or after newline
        # Pattern: start of line, optional whitespace, number, period or paren
        def replace_numbered_point(match):
            leading = match.group(1) or ""
            number = match.group(2)
            separator = match.group(3)
            trailing = match.group(4) or ""

            # Use localized "point" word for period, just the number for parenthesis
            if separator == '.':
                return f"{leading}{point_word}{number}.{trailing}"
            else:  # )
                return f"{leading}{number}.{trailing}"

        # Match numbered lists at start of line
        result = re.sub(
            r'(^|\n)(\d{1,3})([.\)])(\s*)',
            replace_numbered_point,
            result
        )

        return result

    def _convert_math_expressions(self, text: str) -> str:
        """Convert mathematical expressions to speakable text.

        Args:
            text: The text to process.

        Returns:
            Text with math expressions converted.
        """
        result = text

        # Get localized words
        equals_word = self._current_map.get('equals', ' equals ')
        plus_word = self._current_map.get('plus', ' plus ')
        percent_word = self._current_map.get('percent', ' percent')
        greater_or_equal = self._current_map.get('greater_or_equal', ' greater than or equal to ')
        less_or_equal = self._current_map.get('less_or_equal', ' less than or equal to ')
        not_equal = self._current_map.get('not_equal', ' not equal to ')

        # Convert multi-character operators first
        result = result.replace('>=', greater_or_equal)
        result = result.replace('<=', less_or_equal)
        result = result.replace('!=', not_equal)
        result = result.replace('==', equals_word)

        # Convert equations like "x = 5" or "a + b = c"
        # Match: something = something (with spaces around equals)
        def replace_equals(match):
            return f"{match.group(1)}{equals_word}{match.group(2)}"

        result = re.sub(
            r'(\w+)\s*=\s*(\w+)',
            replace_equals,
            result
        )

        # Convert standalone = signs (not in URLs or paths)
        # Only convert if surrounded by spaces or at word boundaries
        result = re.sub(r'(?<=\s)=(?=\s)', equals_word, result)

        # Convert + signs in mathematical context
        def replace_plus(match):
            return f"{match.group(1)}{plus_word}{match.group(2)}"

        result = re.sub(r'(\d+)\s*\+\s*(\d+)', replace_plus, result)

        # Convert percentage patterns like "50%" or "100%"
        def replace_percent(match):
            return f"{match.group(1)}{percent_word}"

        result = re.sub(r'(\d+)%', replace_percent, result)

        return result

    def _convert_standalone_symbols(self, text: str) -> str:
        """Convert standalone symbols to speakable text.

        Args:
            text: The text to process.

        Returns:
            Text with standalone symbols converted.
        """
        result = text

        # Get localized words
        dollars_word = self._current_map.get('dollars', ' dollars')
        euros_word = self._current_map.get('euros', ' euros')
        pounds_word = self._current_map.get('pounds', ' pounds')
        rubles_word = self._current_map.get('rubles', ' rubles')
        and_word = self._current_map.get('and', ' and ')
        number_word = self._current_map.get('number', ' number ')
        arrow_word = self._current_map.get('arrow', ' arrow ')

        # Convert currency amounts
        def replace_dollars(match):
            return f"{match.group(1)}{dollars_word}"
        def replace_euros(match):
            return f"{match.group(1)}{euros_word}"
        def replace_pounds(match):
            return f"{match.group(1)}{pounds_word}"
        def replace_rubles(match):
            return f"{match.group(1)}{rubles_word}"

        result = re.sub(r'\$(\d+(?:\.\d{2})?)', replace_dollars, result)
        result = re.sub(r'€(\d+(?:\.\d{2})?)', replace_euros, result)
        result = re.sub(r'£(\d+(?:\.\d{2})?)', replace_pounds, result)
        result = re.sub(r'₽(\d+(?:\.\d{2})?)', replace_rubles, result)

        # Convert bullet points at start of lines
        result = re.sub(r'(^|\n)\s*[•◦▪▸►]\s*', r'\1', result)

        # Convert standalone & to "and"
        result = re.sub(r'\s+&\s+', and_word, result)

        # Convert # followed by numbers (like #1, #42)
        def replace_number(match):
            return f"{number_word}{match.group(1)}"
        result = re.sub(r'#(\d+)', replace_number, result)

        # Convert arrows
        result = result.replace('→', arrow_word)
        result = result.replace('←', arrow_word)
        result = result.replace('->', arrow_word)
        result = result.replace('<-', arrow_word)

        return result
