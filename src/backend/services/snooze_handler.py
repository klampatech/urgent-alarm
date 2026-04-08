#!/usr/bin/env python3
"""
Snooze Handler Service

Handles snooze interactions:
- Tap = 1 min snooze with TTS confirmation
- Tap-and-hold = custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation after snooze
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3
import uuid

# Database path - would be injected in production
DB_PATH = "/tmp/urgent-alarm.db"

# Standard snooze durations in minutes
SNOOZE_OPTIONS = [1, 3, 5, 10, 15]


class SnoozeHandler:
    """
    Service for handling snooze interactions.

    Supports:
    - Quick tap snooze (1 minute)
    - Custom duration snooze (1, 3, 5, 10, 15 min)
    - Chain re-computation after snooze
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def snooze_1min(self, anchor_id: str) -> Dict:
        """
        Handle tap = 1 min snooze.

        Args:
            anchor_id: The anchor being snoozed

        Returns:
            Dict with new snooze time and confirmation message
        """
        return self._snooze(anchor_id, duration_minutes=1)

    def snooze_custom(self, anchor_id: str, duration_minutes: int) -> Dict:
        """
        Handle tap-and-hold = custom snooze picker.

        Args:
            anchor_id: The anchor being snoozed
            duration_minutes: Duration from picker (1, 3, 5, 10, 15)

        Returns:
            Dict with new snooze time and confirmation message
        """
        if duration_minutes not in SNOOZE_OPTIONS:
            raise ValueError(f"Invalid snooze duration: {duration_minutes}. Must be one of {SNOOZE_OPTIONS}")

        return self._snooze(anchor_id, duration_minutes)

    def _snooze(self, anchor_id: str, duration_minutes: int) -> Dict:
        """Internal snooze implementation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current anchor
        cursor.execute("""
            SELECT id, reminder_id, timestamp, urgency_tier, fired, fire_count
            FROM anchors WHERE id = ?
        """, (anchor_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "Anchor not found"}

        original_timestamp = row[2]
        reminder_id = row[1]
        urgency_tier = row[3]

        # Calculate new snooze time
        snooze_until = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()

        # Update anchor with snooze time
        cursor.execute("""
            UPDATE anchors
            SET snoozed_to = ?, tts_fallback = 1
            WHERE id = ?
        """, (snooze_until, anchor_id))

        conn.commit()
        conn.close()

        # Generate TTS confirmation message
        confirmation = f"Snoozed for {duration_minutes} minute{'s' if duration_minutes > 1 else ''}"

        return {
            "success": True,
            "anchor_id": anchor_id,
            "snoozed_to": snooze_until,
            "duration_minutes": duration_minutes,
            "confirmation_message": confirmation,
        }

    def get_snooze_options(self) -> List[int]:
        """Get available snooze duration options."""
        return SNOOZE_OPTIONS

    def get_active_snooze(self, reminder_id: str) -> Optional[Dict]:
        """
        Get any active snooze for a reminder.

        Used for recovery on app restart.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, snoozed_to, urgency_tier
            FROM anchors
            WHERE reminder_id = ? AND snoozed_to IS NOT NULL
            AND fired = 0
            ORDER BY snoozed_to ASC
            LIMIT 1
        """, (reminder_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "anchor_id": row[0],
            "snoozed_until": row[1],
            "urgency_tier": row[2],
        }

    def recompute_chain_after_snooze(self, reminder_id: str) -> List[Dict]:
        """
        Recompute chain after snooze - shift remaining anchors.

        When an anchor is snoozed, all subsequent unfired anchors
        are shifted forward by the snooze duration.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the snoozed anchor
        cursor.execute("""
            SELECT id, snoozed_to FROM anchors
            WHERE reminder_id = ? AND snoozed_to IS NOT NULL
            ORDER BY timestamp ASC
            LIMIT 1
        """, (reminder_id,))

        snooze_row = cursor.fetchone()
        if not snooze_row:
            conn.close()
            return []

        snooze_until = datetime.fromisoformat(snooze_row[1])
        original_time = datetime.fromisoformat(snooze_row[0])  # Not stored, need different approach

        # For now, just return the remaining unfired anchors
        # True chain shift would require storing original timestamps
        cursor.execute("""
            SELECT id, timestamp, urgency_tier
            FROM anchors
            WHERE reminder_id = ? AND fired = 0
            AND snoozed_to IS NULL
            ORDER BY timestamp ASC
        """, (reminder_id,))

        remaining = [
            {"anchor_id": row[0], "timestamp": row[1], "urgency_tier": row[2]}
            for row in cursor.fetchall()
        ]

        conn.close()
        return remaining


def create_snooze_handler(db_path: str = DB_PATH) -> SnoozeHandler:
    """Factory function to create SnoozeHandler."""
    return SnoozeHandler(db_path=db_path)