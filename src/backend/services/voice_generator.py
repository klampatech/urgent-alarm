"""
Voice Message Generator Service

Per spec Section 4 & 10: Generates voice messages using personality templates.
Extracts logic from test_server.py for modularity and testability.
"""

import random
from typing import Optional

from backend.services.message_templates import VOICE_PERSONALITIES, VALID_PERSONALITIES


# Default personality per spec Section 10.1
DEFAULT_PERSONALITY = 'assistant'


class VoiceGenerator:
    """Generates voice messages for escalation anchors"""

    def __init__(self, personality: Optional[str] = None):
        """
        Initialize voice generator with a personality.

        Args:
            personality: One of 'coach', 'assistant', 'best_friend', 'no_nonsense', 'calm'
                       Defaults to 'assistant' per spec.
        """
        self.personality = personality or DEFAULT_PERSONALITY
        if self.personality not in VALID_PERSONALITIES:
            raise ValueError(f"Invalid personality: {personality}. Valid: {VALID_PERSONALITIES}")

    def generate(
        self,
        urgency_tier: str,
        destination: str,
        drive_duration: int,
        minutes_remaining: int,
    ) -> str:
        """
        Generate a voice message for the given context.

        Per spec Section 10.3:
        - Uses personality-specific message templates
        - Selects random variation from 3+ available
        - Substitutes {dest}, {dur}, {remaining}, {plural} placeholders

        Args:
            urgency_tier: One of calm, casual, pointed, urgent, pushing, firm, critical, alarm
            destination: The destination name/address
            drive_duration: Total drive time in minutes
            minutes_remaining: Minutes until departure

        Returns:
            Generated message string ready for TTS
        """
        templates = VOICE_PERSONALITIES.get(self.personality, VOICE_PERSONALITIES[DEFAULT_PERSONALITY])
        messages = templates.get(urgency_tier, templates['calm'])

        # Select random message from variations
        template = random.choice(messages)

        # Handle plural for "minute" vs "minutes"
        plural = '' if minutes_remaining == 1 else 'S'

        return template.format(
            dest=destination,
            dur=drive_duration,
            remaining=minutes_remaining,
            plural=plural,
        )

    def get_personality(self) -> str:
        """Return the current personality setting."""
        return self.personality


def generate_voice_message(
    personality: str,
    urgency_tier: str,
    destination: str,
    drive_duration: int,
    minutes_remaining: int,
) -> str:
    """
    Convenience function to generate a voice message.

    Args:
        personality: Voice personality to use
        urgency_tier: Current urgency tier
        destination: Destination address/name
        drive_duration: Total drive time in minutes
        minutes_remaining: Minutes remaining until departure

    Returns:
        Generated message string
    """
    generator = VoiceGenerator(personality)
    return generator.generate(urgency_tier, destination, drive_duration, minutes_remaining)