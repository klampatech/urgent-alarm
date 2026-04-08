#!/usr/bin/env python3
"""
ElevenLabs TTS Adapter

Implements ITTSAdapter using ElevenLabs API for text-to-speech.
"""

import os
import json
from typing import Optional

from .tts_adapter import ITTSAdapter, TTSResult, TTSError


class ElevenLabsAdapter(ITTSAdapter):
    """
    Adapter for ElevenLabs TTS API.

    Environment variables:
    - ELEVENLABS_API_KEY: API key for ElevenLabs
    - ELEVENLABS_VOICE_ID: Default voice ID (optional)
    - ELEVENLABS_MODEL: Model name (default: eleven_monolingual_v1)

    Cache:
    - Audio is cached at /tmp/tts_cache/{reminder_id}/{anchor_id}.mp3
    - Set TTS_CACHE_DIR to override
    """

    DEFAULT_MODEL = "eleven_monolingual_v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get('ELEVENLABS_API_KEY')
        self.voice_id = voice_id or os.environ.get('ELEVENLABS_VOICE_ID')
        self.model = model or os.environ.get('ELEVENLABS_MODEL', self.DEFAULT_MODEL)
        self.base_url = "https://api.elevenlabs.io/v1"

    def is_available(self) -> bool:
        """Check if ElevenLabs API is configured."""
        return bool(self.api_key)

    def get_cache_path(self, cache_key: str) -> str:
        """Get path for caching audio files."""
        # Parse reminder_id and anchor_id from cache_key
        parts = cache_key.split('/')
        if len(parts) >= 2:
            reminder_id = parts[0]
            anchor_id = parts[1] if len(parts) > 1 else 'default'
        else:
            reminder_id = cache_key
            anchor_id = 'default'

        cache_dir = os.environ.get('TTS_CACHE_DIR', '/tmp/tts_cache')
        reminder_dir = os.path.join(cache_dir, reminder_id)
        os.makedirs(reminder_dir, exist_ok=True)

        return os.path.join(reminder_dir, f"{anchor_id}.mp3")

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> TTSResult:
        """
        Synthesize text to speech using ElevenLabs API.

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID override

        Returns:
            TTSResult with audio path or error
        """
        if not self.is_available():
            return TTSResult(
                audio_path=None,
                text=text,
                duration_seconds=None,
                success=False,
                used_cache=False,
                error="ElevenLabs API key not configured"
            )

        # Determine voice ID
        use_voice = voice_id or self.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel default

        try:
            import requests

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            }

            payload = {
                "text": text,
                "model_id": self.model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5,
                }
            }

            response = requests.post(
                f"{self.base_url}/text-to-speech/{use_voice}",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                return TTSResult(
                    audio_path=None,
                    text=text,
                    duration_seconds=None,
                    success=False,
                    used_cache=False,
                    error=f"ElevenLabs API error: {response.status_code}"
                )

            # Generate cache key from text hash
            import hashlib
            cache_key = hashlib.md5(text.encode()).hexdigest()
            cache_path = self.get_cache_path(cache_key)

            # Write audio to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)

            # Estimate duration (rough: ~150 chars per minute at normal speed)
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
                error=f"Synthesis failed: {e}"
            )


# Pre-configured voices for ElevenLabs
ELEVENLABS_VOICES = {
    'Rachel': '21m00Tcm4TlvDq8ikWAM',
    'Adam': 'pNInz6obpgDQGcFmaJgB',
    'Arnold': 'AZnzlk1XvdvUeBnXmlld',
    'Bella': 'EXAVITQu4vr4xnSDxMaL',
    'Domi': 'ErXwobaYiN019LbfYUSL',
    'Elliot': 'gZLpMhMQ0100Bge110d',
    'Fin': 'jsCqWAovK2LkecwTzVEM',
    'Freya': 'jsCqWAovK2LkecwTzVEM',  # duplicate reference
    'George': 'jT2Wn4hPWbTJLHzwKj9R',
    'Grace': 'zqtKKEzQPr rz7wDaT3V',
}