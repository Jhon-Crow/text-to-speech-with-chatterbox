"""Plain text file reader."""

from pathlib import Path

from .base import DocumentReader, DocumentContent


class TextReader(DocumentReader):
    """Reader for plain text files.

    This reader handles .txt files with various encodings.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported text extensions."""
        return [".txt", ".TXT"]

    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from a text file.

        Args:
            file_path: Path to the text file.

        Returns:
            DocumentContent with extracted text.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be decoded.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        # Try different encodings
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

        text = None
        for encoding in encodings:
            try:
                text = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise ValueError(f"Could not decode text file with any known encoding: {file_path}")

        # Estimate page count (roughly 3000 characters per page)
        estimated_pages = max(1, len(text) // 3000)

        return DocumentContent(
            text=text,
            footnotes=[],  # Plain text doesn't have structured footnotes
            page_count=estimated_pages,
            metadata={"source": str(file_path), "format": "txt"}
        )
