#!/usr/bin/env python3
"""
TTS Adapter Interface

Defines the contract for Text-to-Speech generation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class TTSResult:
    """Result of TTS generation."""
    audio_path: Optional[str]  # Path to generated audio file
    text: str  # The text that was synthesized
    duration_seconds: Optional[float]  # Duration of audio
    success: bool  # Whether generation succeeded
    used_cache: bool  # Whether cached audio was used
    error: Optional[str] = None  # Error message if failed


class ITTSAdapter(ABC):
    """
    Interface for TTS adapters.

    Implementations must provide:
    - synthesize: Generate audio from text
    - is_available: Check if the adapter can make requests
    - get_cache_path: Get path for caching audio
    """

    @abstractmethod
    def synthesize(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID to use

        Returns:
            TTSResult with audio path or error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the TTS service is available.

        Returns:
            True if the adapter can make requests, False otherwise
        """
        pass

    def get_cache_path(self, cache_key: str) -> str:
        """
        Get the path for caching audio files.

        Args:
            cache_key: Unique identifier for the audio (e.g., reminder_id + anchor_id)

        Returns:
            Absolute path for the cache file
        """
        cache_dir = os.environ.get('TTS_CACHE_DIR', '/tmp/tts_cache')
        return os.path.join(cache_dir, f"{cache_key}.mp3")


class TTSError(Exception):
    """Error raised when TTS synthesis fails."""
    pass