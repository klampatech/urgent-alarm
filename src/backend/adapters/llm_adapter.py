#!/usr/bin/env python3
"""
Language Model Adapter Interface

Defines the contract for LLM-powered reminder parsing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedReminder:
    """Result of parsing a natural language reminder."""
    destination: str
    arrival_time: Optional[str]  # ISO format
    drive_duration: Optional[int]  # minutes
    reminder_type: str  # 'countdown_event', 'simple_countdown', etc.
    confidence: float  # 0.0 - 1.0
    raw_input: str


class ILanguageModelAdapter(ABC):
    """
    Interface for language model adapters.

    Implementations must provide:
    - parse_reminder: Parse natural language input
    - is_available: Check if the adapter can make requests
    """

    @abstractmethod
    def parse_reminder(self, input_text: str) -> ParsedReminder:
        """
        Parse a natural language reminder string.

        Args:
            input_text: Raw user input like "30 min drive to downtown, 9am meeting"

        Returns:
            ParsedReminder with extracted fields and confidence score

        Raises:
            LLMParseError: If parsing fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM service is available.

        Returns:
            True if the adapter can make requests, False otherwise
        """
        pass


class LLMParseError(Exception):
    """Error raised when LLM parsing fails."""
    pass