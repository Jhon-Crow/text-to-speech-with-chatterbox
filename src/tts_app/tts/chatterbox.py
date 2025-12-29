"""Chatterbox TTS engine implementation."""

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .base import TTSEngine, TTSConfig, TTSResult, ProgressCallback, CancelCheck

logger = logging.getLogger(__name__)


@contextmanager
def _patch_torch_load_for_cpu(device: str):
    """Context manager that patches torch.load to use map_location for CPU/MPS devices.

    This is a workaround for the chatterbox multilingual model which doesn't properly
    handle loading models that were saved on CUDA devices when running on CPU.

    See: https://github.com/resemble-ai/chatterbox/issues/96

    Args:
        device: The target device ("cpu", "cuda", "mps", etc.)
    """
    import torch

    # Only patch if we're loading on a non-CUDA device
    if device in ("cpu", "mps") or (device == "cuda" and not torch.cuda.is_available()):
        original_torch_load = torch.load

        def patched_torch_load(f, map_location=None, **kwargs):
            # If no map_location specified, default to CPU for safe loading
            if map_location is None:
                map_location = "cpu"
            return original_torch_load(f, map_location=map_location, **kwargs)

        torch.load = patched_torch_load
        try:
            yield
        finally:
            torch.load = original_torch_load
    else:
        # No patching needed for CUDA devices
        yield


class HuggingFaceTokenError(RuntimeError):
    """Error raised when HuggingFace token is required but not configured."""
    pass


class CUDANotAvailableError(RuntimeError):
    """Error raised when model requires CUDA but it's not available."""
    pass


