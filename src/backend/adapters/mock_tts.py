#!/usr/bin/env python3
"""
Mock TTS Adapter for Testing

Returns silent placeholder audio files without API calls.
"""

import os
from typing import Optional

from .tts_adapter import ITTSAdapter, TTSResult


class MockTTSAdapter(ITTSAdapter):
    """
    Mock adapter that returns placeholder audio files.

    Useful for:
    - Unit testing without external API calls
    - CI/CD pipelines where API keys aren't available
    - Pre-generating TTS without network

    Creates silent MP3 placeholder files for testing.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize mock TTS adapter.

        Args:
            cache_dir: Directory for cache files (default: /tmp/tts_cache)
        """
        self.cache_dir = cache_dir or os.environ.get('TTS_CACHE_DIR', '/tmp/tts_cache')

    def is_available(self) -> bool:
        """Always available - no external dependencies."""
        return True

    def get_cache_path(self, cache_key: str) -> str:
        """Get path for caching mock audio files."""
        # Parse reminder_id and anchor_id from cache_key
        parts = cache_key.split('/')
        if len(parts) >= 2:
            reminder_id = parts[0]
            anchor_id = parts[1] if len(parts) > 1 else 'default'
        else:
            reminder_id = 'default'
            anchor_id = cache_key

        reminder_dir = os.path.join(self.cache_dir, reminder_id)
        os.makedirs(reminder_dir, exist_ok=True)

        return os.path.join(reminder_dir, f"{anchor_id}.mp3")

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        Create a placeholder audio file.

        For testing purposes, creates an empty/silent file.
        In real implementation, this would generate a valid silent MP3.
        """
        import hashlib

        # Generate cache key from text
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_path = self.get_cache_path(cache_key)

        # Create a minimal valid MP3 file (silent)
        # This is a minimal valid MP3 frame (silent)
        minimal_mp3 = bytes([
            0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ])

        try:
            with open(cache_path, 'wb') as f:
                f.write(minimal_mp3)

            # Estimate duration (rough: ~150 chars per minute)
            duration = len(text) / 150 / 60

            return TTSResult(
                audio_path=cache_path,
                text=text,
                duration_seconds=duration,
                success=True,
                used_cache=False,
            )
        except Exception as e:
            return TTSResult(
                audio_path=None,
                text=text,
                duration_seconds=None,
                success=False,
                used_cache=False,
                error=f"Failed to create mock audio: {e}"
            )


class DeterministicMockTTS(MockTTSAdapter):
    """
    Mock TTS that always returns the same audio file.

    Useful for tests that need strict determinism.
    """

    def __init__(self, fixed_path: Optional[str] = None):
        """
        Initialize deterministic mock.

        Args:
            fixed_path: Fixed path to return for all audio
        """
        super().__init__()
        self.fixed_path = fixed_path or '/tmp/mock_tts.mp3'

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """Return fixed audio path with estimated duration."""
        duration = len(text) / 150 / 60

        return TTSResult(
            audio_path=self.fixed_path,
            text=text,
            duration_seconds=duration,
            success=True,
            used_cache=False,
        )