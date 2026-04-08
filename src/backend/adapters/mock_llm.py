#!/usr/bin/env python3
"""
Mock Language Model Adapter for Testing

Returns predefined fixtures without making API calls.
"""

from typing import Optional, Dict
import re
from datetime import datetime, timedelta

from .llm_adapter import ILanguageModelAdapter, ParsedReminder


class MockLLMAdapter(ILanguageModelAdapter):
    """
    Mock adapter that returns predefined parsing results.

    Useful for:
    - Unit testing without external API calls
    - CI/CD pipelines where API keys aren't available
    - Deterministic test scenarios

    The adapter uses pattern matching to return appropriate fixtures
    based on test input patterns.
    """

    # Predefined fixtures for common test scenarios
    FIXTURES: Dict[str, ParsedReminder] = {
        'meeting': ParsedReminder(
            destination="downtown office",
            arrival_time="2026-04-09T09:00:00",
            drive_duration=30,
            reminder_type="countdown_event",
            confidence=0.95,
            raw_input="",
        ),
        'appointment': ParsedReminder(
            destination="doctor's office",
            arrival_time="2026-04-09T14:00:00",
            drive_duration=20,
            reminder_type="countdown_event",
            confidence=0.90,
            raw_input="",
        ),
        'gym': ParsedReminder(
            destination="fitness center",
            arrival_time="2026-04-09T18:00:00",
            drive_duration=15,
            reminder_type="countdown_event",
            confidence=0.85,
            raw_input="",
        ),
    }

    def __init__(self, fixture_name: str = 'meeting'):
        """
        Initialize mock adapter with a specific fixture.

        Args:
            fixture_name: Name of fixture to return (meeting, appointment, gym)
        """
        self.fixture_name = fixture_name

    def is_available(self) -> bool:
        """Always available - no external dependencies."""
        return True

    def parse_reminder(self, input_text: str) -> ParsedReminder:
        """
        Parse reminder using predefined fixtures.

        Uses keyword matching to select appropriate fixture,
        with fallback to keyword-based parsing from test_server.
        """
        input_lower = input_text.lower()

        # Try to match a fixture based on keywords
        if 'meeting' in input_lower or 'office' in input_lower:
            fixture = self.FIXTURES['meeting']
        elif 'doctor' in input_lower or 'appointment' in input_lower:
            fixture = self.FIXTURES['appointment']
        elif 'gym' in input_lower or 'workout' in input_lower:
            fixture = self.FIXTURES['gym']
        else:
            # Fallback to basic parsing
            return self._fallback_parse(input_text)

        # Return copy with raw_input set
        return ParsedReminder(
            destination=fixture.destination,
            arrival_time=fixture.arrival_time,
            drive_duration=fixture.drive_duration,
            reminder_type=fixture.reminder_type,
            confidence=fixture.confidence,
            raw_input=input_text,
        )

    def _fallback_parse(self, input_text: str) -> ParsedReminder:
        """
        Fallback to simple keyword-based parsing.

        This mirrors the behavior in test_server.py for consistent testing.
        """
        result = {
            'destination': None,
            'arrival_time': None,
            'drive_duration': None,
            'reminder_type': 'countdown_event',
            'confidence': 0.5,
            'raw_input': input_text,
        }

        # Extract destination (everything after "to")
        dest_match = re.search(r'to\s+([^,]+?)(?:,|$)', input_text, re.IGNORECASE)
        if dest_match:
            result['destination'] = dest_match.group(1).strip()
        else:
            result['destination'] = input_text.strip()

        # Extract drive duration
        duration_match = re.search(r'(\d+)\s*(?:minute|min)', input_text, re.IGNORECASE)
        if duration_match:
            result['drive_duration'] = int(duration_match.group(1))

        # Extract time
        time_match = re.search(r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)', input_text, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            period = time_match.group(3).lower()

            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0

            now = datetime.now()
            arrival = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time is in past, assume tomorrow
            if arrival <= now:
                arrival += timedelta(days=1)

            result['arrival_time'] = arrival.isoformat()
            result['confidence'] = 0.7

        return ParsedReminder(**result)


class DeterministicMockAdapter(MockLLMAdapter):
    """
    Mock adapter that always returns the same parsed result.

    Useful for tests that need strict determinism.
    """

    def __init__(
        self,
        destination: str = "test destination",
        arrival_time: Optional[str] = None,
        drive_duration: int = 30,
        reminder_type: str = "countdown_event",
        confidence: float = 0.9
    ):
        self.destination = destination
        self.arrival_time = arrival_time or (datetime.now() + timedelta(hours=2)).isoformat()
        self.drive_duration = drive_duration
        self.reminder_type = reminder_type
        self.confidence = confidence

    def parse_reminder(self, input_text: str) -> ParsedReminder:
        """Return fixed parsed reminder."""
        return ParsedReminder(
            destination=self.destination,
            arrival_time=self.arrival_time,
            drive_duration=self.drive_duration,
            reminder_type=self.reminder_type,
            confidence=self.confidence,
            raw_input=input_text,
        )