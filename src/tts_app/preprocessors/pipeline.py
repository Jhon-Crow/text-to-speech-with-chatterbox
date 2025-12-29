"""Preprocessing pipeline for chaining multiple preprocessors."""

from typing import Optional

from .base import TextPreprocessor, ProcessingContext
from .page_numbers import PageNumberRemover
from .footnotes import FootnoteHandler
from .symbols import SymbolConverter


class PreprocessorPipeline:
    """Pipeline for running multiple text preprocessors in sequence.

    This allows chaining preprocessors together for comprehensive
    text cleaning before TTS conversion.

    Example:
        >>> pipeline = PreprocessorPipeline()
        >>> pipeline.add(PageNumberRemover())
        >>> pipeline.add(FootnoteHandler())
        >>> cleaned = pipeline.process(text, context)
    """

    def __init__(self):
        """Initialize an empty pipeline."""
        self._preprocessors: list[TextPreprocessor] = []

    def add(self, preprocessor: TextPreprocessor) -> "PreprocessorPipeline":
        """Add a preprocessor to the pipeline.

        Args:
            preprocessor: The preprocessor to add.

        Returns:
            Self for method chaining.
        """
        self._preprocessors.append(preprocessor)
        return self

    def remove(self, name: str) -> bool:
        """Remove a preprocessor by name.

        Args:
            name: The name of the preprocessor to remove.

        Returns:
            True if a preprocessor was removed.
        """
        original_length = len(self._preprocessors)
        self._preprocessors = [p for p in self._preprocessors if p.name != name]
        return len(self._preprocessors) < original_length

    def process(self, text: str, context: ProcessingContext) -> str:
        """Run all preprocessors on the text.

        Args:
            text: The text to process.
            context: Processing context.

        Returns:
            The processed text after all preprocessors have run.
        """
        result = text

        for preprocessor in self._preprocessors:
            if preprocessor.enabled:
                result = preprocessor.process(result, context)

        # Final cleanup: normalize whitespace
        result = self._normalize_whitespace(result)

        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        Args:
            text: The text to normalize.

        Returns:
            Text with normalized whitespace.
        """
        import re

        # Replace multiple spaces with single space
        result = re.sub(r'[ \t]+', ' ', text)

        # Replace more than 2 consecutive newlines with just 2
        result = re.sub(r'\n{3,}', '\n\n', result)

        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in result.split('\n')]
        result = '\n'.join(lines)

        # Strip overall
        return result.strip()

    @property
    def preprocessors(self) -> list[str]:
        """Get names of all preprocessors in the pipeline.

        Returns:
            List of preprocessor names.
        """
        return [p.name for p in self._preprocessors]


def create_default_pipeline() -> PreprocessorPipeline:
    """Create a pipeline with default preprocessors.

    Returns:
        A pipeline with page number, footnote, and symbol handlers.
    """
    pipeline = PreprocessorPipeline()
    pipeline.add(PageNumberRemover())
    pipeline.add(FootnoteHandler())
    pipeline.add(SymbolConverter())
    return pipeline
