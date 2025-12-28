"""Tests for document readers."""

import pytest
from pathlib import Path
import tempfile

from tts_app.readers import (
    DocumentReader,
    DOCReader,
    TextReader,
    MarkdownReader,
    RTFReader,
    ReaderRegistry,
)
from tts_app.readers.base import DocumentContent
from tts_app.readers.registry import create_default_registry


class TestDocumentContent:
    """Tests for DocumentContent dataclass."""

    def test_create_minimal(self):
        """Test creating content with just text."""
        content = DocumentContent(text="Hello world")
        assert content.text == "Hello world"
        assert content.footnotes == []
        assert content.page_count is None
        assert content.metadata == {}

    def test_create_full(self):
        """Test creating content with all fields."""
        content = DocumentContent(
            text="Main text",
            footnotes=["[1] Note 1"],
            page_count=5,
            metadata={"source": "test.pdf"}
        )
        assert content.text == "Main text"
        assert len(content.footnotes) == 1
        assert content.page_count == 5
        assert content.metadata["source"] == "test.pdf"


class TestTextReader:
    """Tests for TextReader."""

    def test_supported_extensions(self):
        """Test that .txt is supported."""
        reader = TextReader()
        assert ".txt" in reader.supported_extensions
        assert ".TXT" in reader.supported_extensions

    def test_can_read_txt_file(self):
        """Test that reader identifies txt files correctly."""
        reader = TextReader()
        assert reader.can_read(Path("test.txt"))
        assert reader.can_read(Path("test.TXT"))
        assert not reader.can_read(Path("test.pdf"))

    def test_read_utf8_file(self):
        """Test reading UTF-8 encoded file."""
        reader = TextReader()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
            f.write("Hello, World!\nThis is a test.")
            temp_path = Path(f.name)

        try:
            content = reader.read(temp_path)
            assert "Hello, World!" in content.text
            assert "This is a test." in content.text
            assert content.page_count >= 1
        finally:
            temp_path.unlink()

    def test_read_nonexistent_file(self):
        """Test that reading nonexistent file raises error."""
        reader = TextReader()
        with pytest.raises(FileNotFoundError):
            reader.read(Path("/nonexistent/file.txt"))


class TestMarkdownReader:
    """Tests for MarkdownReader."""

    def test_supported_extensions(self):
        """Test that .md is supported."""
        reader = MarkdownReader()
        assert ".md" in reader.supported_extensions
        assert ".markdown" in reader.supported_extensions

    def test_read_markdown_file(self):
        """Test reading markdown file."""
        reader = MarkdownReader()

        md_content = """# Title

This is a paragraph with **bold** and *italic* text.

## Section

- List item 1
- List item 2

[Link text](https://example.com)
"""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as f:
            f.write(md_content)
            temp_path = Path(f.name)

        try:
            content = reader.read(temp_path)
            # Bold/italic markers should be removed
            assert "**" not in content.text
            assert "*" not in content.text
            # Link should be converted to just text
            assert "Link text" in content.text
            assert "https://example.com" not in content.text
        finally:
            temp_path.unlink()

    def test_extract_footnotes(self):
        """Test footnote extraction from markdown."""
        reader = MarkdownReader()

        md_content = """Some text with a footnote[^1].

[^1]: This is the footnote content.
"""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as f:
            f.write(md_content)
            temp_path = Path(f.name)

        try:
            content = reader.read(temp_path)
            assert len(content.footnotes) >= 1
            assert "footnote content" in content.footnotes[0]
        finally:
            temp_path.unlink()


class TestReaderRegistry:
    """Tests for ReaderRegistry."""

    def test_register_and_get_reader(self):
        """Test registering and retrieving a reader."""
        registry = ReaderRegistry()
        reader = TextReader()
        registry.register(reader)

        found = registry.get_reader(Path("test.txt"))
        assert found is reader

    def test_get_reader_not_found(self):
        """Test that None is returned for unsupported format."""
        registry = ReaderRegistry()
        found = registry.get_reader(Path("test.unknown"))
        assert found is None

    def test_supported_extensions(self):
        """Test getting all supported extensions."""
        registry = ReaderRegistry()
        registry.register(TextReader())
        registry.register(MarkdownReader())

        extensions = registry.supported_extensions
        assert ".txt" in extensions
        assert ".md" in extensions

    def test_read_with_registry(self):
        """Test reading file through registry."""
        registry = create_default_registry()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            content = registry.read(temp_path)
            assert content.text == "Test content"
        finally:
            temp_path.unlink()

    def test_read_unsupported_format(self):
        """Test that reading unsupported format raises error."""
        registry = ReaderRegistry()

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                registry.read(temp_path)
        finally:
            temp_path.unlink()


class TestDOCReader:
    """Tests for DOCReader."""

    def test_supported_extensions(self):
        """Test that .doc is supported."""
        reader = DOCReader()
        assert ".doc" in reader.supported_extensions
        assert ".DOC" in reader.supported_extensions

    def test_can_read_doc_file(self):
        """Test that reader identifies doc files correctly."""
        reader = DOCReader()
        assert reader.can_read(Path("test.doc"))
        assert reader.can_read(Path("test.DOC"))
        assert not reader.can_read(Path("test.docx"))

    def test_read_nonexistent_file(self):
        """Test that reading nonexistent file raises error."""
        reader = DOCReader()
        with pytest.raises(FileNotFoundError):
            reader.read(Path("/nonexistent/file.doc"))


class TestRTFReader:
    """Tests for RTFReader."""

    def test_supported_extensions(self):
        """Test that .rtf is supported."""
        reader = RTFReader()
        assert ".rtf" in reader.supported_extensions
        assert ".RTF" in reader.supported_extensions

    def test_can_read_rtf_file(self):
        """Test that reader identifies rtf files correctly."""
        reader = RTFReader()
        assert reader.can_read(Path("test.rtf"))
        assert reader.can_read(Path("test.RTF"))
        assert not reader.can_read(Path("test.txt"))

    def test_read_nonexistent_file(self):
        """Test that reading nonexistent file raises error."""
        reader = RTFReader()
        with pytest.raises(FileNotFoundError):
            reader.read(Path("/nonexistent/file.rtf"))


class TestDefaultRegistry:
    """Tests for the default registry."""

    def test_default_registry_has_readers(self):
        """Test that default registry has all expected readers."""
        registry = create_default_registry()
        extensions = registry.supported_extensions

        # Should support all required formats (PDF, DOC, DOCX, TXT, MD, RTF)
        assert any(".pdf" in ext.lower() for ext in extensions)
        assert any(".doc" == ext.lower() for ext in extensions)  # DOC (legacy)
        assert any(".docx" in ext.lower() for ext in extensions)
        assert any(".txt" in ext.lower() for ext in extensions)
        assert any(".md" in ext.lower() for ext in extensions)
        assert any(".rtf" in ext.lower() for ext in extensions)
