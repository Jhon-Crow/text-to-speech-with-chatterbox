"""Page number removal preprocessor."""

import re

from .base import TextPreprocessor, ProcessingContext


class PageNumberRemover(TextPreprocessor):
    """Preprocessor that removes page numbers from text.

    This preprocessor identifies and removes common page number patterns:
    - Standalone numbers on their own line
    - "Page X" or "Page X of Y" formats
    - Roman numerals (i, ii, iii, etc.)
    - Numbers at the beginning or end of lines that match page patterns
    """

    @property
    def name(self) -> str:
        """Return the preprocessor name."""
        return "page_number_remover"

    def process(self, text: str, context: ProcessingContext) -> str:
        """Remove page numbers from text.

        Args:
            text: The text to process.
            context: Processing context with page count for validation.

        Returns:
            Text with page numbers removed.
        """
        lines = text.split("\n")
        processed_lines = []

        max_page = context.page_count or 10000  # Default to high number if unknown

        for line in lines:
            stripped = line.strip()

            # Skip if the line is a page number
            if self._is_page_number(stripped, max_page):
                continue

            # Remove page indicators from line ends/starts
            cleaned = self._clean_line_page_indicators(line, max_page)
            processed_lines.append(cleaned)

        return "\n".join(processed_lines)

    def _is_page_number(self, line: str, max_page: int) -> bool:
        """Check if a line is just a page number.

        Args:
            line: The stripped line to check.
            max_page: Maximum expected page number.

        Returns:
            True if the line is a page number.
        """
        if not line:
            return False

        # Pattern: just a number
        if re.match(r'^\d+$', line):
            try:
                num = int(line)
                # Likely a page number if within reasonable range
                return 1 <= num <= max_page * 2
            except ValueError:
                return False

        # Pattern: "Page X" or "Page X of Y"
        if re.match(r'^[Pp]age\s+\d+(\s+(of|/)\s+\d+)?$', line):
            return True

        # Pattern: "- X -" or "-- X --" (centered page numbers)
        if re.match(r'^[-–—]\s*\d+\s*[-–—]$', line):
            return True

        # Pattern: Roman numerals (common for prefaces)
        if re.match(r'^[ivxlcdmIVXLCDM]+$', line):
            return True

        return False

    def _clean_line_page_indicators(self, line: str, max_page: int) -> str:
        """Remove page indicators from line edges.

        Args:
            line: The line to clean.
            max_page: Maximum expected page number.

        Returns:
            Line with page indicators removed.
        """
        # Remove trailing page numbers like "text 123" at end of line
        # Be careful not to remove legitimate numbers
        result = line

        # Pattern: trailing number that looks like a page number
        match = re.search(r'\s+(\d{1,4})\s*$', result)
        if match:
            num = int(match.group(1))
            if 1 <= num <= max_page * 2:
                # Check if this is likely a page number (end of paragraph)
                # Only remove if the preceding text ends reasonably
                preceding = result[:match.start()]
                if preceding.rstrip().endswith(('.', '!', '?', '"', "'", ')', ']')):
                    result = preceding.rstrip()

        return result
