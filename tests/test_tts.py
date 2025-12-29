"""Tests for TTS engine."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tts_app.tts import TTSEngine, TTSConfig, ChatterboxEngine
from tts_app.tts.base import TTSResult
from tts_app.tts.chatterbox import (
    HuggingFaceTokenError,
    CUDANotAvailableError,
    _patch_torch_load_for_cpu,
)


class TestTTSConfig:
    """Tests for TTSConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TTSConfig()
        assert config.model_type == "turbo"
        assert config.language == "en"
        assert config.voice_reference is None
        assert config.device == "auto"
        assert config.chunk_size == 500

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TTSConfig(
            model_type="multilingual",
            language="fr",
            voice_reference=Path("/path/to/voice.wav"),
            device="cuda",
            chunk_size=1000
        )
        assert config.model_type == "multilingual"
        assert config.language == "fr"
        assert config.voice_reference == Path("/path/to/voice.wav")
        assert config.device == "cuda"
        assert config.chunk_size == 1000

    def test_hf_token_default(self):
        """Test hf_token defaults to None."""
        config = TTSConfig()
        assert config.hf_token is None

    def test_hf_token_custom(self):
        """Test hf_token can be set."""
        config = TTSConfig(hf_token="hf_test_token_123")
        assert config.hf_token == "hf_test_token_123"


class TestTTSResult:
    """Tests for TTSResult."""

    def test_create_result(self):
        """Test creating a TTS result."""
        result = TTSResult(
            audio_path=Path("/path/to/output.wav"),
            duration_seconds=60.5,
            sample_rate=22050,
            text_processed="Hello world"
        )
        assert result.audio_path == Path("/path/to/output.wav")
        assert result.duration_seconds == 60.5
        assert result.sample_rate == 22050
        assert result.text_processed == "Hello world"


class TestChatterboxEngine:
    """Tests for ChatterboxEngine."""

    def test_name(self):
        """Test engine name."""
        engine = ChatterboxEngine()
        assert engine.name == "chatterbox"

    def test_not_initialized_by_default(self):
        """Test that engine is not initialized by default."""
        engine = ChatterboxEngine()
        assert engine.is_initialized() is False

    def test_supported_languages_before_init(self):
        """Test getting supported languages before initialization."""
        engine = ChatterboxEngine()
        # Should return English by default
        languages = engine.get_supported_languages()
        assert "en" in languages

    def test_synthesize_without_init_raises(self):
        """Test that synthesize raises error if not initialized."""
        engine = ChatterboxEngine()
        with pytest.raises(RuntimeError, match="not initialized"):
            engine.synthesize("Hello", Path("/tmp/test.wav"))

    def test_split_into_chunks_short_text(self):
        """Test that short text is not split."""
        engine = ChatterboxEngine()
        engine._config = TTSConfig(chunk_size=500)

        text = "This is a short text."
        chunks = engine._split_into_chunks(text, 500)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_into_chunks_long_text(self):
        """Test that long text is split at sentence boundaries."""
        engine = ChatterboxEngine()
        engine._config = TTSConfig(chunk_size=50)

        text = "First sentence here. Second sentence here. Third sentence here."
        chunks = engine._split_into_chunks(text, 50)

        assert len(chunks) > 1
        # Each chunk should be within size limit or contain a single sentence
        for chunk in chunks:
            assert len(chunk) <= 100  # Allow some flexibility for sentence boundaries

    def test_split_sentences(self):
        """Test sentence splitting."""
        engine = ChatterboxEngine()

        text = "First sentence. Second sentence! Third sentence?"
        sentences = engine._split_sentences(text)

        assert len(sentences) == 3
        assert "First sentence." in sentences[0]

    def test_config_stored_after_init_attempt(self):
        """Test that config is stored even if initialization fails.

        Note: Full initialization tests require the chatterbox-tts library
        to be installed with GPU support. This test verifies the engine
        stores the config properly.
        """
        engine = ChatterboxEngine()
        config = TTSConfig(model_type="turbo", device="cpu")

        # The engine should store config even if init fails (no chatterbox installed)
        try:
            engine.initialize(config)
        except (RuntimeError, ImportError, ModuleNotFoundError):
            # Expected when chatterbox-tts is not installed
            pass

        # Config should still be stored
        assert engine._config == config


