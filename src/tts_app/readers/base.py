"""Base document reader interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DocumentContent:
    """Represents extracted content from a document.

    Attributes:
        text: The main text content of the document.
        footnotes: List of footnotes found in the document.
        page_count: Number of pages in the document (if applicable).
        metadata: Additional metadata about the document.
    """
    text: str
    footnotes: list[str] = field(default_factory=list)
    page_count: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class DocumentReader(ABC):
    """Abstract base class for document readers.

    This class defines the interface that all document readers must implement.
    To add support for a new file format, create a subclass that implements
    the `read` method and register it with the ReaderRegistry.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this reader supports.

        Returns:
            List of extensions (e.g., ['.pdf', '.PDF']).
        """
        pass

    @abstractmethod
    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from a document.

        Args:
            file_path: Path to the document file.

        Returns:
            DocumentContent with extracted text and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported.
        """
        pass

    def can_read(self, file_path: Path) -> bool:
        """Check if this reader can read the given file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file extension is supported.
        """
        return file_path.suffix.lower() in [ext.lower() for ext in self.supported_extensions]
