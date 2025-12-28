"""Base text preprocessor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessingContext:
    """Context information for text processing.

    Attributes:
        footnotes: List of footnotes from the document.
        ignore_footnotes: Whether to remove footnote references.
        page_count: Number of pages in the document.
    """
    footnotes: list[str]
    ignore_footnotes: bool = False
    page_count: Optional[int] = None


class TextPreprocessor(ABC):
    """Abstract base class for text preprocessors.

    Text preprocessors transform text to prepare it for TTS.
    They can remove page numbers, handle footnotes, normalize
    whitespace, etc.

    To add a new preprocessor, create a subclass that implements
    the `process` method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the preprocessor name for identification."""
        pass

    @abstractmethod
    def process(self, text: str, context: ProcessingContext) -> str:
        """Process the text and return the result.

        Args:
            text: The text to process.
            context: Processing context with additional information.

        Returns:
            The processed text.
        """
        pass

    @property
    def enabled(self) -> bool:
        """Check if this preprocessor is enabled.

        Returns:
            True by default. Override to add conditional logic.
        """
        return True
