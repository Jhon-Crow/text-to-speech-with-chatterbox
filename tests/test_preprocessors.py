"""Tests for text preprocessors."""

import pytest

from tts_app.preprocessors import (
    TextPreprocessor,
    PageNumberRemover,
    FootnoteHandler,
    SymbolConverter,
    PreprocessorPipeline,
)
from tts_app.preprocessors.base import ProcessingContext
from tts_app.preprocessors.pipeline import create_default_pipeline


class TestProcessingContext:
    """Tests for ProcessingContext."""

    def test_create_minimal(self):
        """Test creating context with minimal args."""
        ctx = ProcessingContext(footnotes=[])
        assert ctx.footnotes == []
        assert ctx.ignore_footnotes is False
        assert ctx.page_count is None

    def test_create_full(self):
        """Test creating context with all args."""
        ctx = ProcessingContext(
            footnotes=["[1] Note"],
            ignore_footnotes=True,
            page_count=10
        )
        assert len(ctx.footnotes) == 1
        assert ctx.ignore_footnotes is True
        assert ctx.page_count == 10


class TestPageNumberRemover:
    """Tests for PageNumberRemover."""

    def test_name(self):
        """Test processor name."""
        processor = PageNumberRemover()
        assert processor.name == "page_number_remover"

    def test_remove_standalone_numbers(self):
        """Test removing standalone page numbers."""
        processor = PageNumberRemover()
        ctx = ProcessingContext(footnotes=[], page_count=50)

        text = "Some text here.\n\n42\n\nMore text here."
        result = processor.process(text, ctx)

        assert "Some text here." in result
        assert "More text here." in result
        # The standalone "42" should be removed
        lines = [line.strip() for line in result.split("\n") if line.strip()]
        assert "42" not in lines

    def test_remove_page_x_format(self):
        """Test removing 'Page X' format."""
        processor = PageNumberRemover()
        ctx = ProcessingContext(footnotes=[], page_count=50)

        text = "Some text.\nPage 15\nMore text."
        result = processor.process(text, ctx)

        assert "Some text." in result
        assert "More text." in result
        assert "Page 15" not in result

    def test_remove_page_x_of_y_format(self):
        """Test removing 'Page X of Y' format."""
        processor = PageNumberRemover()
        ctx = ProcessingContext(footnotes=[], page_count=50)

        text = "Some text.\nPage 5 of 20\nMore text."
        result = processor.process(text, ctx)

        assert "Page 5 of 20" not in result

    def test_remove_centered_page_numbers(self):
        """Test removing centered page numbers like '- 42 -'."""
        processor = PageNumberRemover()
        ctx = ProcessingContext(footnotes=[], page_count=50)

        text = "Some text.\n- 42 -\nMore text."
        result = processor.process(text, ctx)

        assert "- 42 -" not in result

    def test_keep_regular_numbers(self):
        """Test that regular numbers in text are kept."""
        processor = PageNumberRemover()
        ctx = ProcessingContext(footnotes=[], page_count=50)

        text = "The year was 1984. There were 100 people."
        result = processor.process(text, ctx)

        assert "1984" in result
        assert "100" in result


