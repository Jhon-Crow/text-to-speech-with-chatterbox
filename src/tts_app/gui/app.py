"""Main GUI application using CustomTkinter."""

import logging
import threading
import traceback
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


class SuccessDialog(ctk.CTkToplevel):
    """Custom success dialog with Open File Location button.

    This dialog displays a success message and provides buttons to open
    the file location in the file explorer.
    """

    def __init__(self, parent, title: str, message: str, file_path: Path):
        """Initialize the success dialog.

        Args:
            parent: Parent window.
            title: Dialog title.
            message: Success message.
            file_path: Path to the generated file.
        """
        super().__init__(parent)

        self._file_path = file_path

        self.title(title)
        self.geometry("450x200")
        self.minsize(400, 180)
        self.transient(parent)
        self.grab_set()

        # Main frame with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Success icon and title
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        success_label = ctk.CTkLabel(
            title_frame,
            text="Success",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#55AA55"
        )
        success_label.pack(side="left")

        # Message
        message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        message_label.pack(fill="x", pady=(0, 15))

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        # Open File Location button
        open_location_btn = ctk.CTkButton(
            button_frame,
            text="Open File Location",
            command=self._open_file_location,
            width=140
        )
        open_location_btn.pack(side="left", padx=(0, 10))

        # OK button
        ok_btn = ctk.CTkButton(
            button_frame,
            text="OK",
            command=self.destroy,
            width=80
        )
        ok_btn.pack(side="right")

        # Center the dialog on parent
        self.update_idletasks()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center this dialog on the parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()

        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self.geometry(f"+{x}+{y}")

    def _open_file_location(self):
        """Open the file's directory in the system file explorer."""
        import platform
        import subprocess

        folder_path = self._file_path.parent

        try:
            system = platform.system()
            if system == "Windows":
                # On Windows, use explorer with /select to highlight the file
                subprocess.run(["explorer", "/select,", str(self._file_path)])
            elif system == "Darwin":
                # On macOS, use open command with -R to reveal the file
                subprocess.run(["open", "-R", str(self._file_path)])
            else:
                # On Linux, use xdg-open to open the folder
                subprocess.run(["xdg-open", str(folder_path)])
        except Exception as e:
            logger.warning(f"Failed to open file location: {e}")
            # Fall back to showing a message
            CTkMessagebox(
                master=self,
                title="Info",
                message=f"File is located at:\n{folder_path}",
                icon="info",
                width=400
            )


