"""
Unit tests for Feedback Loop Service

Per spec Section 11.4: Tests for drive duration adjustment based on user feedback.
TC-01 through TC-07 per spec Section 11.5.
"""

import pytest
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from backend.services.feedback_loop import (
    FeedbackLoop,
    DriveAdjustment,
    create_feedback_loop,
    MAX_ADJUSTMENT_MINUTES,
    ADJUSTMENT_INCREMENT_MINUTES,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create tables
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create destination_adjustments table (matching schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destination_adjustments (
            destination TEXT PRIMARY KEY,
            adjustment_minutes INTEGER DEFAULT 0,
            hit_count INTEGER DEFAULT 0,
            miss_count INTEGER DEFAULT 0
        )
    """)

    # Create history table (for stats_service tests)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            reminder_id TEXT,
            destination TEXT,
            scheduled_arrival TEXT,
            outcome TEXT,
            feedback_type TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.unlink(path)


class TestFeedbackLoop:
    """Tests for FeedbackLoop class"""

    def test_record_left_too_late_feedback_increments_adjustment(self, temp_db):
        """TC-01: "Left too late" feedback increases adjustment by 2 minutes"""
        feedback_loop = FeedbackLoop(temp_db)

        result = feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        assert result.adjustment_minutes == 2
        assert result.miss_count == 1
        assert result.hit_count == 0

    def test_multiple_left_too_late_feedback_accumulates(self, temp_db):
        """TC-02: Multiple "left too late" feedback events accumulate (+2 min each)"""
        feedback_loop = FeedbackLoop(temp_db)

        # First feedback
        feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        # Second feedback
        result = feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        assert result.adjustment_minutes == 4
        assert result.miss_count == 2

    def test_adjustment_capped_at_15_minutes(self, temp_db):
        """TC-03: Adjustment is capped at +15 minutes maximum"""
        feedback_loop = FeedbackLoop(temp_db)

        # Record 8 "left too_late" events (would be +16, but capped at 15)
        for i in range(8):
            feedback_loop.record_feedback(
                destination="123 Main St",
                outcome="miss",
                feedback_type="left_too_late"
            )

        result = feedback_loop.get_adjustment("123 Main St")
        assert result.adjustment_minutes == MAX_ADJUSTMENT_MINUTES  # 15

    def test_hit_feedback_increments_hit_count(self, temp_db):
        """TC-04: "Hit" feedback increments hit_count without changing adjustment"""
        feedback_loop = FeedbackLoop(temp_db)

        # First, set up a miss
        feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        # Then record a hit
        result = feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="hit",
            feedback_type=None
        )

        assert result.adjustment_minutes == 2  # Still 2 from the miss
        assert result.hit_count == 1
        assert result.miss_count == 1

    def test_get_adjustment_returns_none_for_unknown_destination(self, temp_db):
        """TC-05: Unknown destination returns None"""
        feedback_loop = FeedbackLoop(temp_db)

        result = feedback_loop.get_adjustment("Unknown Address")

        assert result is None

    def test_get_adjusted_drive_duration_adds_adjustment(self, temp_db):
        """TC-06: get_adjusted_drive_duration returns original + adjustment"""
        feedback_loop = FeedbackLoop(temp_db)

        # Set up adjustment
        feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        # Get adjusted duration
        adjusted = feedback_loop.get_adjusted_drive_duration(30, "123 Main St")

        assert adjusted == 32  # 30 + 2

    def test_adjustment_stays_at_cap_after_multiple_events(self, temp_db):
        """TC-07: After reaching cap, further misses don't change adjustment"""
        feedback_loop = FeedbackLoop(temp_db)

        # Add enough misses to hit the cap
        for _ in range(10):  # Would be +20, but capped at 15
            feedback_loop.record_feedback(
                destination="123 Main St",
                outcome="miss",
                feedback_type="left_too_late"
            )

        result = feedback_loop.get_adjustment("123 Main St")
        assert result.adjustment_minutes == MAX_ADJUSTMENT_MINUTES

        # Record one more - should still be capped
        feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        result = feedback_loop.get_adjustment("123 Main St")
        assert result.adjustment_minutes == MAX_ADJUSTMENT_MINUTES

    def test_clear_adjustment_deletes_record(self, temp_db):
        """Clear adjustment removes the destination record"""
        feedback_loop = FeedbackLoop(temp_db)

        # Add adjustment
        feedback_loop.record_feedback(
            destination="123 Main St",
            outcome="miss",
            feedback_type="left_too_late"
        )

        # Clear it
        deleted = feedback_loop.clear_adjustment("123 Main St")

        assert deleted is True
        assert feedback_loop.get_adjustment("123 Main St") is None

    def test_clear_adjustment_returns_false_for_unknown(self, temp_db):
        """Clear adjustment returns False for unknown destination"""
        feedback_loop = FeedbackLoop(temp_db)

        deleted = feedback_loop.clear_adjustment("Unknown Place")

        assert deleted is False


class TestFactoryFunction:
    """Tests for create_feedback_loop factory function"""

    def test_create_feedback_loop_returns_feedback_loop_instance(self):
        """Factory function returns a FeedbackLoop instance"""
        # Use in-memory database for test
        instance = create_feedback_loop(":memory:")
        assert isinstance(instance, FeedbackLoop)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])