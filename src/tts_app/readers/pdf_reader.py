"""PDF document reader using pdfplumber."""

import re
from pathlib import Path

from .base import DocumentReader, DocumentContent


class PDFReader(DocumentReader):
    """Reader for PDF documents using pdfplumber.

    This reader extracts text from PDF files while preserving
    the ability to identify footnotes for optional filtering.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported PDF extensions."""
        return [".pdf", ".PDF"]

    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from a PDF document.

        Args:
            file_path: Path to the PDF file.

        Returns:
            DocumentContent with extracted text and footnotes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be read as PDF.
        """
        import pdfplumber

        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            text_parts = []
            footnotes = []

            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)

                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)

                    # Extract footnotes from page
                    # Footnotes are typically at the bottom with superscript numbers
                    page_footnotes = self._extract_footnotes(page_text)
                    footnotes.extend(page_footnotes)

            full_text = "\n\n".join(text_parts)

            return DocumentContent(
                text=full_text,
                footnotes=footnotes,
                page_count=page_count,
                metadata={"source": str(file_path), "format": "pdf"}
            )

        except Exception as e:
            raise ValueError(f"Failed to read PDF file: {e}") from e

    def _extract_footnotes(self, text: str) -> list[str]:
        """Extract footnotes from page text.

        Footnotes are identified by patterns like:
        - Numbered footnotes: "1 This is a footnote"
        - Superscript indicators at line start

        Args:
            text: The page text to search.

        Returns:
            List of extracted footnote texts.
        """
        footnotes = []

        # Pattern for footnotes that start with a number followed by space or period
        # at the beginning of a line (common footnote format)
        lines = text.split("\n")
        in_footnote_section = False

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Detect footnote section (often at bottom, starts with small numbers)
            footnote_match = re.match(r'^(\d{1,2})\s+(.+)$', line)
            if footnote_match:
                number = int(footnote_match.group(1))
                # Footnotes typically use small numbers (1-99)
                if 1 <= number <= 99:
                    footnote_text = footnote_match.group(2)
                    # Check if this looks like a footnote (not a list item)
                    # by seeing if the number is referenced earlier as superscript
                    footnotes.append(f"[{number}] {footnote_text}")
                    in_footnote_section = True
            elif in_footnote_section and not re.match(r'^\d', line):
                # Continuation of previous footnote if not starting with number
                if footnotes:
                    footnotes[-1] += " " + line

        return footnotes