class ErrorDialog(ctk.CTkToplevel):
    """Custom error dialog with copy button for error message.

    This dialog displays an error message and provides a button to copy
    the full error text to the clipboard.
    """

    def __init__(self, parent, title: str, message: str, full_traceback: str = ""):
        """Initialize the error dialog.

        Args:
            parent: Parent window.
            title: Dialog title.
            message: Short error message.
            full_traceback: Full traceback for copying (optional).
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("500x300")
        self.minsize(400, 200)
        self.transient(parent)
        self.grab_set()

        # Store the full error text for copying
        self._error_text = f"{message}\n\n{full_traceback}" if full_traceback else message

        # Main frame with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Error icon and title
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        error_label = ctk.CTkLabel(
            title_frame,
            text="❌ Error",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FF5555"
        )
        error_label.pack(side="left")

        # Error message in scrollable text
        text_frame = ctk.CTkFrame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(0, 15))

        self._error_textbox = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self._error_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        self._error_textbox.insert("1.0", self._error_text)
        self._error_textbox.configure(state="disabled")

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        # Copy button
        copy_btn = ctk.CTkButton(
            button_frame,
            text="📋 Copy Error",
            command=self._copy_to_clipboard,
            width=120
        )
        copy_btn.pack(side="left", padx=(0, 10))

        # OK button
        ok_btn = ctk.CTkButton(
            button_frame,
            text="OK",
            command=self.destroy,
            width=80
        )
        ok_btn.pack(side="right")

        # Center the dialog on parent
        self.update_idletasks()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center this dialog on the parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()

        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self.geometry(f"+{x}+{y}")

    def _copy_to_clipboard(self):
        """Copy the error text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self._error_text)

        # Show feedback
        CTkMessagebox(
            master=self,
            title="Copied",
            message="Error text copied to clipboard!",
            icon="check",
            width=300
        )


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
        self.geometry("700x700")
        self.minsize(600, 500)

        # Set appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Initialize components
        self._reader_registry: ReaderRegistry = create_default_registry()
        self._pipeline: PreprocessorPipeline = create_default_pipeline()
        self._tts_engine: Optional[ChatterboxEngine] = None
        self._processing = False
        self._cancel_requested = False  # Flag to signal cancellation
        self._progress_animation_id = None  # Track progress bar animation
        self._button_animation_id = None  # Track button ellipsis animation
        self._ellipsis_state = 0  # Current ellipsis state (0-3)

        # Variables
        self._input_file = ctk.StringVar()
        self._output_file = ctk.StringVar()
        self._voice_reference = ctk.StringVar()
        self._model_type = ctk.StringVar(value="turbo")
        self._language = ctk.StringVar(value="en")
        self._ignore_footnotes = ctk.BooleanVar(value=True)
        self._device = ctk.StringVar(value="auto")
        self._hf_token = ctk.StringVar()

        # Build UI
        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Scrollable main container
        self._scrollable_frame = ctk.CTkScrollableFrame(self)
        self._scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Main frame inside scrollable area
        main_frame = ctk.CTkFrame(self._scrollable_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

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
            ("auto", "Auto-detect"),
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

        # Language auto-detect help text
        self._language_help = ctk.CTkLabel(
            self._language_frame,
            text="Auto-detect works best for single-language texts",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self._language_help.pack(side="left", padx=(10, 0))

        # Device selection
        device_frame = ctk.CTkFrame(options_frame)
        device_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(device_frame, text="Device:").pack(side="left")

        # Auto-detect includes: NVIDIA CUDA, AMD ROCm, Apple MPS
        for device, label in [("auto", "Auto (GPU/CPU)"), ("cuda", "GPU"), ("cpu", "CPU")]:
            rb = ctk.CTkRadioButton(
                device_frame,
                text=label,
                variable=self._device,
                value=device
            )
            rb.pack(side="left", padx=(20, 0))

        # Device help text (more detailed with AMD information)
        device_help = ctk.CTkLabel(
            options_frame,
            text="Auto detects: NVIDIA (CUDA), AMD (ROCm on Linux), Apple (MPS). Note: AMD GPUs on Windows use CPU.",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        device_help.pack(anchor="w", padx=(80, 0))

        # CPU performance note
        cpu_note = ctk.CTkLabel(
            options_frame,
            text="CPU mode is slower (5-15 min/chunk). For faster CPU: use Turbo model, reduce text length.",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        cpu_note.pack(anchor="w", padx=(80, 0))

        # HuggingFace Token section
        hf_token_frame = ctk.CTkFrame(options_frame)
        hf_token_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(hf_token_frame, text="HF Token (optional):").pack(side="left")

        self._hf_token_entry = ctk.CTkEntry(
            hf_token_frame,
            textvariable=self._hf_token,
            placeholder_text="Enter HuggingFace token for Turbo model",
            show="*",
            width=300
        )
        self._hf_token_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # HF Token help text
        hf_token_help = ctk.CTkLabel(
            options_frame,
            text="Required for Turbo model. Get token at: huggingface.co/settings/tokens",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        hf_token_help.pack(anchor="w", padx=(80, 0), pady=(2, 10))

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

        # Button frame for convert and cancel buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))

        # Convert button
        self._convert_btn = ctk.CTkButton(
            button_frame,
            text="Convert to Speech",
            command=self._start_conversion,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self._convert_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Cancel button (hidden by default)
        self._cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_conversion,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#CC4444",
            hover_color="#AA3333"
        )
        self._cancel_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self._cancel_btn.pack_forget()  # Hidden by default

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
            ("Rich Text files", "*.rtf"),
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
        self._cancel_requested = False
        self._convert_btn.configure(state="disabled", text="Converting")
        self._cancel_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))  # Show cancel button
        self._progress_bar.set(0)
        self._start_button_animation()  # Start ellipsis animation

        thread = threading.Thread(target=self._run_conversion)
        thread.daemon = True
        thread.start()

    def _cancel_conversion(self):
        """Request cancellation of the ongoing conversion."""
        if self._processing and not self._cancel_requested:
            self._cancel_requested = True
            self._cancel_btn.configure(state="disabled", text="Cancelling")
            self._update_progress(0, "Cancelling... (saving generated audio)")
            logger.info("Cancellation requested by user")

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
            model_name = self._model_type.get()
            device_name = self._device.get()

            # Handle language auto-detection for multilingual model
            language = self._language.get()
            if model_name == "multilingual" and language == "auto":
                self._update_progress(0.22, "Detecting language...")
                from tts_app.utils.language_detection import detect_primary_language, get_language_name
                language = detect_primary_language(processed_text)
                detected_name = get_language_name(language)
                logger.info(f"Auto-detected language: {language} ({detected_name})")
                self._update_progress(0.23, f"Detected language: {detected_name}")

            self._update_progress(0.25, f"Initializing {model_name} model on {device_name}...")

            # Start indeterminate animation for model download/initialization
            # This provides visual feedback that something is happening during long waits
            self.after(0, self._start_indeterminate_progress)
            self.after(0, lambda: self._progress_label.configure(
                text=f"Downloading/loading {model_name} model (may take several minutes on first run)..."
            ))

            config = TTSConfig(
                model_type=model_name,
                language=language,
                voice_reference=Path(self._voice_reference.get()) if self._voice_reference.get() else None,
                device=device_name,
                hf_token=self._hf_token.get() if self._hf_token.get() else None
            )

            if self._tts_engine is None:
                self._tts_engine = ChatterboxEngine()

            self._tts_engine.initialize(config)

            # Stop indeterminate animation and switch back to determinate progress
            self.after(0, self._stop_indeterminate_progress)
            self._update_progress(0.35, "TTS engine ready, starting synthesis...")

            # Step 4: Synthesize speech
            def progress_callback(current, total, status, estimated_remaining):
                progress = 0.35 + (0.60 * current / total)
                # Format estimated time remaining
                time_str = ""
                if estimated_remaining is not None and estimated_remaining > 0:
                    mins = int(estimated_remaining // 60)
                    secs = int(estimated_remaining % 60)
                    if mins > 0:
                        time_str = f" (~{mins}m {secs}s remaining)"
                    else:
                        time_str = f" (~{secs}s remaining)"
                self._update_progress(progress, f"Synthesizing: {status}{time_str}")

            def cancel_check():
                return self._cancel_requested

            result = self._tts_engine.synthesize(
                processed_text,
                output_path,
                progress_callback=progress_callback,
                cancel_check=cancel_check
            )

            # Handle result (complete or cancelled with partial)
            duration_str = f"{int(result.duration_seconds // 60)}:{int(result.duration_seconds % 60):02d}"

            if result.was_cancelled:
                # Partial result from cancellation
                self._update_progress(1.0, f"Cancelled - partial audio saved ({result.chunks_completed}/{result.chunks_total} chunks)")
                self.after(0, lambda: SuccessDialog(
                    self,
                    title="Conversion Cancelled",
                    message=f"Partial audio saved to:\n{output_path}\n\n"
                            f"Duration: {duration_str}\n"
                            f"Progress: {result.chunks_completed}/{result.chunks_total} chunks",
                    file_path=output_path
                ))
            else:
                # Complete
                self._update_progress(1.0, "Complete!")
                self.after(0, lambda: SuccessDialog(
                    self,
                    title="Conversion Complete",
                    message=f"Audio saved to:\n{output_path}\n\nDuration: {duration_str}",
                    file_path=output_path
                ))

        except Exception as e:
            logger.exception("Conversion failed")
            error_msg = str(e)
            tb = traceback.format_exc()
            # Stop indeterminate progress if it was running
            self.after(0, self._stop_indeterminate_progress)
            self.after(0, lambda: ErrorDialog(
                self,
                title="Conversion Error",
                message=f"Conversion failed:\n{error_msg}",
                full_traceback=tb
            ))

        finally:
            self._processing = False
            self.after(0, self._reset_ui)

    def _update_progress(self, value: float, status: str):
        """Update progress bar and status from any thread."""
        self.after(0, lambda: self._progress_bar.set(value))
        self.after(0, lambda: self._progress_label.configure(text=status))
        self.after(0, lambda: self._status_label.configure(text=status))

    def _start_indeterminate_progress(self):
        """Start indeterminate progress bar animation (for long operations without known progress)."""
        self._progress_bar.configure(mode="indeterminate")
        self._progress_bar.start()

    def _stop_indeterminate_progress(self):
        """Stop indeterminate progress bar animation and switch back to determinate mode."""
        self._progress_bar.stop()
        self._progress_bar.configure(mode="determinate")

    def _start_button_animation(self):
        """Start ellipsis animation on buttons to show activity."""
        self._ellipsis_state = 0
        self._animate_button_ellipsis()

    def _stop_button_animation(self):
        """Stop ellipsis animation on buttons."""
        if self._button_animation_id:
            self.after_cancel(self._button_animation_id)
            self._button_animation_id = None

    def _animate_button_ellipsis(self):
        """Animate ellipsis on Converting.../Cancelling... buttons."""
        if not self._processing:
            return

        ellipsis = "." * (self._ellipsis_state % 4)
        padded_ellipsis = ellipsis.ljust(3)  # Pad to 3 chars to prevent button resizing

        if self._cancel_requested:
            self._cancel_btn.configure(text=f"Cancelling{padded_ellipsis}")
        else:
            self._convert_btn.configure(text=f"Converting{padded_ellipsis}")

        self._ellipsis_state += 1
        self._button_animation_id = self.after(400, self._animate_button_ellipsis)

    def _reset_ui(self):
        """Reset UI after conversion."""
        self._stop_button_animation()  # Stop ellipsis animation
        self._convert_btn.configure(state="normal", text="Convert to Speech")
        self._cancel_btn.pack_forget()  # Hide cancel button
        self._cancel_btn.configure(state="normal", text="Cancel")  # Reset cancel button
        self._cancel_requested = False
        self._progress_label.configure(text="Ready")


def run_app():
    """Create and run the application."""
    app = TTSApplication()
    app.mainloop()
