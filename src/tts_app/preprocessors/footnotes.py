"""Footnote handling preprocessor."""

import re
from typing import Optional

from .base import TextPreprocessor, ProcessingContext


class FootnoteHandler(TextPreprocessor):
    """Preprocessor that handles footnotes in text.

    Depending on configuration, this preprocessor can either:
    - Remove footnote references from text (when ignore_footnotes=True)
    - Insert footnote content inline where references appear (when ignore_footnotes=False)

    Footnote patterns handled:
    - Superscript-style: text¹ or text²
    - Bracket-style: text[1] or text[2]
    - Asterisk-style: text* or text**
    """

    @property
    def name(self) -> str:
        """Return the preprocessor name."""
        return "footnote_handler"

    def process(self, text: str, context: ProcessingContext) -> str:
        """Process footnotes in text.

        If ignore_footnotes is True, removes all footnote references.
        If ignore_footnotes is False, inserts footnote text inline.

        Args:
            text: The text to process.
            context: Processing context with footnotes list and ignore flag.

        Returns:
            Text with footnotes processed according to settings.
        """
        if context.ignore_footnotes:
            return self._remove_footnote_references(text)
        else:
            return self._insert_footnotes_inline(text, context.footnotes)

    def _remove_footnote_references(self, text: str) -> str:
        """Remove all footnote references from text.

        Args:
            text: The text to clean.

        Returns:
            Text with footnote references removed.
        """
        result = text

        # Remove bracket-style references [1], [2], etc.
        result = re.sub(r'\[\d+\]', '', result)

        # Remove superscript numbers (unicode superscripts)
        superscripts = '⁰¹²³⁴⁵⁶⁷⁸⁹'
        for sup in superscripts:
            result = result.replace(sup, '')

        # Remove asterisk footnotes (* or **)
        result = re.sub(r'(?<=[a-zA-Z.,!?])\*{1,3}(?=\s|$|[.,!?])', '', result)

        # Remove caret-style references ^1, ^2, etc. (markdown style)
        result = re.sub(r'\^\d+', '', result)

        # Clean up any double spaces created
        result = re.sub(r'  +', ' ', result)

        return result

    def _insert_footnotes_inline(self, text: str, footnotes: list[str]) -> str:
        """Insert footnote content inline where references appear.

        Args:
            text: The text with footnote references.
            footnotes: List of footnote texts in format "[N] text".

        Returns:
            Text with footnotes inserted inline.
        """
        if not footnotes:
            return text

        # Build a mapping of footnote numbers to content
        footnote_map = self._parse_footnotes(footnotes)

        result = text

        # Replace bracket-style references [N] with inline footnotes
        def replace_bracket(match):
            num = match.group(1)
            if num in footnote_map:
                return f" (Footnote: {footnote_map[num]}) "
            return match.group(0)

        result = re.sub(r'\[(\d+)\]', replace_bracket, result)

        # Replace superscript numbers
        superscript_map = {
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
            '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'
        }

        for sup, num in superscript_map.items():
            if sup in result and num in footnote_map:
                result = result.replace(sup, f" (Footnote: {footnote_map[num]}) ")

        # Replace caret-style references ^N
        def replace_caret(match):
            num = match.group(1)
            if num in footnote_map:
                return f" (Footnote: {footnote_map[num]}) "
            return match.group(0)

        result = re.sub(r'\^(\d+)', replace_caret, result)

        # Clean up spacing
        result = re.sub(r'  +', ' ', result)
        result = re.sub(r' +([.,!?])', r'\1', result)

        return result

    def _parse_footnotes(self, footnotes: list[str]) -> dict[str, str]:
        """Parse footnote list into a number->content mapping.

        Args:
            footnotes: List of footnotes in format "[N] text".

        Returns:
            Dictionary mapping footnote numbers to content.
        """
        footnote_map = {}

        for footnote in footnotes:
            # Parse "[N] text" format
            match = re.match(r'\[(\d+)\]\s*(.+)', footnote)
            if match:
                num = match.group(1)
                content = match.group(2).strip()
                footnote_map[num] = content

        return footnote_map
