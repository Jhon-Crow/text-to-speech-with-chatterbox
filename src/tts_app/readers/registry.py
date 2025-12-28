"""Registry for document readers."""

from pathlib import Path
from typing import Optional, Type

from .base import DocumentReader, DocumentContent


class ReaderRegistry:
    """Registry for managing document readers.

    This registry allows dynamic registration of document readers,
    making the architecture extensible for new file formats.

    Example:
        >>> registry = ReaderRegistry()
        >>> registry.register(PDFReader())
        >>> content = registry.read(Path("document.pdf"))
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._readers: list[DocumentReader] = []

    def register(self, reader: DocumentReader) -> None:
        """Register a document reader.

        Args:
            reader: An instance of a DocumentReader subclass.
        """
        self._readers.append(reader)

    def unregister(self, reader_type: Type[DocumentReader]) -> bool:
        """Unregister a document reader by type.

        Args:
            reader_type: The class of the reader to remove.

        Returns:
            True if a reader was removed, False otherwise.
        """
        original_length = len(self._readers)
        self._readers = [r for r in self._readers if not isinstance(r, reader_type)]
        return len(self._readers) < original_length

    def get_reader(self, file_path: Path) -> Optional[DocumentReader]:
        """Get a reader that can handle the given file.

        Args:
            file_path: Path to the file.

        Returns:
            A DocumentReader that can read the file, or None if no reader found.
        """
        for reader in self._readers:
            if reader.can_read(file_path):
                return reader
        return None

    def read(self, file_path: Path) -> DocumentContent:
        """Read a document using the appropriate reader.

        Args:
            file_path: Path to the document.

        Returns:
            DocumentContent with extracted text and metadata.

        Raises:
            ValueError: If no reader can handle the file format.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        reader = self.get_reader(path)
        if reader is None:
            supported = self.supported_extensions
            raise ValueError(
                f"Unsupported file format: {path.suffix}. "
                f"Supported formats: {', '.join(supported)}"
            )

        return reader.read(path)

    @property
    def supported_extensions(self) -> list[str]:
        """Get all supported file extensions.

        Returns:
            List of all supported extensions across all registered readers.
        """
        extensions = set()
        for reader in self._readers:
            extensions.update(reader.supported_extensions)
        return sorted(extensions)

    def get_file_filter(self) -> str:
        """Get a file dialog filter string for all supported formats.

        Returns:
            Filter string suitable for file dialogs (e.g., "*.pdf;*.docx;*.txt").
        """
        patterns = [f"*{ext}" for ext in self.supported_extensions]
        return ";".join(patterns)


def create_default_registry() -> ReaderRegistry:
    """Create a registry with all default document readers.

    Returns:
        A ReaderRegistry with PDF, DOC, DOCX, TXT, and MD readers registered.
    """
    from .pdf_reader import PDFReader
    from .doc_reader import DOCReader
    from .docx_reader import DOCXReader
    from .text_reader import TextReader
    from .markdown_reader import MarkdownReader

    registry = ReaderRegistry()
    registry.register(PDFReader())
    registry.register(DOCReader())
    registry.register(DOCXReader())
    registry.register(TextReader())
    registry.register(MarkdownReader())

    return registry
