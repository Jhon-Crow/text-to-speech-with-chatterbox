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
    """

    # Symbol to spoken text mapping
    SYMBOL_MAP = {
        # Mathematical operators
        '=': ' equals ',
        '+': ' plus ',
        '-': ' minus ',  # Will be handled carefully to avoid conflicts with hyphens
        '*': ' times ',  # Will be handled carefully to avoid bullet point conflicts
        '/': ' divided by ',
        '%': ' percent',
        '<': ' less than ',
        '>': ' greater than ',
        '<=': ' less than or equal to ',
        '>=': ' greater than or equal to ',
        '!=': ' not equal to ',
        '==': ' equals ',
        '→': ' arrow ',
        '←': ' arrow ',
        '↔': ' bidirectional arrow ',

        # Currency symbols
        '$': ' dollars ',
        '€': ' euros ',
        '£': ' pounds ',
        '¥': ' yen ',
        '₽': ' rubles ',

        # Common special characters
        '@': ' at ',
        '&': ' and ',
        '#': ' number ',

        # Bullets and list markers
        '•': ', ',
        '◦': ', ',
        '▪': ', ',
        '▸': ', ',
        '►': ', ',
    }

    # Russian symbol map
    SYMBOL_MAP_RU = {
        '=': ' равно ',
        '+': ' плюс ',
        '-': ' минус ',
        '*': ' умножить на ',
        '/': ' делить на ',
        '%': ' процент',
        '<': ' меньше чем ',
        '>': ' больше чем ',
        '→': ' стрелка ',
        '←': ' стрелка ',
        '$': ' долларов ',
        '€': ' евро ',
        '£': ' фунтов ',
        '¥': ' иен ',
        '₽': ' рублей ',
        '@': ' собака ',
        '&': ' и ',
        '#': ' номер ',
    }

    @property
    def name(self) -> str:
        """Return the preprocessor name."""
        return "symbol_converter"

    def process(self, text: str, context: ProcessingContext) -> str:
        """Process symbols and numbered points in text.

        Args:
            text: The text to process.
            context: Processing context (unused in this preprocessor).

        Returns:
            Text with symbols converted to readable words.
        """
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

        # Convert "1." or "1)" at start of line or after newline
        # Pattern: start of line, optional whitespace, number, period or paren
        def replace_numbered_point(match):
            leading = match.group(1) or ""
            number = match.group(2)
            separator = match.group(3)
            trailing = match.group(4) or ""

            # Use "point" for period, just the number for parenthesis
            if separator == '.':
                return f"{leading}Point {number}.{trailing}"
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

        # Convert multi-character operators first
        result = result.replace('>=', ' greater than or equal to ')
        result = result.replace('<=', ' less than or equal to ')
        result = result.replace('!=', ' not equal to ')
        result = result.replace('==', ' equals ')

        # Convert equations like "x = 5" or "a + b = c"
        # Match: something = something (with spaces around equals)
        result = re.sub(
            r'(\w+)\s*=\s*(\w+)',
            r'\1 equals \2',
            result
        )

        # Convert standalone = signs (not in URLs or paths)
        # Only convert if surrounded by spaces or at word boundaries
        result = re.sub(r'(?<=\s)=(?=\s)', ' equals ', result)

        # Convert + signs in mathematical context
        result = re.sub(r'(\d+)\s*\+\s*(\d+)', r'\1 plus \2', result)

        # Convert percentage patterns like "50%" or "100%"
        result = re.sub(r'(\d+)%', r'\1 percent', result)

        return result

    def _convert_standalone_symbols(self, text: str) -> str:
        """Convert standalone symbols to speakable text.

        Args:
            text: The text to process.

        Returns:
            Text with standalone symbols converted.
        """
        result = text

        # Convert currency amounts
        result = re.sub(r'\$(\d+(?:\.\d{2})?)', r'\1 dollars', result)
        result = re.sub(r'€(\d+(?:\.\d{2})?)', r'\1 euros', result)
        result = re.sub(r'£(\d+(?:\.\d{2})?)', r'\1 pounds', result)
        result = re.sub(r'₽(\d+(?:\.\d{2})?)', r'\1 rubles', result)

        # Convert bullet points at start of lines
        result = re.sub(r'(^|\n)\s*[•◦▪▸►]\s*', r'\1', result)

        # Convert standalone & to "and"
        result = re.sub(r'\s+&\s+', ' and ', result)

        # Convert # followed by numbers (like #1, #42)
        result = re.sub(r'#(\d+)', r'number \1', result)

        # Convert arrows
        result = result.replace('→', ' arrow ')
        result = result.replace('←', ' arrow ')
        result = result.replace('->', ' arrow ')
        result = result.replace('<-', ' arrow ')

        return result
