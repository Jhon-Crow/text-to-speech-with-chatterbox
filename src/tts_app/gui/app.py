"""Main GUI application using CustomTkinter."""

import logging
import threading
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from tts_app.readers import ReaderRegistry
from tts_app.readers.registry import create_default_registry
from tts_app.preprocessors import PreprocessorPipeline, ProcessingContext
from tts_app.preprocessors.pipeline import create_default_pipeline
from tts_app.tts import ChatterboxEngine, TTSConfig

logger = logging.getLogger(__name__)


class TTSApplication(ctk.CTk):
    """Main application window for Text-to-Speech conversion.

    This provides a user-friendly interface for:
    - Selecting input documents (PDF, DOCX, TXT, MD)
    - Configuring TTS options (model, language, voice reference)
    - Setting preprocessing options (ignore footnotes)
    - Converting documents to speech
    """

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        # Configure window
        self.title("Text to Speech with Chatterbox")
        self.geometry("700x600")
        self.minsize(600, 500)

        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Initialize components
        self._reader_registry: ReaderRegistry = create_default_registry()
        self._pipeline: PreprocessorPipeline = create_default_pipeline()
        self._tts_engine: Optional[ChatterboxEngine] = None
        self._processing = False

        # Variables
        self._input_file = ctk.StringVar()
        self._output_file = ctk.StringVar()
        self._voice_reference = ctk.StringVar()
        self._model_type = ctk.StringVar(value="turbo")
        self._language = ctk.StringVar(value="en")
        self._ignore_footnotes = ctk.BooleanVar(value=True)
        self._device = ctk.StringVar(value="auto")

        # Build UI
        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Document to Speech Converter",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # Input file section
        self._create_file_section(
            main_frame,
            "Input Document:",
            self._input_file,
            self._browse_input,
            self._get_input_filetypes()
        )

        # Output file section
        self._create_file_section(
            main_frame,
            "Output Audio File:",
            self._output_file,
            self._browse_output,
            [("WAV files", "*.wav")],
            save=True
        )

        # Voice reference section (optional)
        voice_frame = ctk.CTkFrame(main_frame)
        voice_frame.pack(fill="x", pady=(10, 0))

        voice_label = ctk.CTkLabel(voice_frame, text="Voice Reference (optional):")
        voice_label.pack(anchor="w")

        voice_input_frame = ctk.CTkFrame(voice_frame)
        voice_input_frame.pack(fill="x", pady=(5, 0))

        voice_entry = ctk.CTkEntry(
            voice_input_frame,
            textvariable=self._voice_reference,
            placeholder_text="Select a ~10 second audio file for voice cloning"
        )
        voice_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        voice_btn = ctk.CTkButton(
            voice_input_frame,
            text="Browse",
            command=self._browse_voice_reference,
            width=100
        )
        voice_btn.pack(side="right")

        clear_btn = ctk.CTkButton(
            voice_input_frame,
            text="Clear",
            command=lambda: self._voice_reference.set(""),
            width=60,
            fg_color="gray"
        )
        clear_btn.pack(side="right", padx=(0, 5))

        # Options frame
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=(20, 0))

        options_label = ctk.CTkLabel(
            options_frame,
            text="Options",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_label.pack(anchor="w", pady=(0, 10))

        # Model selection
        model_frame = ctk.CTkFrame(options_frame)
        model_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(model_frame, text="Model:").pack(side="left")

        for model, label in [("turbo", "Turbo (Fast)"), ("standard", "Standard"), ("multilingual", "Multilingual")]:
            rb = ctk.CTkRadioButton(
                model_frame,
                text=label,
                variable=self._model_type,
                value=model,
                command=self._on_model_change
            )
            rb.pack(side="left", padx=(20, 0))

        # Language selection (for multilingual model)
        self._language_frame = ctk.CTkFrame(options_frame)
        self._language_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self._language_frame, text="Language:").pack(side="left")

        languages = [
            ("en", "English"), ("fr", "French"), ("de", "German"),
            ("es", "Spanish"), ("it", "Italian"), ("pt", "Portuguese"),
            ("ru", "Russian"), ("zh", "Chinese"), ("ja", "Japanese"),
            ("ko", "Korean"), ("ar", "Arabic"), ("hi", "Hindi")
        ]

        self._language_menu = ctk.CTkOptionMenu(
            self._language_frame,
            variable=self._language,
            values=[f"{code} - {name}" for code, name in languages],
            command=self._on_language_select
        )
        self._language_menu.pack(side="left", padx=(20, 0))
        self._language_frame.pack_forget()  # Hidden by default

        # Device selection
        device_frame = ctk.CTkFrame(options_frame)
        device_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(device_frame, text="Device:").pack(side="left")

        for device, label in [("auto", "Auto"), ("cuda", "GPU (CUDA)"), ("cpu", "CPU")]:
            rb = ctk.CTkRadioButton(
                device_frame,
                text=label,
                variable=self._device,
                value=device
            )
            rb.pack(side="left", padx=(20, 0))

        # Footnotes option
        footnote_frame = ctk.CTkFrame(options_frame)
        footnote_frame.pack(fill="x", pady=(0, 10))

        self._footnote_checkbox = ctk.CTkCheckBox(
            footnote_frame,
            text="Ignore footnotes (don't read them aloud)",
            variable=self._ignore_footnotes
        )
        self._footnote_checkbox.pack(anchor="w")

        # Progress bar
        self._progress_frame = ctk.CTkFrame(main_frame)
        self._progress_frame.pack(fill="x", pady=(20, 0))

        self._progress_label = ctk.CTkLabel(self._progress_frame, text="Ready")
        self._progress_label.pack(anchor="w")

        self._progress_bar = ctk.CTkProgressBar(self._progress_frame)
        self._progress_bar.pack(fill="x", pady=(5, 0))
        self._progress_bar.set(0)

        # Convert button
        self._convert_btn = ctk.CTkButton(
            main_frame,
            text="Convert to Speech",
            command=self._start_conversion,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self._convert_btn.pack(fill="x", pady=(20, 0))

        # Status bar
        self._status_label = ctk.CTkLabel(
            main_frame,
            text="Select an input file to begin",
            text_color="gray"
        )
        self._status_label.pack(pady=(10, 0))

    def _create_file_section(self, parent, label_text, variable, browse_command, filetypes, save=False):
        """Create a file selection section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(frame, text=label_text)
        label.pack(anchor="w")

        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(fill="x", pady=(5, 0))

        entry = ctk.CTkEntry(input_frame, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn = ctk.CTkButton(
            input_frame,
            text="Browse",
            command=browse_command,
            width=100
        )
        btn.pack(side="right")

    def _get_input_filetypes(self):
        """Get file types for input file dialog."""
        extensions = self._reader_registry.supported_extensions
        patterns = " ".join(f"*{ext}" for ext in extensions)
        return [
            ("Supported documents", patterns),
            ("PDF files", "*.pdf"),
            ("Word documents", "*.doc *.docx"),
            ("Text files", "*.txt"),
            ("Markdown files", "*.md"),
            ("All files", "*.*")
        ]

    def _browse_input(self):
        """Open file dialog for input file."""
        from tkinter import filedialog

        filetypes = self._get_input_filetypes()
        filename = filedialog.askopenfilename(
            title="Select Input Document",
            filetypes=filetypes
        )
        if filename:
            self._input_file.set(filename)
            # Auto-generate output filename
            input_path = Path(filename)
            output_path = input_path.with_suffix(".wav")
            self._output_file.set(str(output_path))
            self._status_label.configure(text=f"Selected: {input_path.name}")

    def _browse_output(self):
        """Open file dialog for output file."""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            title="Save Audio File",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if filename:
            self._output_file.set(filename)

    def _browse_voice_reference(self):
        """Open file dialog for voice reference file."""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Select Voice Reference Audio",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.ogg"),
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self._voice_reference.set(filename)

    def _on_model_change(self):
        """Handle model type change."""
        if self._model_type.get() == "multilingual":
            self._language_frame.pack(fill="x", pady=(0, 10), after=self._language_frame.master.winfo_children()[1])
        else:
            self._language_frame.pack_forget()

    def _on_language_select(self, value):
        """Handle language selection."""
        # Extract language code from "en - English" format
        code = value.split(" - ")[0]
        self._language.set(code)

    def _start_conversion(self):
        """Start the conversion process in a background thread."""
        if self._processing:
            return

        # Validate inputs
        input_file = self._input_file.get().strip()
        output_file = self._output_file.get().strip()

        if not input_file:
            CTkMessagebox(
                title="Error",
                message="Please select an input file.",
                icon="cancel"
            )
            return

        if not output_file:
            CTkMessagebox(
                title="Error",
                message="Please select an output file location.",
                icon="cancel"
            )
            return

        if not Path(input_file).exists():
            CTkMessagebox(
                title="Error",
                message=f"Input file not found: {input_file}",
                icon="cancel"
            )
            return

        # Start conversion in background thread
        self._processing = True
        self._convert_btn.configure(state="disabled", text="Converting...")
        self._progress_bar.set(0)

        thread = threading.Thread(target=self._run_conversion)
        thread.daemon = True
        thread.start()

    def _run_conversion(self):
        """Run the conversion process (in background thread)."""
        try:
            input_path = Path(self._input_file.get())
            output_path = Path(self._output_file.get())

            # Step 1: Read document
            self._update_progress(0.1, "Reading document...")
            content = self._reader_registry.read(input_path)
            logger.info(f"Read document: {content.page_count} pages, {len(content.text)} chars")

            # Step 2: Preprocess text
            self._update_progress(0.2, "Preprocessing text...")
            context = ProcessingContext(
                footnotes=content.footnotes,
                ignore_footnotes=self._ignore_footnotes.get(),
                page_count=content.page_count
            )
            processed_text = self._pipeline.process(content.text, context)
            logger.info(f"Processed text: {len(processed_text)} chars")

            if not processed_text.strip():
                raise ValueError("No text content found in document")

            # Step 3: Initialize TTS engine
            self._update_progress(0.3, "Initializing TTS engine...")
            config = TTSConfig(
                model_type=self._model_type.get(),
                language=self._language.get(),
                voice_reference=Path(self._voice_reference.get()) if self._voice_reference.get() else None,
                device=self._device.get()
            )

            if self._tts_engine is None:
                self._tts_engine = ChatterboxEngine()

            self._tts_engine.initialize(config)

            # Step 4: Synthesize speech
            def progress_callback(current, total, status):
                progress = 0.3 + (0.65 * current / total)
                self._update_progress(progress, f"Synthesizing: {status}")

            result = self._tts_engine.synthesize(
                processed_text,
                output_path,
                progress_callback=progress_callback
            )

            # Complete
            self._update_progress(1.0, "Complete!")
            duration_str = f"{int(result.duration_seconds // 60)}:{int(result.duration_seconds % 60):02d}"

            self.after(0, lambda: CTkMessagebox(
                title="Success",
                message=f"Audio saved to:\n{output_path}\n\nDuration: {duration_str}",
                icon="check"
            ))

        except Exception as e:
            logger.exception("Conversion failed")
            self.after(0, lambda: CTkMessagebox(
                title="Error",
                message=f"Conversion failed:\n{str(e)}",
                icon="cancel"
            ))

        finally:
            self._processing = False
            self.after(0, self._reset_ui)

    def _update_progress(self, value: float, status: str):
        """Update progress bar and status from any thread."""
        self.after(0, lambda: self._progress_bar.set(value))
        self.after(0, lambda: self._progress_label.configure(text=status))
        self.after(0, lambda: self._status_label.configure(text=status))

    def _reset_ui(self):
        """Reset UI after conversion."""
        self._convert_btn.configure(state="normal", text="Convert to Speech")
        self._progress_label.configure(text="Ready")


def run_app():
    """Create and run the application."""
    app = TTSApplication()
    app.mainloop()
