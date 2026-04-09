#!/usr/bin/env python3
"""
Background Scheduling Service

Handles scheduling of anchor firing with:
- Individual anchor task scheduling
- Recovery scan on app launch
- Re-registration after crash recovery
- Late fire logging

This service provides the backend logic that the Notifee mobile integration
would consume when anchors are scheduled.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/urgent-alarm.db"
GRACE_WINDOW_MINUTES = 15
LATE_FIRE_THRESHOLD_SECONDS = 60


class AnchorStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    FIRED = "fired"
    MISSED = "missed"
    SNOOZED = "snoozed"


@dataclass
class ScheduledAnchor:
    id: str
    reminder_id: str
    timestamp: datetime
    urgency_tier: str
    tts_clip_path: Optional[str]
    fired: bool
    fire_count: int
    snoozed_to: Optional[datetime]
    tts_fallback: bool


def get_db_connection():
    """Get database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_pending_anchors(reminder_id: Optional[str] = None) -> list[ScheduledAnchor]:
    """Get all pending (unfired) anchors, optionally filtered by reminder."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if reminder_id:
        cursor.execute("""
            SELECT * FROM anchors
            WHERE fired = 0 AND reminder_id = ?
            ORDER BY timestamp ASC
        """, (reminder_id,))
    else:
        cursor.execute("""
            SELECT * FROM anchors
            WHERE fired = 0
            ORDER BY timestamp ASC
        """)

    rows = cursor.fetchall()
    conn.close()

    anchors = []
    for row in rows:
        anchors.append(ScheduledAnchor(
            id=row['id'],
            reminder_id=row['reminder_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            urgency_tier=row['urgency_tier'],
            tts_clip_path=row['tts_clip_path'],
            fired=bool(row['fired']),
            fire_count=row['fire_count'],
            snoozed_to=datetime.fromisoformat(row['snoozed_to']) if row['snoozed_to'] else None,
            tts_fallback=bool(row['tts_fallback'])
        ))
    return anchors


def get_overdue_anchors() -> list[ScheduledAnchor]:
    """Get anchors that are within the grace window and should fire."""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()
    grace_cutoff = now + timedelta(minutes=GRACE_WINDOW_MINUTES)

    cursor.execute("""
        SELECT * FROM anchors
        WHERE fired = 0
        AND (
            timestamp <= datetime('now')
            OR (snoozed_to IS NOT NULL AND snoozed_to <= datetime('now'))
        )
        AND timestamp > datetime('now', '-' || ? || ' minutes')
        ORDER BY timestamp ASC
    """, (GRACE_WINDOW_MINUTES,))

    rows = cursor.fetchall()
    conn.close()

    anchors = []
    for row in rows:
        anchors.append(ScheduledAnchor(
            id=row['id'],
            reminder_id=row['reminder_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            urgency_tier=row['urgency_tier'],
            tts_clip_path=row['tts_clip_path'],
            fired=bool(row['fired']),
            fire_count=row['fire_count'],
            snoozed_to=datetime.fromisoformat(row['snoozed_to']) if row['snoozed_to'] else None,
            tts_fallback=bool(row['tts_fallback'])
        ))
    return anchors


def get_missed_anchors() -> list[ScheduledAnchor]:
    """Get anchors that missed their scheduled time by more than the grace window."""
    conn = get_db_connection()
    cursor = conn.cursor()

    grace_cutoff = datetime.now() - timedelta(minutes=GRACE_WINDOW_MINUTES)

    cursor.execute("""
        SELECT * FROM anchors
        WHERE fired = 0
        AND timestamp < ?
        ORDER BY timestamp ASC
    """, (grace_cutoff.isoformat(),))

    rows = cursor.fetchall()
    conn.close()

    anchors = []
    for row in rows:
        anchors.append(ScheduledAnchor(
            id=row['id'],
            reminder_id=row['reminder_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            urgency_tier=row['urgency_tier'],
            tts_clip_path=row['tts_clip_path'],
            fired=bool(row['fired']),
            fire_count=row['fire_count'],
            snoozed_to=datetime.fromisoformat(row['snoozed_to']) if row['snoozed_to'] else None,
            tts_fallback=bool(row['tts_fallback'])
        ))
    return anchors


def mark_anchor_fired(anchor_id: str, late_seconds: Optional[int] = None) -> bool:
    """Mark an anchor as fired. Returns True if successful."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Log late fires
    if late_seconds and late_seconds > LATE_FIRE_THRESHOLD_SECONDS:
        logger.warning(
            f"Late anchor fire: anchor_id={anchor_id}, "
            f"late_seconds={late_seconds}"
        )

    cursor.execute("""
        UPDATE anchors
        SET fired = 1, fire_count = fire_count + 1
        WHERE id = ?
    """, (anchor_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def mark_anchor_missed(anchor_id: str, missed_reason: str) -> bool:
    """Mark an anchor as missed with a reason."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE anchors
        SET fired = 1, fire_count = fire_count + 1
        WHERE id = ?
    """, (anchor_id,))

    # Record in history
    cursor.execute("""
        SELECT reminder_id FROM anchors WHERE id = ?
    """, (anchor_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            INSERT INTO history (id, reminder_id, destination, scheduled_arrival, outcome, missed_reason, created_at)
            SELECT ?, reminder_id, destination, arrival_time, 'miss', ?, datetime('now')
            FROM reminders WHERE id = ?
        """, (str(uuid.uuid4()), missed_reason, row['reminder_id']))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def recovery_scan() -> dict:
    """
    Run recovery scan on app launch.
    Fires anchors within grace window, drops overdue anchors.
    Returns scan results.
    """
    now = datetime.now()
    results = {
        "fired": [],
        "missed": [],
        "skipped": []
    }

    # Get overdue anchors (more than grace window late)
    missed_anchors = get_missed_anchors()
    for anchor in missed_anchors:
        mark_anchor_missed(anchor.id, "background_task_killed")
        results["missed"].append({
            "anchor_id": anchor.id,
            "reason": "background_task_killed"
        })
        logger.info(f"Recovery scan: dropped overdue anchor {anchor.id}")

    # Get anchors within grace window that should fire
    overdue_anchors = get_overdue_anchors()
    for anchor in overdue_anchors:
        # Calculate late seconds
        scheduled_time = anchor.snoozed_to or anchor.timestamp
        late_seconds = int((now - scheduled_time).total_seconds())

        if mark_anchor_fired(anchor.id, late_seconds):
            results["fired"].append({
                "anchor_id": anchor.id,
                "late_seconds": late_seconds
            })
            logger.info(f"Recovery scan: fired overdue anchor {anchor.id}, late by {late_seconds}s")

    return results


def reregister_pending_anchors() -> int:
    """
    Re-register all pending (unfired) anchors with the scheduler.
    Returns count of re-registered anchors.
    This is called on app launch after crash/termination.
    """
    pending = get_pending_anchors()
    count = len(pending)

    logger.info(f"Re-registering {count} pending anchors with scheduler")

    # In a real implementation, this would schedule each anchor with Notifee
    # For the Python backend, we just log the pending anchors
    for anchor in pending:
        logger.debug(f"Pending anchor: {anchor.id} at {anchor.timestamp}")

    return count


def get_next_scheduled_anchor() -> Optional[ScheduledAnchor]:
    """Get the next anchor scheduled to fire."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM anchors
        WHERE fired = 0
        ORDER BY timestamp ASC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return ScheduledAnchor(
        id=row['id'],
        reminder_id=row['reminder_id'],
        timestamp=datetime.fromisoformat(row['timestamp']),
        urgency_tier=row['urgency_tier'],
        tts_clip_path=row['tts_clip_path'],
        fired=bool(row['fired']),
        fire_count=row['fire_count'],
        snoozed_to=datetime.fromisoformat(row['snoozed_to']) if row['snoozed_to'] else None,
        tts_fallback=bool(row['tts_fallback'])
    )


def schedule_anchor(anchor_id: str) -> bool:
    """
    Schedule an anchor with the background scheduler (Notifee).
    Returns True if successfully scheduled.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM anchors WHERE id = ?
    """, (anchor_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    anchor = ScheduledAnchor(
        id=row['id'],
        reminder_id=row['reminder_id'],
        timestamp=datetime.fromisoformat(row['timestamp']),
        urgency_tier=row['urgency_tier'],
        tts_clip_path=row['tts_clip_path'],
        fired=bool(row['fired']),
        fire_count=row['fire_count'],
        snoozed_to=datetime.fromisoformat(row['snoozed_to']) if row['snoozed_to'] else None,
        tts_fallback=bool(row['tts_fallback'])
    )

    # In a real implementation, this would call Notifee API
    # For now, we just log that the anchor would be scheduled
    scheduled_time = anchor.snoozed_to or anchor.timestamp
    logger.info(f"Scheduling anchor {anchor_id} for {scheduled_time.isoformat()}")

    conn.close()
    return True


# Import uuid for generating history IDs
import uuid
