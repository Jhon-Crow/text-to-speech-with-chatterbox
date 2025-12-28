"""DOC document reader for legacy Microsoft Word files."""

import re
import struct
from pathlib import Path
from typing import Optional

from .base import DocumentReader, DocumentContent


class DOCReader(DocumentReader):
    """Reader for legacy DOC documents (Microsoft Word 97-2003).

    This reader extracts text from .doc files using the OLE file structure.
    Note that .doc files have a more complex binary format than .docx files.
    For full-featured .doc support, consider using external tools like antiword.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported DOC extensions."""
        return [".doc", ".DOC"]

    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from a DOC document.

        Args:
            file_path: Path to the DOC file.

        Returns:
            DocumentContent with extracted text and footnotes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be read as DOC.
        """
        import olefile

        if not file_path.exists():
            raise FileNotFoundError(f"DOC file not found: {file_path}")

        try:
            ole = olefile.OleFileIO(file_path)

            # Try to get the Word document stream
            text = ""

            if ole.exists("WordDocument"):
                word_doc = ole.openstream("WordDocument")
                word_data = word_doc.read()

                # Try to extract text from the document
                text = self._extract_text_from_word_document(ole, word_data)

            if not text.strip():
                # Fallback: try to get any readable text from streams
                text = self._extract_fallback_text(ole)

            ole.close()

            # Extract footnotes from text
            footnotes = self._extract_footnotes(text)

            # Estimate page count (roughly 500 words per page)
            word_count = len(text.split())
            estimated_pages = max(1, word_count // 500)

            return DocumentContent(
                text=text,
                footnotes=footnotes,
                page_count=estimated_pages,
                metadata={"source": str(file_path), "format": "doc"}
            )

        except Exception as e:
            raise ValueError(f"Failed to read DOC file: {e}") from e

    def _extract_text_from_word_document(self, ole, word_data: bytes) -> str:
        """Extract text from Word document stream.

        Args:
            ole: The OleFileIO object.
            word_data: The raw WordDocument stream data.

        Returns:
            Extracted text content.
        """
        text_parts = []

        # Try to get the text from various possible locations

        # Method 1: Try to read from the document text table
        if ole.exists("1Table") or ole.exists("0Table"):
            table_name = "1Table" if ole.exists("1Table") else "0Table"
            try:
                table_stream = ole.openstream(table_name)
                table_data = table_stream.read()

                # The FIB (File Information Block) contains offsets
                # Try to extract readable ASCII/Unicode text from the stream
                text = self._extract_readable_text(word_data)
                if text:
                    text_parts.append(text)
            except Exception:
                pass

        # Method 2: Direct text extraction from WordDocument stream
        if not text_parts:
            text = self._extract_readable_text(word_data)
            if text:
                text_parts.append(text)

        return "\n".join(text_parts)

    def _extract_readable_text(self, data: bytes) -> str:
        """Extract readable text from binary data.

        This is a simplified extraction that looks for readable text
        in the binary stream. For complex documents, external tools
        may provide better results.

        Args:
            data: Binary data to extract text from.

        Returns:
            Extracted text.
        """
        # Try UTF-16LE first (common for modern Word)
        try:
            # Look for the text start after FIB (File Information Block)
            # FIB is typically at least 68 bytes
            text = self._decode_text(data)
            if text and len(text) > 10:  # At least some meaningful content
                return text
        except Exception:
            pass

        # Try extracting ASCII text
        try:
            ascii_text = self._extract_ascii_text(data)
            if ascii_text:
                return ascii_text
        except Exception:
            pass

        return ""

    def _decode_text(self, data: bytes) -> str:
        """Decode text from Word document data.

        Args:
            data: Binary data from the WordDocument stream.

        Returns:
            Decoded text.
        """
        text_parts = []

        # Try to find readable Unicode strings
        i = 0
        current_text = []

        while i < len(data) - 1:
            # Look for Unicode characters (UTF-16LE)
            char_code = data[i] + (data[i + 1] << 8)

            # Printable ASCII in Unicode
            if 0x20 <= char_code <= 0x7E or char_code in (0x0A, 0x0D, 0x09):
                current_text.append(chr(char_code))
            elif current_text:
                # End of a text segment
                segment = "".join(current_text)
                if len(segment) >= 3:  # Only keep segments with at least 3 chars
                    text_parts.append(segment)
                current_text = []

            i += 2

        # Don't forget the last segment
        if current_text:
            segment = "".join(current_text)
            if len(segment) >= 3:
                text_parts.append(segment)

        # Join with spaces, avoiding duplicates
        result = " ".join(text_parts)

        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result)

        return result.strip()

    def _extract_ascii_text(self, data: bytes) -> str:
        """Extract ASCII text from binary data.

        Args:
            data: Binary data to extract from.

        Returns:
            Extracted ASCII text.
        """
        text_parts = []
        current_text = []

        for byte in data:
            # Printable ASCII or common whitespace
            if 0x20 <= byte <= 0x7E or byte in (0x0A, 0x0D, 0x09):
                current_text.append(chr(byte))
            elif current_text:
                segment = "".join(current_text)
                if len(segment) >= 5:  # Only keep segments with at least 5 chars
                    text_parts.append(segment)
                current_text = []

        # Don't forget the last segment
        if current_text:
            segment = "".join(current_text)
            if len(segment) >= 5:
                text_parts.append(segment)

        # Join with spaces
        result = " ".join(text_parts)

        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result)

        return result.strip()

    def _extract_fallback_text(self, ole) -> str:
        """Fallback text extraction by scanning all streams.

        Args:
            ole: The OleFileIO object.

        Returns:
            Any text that could be extracted.
        """
        all_text = []

        for stream_path in ole.listdir():
            try:
                stream = ole.openstream(stream_path)
                data = stream.read()

                # Skip very small streams
                if len(data) < 100:
                    continue

                text = self._extract_readable_text(data)
                if text and len(text) > 20:
                    all_text.append(text)
            except Exception:
                continue

        return "\n".join(all_text)

    def _extract_footnotes(self, text: str) -> list[str]:
        """Extract footnotes from document text.

        Args:
            text: The document text.

        Returns:
            List of extracted footnote texts.
        """
        footnotes = []

        # Pattern for footnotes that start with a number followed by space
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for footnote patterns
            footnote_match = re.match(r'^(\d{1,2})\s+(.+)$', line)
            if footnote_match:
                number = int(footnote_match.group(1))
                if 1 <= number <= 99:
                    footnote_text = footnote_match.group(2)
                    footnotes.append(f"[{number}] {footnote_text}")

        return footnotes