class TestChatterboxEngineMultilingual:
    """Tests for multilingual model support."""

    def test_multilingual_languages(self):
        """Test that multilingual model supports expected languages."""
        engine = ChatterboxEngine()
        expected = ["en", "fr", "de", "es", "zh", "ja", "ko"]

        for lang in expected:
            assert lang in ChatterboxEngine.MULTILINGUAL_LANGUAGES


class TestChatterboxErrorHandling:
    """Tests for error handling in ChatterboxEngine."""

    def test_huggingface_token_error_is_runtime_error(self):
        """Test that HuggingFaceTokenError is a RuntimeError."""
        assert issubclass(HuggingFaceTokenError, RuntimeError)

    def test_cuda_not_available_error_is_runtime_error(self):
        """Test that CUDANotAvailableError is a RuntimeError."""
        assert issubclass(CUDANotAvailableError, RuntimeError)

    def test_huggingface_token_error_message(self):
        """Test that HuggingFaceTokenError can be raised with message."""
        with pytest.raises(HuggingFaceTokenError, match="Token"):
            raise HuggingFaceTokenError("Token required")

    def test_cuda_not_available_error_message(self):
        """Test that CUDANotAvailableError can be raised with message."""
        with pytest.raises(CUDANotAvailableError, match="CUDA"):
            raise CUDANotAvailableError("CUDA not available")


class TestTorchLoadPatch:
    """Tests for the torch.load CPU patching workaround."""

    def test_patch_applied_for_cpu_device(self):
        """Test that torch.load is patched when device is 'cpu'."""
        import torch

        original_load = torch.load
        call_args = []

        # Mock torch.load to record calls
        def mock_load(f, map_location=None, **kwargs):
            call_args.append({"map_location": map_location})
            return {}

        with patch.object(torch, "load", mock_load):
            with _patch_torch_load_for_cpu("cpu"):
                # The patched version should default map_location to "cpu"
                torch.load("dummy_path")

        assert len(call_args) == 1
        assert call_args[0]["map_location"] == "cpu"

    def test_patch_applied_for_mps_device(self):
        """Test that torch.load is patched when device is 'mps'."""
        import torch

        call_args = []

        def mock_load(f, map_location=None, **kwargs):
            call_args.append({"map_location": map_location})
            return {}

        with patch.object(torch, "load", mock_load):
            with _patch_torch_load_for_cpu("mps"):
                torch.load("dummy_path")

        assert len(call_args) == 1
        assert call_args[0]["map_location"] == "cpu"

    def test_patch_preserves_explicit_map_location(self):
        """Test that explicit map_location is preserved when patching."""
        import torch

        call_args = []

        def mock_load(f, map_location=None, **kwargs):
            call_args.append({"map_location": map_location})
            return {}

        with patch.object(torch, "load", mock_load):
            with _patch_torch_load_for_cpu("cpu"):
                # Explicitly pass map_location - it should be preserved
                torch.load("dummy_path", map_location="cuda:0")

        assert len(call_args) == 1
        assert call_args[0]["map_location"] == "cuda:0"

    def test_patch_restored_after_context(self):
        """Test that torch.load is restored after the context exits."""
        import torch

        original_load = torch.load

        with _patch_torch_load_for_cpu("cpu"):
            # During the context, load may be patched
            pass

        # After the context, should be restored
        assert torch.load is original_load

    def test_no_patch_for_cuda_when_available(self):
        """Test that torch.load is not patched for CUDA when available."""
        import torch

        original_load = torch.load

        # Mock cuda as available
        with patch.object(torch.cuda, "is_available", return_value=True):
            with _patch_torch_load_for_cpu("cuda"):
                # Should not be patched when CUDA is available
                assert torch.load is original_load
