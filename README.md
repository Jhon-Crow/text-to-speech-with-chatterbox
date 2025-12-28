# Text to Speech with Chatterbox

A desktop application that converts documents (PDF, DOC, DOCX, TXT, MD) to speech using [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) by Resemble AI.

## Features

- **Multiple input formats**: PDF, DOC, DOCX, TXT, and Markdown files
- **Chatterbox TTS models**:
  - **Turbo**: Fast, English-only (350M parameters)
  - **Standard**: English with CFG tuning (500M parameters)
  - **Multilingual**: 23+ languages (500M parameters)
- **Voice cloning**: Use a reference audio file to clone voices
- **Smart text preprocessing**:
  - Automatic page number removal
  - Optional footnote handling (ignore or read inline)
- **GPU acceleration**: CUDA support for faster generation
- **Extensible architecture**: Easy to add new file formats or TTS engines

## Installation

### Download Pre-built Windows Executable (Recommended)

**No Python installation required!**

1. Go to the [Releases page](https://github.com/Jhon-Crow/text-to-speech-with-chatterbox/releases)
2. Download `tts_chatterbox_windows.zip` from the latest release
3. Extract the zip file to a folder
4. Run `tts_chatterbox.exe`

**Requirements for the executable:**
- Windows 10 or later
- NVIDIA GPU with CUDA (recommended) or CPU

### Install from Source (for developers)

**Requirements:**
- Python 3.10 or higher
- NVIDIA GPU with CUDA (recommended) or CPU

```bash
# Clone the repository
git clone https://github.com/Jhon-Crow/text-to-speech-with-chatterbox.git
cd text-to-speech-with-chatterbox

# Install the package
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### Build Windows Executable (for developers)

If you want to build the executable yourself:

```bash
# Install with dev dependencies
pip install -e .[dev]

# Build the executable
pyinstaller tts_chatterbox.spec

# The executable will be in dist/tts_chatterbox/
```

Or simply run `build.bat` on Windows.

> **Note:** Pre-built executables are available on the [Releases page](https://github.com/Jhon-Crow/text-to-speech-with-chatterbox/releases).

## Usage

### GUI Application

Run the application:

```bash
tts-chatterbox
```

Or run directly:

```bash
python -m tts_app.main
```

### Python API

```python
from pathlib import Path
from tts_app.readers.registry import create_default_registry
from tts_app.preprocessors.pipeline import create_default_pipeline
from tts_app.preprocessors.base import ProcessingContext
from tts_app.tts import ChatterboxEngine, TTSConfig

# Read a document
registry = create_default_registry()
content = registry.read(Path("document.pdf"))

# Preprocess the text
pipeline = create_default_pipeline()
context = ProcessingContext(
    footnotes=content.footnotes,
    ignore_footnotes=True,  # Set to False to read footnotes inline
    page_count=content.page_count
)
processed_text = pipeline.process(content.text, context)

# Convert to speech
engine = ChatterboxEngine()
config = TTSConfig(
    model_type="turbo",  # or "standard" or "multilingual"
    language="en",
    device="auto"  # or "cuda" or "cpu"
)
engine.initialize(config)

result = engine.synthesize(processed_text, Path("output.wav"))
print(f"Audio saved: {result.audio_path} ({result.duration_seconds:.1f}s)")
```

## Architecture

The application is designed with extensibility in mind:

```
src/tts_app/
├── readers/           # Document readers (PDF, DOC, DOCX, TXT, MD)
│   ├── base.py       # Abstract DocumentReader class
│   ├── registry.py   # Reader registry for dynamic format support
│   ├── pdf_reader.py
│   ├── doc_reader.py
│   ├── docx_reader.py
│   ├── text_reader.py
│   └── markdown_reader.py
├── preprocessors/     # Text preprocessing pipeline
│   ├── base.py       # Abstract TextPreprocessor class
│   ├── pipeline.py   # Preprocessing pipeline
│   ├── page_numbers.py
│   └── footnotes.py
├── tts/              # TTS engine wrappers
│   ├── base.py       # Abstract TTSEngine class
│   └── chatterbox.py # Chatterbox TTS implementation
├── gui/              # GUI application
│   └── app.py        # CustomTkinter application
└── main.py           # Entry point
```

### Adding a New Document Format

1. Create a new reader class inheriting from `DocumentReader`:

```python
from tts_app.readers.base import DocumentReader, DocumentContent

class MyFormatReader(DocumentReader):
    @property
    def supported_extensions(self) -> list[str]:
        return [".myformat"]

    def read(self, file_path: Path) -> DocumentContent:
        # Your implementation here
        return DocumentContent(text=..., footnotes=[])
```

2. Register it with the registry:

```python
registry.register(MyFormatReader())
```

### Adding a New Preprocessor

1. Create a preprocessor inheriting from `TextPreprocessor`:

```python
from tts_app.preprocessors.base import TextPreprocessor, ProcessingContext

class MyPreprocessor(TextPreprocessor):
    @property
    def name(self) -> str:
        return "my_preprocessor"

    def process(self, text: str, context: ProcessingContext) -> str:
        # Your processing here
        return modified_text
```

2. Add it to the pipeline:

```python
pipeline.add(MyPreprocessor())
```

## Supported Languages (Multilingual Model)

Arabic (ar), Danish (da), German (de), Greek (el), English (en), Spanish (es), Finnish (fi), French (fr), Hebrew (he), Hindi (hi), Italian (it), Japanese (ja), Korean (ko), Malay (ms), Dutch (nl), Norwegian (no), Polish (pl), Portuguese (pt), Russian (ru), Swedish (sv), Swahili (sw), Turkish (tr), Chinese (zh)

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Running Tests with Coverage

```bash
pytest tests/ -v --cov=tts_app --cov-report=html
```

## License

MIT License

## Acknowledgments

- [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) by Resemble AI
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern GUI
- [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF text extraction
- [olefile](https://github.com/decalage2/olefile) for DOC (legacy Word) support
- [python-docx](https://github.com/python-openxml/python-docx) for DOCX support
