"""Document readers for various file formats."""

from .base import DocumentReader
from .pdf_reader import PDFReader
from .doc_reader import DOCReader
from .docx_reader import DOCXReader
from .text_reader import TextReader
from .markdown_reader import MarkdownReader
from .registry import ReaderRegistry

__all__ = [
    "DocumentReader",
    "PDFReader",
    "DOCReader",
    "DOCXReader",
    "TextReader",
    "MarkdownReader",
    "ReaderRegistry",
]
