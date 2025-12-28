"""RTF document reader for Rich Text Format files."""

import re
from pathlib import Path

from .base import DocumentReader, DocumentContent


class RTFReader(DocumentReader):
    """Reader for RTF documents (Rich Text Format).

    This reader extracts text from .rtf files using the striprtf library.
    RTF is a cross-platform document format that preserves basic formatting.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported RTF extensions."""
        return [".rtf", ".RTF"]

    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from an RTF document.

        Args:
            file_path: Path to the RTF file.

        Returns:
            DocumentContent with extracted text.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be read as RTF.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"RTF file not found: {file_path}")

        try:
            from striprtf.striprtf import rtf_to_text
        except ImportError:
            raise ImportError(
                "striprtf library is required for RTF support. "
                "Install it with: pip install striprtf"
            )

        # Try different encodings
        encodings = ["utf-8", "cp1252", "latin-1"]

        rtf_content = None
        for encoding in encodings:
            try:
                rtf_content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if rtf_content is None:
            raise ValueError(f"Could not decode RTF file with any known encoding: {file_path}")

        try:
            # Convert RTF to plain text
            text = rtf_to_text(rtf_content)
        except Exception as e:
            raise ValueError(f"Failed to parse RTF content: {e}") from e

        # Clean up the text
        text = self._clean_text(text)

        # Extract footnotes
        footnotes = self._extract_footnotes(text)

        # Estimate page count (roughly 3000 characters per page)
        estimated_pages = max(1, len(text) // 3000)

        return DocumentContent(
            text=text,
            footnotes=footnotes,
            page_count=estimated_pages,
            metadata={"source": str(file_path), "format": "rtf"}
        )

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text.

        Args:
            text: Raw extracted text.

        Returns:
            Cleaned text.
        """
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Remove form feed and other control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        return text.strip()

    def _extract_footnotes(self, text: str) -> list[str]:
        """Extract footnotes from document text.

        Args:
            text: The document text.

        Returns:
            List of extracted footnote texts.
        """
        footnotes = []

        # Pattern for footnotes that start with a number in brackets or superscript
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for footnote patterns like [1], (1), or just "1." at line start
            footnote_match = re.match(r'^[\[\(]?(\d{1,2})[\]\)]?\.?\s+(.+)$', line)
            if footnote_match:
                number = int(footnote_match.group(1))
                if 1 <= number <= 99:
                    footnote_text = footnote_match.group(2)
                    if len(footnote_text) > 10:  # Only keep meaningful footnotes
                        footnotes.append(f"[{number}] {footnote_text}")

        return footnotes
