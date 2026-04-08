#!/usr/bin/env python3
"""
Dismissal Handler Service

Handles dismissal interactions:
- Swipe-to-dismiss with feedback prompt
- Records outcome in history
- Updates destination adjustments based on feedback
"""

from datetime import datetime
from typing import Optional, Dict, List
import sqlite3
import uuid

# Database path - would be injected in production
DB_PATH = "/tmp/urgent-alarm.db"

# Feedback types for dismissal
FEEDBACK_TYPES = [
    "left_early",       # User left early, arrived with time to spare
    "on_time",          # User arrived on time
    "left_too_late",    # User left too late
    "cancelled",        # Reminder was cancelled
    "not_needed",       # Destination no longer needed
]


class DismissalHandler:
    """
    Service for handling dismissal interactions.

    Supports:
    - Swipe-to-dismiss with feedback prompt
    - Outcome recording in history
    - Feedback-driven drive duration adjustment
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def dismiss_with_feedback(
        self,
        anchor_id: str,
        outcome: str,
        feedback_type: Optional[str] = None
    ) -> Dict:
        """
        Handle swipe-to-dismiss with feedback.

        Args:
            anchor_id: The anchor being dismissed
            outcome: One of 'hit', 'miss', 'cancelled'
            feedback_type: Optional feedback for misses

        Returns:
            Dict with dismissal result and any adjustments
        """
        if outcome not in ['hit', 'miss', 'cancelled']:
            raise ValueError(f"Invalid outcome: {outcome}")

        if outcome == 'miss' and feedback_type not in FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type: {feedback_type}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get anchor and reminder info
        cursor.execute("""
            SELECT id, reminder_id, timestamp, urgency_tier
            FROM anchors WHERE id = ?
        """, (anchor_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "Anchor not found"}

        reminder_id = row[1]
        scheduled_time = row[2]
        urgency_tier = row[3]

        # Get reminder destination
        cursor.execute("""
            SELECT destination, arrival_time FROM reminders WHERE id = ?
        """, (reminder_id,))

        reminder_row = cursor.fetchone()
        destination = reminder_row[0] if reminder_row else "unknown"

        # Mark anchor as fired
        cursor.execute("""
            UPDATE anchors SET fired = 1, fire_count = fire_count + 1
            WHERE id = ?
        """, (anchor_id,))

        # Record in history
        history_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO history (id, reminder_id, destination, scheduled_arrival, outcome, feedback_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (history_id, reminder_id, destination, scheduled_time, outcome, feedback_type, now))

        # Update destination adjustments based on feedback
        adjustment_result = None
        if outcome == 'miss' and feedback_type == 'left_too_late':
            adjustment_result = self._update_adjustment(cursor, destination)

        conn.commit()
        conn.close()

        return {
            "success": True,
            "anchor_id": anchor_id,
            "outcome": outcome,
            "feedback_type": feedback_type,
            "history_id": history_id,
            "adjustment": adjustment_result,
        }

    def _update_adjustment(self, cursor, destination: str) -> Dict:
        """
        Update destination adjustment based on miss feedback.

        Applies +2 min per miss, capped at +15 min total (per spec).
        """
        # Get current adjustment
        cursor.execute("""
            SELECT adjustment_minutes FROM destination_adjustments
            WHERE destination = ?
        """, (destination,))

        row = cursor.fetchone()
        current_adj = row[0] if row else 0

        # Cap at +15 min
        new_adj = min(current_adj + 2, 15)

        # Update or insert
        cursor.execute("""
            INSERT INTO destination_adjustments (destination, adjustment_minutes, miss_count)
            VALUES (?, ?, 1)
            ON CONFLICT(destination) DO UPDATE SET
                adjustment_minutes = ?,
                miss_count = miss_count + 1
        """, (destination, new_adj, new_adj))

        return {
            "destination": destination,
            "previous_adjustment": current_adj,
            "new_adjustment": new_adj,
            "change": new_adj - current_adj,
        }

    def get_feedback_options(self, outcome: str) -> List[str]:
        """
        Get available feedback options based on outcome.

        Args:
            outcome: The outcome type

        Returns:
            List of applicable feedback types
        """
        if outcome == "miss":
            return ["left_too_late", "cancelled", "not_needed"]
        elif outcome == "hit":
            return ["left_early", "on_time"]
        else:
            return []

    def dismiss_early_hit(self, anchor_id: str, feedback_type: str = "left_early") -> Dict:
        """
        Quick dismissal for early arrival (hit).

        Convenience method for on-time or early arrivals.
        """
        return self.dismiss_with_feedback(anchor_id, "hit", feedback_type)

    def dismiss_late_miss(self, anchor_id: str, feedback_type: str = "left_too_late") -> Dict:
        """
        Quick dismissal for late arrival (miss).

        Convenience method for missed arrivals.
        """
        return self.dismiss_with_feedback(anchor_id, "miss", feedback_type)

    def get_dismissal_history(self, reminder_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent dismissal history for a reminder.

        Used for displaying dismissal history in UI.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, outcome, feedback_type, created_at
            FROM history
            WHERE reminder_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (reminder_id, limit))

        history = [
            {
                "history_id": row[0],
                "outcome": row[1],
                "feedback_type": row[2],
                "timestamp": row[3],
            }
            for row in cursor.fetchall()
        ]

        conn.close()
        return history


def create_dismissal_handler(db_path: str = DB_PATH) -> DismissalHandler:
    """Factory function to create DismissalHandler."""
    return DismissalHandler(db_path=db_path)