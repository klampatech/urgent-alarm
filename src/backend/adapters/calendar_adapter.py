#!/usr/bin/env python3
"""
Calendar Adapter Interface

Defines the common interface for calendar integrations.
Supports Apple Calendar via EventKit (iOS) and Google Calendar via Google Calendar API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class CalendarType(Enum):
    APPLE = "apple"
    GOOGLE = "google"


@dataclass
class CalendarEvent:
    """Represents a calendar event with location."""
    id: str
    title: str
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    calendar_type: CalendarType
    recurrence: Optional[str] = None  # daily, weekly, etc.


@dataclass
class ReminderSuggestion:
    """A suggested departure reminder from a calendar event."""
    event: CalendarEvent
    suggested_drive_duration: int  # minutes
    confidence: float  # 0.0 - 1.0


class ICalendarAdapter(ABC):
    """Interface for calendar adapters."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if calendar is connected/authorized."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Connect to calendar (request permissions)."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from calendar."""
        pass

    @abstractmethod
    def get_events(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[CalendarEvent]:
        """Get calendar events within a date range."""
        pass

    @abstractmethod
    def get_events_with_location(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[CalendarEvent]:
        """Get calendar events that have a location (for departure suggestions)."""
        pass

    @abstractmethod
    def get_suggestions(
        self,
        start_date: datetime,
        end_date: datetime,
        default_drive_duration: int = 15
    ) -> list[ReminderSuggestion]:
        """Get reminder suggestions from events with locations."""
        pass

    @abstractmethod
    def sync(self) -> bool:
        """Perform a full sync of calendar events."""
        pass

    @abstractmethod
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync."""
        pass
