#!/usr/bin/env python3
"""
Apple Calendar Adapter

Implements calendar integration via EventKit (iOS).
In production, this would use the native EventKit framework via a React Native bridge.
For backend testing, we provide a mock implementation.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .calendar_adapter import (
    ICalendarAdapter, CalendarEvent, CalendarType, ReminderSuggestion
)

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/urgent-alarm.db"


class AppleCalendarAdapter(ICalendarAdapter):
    """Apple Calendar adapter using EventKit."""

    def __init__(self):
        self._connected = False
        self._last_sync: Optional[datetime] = None

    def is_connected(self) -> bool:
        """Check if calendar is connected/authorized."""
        # Check stored state
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_connected FROM calendar_sync
            WHERE calendar_type = 'apple'
        """)
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 1

    def connect(self) -> bool:
        """Connect to calendar (request permissions)."""
        # In production, this would trigger EventKit permission request
        # For now, just mark as connected in our sync state
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO calendar_sync
            (calendar_type, is_connected, last_sync_at)
            VALUES ('apple', 1, NULL)
        """)

        conn.commit()
        self._connected = True
        conn.close()

        logger.info("Apple Calendar connected")
        return True

    def disconnect(self) -> bool:
        """Disconnect from calendar."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE calendar_sync
            SET is_connected = 0
            WHERE calendar_type = 'apple'
        """)

        conn.commit()
        self._connected = False
        conn.close()

        logger.info("Apple Calendar disconnected")
        return True

    def get_events(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[CalendarEvent]:
        """Get calendar events within a date range."""
        # In production, this would query EventKit
        # For testing, return empty list
        logger.debug(f"Getting Apple Calendar events from {start_date} to {end_date}")
        return []

    def get_events_with_location(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[CalendarEvent]:
        """Get calendar events that have a location (for departure suggestions)."""
        events = self.get_events(start_date, end_date)
        return [e for e in events if e.location]

    def get_suggestions(
        self,
        start_date: datetime,
        end_date: datetime,
        default_drive_duration: int = 15
    ) -> list[ReminderSuggestion]:
        """Get reminder suggestions from events with locations."""
        events = self.get_events_with_location(start_date, end_date)
        suggestions = []

        for event in events:
            suggestions.append(ReminderSuggestion(
                event=event,
                suggested_drive_duration=default_drive_duration,
                confidence=0.9 if event.location else 0.5
            ))

        return suggestions

    def sync(self) -> bool:
        """Perform a full sync of calendar events."""
        if not self.is_connected():
            logger.warning("Cannot sync Apple Calendar - not connected")
            return False

        now = datetime.now()
        start = now - timedelta(days=1)
        end = now + timedelta(days=30)  # Sync next 30 days

        events = self.get_events(start, end)
        logger.info(f"Apple Calendar sync: {len(events)} events")

        self._last_sync = now
        return True

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT last_sync_at FROM calendar_sync
            WHERE calendar_type = 'apple'
        """)
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None


def get_apple_calendar_adapter() -> AppleCalendarAdapter:
    """Get the Apple Calendar adapter instance."""
    return AppleCalendarAdapter()
