"""Base TTS engine interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable


@dataclass
class TTSConfig:
    """Configuration for TTS generation.

    Attributes:
        model_type: Which Chatterbox model to use ("turbo", "standard", "multilingual").
        language: Language code for multilingual model (e.g., "en", "fr", "de").
        voice_reference: Optional path to a voice reference audio file for cloning.
        device: Device to use ("cuda", "cpu", or "auto").
        chunk_size: Maximum characters per TTS chunk (for long texts).
        hf_token: Optional HuggingFace token for model download.
    """
    model_type: str = "turbo"
    language: str = "en"
    voice_reference: Optional[Path] = None
    device: str = "auto"
    chunk_size: int = 500  # Characters per chunk
    hf_token: Optional[str] = None


@dataclass
class TTSResult:
    """Result of TTS generation.

    Attributes:
        audio_path: Path to the generated audio file.
        duration_seconds: Duration of the audio in seconds.
        sample_rate: Sample rate of the audio.
        text_processed: The text that was converted to speech.
    """
    audio_path: Path
    duration_seconds: float
    sample_rate: int
    text_processed: str


ProgressCallback = Callable[[int, int, str], None]  # (current, total, status)


class TTSEngine(ABC):
    """Abstract base class for text-to-speech engines.

    This defines the interface for TTS engines. Currently supports
    Chatterbox TTS, but the architecture allows adding other engines.
    """

    @abstractmethod
    def initialize(self, config: TTSConfig) -> None:
        """Initialize the TTS engine with configuration.

        Args:
            config: TTS configuration settings.
        """
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> TTSResult:
        """Synthesize speech from text.

        Args:
            text: The text to convert to speech.
            output_path: Path where the audio file should be saved.
            progress_callback: Optional callback for progress updates.

        Returns:
            TTSResult with information about the generated audio.
        """
        pass

    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if the engine is initialized and ready.

        Returns:
            True if the engine is ready for synthesis.
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes.

        Returns:
            List of supported language codes.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the engine name.

        Returns:
            Name of the TTS engine.
        """
        pass