class TestFootnoteHandler:
    """Tests for FootnoteHandler."""

    def test_name(self):
        """Test processor name."""
        processor = FootnoteHandler()
        assert processor.name == "footnote_handler"

    def test_remove_bracket_footnotes(self):
        """Test removing [1] style footnotes when ignored."""
        processor = FootnoteHandler()
        ctx = ProcessingContext(footnotes=[], ignore_footnotes=True)

        text = "This is some text[1] with a footnote[2]."
        result = processor.process(text, ctx)

        assert "[1]" not in result
        assert "[2]" not in result
        assert "This is some text with a footnote." in result

    def test_remove_caret_footnotes(self):
        """Test removing ^1 style footnotes when ignored."""
        processor = FootnoteHandler()
        ctx = ProcessingContext(footnotes=[], ignore_footnotes=True)

        text = "This is some text^1 with a footnote."
        result = processor.process(text, ctx)

        assert "^1" not in result

    def test_insert_footnotes_inline(self):
        """Test inserting footnote content inline when not ignored."""
        processor = FootnoteHandler()
        ctx = ProcessingContext(
            footnotes=["[1] This is footnote one."],
            ignore_footnotes=False
        )

        text = "This is some text[1] with a footnote."
        result = processor.process(text, ctx)

        assert "Footnote:" in result
        assert "This is footnote one" in result

    def test_multiple_footnotes_inline(self):
        """Test inserting multiple footnotes inline."""
        processor = FootnoteHandler()
        ctx = ProcessingContext(
            footnotes=["[1] First note.", "[2] Second note."],
            ignore_footnotes=False
        )

        text = "Text with first[1] and second[2] references."
        result = processor.process(text, ctx)

        assert "First note" in result
        assert "Second note" in result


class TestPreprocessorPipeline:
    """Tests for PreprocessorPipeline."""

    def test_add_and_process(self):
        """Test adding preprocessors and processing text."""
        pipeline = PreprocessorPipeline()
        pipeline.add(PageNumberRemover())

        ctx = ProcessingContext(footnotes=[], page_count=10)
        text = "Text\n\n5\n\nMore text"
        result = pipeline.process(text, ctx)

        # Page number should be removed
        lines = [line.strip() for line in result.split("\n") if line.strip()]
        assert "5" not in lines

    def test_chain_preprocessors(self):
        """Test chaining multiple preprocessors."""
        pipeline = PreprocessorPipeline()
        pipeline.add(PageNumberRemover())
        pipeline.add(FootnoteHandler())

        ctx = ProcessingContext(footnotes=[], ignore_footnotes=True, page_count=10)
        text = "Text[1]\n\n5\n\nMore text[2]"
        result = pipeline.process(text, ctx)

        # Both page numbers and footnote references should be removed
        assert "[1]" not in result
        assert "[2]" not in result

    def test_remove_preprocessor(self):
        """Test removing a preprocessor by name."""
        pipeline = PreprocessorPipeline()
        pipeline.add(PageNumberRemover())
        pipeline.add(FootnoteHandler())

        assert len(pipeline.preprocessors) == 2

        removed = pipeline.remove("page_number_remover")
        assert removed is True
        assert len(pipeline.preprocessors) == 1

    def test_normalize_whitespace(self):
        """Test that pipeline normalizes whitespace."""
        pipeline = PreprocessorPipeline()
        ctx = ProcessingContext(footnotes=[])

        text = "Line 1\n\n\n\n\nLine 2"
        result = pipeline.process(text, ctx)

        # Multiple newlines should be reduced
        assert "\n\n\n" not in result


