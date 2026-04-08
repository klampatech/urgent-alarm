#!/usr/bin/env python3
"""
Reminder Parser Service

Connects LLM adapter to reminder creation flow with fallback support.
"""

import os
from typing import Optional, Tuple
from datetime import datetime, timedelta

from ..adapters.llm_adapter import ILanguageModelAdapter, ParsedReminder, LLMParseError


class ReminderParser:
    """
    Service for parsing natural language reminders.

    Uses LLM adapter with fallback to keyword-based parsing.
    Provides confirmation card data for UI display.
    """

    def __init__(self, adapter: Optional[ILanguageModelAdapter] = None):
        """
        Initialize parser with optional adapter.

        Args:
            adapter: LLM adapter to use. If None, uses environment to determine
                    which adapter to instantiate (mock for tests, MiniMax for production).
        """
        self.adapter = adapter

    def _get_adapter(self) -> ILanguageModelAdapter:
        """Get or create the LLM adapter based on environment."""
        if self.adapter is not None:
            return self.adapter

        # Check for test mode (no API keys)
        if not os.environ.get('MINIMAX_API_KEY'):
            from ..adapters.mock_llm import MockLLMAdapter
            return MockLLMAdapter()

        # Use MiniMax adapter in production
        from ..adapters.minimax_adapter import MiniMaxAdapter
        return MiniMaxAdapter()

    def parse(self, input_text: str) -> Tuple[ParsedReminder, bool]:
        """
        Parse natural language input to reminder fields.

        Args:
            input_text: Raw user input like "30 min drive to downtown, 9am meeting"

        Returns:
            Tuple of (ParsedReminder, used_llm: bool)
            - used_llm: True if LLM was used, False if fallback was used
        """
        adapter = self._get_adapter()

        # Try LLM first if available
        if adapter.is_available():
            try:
                result = adapter.parse_reminder(input_text)
                return result, True
            except LLMParseError:
                # Fall through to keyword parsing
                pass

        # Fallback to keyword-based parsing
        result = self._keyword_parse(input_text)
        return result, False

    def _keyword_parse(self, input_text: str) -> ParsedReminder:
        """
        Keyword-based fallback parsing.

        Mirrors the behavior in test_server.py for consistent results.
        """
        import re

        result = {
            'destination': None,
            'arrival_time': None,
            'drive_duration': None,
            'reminder_type': 'countdown_event',
            'confidence': 0.0,
        }

        # Extract destination
        dest_patterns = [
            r'to\s+([^,]+?)(?:,|arrive|check-in|$)',
            r'for\s+([^,]+?)(?:,|$)',
        ]
        for pattern in dest_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                result['destination'] = match.group(1).strip()
                break

        if not result['destination']:
            result['destination'] = input_text.strip()

        # Extract drive duration
        duration_patterns = [
            r'(\d+)\s*(?:minute|min)\s*drive',
            r'drive\s*(?:of\s*)?(\d+)\s*(?:minute|min)',
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                result['drive_duration'] = int(match.group(1))
                break

        if not result['drive_duration']:
            # Check for "in X minutes" (simple countdown)
            match = re.search(r'in\s+(\d+)\s*(?:minute|min)', input_text, re.IGNORECASE)
            if match:
                result['drive_duration'] = 0
                result['reminder_type'] = 'simple_countdown'

        # Extract time
        now = datetime.now()
        time_patterns = [
            r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2) or 0)
                period = match.group(3).lower()

                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0

                arrival = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if arrival <= now:
                    arrival += timedelta(days=1)

                result['arrival_time'] = arrival.isoformat()
                result['confidence'] = 0.7
                break

        # Calculate confidence
        if result['destination']:
            result['confidence'] += 0.2
        if result['arrival_time']:
            result['confidence'] += 0.3
        if result['drive_duration'] is not None:
            result['confidence'] += 0.3

        return ParsedReminder(
            destination=result['destination'],
            arrival_time=result['arrival_time'],
            drive_duration=result['drive_duration'],
            reminder_type=result['reminder_type'],
            confidence=min(result['confidence'], 1.0),
            raw_input=input_text,
        )

    def get_confirmation_card(self, parsed: ParsedReminder) -> dict:
        """
        Generate confirmation card data for UI display.

        Args:
            parsed: Parsed reminder from parse()

        Returns:
            Dict with display-ready fields for confirmation UI
        """
        return {
            'destination': parsed.destination,
            'arrival_time': parsed.arrival_time,
            'arrival_time_display': self._format_arrival_time(parsed.arrival_time),
            'drive_duration': parsed.drive_duration,
            'drive_duration_display': self._format_drive_duration(parsed.drive_duration),
            'reminder_type': parsed.reminder_type,
            'confidence': parsed.confidence,
            'confidence_display': self._format_confidence(parsed.confidence),
        }

    def _format_arrival_time(self, arrival_time: Optional[str]) -> str:
        """Format arrival time for display."""
        if not arrival_time:
            return "Not set"
        try:
            dt = datetime.fromisoformat(arrival_time)
            return dt.strftime("%I:%M %p")  # e.g., "09:00 AM"
        except:
            return arrival_time

    def _format_drive_duration(self, drive_duration: Optional[int]) -> str:
        """Format drive duration for display."""
        if drive_duration is None:
            return "Not set"
        if drive_duration == 0:
            return "Timer"
        return f"{drive_duration} min"

    def _format_confidence(self, confidence: float) -> str:
        """Format confidence as human-readable string."""
        if confidence >= 0.9:
            return "High"
        elif confidence >= 0.7:
            return "Medium"
        elif confidence >= 0.5:
            return "Low"
        else:
            return "Very Low"


def create_parser(adapter: Optional[ILanguageModelAdapter] = None) -> ReminderParser:
    """
    Factory function to create a ReminderParser.

    Args:
        adapter: Optional LLM adapter

    Returns:
        Configured ReminderParser instance
    """
    return ReminderParser(adapter=adapter)