"""
Feedback Loop Service

Per spec Section 11.4: Handles drive duration adjustments based on user feedback.
When a user reports "left too late", this service adjusts the drive_duration
estimate for that destination for future reminders.

The adjustment formula per spec Section 11.4:
- adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)
- Capped at +15 minutes maximum

This service stores adjustments in the destination_adjustments table.
"""

import sqlite3
from dataclasses import dataclass
from typing import Optional
import os

# Use the same DB path convention as other services
DB_PATH = os.environ.get("DB_PATH", "/tmp/urgent-alarm.db")

# Maximum adjustment cap per spec Section 11.4
MAX_ADJUSTMENT_MINUTES = 15
ADJUSTMENT_INCREMENT_MINUTES = 2


@dataclass
class DriveAdjustment:
    """Represents the drive duration adjustment for a destination."""
    destination: str
    adjustment_minutes: int
    hit_count: int
    miss_count: int


class FeedbackLoop:
    """
    Handles feedback-driven drive duration adjustments.

    When a user dismisses an alarm with "left too late" feedback,
    this service increments the adjustment for that destination.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_feedback(
        self,
        destination: str,
        outcome: str,
        feedback_type: Optional[str] = None
    ) -> DriveAdjustment:
        """
        Record user feedback and adjust drive duration if needed.

        Args:
            destination: The destination address
            outcome: "hit" (on time) or "miss" (late)
            feedback_type: For misses, the feedback category (e.g., "left_too_late")

        Returns:
            DriveAdjustment with updated values

        Per spec Section 11.4:
        - On "left_too_late" feedback: add 2 minutes, capped at +15
        - On "hit" outcome: increment hit_count for tracking
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current adjustment
        cursor.execute(
            "SELECT destination, adjustment_minutes, hit_count, miss_count "
            "FROM destination_adjustments WHERE destination = ?",
            (destination,)
        )
        row = cursor.fetchone()

        if row:
            current_adj = row["adjustment_minutes"]
            hit_count = row["hit_count"]
            miss_count = row["miss_count"]
        else:
            current_adj = 0
            hit_count = 0
            miss_count = 0

        # Apply adjustment based on feedback type
        if outcome == "miss" and feedback_type == "left_too_late":
            new_adj = min(current_adj + ADJUSTMENT_INCREMENT_MINUTES, MAX_ADJUSTMENT_MINUTES)
            miss_count += 1

            cursor.execute("""
                INSERT INTO destination_adjustments
                    (destination, adjustment_minutes, hit_count, miss_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(destination) DO UPDATE SET
                    adjustment_minutes = ?,
                    miss_count = ?
            """, (destination, new_adj, hit_count, miss_count, new_adj, miss_count))

            current_adj = new_adj
        elif outcome == "hit":
            hit_count += 1
            cursor.execute("""
                INSERT INTO destination_adjustments
                    (destination, adjustment_minutes, hit_count, miss_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(destination) DO UPDATE SET
                    hit_count = ?
            """, (destination, current_adj, hit_count, miss_count, hit_count))
        else:
            # Other feedback types don't change adjustment
            pass

        conn.commit()
        conn.close()

        return DriveAdjustment(
            destination=destination,
            adjustment_minutes=current_adj,
            hit_count=hit_count,
            miss_count=miss_count
        )

    def get_adjustment(self, destination: str) -> Optional[DriveAdjustment]:
        """
        Get the current adjustment for a destination.

        Args:
            destination: The destination address

        Returns:
            DriveAdjustment if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT destination, adjustment_minutes, hit_count, miss_count "
            "FROM destination_adjustments WHERE destination = ?",
            (destination,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return DriveAdjustment(
                destination=row["destination"],
                adjustment_minutes=row["adjustment_minutes"],
                hit_count=row["hit_count"],
                miss_count=row["miss_count"]
            )
        return None

    def get_adjusted_drive_duration(self, original_duration: int, destination: str) -> int:
        """
        Calculate the adjusted drive duration for a destination.

        Args:
            original_duration: The base drive duration in minutes
            destination: The destination address

        Returns:
            Adjusted drive duration (original + adjustment, capped at +15)
        """
        adjustment = self.get_adjustment(destination)
        if adjustment:
            return original_duration + adjustment.adjustment_minutes
        return original_duration

    def clear_adjustment(self, destination: str) -> bool:
        """
        Clear the adjustment for a destination (e.g., when user manually resets).

        Args:
            destination: The destination address

        Returns:
            True if adjustment was deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM destination_adjustments WHERE destination = ?",
            (destination,)
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted


def create_feedback_loop(db_path: str = DB_PATH) -> FeedbackLoop:
    """Factory function to create a FeedbackLoop instance."""
    return FeedbackLoop(db_path)