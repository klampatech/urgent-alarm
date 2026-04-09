"""
Statistics Service for History and Stats

Per spec Section 11: Computes hit rate, streak, and common miss window from history.
Extracts logic from test_server.py for modularity and testability.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


# Database path - would normally be injected
DB_PATH = '/tmp/urgent_alarm.db'


@dataclass
class StatsResult:
    """Result of stats calculations"""
    hit_rate: float
    total_count: int
    hit_count: int
    miss_count: int


@dataclass
class StreakResult:
    """Result of streak calculation"""
    current_streak: int
    longest_streak: int
    is_recurring: bool


class StatsService:
    """Service for computing user statistics from history"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize stats service.

        Args:
            db_path: Optional path to SQLite database. Defaults to /tmp/urgent_alarm.db
        """
        self.db_path = db_path or DB_PATH

    def get_hit_rate(self, days: int = 7) -> StatsResult:
        """
        Calculate hit rate for trailing N days.

        Per spec Section 11.3:
        - Returns percentage of reminders that were "hit" (user left on time)
        - Excludes pending and in-progress outcomes

        Args:
            days: Number of trailing days to analyze (default 7)

        Returns:
            StatsResult with hit_rate (0-100), total/hit/miss counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT outcome, COUNT(*) as count
            FROM history
            WHERE created_at >= ? AND outcome != 'pending'
            GROUP BY outcome
        """, (cutoff,))

        results = cursor.fetchall()
        conn.close()

        total = sum(r[1] for r in results)
        hits = sum(r[1] for r in results if r[0] == 'hit')
        misses = sum(r[1] for r in results if r[0] == 'miss')

        hit_rate = (hits / total * 100) if total > 0 else 0.0

        return StatsResult(
            hit_rate=hit_rate,
            total_count=total,
            hit_count=hits,
            miss_count=misses,
        )

    def get_streak(self, reminder_id: str) -> StreakResult:
        """
        Calculate current streak for a recurring reminder.

        Per spec Section 11.4:
        - Counts consecutive "hit" outcomes from most recent backward
        - Returns both current and longest streak

        Args:
            reminder_id: The reminder to check streak for

        Returns:
            StreakResult with current_streak, longest_streak, is_recurring
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all history for this reminder, ordered by created_at descending
        cursor.execute("""
            SELECT outcome, created_at
            FROM history
            WHERE reminder_id = ?
            ORDER BY created_at DESC
        """, (reminder_id,))

        results = cursor.fetchall()
        conn.close()

        if not results:
            return StreakResult(current_streak=0, longest_streak=0, is_recurring=False)

        # Check if reminder is recurring (has future scheduled anchors)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM anchors
            WHERE reminder_id = ? AND timestamp > datetime('now')
        """, (reminder_id,))
        is_recurring = cursor.fetchone()[0] > 0
        conn.close()

        # Calculate current streak (consecutive hits from most recent)
        current_streak = 0
        for outcome, _ in results:
            if outcome == 'hit':
                current_streak += 1
            else:
                break

        # Calculate longest streak (any consecutive run)
        longest_streak = 0
        run = 0
        for outcome, _ in results:
            if outcome == 'hit':
                run += 1
                longest_streak = max(longest_streak, run)
            else:
                run = 0

        return StreakResult(
            current_streak=current_streak,
            longest_streak=longest_streak,
            is_recurring=is_recurring,
        )

    def get_common_miss_window(self) -> Optional[str]:
        """
        Find the most frequently missed urgency tier.

        Per spec Section 11.4:
        - Analyzes history to find which tier is most commonly "missed"
        - Helps users understand their problem time windows

        Returns:
            Urgency tier name (e.g., 'urgent', 'pushing') or None if no data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get tier distribution for misses
        cursor.execute("""
            SELECT urgency_tier, COUNT(*) as count
            FROM history
            WHERE outcome = 'miss'
            GROUP BY urgency_tier
            ORDER BY count DESC
            LIMIT 1
        """, ())

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None


# Convenience function for simple usage
def calculate_hit_rate(days: int = 7, db_path: Optional[str] = None) -> float:
    """
    Simple function to calculate hit rate.

    Args:
        days: Number of trailing days
        db_path: Optional database path

    Returns:
        Hit rate as percentage (0-100)
    """
    service = StatsService(db_path)
    return service.get_hit_rate(days).hit_rate