class ChatterboxEngine(TTSEngine):
    """TTS engine using Resemble AI's Chatterbox models.

    Supports three model variants:
    - Turbo: Fast, English-only, 350M parameters
    - Standard: English with CFG tuning, 500M parameters
    - Multilingual: 23+ languages, 500M parameters
    """

    # Supported languages for the multilingual model
    MULTILINGUAL_LANGUAGES = [
        "ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi",
        "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv",
        "sw", "tr", "zh"
    ]

    def __init__(self):
        """Initialize the Chatterbox engine."""
        self._model = None
        self._config: Optional[TTSConfig] = None
        self._initialized = False
        self._vram_warning: Optional[str] = None

    def get_vram_warning(self) -> Optional[str]:
        """Get any VRAM warning message from initialization.

        Returns:
            Warning message if GPU VRAM is insufficient, None otherwise.
        """
        return self._vram_warning

    @property
    def name(self) -> str:
        """Get the engine name."""
        return "chatterbox"

    # Minimum VRAM recommended for models (in GB)
    # Multilingual and Standard models are ~500M params, Turbo is ~350M params
    MIN_VRAM_MULTILINGUAL_GB = 3.0  # Multilingual needs more for language embeddings
    MIN_VRAM_STANDARD_GB = 2.5
    MIN_VRAM_TURBO_GB = 2.0

    def _detect_best_device(self) -> str:
        """Detect the best available device for inference.

        Checks for GPU availability in the following order:
        1. NVIDIA CUDA (requires CUDA-enabled PyTorch build)
        2. AMD ROCm (via HIP backend in PyTorch - requires ROCm PyTorch build)
        3. Apple MPS (Apple Silicon)
        4. CPU fallback

        Returns:
            Device string ("cuda", "mps", or "cpu").
        """
        import torch

        # Check for NVIDIA CUDA
        # Note: torch.cuda.is_available() can return False for AMD GPUs on Windows
        # because standard PyTorch Windows builds only support NVIDIA CUDA
        if torch.cuda.is_available():
            try:
                device_name = torch.cuda.get_device_name(0)
                vram_gb = self._get_gpu_vram_gb()
                logger.info(f"CUDA available: {device_name} ({vram_gb:.1f} GB VRAM)")
                return "cuda"
            except Exception as e:
                logger.warning(f"CUDA detected but failed to get device info: {e}")
                # Fall through to CPU

        # Check for MPS (Apple Silicon)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Apple MPS available")
            return "mps"

        logger.info("No GPU available, using CPU")
        return "cpu"

    def _get_gpu_vram_gb(self) -> float:
        """Get the total VRAM of the GPU in gigabytes.

        Returns:
            VRAM in GB, or 0.0 if unable to detect.
        """
        import torch

        if not torch.cuda.is_available():
            return 0.0

        try:
            props = torch.cuda.get_device_properties(0)
            vram_bytes = props.total_memory
            return vram_bytes / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to get GPU VRAM: {e}")
            return 0.0

    def _check_vram_for_model(self, model_type: str) -> tuple[bool, str]:
        """Check if GPU has enough VRAM for the selected model.

        Args:
            model_type: The model type ("turbo", "standard", "multilingual").

        Returns:
            Tuple of (is_sufficient, warning_message).
            If VRAM is sufficient or can't be detected, returns (True, "").
        """
        import torch

        if not torch.cuda.is_available():
            return True, ""

        vram_gb = self._get_gpu_vram_gb()
        if vram_gb == 0.0:
            return True, ""  # Can't detect, proceed anyway

        # Determine minimum VRAM for model
        min_vram = {
            "turbo": self.MIN_VRAM_TURBO_GB,
            "standard": self.MIN_VRAM_STANDARD_GB,
            "multilingual": self.MIN_VRAM_MULTILINGUAL_GB,
        }.get(model_type, self.MIN_VRAM_STANDARD_GB)

        if vram_gb < min_vram:
            device_name = torch.cuda.get_device_name(0)
            warning = (
                f"Your GPU ({device_name}) has {vram_gb:.1f} GB VRAM, "
                f"but {model_type} model needs ~{min_vram:.1f} GB. "
                f"This may cause freezing or out-of-memory errors. "
                f"Consider using CPU mode or the Turbo model for better stability."
            )
            return False, warning

        return True, ""

    def _validate_device(self, requested_device: str) -> str:
        """Validate the requested device and return a valid device.

        If the requested device is not available, falls back to CPU with a warning.

        Args:
            requested_device: The device requested by the user ("cuda", "cpu", "mps", "auto").

        Returns:
            A valid device string that PyTorch can use.
        """
        import torch

        if requested_device == "auto":
            return self._detect_best_device()

        if requested_device == "cuda":
            if not torch.cuda.is_available():
                logger.warning(
                    "GPU (CUDA) was requested but is not available. "
                    "This can happen if:\n"
                    "  - You have an AMD GPU (standard PyTorch only supports NVIDIA CUDA)\n"
                    "  - PyTorch was not installed with CUDA support\n"
                    "  - CUDA drivers are not properly installed\n"
                    "Falling back to CPU mode."
                )
                return "cpu"
            return "cuda"

        if requested_device == "mps":
            if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
                logger.warning("MPS was requested but is not available. Falling back to CPU.")
                return "cpu"
            return "mps"

        return requested_device  # "cpu" or unknown

    def initialize(self, config: TTSConfig) -> None:
        """Initialize the Chatterbox TTS model.

        Args:
            config: TTS configuration settings.

        Raises:
            RuntimeError: If model loading fails.
            HuggingFaceTokenError: If HuggingFace token is required but not configured.
            CUDANotAvailableError: If model requires CUDA but it's not available.
        """
        self._config = config

        # Validate and determine device (with fallback to CPU if GPU not available)
        device = self._validate_device(config.device)

        # Check VRAM for GPU devices and warn if insufficient
        if device == "cuda":
            is_sufficient, warning = self._check_vram_for_model(config.model_type)
            if not is_sufficient:
                logger.warning(warning)
                # Store warning for UI to display
                self._vram_warning = warning
            else:
                self._vram_warning = None
        else:
            self._vram_warning = None

        logger.info(f"Initializing Chatterbox {config.model_type} on {device}")

        # Set HF_TOKEN environment variable if provided in config
        # This helps the turbo model which requires token=True by default
        if hasattr(config, 'hf_token') and config.hf_token:
            os.environ["HF_TOKEN"] = config.hf_token
            logger.info("HuggingFace token configured from settings")

        try:
            if config.model_type == "turbo":
                from chatterbox.tts_turbo import ChatterboxTurboTTS
                self._model = ChatterboxTurboTTS.from_pretrained(device=device)

            elif config.model_type == "multilingual":
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                # Use patch to handle CUDA-saved models on CPU/MPS devices
                # See: https://github.com/resemble-ai/chatterbox/issues/96
                with _patch_torch_load_for_cpu(device):
                    self._model = ChatterboxMultilingualTTS.from_pretrained(device=device)

            else:  # standard
                from chatterbox.tts import ChatterboxTTS
                self._model = ChatterboxTTS.from_pretrained(device=device)

            self._initialized = True
            logger.info("Chatterbox model initialized successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to initialize Chatterbox: {e}")

            # Check for HuggingFace token errors
            if "Token is required" in error_msg or "LocalTokenNotFoundError" in error_msg:
                raise HuggingFaceTokenError(
                    "HuggingFace token is required to download the model.\n\n"
                    "Please do one of the following:\n"
                    "1. Enter your HuggingFace token in the 'HF Token' field in the Options section\n"
                    "2. Set the HF_TOKEN environment variable\n"
                    "3. Run 'huggingface-cli login' in your terminal\n\n"
                    "Get your token at: https://huggingface.co/settings/tokens"
                ) from e

            # Check for CUDA loading errors on CPU machines or AMD GPU users
            if ("torch.cuda.is_available() is False" in error_msg or
                "CUDA device" in error_msg or
                "Torch not compiled with CUDA enabled" in error_msg):
                raise CUDANotAvailableError(
                    "GPU acceleration is not available on this system.\n\n"
                    "Possible reasons:\n"
                    "- You have an AMD GPU (PyTorch Windows builds only support NVIDIA CUDA)\n"
                    "- PyTorch was installed without CUDA support\n"
                    "- NVIDIA drivers are not installed\n\n"
                    "Solution: Select 'Auto (GPU/CPU)' or 'CPU' in Device options.\n"
                    "The application will work on CPU, though slower."
                ) from e

            raise RuntimeError(f"Failed to initialize TTS model: {e}") from e

    def is_initialized(self) -> bool:
        """Check if the engine is initialized."""
        return self._initialized and self._model is not None

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        if self._config and self._config.model_type == "multilingual":
            return self.MULTILINGUAL_LANGUAGES
        return ["en"]  # Turbo and standard are English-only

    def synthesize(
        self,
        text: str,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_check: Optional[CancelCheck] = None
    ) -> TTSResult:
        """Synthesize speech from text.

        Args:
            text: The text to convert to speech.
            output_path: Path where the audio file should be saved.
            progress_callback: Optional callback for progress updates.
            cancel_check: Optional callback that returns True if generation should stop.
                         When cancelled, partial audio is saved and result.was_cancelled is True.

        Returns:
            TTSResult with information about the generated audio.

        Raises:
            RuntimeError: If synthesis fails or engine not initialized.
        """
        if not self.is_initialized():
            raise RuntimeError("TTS engine not initialized. Call initialize() first.")

        import torch
        import torchaudio

        # Split text into chunks for long texts
        chunks = self._split_into_chunks(text, self._config.chunk_size)
        total_chunks = len(chunks)

        logger.info(f"Synthesizing {total_chunks} chunks")

        audio_segments = []
        sample_rate = self._model.sr
        was_cancelled = False
        chunks_completed = 0
        chunk_times = []  # Track time for each chunk to estimate remaining time
        start_time = time.time()

        for i, chunk in enumerate(chunks):
            # Check for cancellation before processing each chunk
            if cancel_check and cancel_check():
                logger.info(f"Generation cancelled at chunk {i + 1}/{total_chunks}")
                was_cancelled = True
                break

            # Calculate estimated remaining time based on average chunk time
            estimated_remaining = None
            if chunk_times:
                avg_chunk_time = sum(chunk_times) / len(chunk_times)
                remaining_chunks = total_chunks - i
                estimated_remaining = avg_chunk_time * remaining_chunks

            if progress_callback:
                progress_callback(i + 1, total_chunks, f"Processing chunk {i + 1}/{total_chunks}", estimated_remaining)

            chunk_start_time = time.time()

            if not chunk.strip():
                continue

            try:
                # Generate audio for this chunk
                wav = self._generate_chunk(chunk)
                audio_segments.append(wav)
                chunks_completed += 1

                # Track chunk processing time for estimation
                chunk_time = time.time() - chunk_start_time
                chunk_times.append(chunk_time)
                logger.debug(f"Chunk {i + 1} took {chunk_time:.1f}s")

            except Exception as e:
                logger.warning(f"Failed to synthesize chunk {i + 1}: {e}")
                # Continue with other chunks
                continue

        # Handle case where no audio was generated
        if not audio_segments:
            if was_cancelled:
                raise RuntimeError("Generation was cancelled before any audio was generated")
            raise RuntimeError("No audio was generated")

        # Concatenate all audio segments
        if len(audio_segments) == 1:
            final_audio = audio_segments[0]
        else:
            # Add small silence between segments
            silence = torch.zeros(1, int(sample_rate * 0.3))  # 300ms silence
            padded_segments = []
            for seg in audio_segments:
                padded_segments.append(seg)
                padded_segments.append(silence)
            # Remove last silence
            padded_segments = padded_segments[:-1]
            final_audio = torch.cat(padded_segments, dim=1)

        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(output_path), final_audio, sample_rate)

        # Calculate duration
        duration = final_audio.shape[1] / sample_rate

        if progress_callback:
            if was_cancelled:
                progress_callback(chunks_completed, total_chunks, f"Cancelled - saved {chunks_completed}/{total_chunks} chunks", None)
            else:
                progress_callback(total_chunks, total_chunks, "Complete", None)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            sample_rate=sample_rate,
            text_processed=text,
            was_cancelled=was_cancelled,
            chunks_completed=chunks_completed,
            chunks_total=total_chunks
        )

    def _generate_chunk(self, text: str):
        """Generate audio for a single text chunk.

        Args:
            text: The text chunk to synthesize.

        Returns:
            Audio tensor.
        """
        voice_ref = None
        if self._config.voice_reference:
            voice_ref = str(self._config.voice_reference)

        if self._config.model_type == "multilingual":
            # Multilingual model requires language_id
            wav = self._model.generate(
                text,
                audio_prompt_path=voice_ref,
                language_id=self._config.language
            )
        elif voice_ref:
            # With voice reference
            wav = self._model.generate(text, audio_prompt_path=voice_ref)
        else:
            # Without voice reference
            wav = self._model.generate(text)

        return wav

    def _split_into_chunks(self, text: str, max_chars: int) -> list[str]:
        """Split text into chunks at natural boundaries.

        Args:
            text: The text to split.
            max_chars: Maximum characters per chunk.

        Returns:
            List of text chunks.
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = self._split_sentences(text)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If single sentence is too long, split by phrases
                if len(sentence) > max_chars:
                    phrases = self._split_phrases(sentence, max_chars)
                    chunks.extend(phrases[:-1])
                    current_chunk = phrases[-1] if phrases else ""
                else:
                    current_chunk = sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: The text to split.

        Returns:
            List of sentences.
        """
        import re

        # Split on sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return sentences

    def _split_phrases(self, text: str, max_chars: int) -> list[str]:
        """Split a long sentence into smaller phrases.

        Args:
            text: The text to split.
            max_chars: Maximum characters per phrase.

        Returns:
            List of phrases.
        """
        import re

        # Split on commas, semicolons, and other natural breaks
        parts = re.split(r'(?<=[,;:])\s+', text)

        phrases = []
        current_phrase = ""

        for part in parts:
            if len(current_phrase) + len(part) <= max_chars:
                current_phrase += " " + part if current_phrase else part
            else:
                if current_phrase:
                    phrases.append(current_phrase.strip())
                # If still too long, force split
                if len(part) > max_chars:
                    words = part.split()
                    current_phrase = ""
                    for word in words:
                        if len(current_phrase) + len(word) + 1 <= max_chars:
                            current_phrase += " " + word if current_phrase else word
                        else:
                            if current_phrase:
                                phrases.append(current_phrase.strip())
                            current_phrase = word
                else:
                    current_phrase = part

        if current_phrase.strip():
            phrases.append(current_phrase.strip())

        return phrases