class TestSymbolConverter:
    """Tests for SymbolConverter."""

    def test_name(self):
        """Test processor name."""
        processor = SymbolConverter()
        assert processor.name == "symbol_converter"

    def test_convert_equals_in_equation(self):
        """Test converting equals sign in equations."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "The formula is x = 5"
        result = processor.process(text, ctx)

        assert "equals" in result.lower()
        assert " = " not in result

    def test_convert_numbered_list_period(self):
        """Test converting numbered lists with periods."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "1. First item\n2. Second item\n3. Third item"
        result = processor.process(text, ctx)

        assert "Point 1" in result
        assert "Point 2" in result
        assert "Point 3" in result

    def test_convert_numbered_list_parenthesis(self):
        """Test converting numbered lists with parentheses."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "1) First item\n2) Second item"
        result = processor.process(text, ctx)

        # Parenthesis-style should just use the number
        assert "1." in result
        assert "2." in result

    def test_convert_percentage(self):
        """Test converting percentage symbol."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "The growth was 50%"
        result = processor.process(text, ctx)

        assert "percent" in result.lower()
        assert "%" not in result

    def test_convert_currency(self):
        """Test converting currency symbols."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "The price is $100"
        result = processor.process(text, ctx)

        assert "dollars" in result.lower()

    def test_convert_ampersand(self):
        """Test converting ampersand to 'and'."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "Salt & pepper"
        result = processor.process(text, ctx)

        assert " and " in result.lower()
        assert "&" not in result

    def test_convert_hash_number(self):
        """Test converting hash with number."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "Issue #42"
        result = processor.process(text, ctx)

        assert "number 42" in result.lower()
        assert "#" not in result

    def test_convert_arrow(self):
        """Test converting arrow symbols."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "Go → forward"
        result = processor.process(text, ctx)

        assert "arrow" in result.lower()

    def test_preserve_hyphens_in_words(self):
        """Test that hyphens in compound words are preserved."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[])

        text = "This is a well-known fact"
        result = processor.process(text, ctx)

        # Hyphens in compound words should not be changed
        assert "well-known" in result or "well known" in result


class TestSymbolConverterLanguageAware:
    """Tests for language-aware symbol conversion."""

    def test_russian_text_uses_russian_symbols(self):
        """Test that Russian text uses Russian symbol words."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "Цена $100"
        result = processor.process(text, ctx)

        # Should use Russian "долларов" instead of English "dollars"
        assert "долларов" in result

    def test_russian_text_uses_russian_equals(self):
        """Test that Russian text uses Russian 'равно' for equals."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "x = 5"
        result = processor.process(text, ctx)

        # Should use Russian "равно" instead of English "equals"
        assert "равно" in result

    def test_russian_text_uses_russian_percent(self):
        """Test that Russian text uses Russian 'процентов' for percent."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "Рост составил 50%"
        result = processor.process(text, ctx)

        # Should use Russian "процентов" instead of English "percent"
        assert "процентов" in result

    def test_russian_numbered_list(self):
        """Test that Russian text uses Russian 'Пункт' for list items."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "1. Первый пункт\n2. Второй пункт"
        result = processor.process(text, ctx)

        # Should use Russian "Пункт" instead of English "Point"
        assert "Пункт 1" in result
        assert "Пункт 2" in result

    def test_english_text_uses_english_symbols(self):
        """Test that English text uses English symbol words."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="en")

        text = "Price is $100"
        result = processor.process(text, ctx)

        assert "dollars" in result

    def test_auto_detect_russian_from_text(self):
        """Test that symbol converter auto-detects Russian text."""
        processor = SymbolConverter()
        # No language specified in context, should auto-detect
        ctx = ProcessingContext(footnotes=[])

        text = "Привет мир! Цена $100"
        result = processor.process(text, ctx)

        # Should detect Russian and use Russian "долларов"
        assert "долларов" in result

    def test_auto_detect_english_from_text(self):
        """Test that symbol converter auto-detects English text."""
        processor = SymbolConverter()
        # No language specified in context, should auto-detect
        ctx = ProcessingContext(footnotes=[])

        text = "Hello world! Price is $100"
        result = processor.process(text, ctx)

        # Should detect English and use English "dollars"
        assert "dollars" in result

    def test_russian_ampersand(self):
        """Test Russian ampersand conversion."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "Соль & перец"
        result = processor.process(text, ctx)

        assert " и " in result

    def test_russian_number_hash(self):
        """Test Russian number hash conversion."""
        processor = SymbolConverter()
        ctx = ProcessingContext(footnotes=[], language="ru")

        text = "Задача #42"
        result = processor.process(text, ctx)

        assert "номер" in result


class TestDefaultPipeline:
    """Tests for the default pipeline."""

    def test_default_pipeline_has_processors(self):
        """Test that default pipeline has expected processors."""
        pipeline = create_default_pipeline()

        names = pipeline.preprocessors
        assert "page_number_remover" in names
        assert "footnote_handler" in names
        assert "symbol_converter" in names
