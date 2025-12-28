"""Markdown file reader."""

import re
from pathlib import Path

from .base import DocumentReader, DocumentContent


class MarkdownReader(DocumentReader):
    """Reader for Markdown files.

    This reader handles .md files and extracts plain text
    while preserving footnotes from markdown syntax.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported markdown extensions."""
        return [".md", ".MD", ".markdown", ".MARKDOWN"]

    def read(self, file_path: Path) -> DocumentContent:
        """Read and extract content from a markdown file.

        Args:
            file_path: Path to the markdown file.

        Returns:
            DocumentContent with extracted text and footnotes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be decoded.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
            except Exception as e:
                raise ValueError(f"Could not decode markdown file: {e}") from e

        # Extract footnotes before converting
        footnotes = self._extract_footnotes(text)

        # Convert markdown to plain text
        plain_text = self._markdown_to_text(text)

        # Estimate page count
        estimated_pages = max(1, len(plain_text) // 3000)

        return DocumentContent(
            text=plain_text,
            footnotes=footnotes,
            page_count=estimated_pages,
            metadata={"source": str(file_path), "format": "markdown"}
        )

    def _extract_footnotes(self, text: str) -> list[str]:
        """Extract footnotes from markdown text.

        Markdown footnotes follow the pattern:
        [^1]: This is a footnote.

        Args:
            text: The markdown text.

        Returns:
            List of footnote texts.
        """
        footnotes = []

        # Match markdown footnote definitions: [^id]: content
        pattern = r'\[\^(\d+)\]:\s*(.+?)(?=\n\[\^|\n\n|\Z)'
        matches = re.findall(pattern, text, re.DOTALL)

        for ref_id, content in matches:
            # Clean up the content
            clean_content = " ".join(content.split())
            footnotes.append(f"[{ref_id}] {clean_content}")

        return footnotes

    def _markdown_to_text(self, markdown: str) -> str:
        """Convert markdown to plain text.

        This removes markdown formatting while preserving the text content.

        Args:
            markdown: The markdown text.

        Returns:
            Plain text with markdown formatting removed.
        """
        text = markdown

        # Remove footnote references [^1] from text
        text = re.sub(r'\[\^\d+\]', '', text)

        # Remove footnote definitions
        text = re.sub(r'\[\^\d+\]:\s*.+?(?=\n\[\^|\n\n|\Z)', '', text, flags=re.DOTALL)

        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', lambda m: m.group(0)[1:-1], text)

        # Remove images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)

        # Convert links [text](url) to just text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Remove emphasis markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # italic
        text = re.sub(r'__([^_]+)__', r'\1', text)  # bold
        text = re.sub(r'_([^_]+)_', r'\1', text)  # italic

        # Remove headers but keep text
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Remove list markers but keep text
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Remove blockquote markers
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text
