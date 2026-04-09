#!/usr/bin/env python3
"""
Notification & Alarm Behavior Service

Handles notification tier escalation and DND handling:
- Tier sounds: chime (calm/casual), beep (pointed/urgent), siren (pushing/firm), alarm loop (critical/alarm)
- DND: silent notification pre-5-min, visual+vibration at T-5
- Quiet hours: suppress 10pm-7am (configurable), queue post-quiet-hours
- Chain overlap: serialize, queue new anchors until current completes
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/urgent-alarm.db"


class UrgencyTier(Enum):
    CALM = "calm"
    CASUAL = "casual"
    POINTED = "pointed"
    URGENT = "urgent"
    PUSHING = "pushing"
    FIRM = "firm"
    CRITICAL = "critical"
    ALARM = "alarm"


class NotificationSound(Enum):
    CHIME = "chime"           # calm/casual
    BEEP = "beep"             # pointed/urgent
    SIREN = "siren"           # pushing/firm
    ALARM_LOOP = "alarm_loop" # critical/alarm


# Map urgency tiers to notification sounds
TIER_TO_SOUND = {
    UrgencyTier.CALM: NotificationSound.CHIME,
    UrgencyTier.CASUAL: NotificationSound.CHIME,
    UrgencyTier.POINTED: NotificationSound.BEEP,
    UrgencyTier.URGENT: NotificationSound.BEEP,
    UrgencyTier.PUSHING: NotificationSound.SIREN,
    UrgencyTier.FIRM: NotificationSound.SIREN,
    UrgencyTier.CRITICAL: NotificationSound.ALARM_LOOP,
    UrgencyTier.ALARM: NotificationSound.ALARM_LOOP,
}

# Map urgency tiers to vibration patterns
TIER_TO_VIBRATION = {
    UrgencyTier.CALM: None,
    UrgencyTier.CASUAL: None,
    UrgencyTier.POINTED: None,
    UrgencyTier.URGENT: None,
    UrgencyTier.PUSHING: "short",
    UrgencyTier.FIRM: "medium",
    UrgencyTier.CRITICAL: "long",
    UrgencyTier.ALARM: "repeat",
}

# Final 5 minutes threshold
FINAL_FIVE_MINUTES = 5


@dataclass
class NotificationConfig:
    """Configuration for a notification."""
    anchor_id: str
    reminder_id: str
    destination: str
    urgency_tier: str
    time_remaining_minutes: int
    tts_clip_path: Optional[str]
    play_sound: bool
    vibrate: bool
    override_dnd: bool


@dataclass
class QuietHours:
    """Quiet hours configuration."""
    enabled: bool
    start_hour: int  # 0-23
    end_hour: int    # 0-7


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_quiet_hours() -> QuietHours:
    """Get current quiet hours configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value FROM user_preferences WHERE key = 'quiet_hours_enabled'
    """)
    row = cursor.fetchone()
    enabled = row and row['value'] == 'true'

    cursor.execute("""
        SELECT value FROM user_preferences WHERE key = 'quiet_hours_start'
    """)
    row = cursor.fetchone()
    start = int(row['value']) if row else 22  # Default 10pm

    cursor.execute("""
        SELECT value FROM user_preferences WHERE key = 'quiet_hours_end'
    """)
    row = cursor.fetchone()
    end = int(row['value']) if row else 7  # Default 7am

    conn.close()
    return QuietHours(enabled=enabled, start_hour=start, end_hour=end)


def is_quiet_hours_active() -> bool:
    """Check if current time is within quiet hours."""
    config = get_quiet_hours()
    if not config.enabled:
        return False

    now = datetime.now()
    current_hour = now.hour

    # Handle overnight quiet hours (e.g., 10pm - 7am)
    if config.start_hour > config.end_hour:
        # Overnight: e.g., 22:00 - 07:00
        return current_hour >= config.start_hour or current_hour < config.end_hour
    else:
        # Same day: e.g., 14:00 - 18:00
        return config.start_hour <= current_hour < config.end_hour


def should_override_dnd(urgency_tier: str, time_remaining_minutes: int) -> bool:
    """
    Determine if notification should override DND.
    Pre-5-min: silent notification
    T-5 and after: visual + vibration override
    """
    tier = UrgencyTier(urgency_tier)
    return time_remaining_minutes <= FINAL_FIVE_MINUTES


def get_notification_sound(urgency_tier: str) -> NotificationSound:
    """Get the notification sound for an urgency tier."""
    try:
        tier = UrgencyTier(urgency_tier)
        return TIER_TO_SOUND[tier]
    except ValueError:
        return NotificationSound.CHIME


def get_vibration_pattern(urgency_tier: str) -> Optional[str]:
    """Get the vibration pattern for an urgency tier."""
    try:
        tier = UrgencyTier(urgency_tier)
        return TIER_TO_VIBRATION[tier]
    except ValueError:
        return None


def is_dnd_active() -> bool:
    """
    Check if Do Not Disturb is active.
    In a real implementation, this would query the system.
    For testing, we check a user preference.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value FROM user_preferences WHERE key = 'dnd_enabled'
    """)
    row = cursor.fetchone()
    conn.close()

    return row and row['value'] == 'true'


def build_notification_config(
    anchor_id: str,
    reminder_id: str,
    destination: str,
    urgency_tier: str,
    time_remaining_minutes: int,
    tts_clip_path: Optional[str]
) -> NotificationConfig:
    """Build notification configuration for an anchor."""

    dnd_active = is_dnd_active()
    quiet_active = is_quiet_hours_active()

    # Determine if this anchor should fire or be suppressed
    override_dnd = should_override_dnd(urgency_tier, time_remaining_minutes)

    # Determine sound and vibration
    sound = get_notification_sound(urgency_tier)
    vibration = get_vibration_pattern(urgency_tier)

    # If DND is active and not overriding, suppress sound
    play_sound = True
    if dnd_active and not override_dnd:
        play_sound = False

    # If quiet hours is active, suppress all notifications
    if quiet_active:
        play_sound = False

    # Vibration happens at T-5 and beyond
    vibrate = vibration is not None and time_remaining_minutes <= FINAL_FIVE_MINUTES

    return NotificationConfig(
        anchor_id=anchor_id,
        reminder_id=reminder_id,
        destination=destination,
        urgency_tier=urgency_tier,
        time_remaining_minutes=time_remaining_minutes,
        tts_clip_path=tts_clip_path,
        play_sound=play_sound,
        vibrate=vibrate,
        override_dnd=override_dnd
    )


def should_fire_anchor(
    anchor_id: str,
    urgency_tier: str,
    scheduled_time: datetime,
    original_scheduled_time: Optional[datetime] = None
) -> tuple[bool, Optional[str]]:
    """
    Determine if an anchor should fire, be suppressed, or queued.
    Returns (should_fire, suppression_reason)
    """

    now = datetime.now()
    dnd_active = is_dnd_active()
    quiet_active = is_quiet_hours_active()

    try:
        tier = UrgencyTier(urgency_tier)
    except ValueError:
        return False, "invalid_urgency_tier"

    # Calculate time remaining
    if original_scheduled_time:
        # This anchor was snoozed
        time_remaining = (original_scheduled_time - now).total_seconds() / 60
    else:
        time_remaining = (scheduled_time - now).total_seconds() / 60

    # Check if overdue by more than 15 minutes
    if time_remaining < -15:
        return False, "overdue_dropped"

    # Check quiet hours
    if quiet_active and time_remaining > 0:
        # Queue for post-quiet-hours
        return False, "quiet_hours_queue"

    # Check DND
    if dnd_active:
        if time_remaining > FINAL_FIVE_MINUTES:
            # Pre-5-min: silent notification only
            return True, None  # Fire but as silent
        else:
            # T-5 and beyond: override DND with visual + vibration
            return True, None

    return True, None


def get_notification_title(urgency_tier: str, destination: str, time_remaining: int) -> str:
    """Generate notification title based on urgency tier."""

    titles = {
        "calm": f"Reminder: {destination}",
        "casual": f"Upcoming: {destination}",
        "pointed": f"Time to leave: {destination}",
        "urgent": f"Leave now: {destination}",
        "pushing": f"GO: {destination}",
        "firm": f"LEAVE NOW: {destination}",
        "critical": f"YOU'RE LATE: {destination}",
        "alarm": f"ALARM: {destination}",
    }

    return titles.get(urgency_tier, f"Reminder: {destination}")


def get_notification_body(time_remaining_minutes: int) -> str:
    """Generate notification body with time remaining."""

    if time_remaining_minutes >= 60:
        hours = time_remaining_minutes // 60
        mins = time_remaining_minutes % 60
        if mins > 0:
            return f"{hours}h {mins}m remaining"
        return f"{hours}h remaining"
    elif time_remaining_minutes == 1:
        return "1 minute remaining"
    elif time_remaining_minutes == 0:
        return "Arrival time!"
    else:
        return f"{time_remaining_minutes} minutes remaining"


def format_notification(
    urgency_tier: str,
    destination: str,
    time_remaining_minutes: int
) -> tuple[str, str]:
    """Format notification title and body."""
    title = get_notification_title(urgency_tier, destination, time_remaining_minutes)
    body = get_notification_body(time_remaining_minutes)
    return title, body


# Chain overlap handling
_is_chain_firing = False


def set_chain_firing(firing: bool) -> None:
    """Set whether a chain is currently firing (for serialization)."""
    global _is_chain_firing
    _is_chain_firing = firing


def is_chain_firing() -> bool:
    """Check if a chain is currently firing."""
    return _is_chain_firing


def queue_anchor_for_later(anchor_id: str) -> bool:
    """
    Queue an anchor to fire after the current chain completes.
    In a real implementation, this would persist to a queue.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Store the queued anchor
    cursor.execute("""
        INSERT OR REPLACE INTO user_preferences (key, value)
        VALUES ('queued_anchor_' || ?, datetime('now'))
    """, (anchor_id,))

    conn.commit()
    conn.close()

    logger.info(f"Queued anchor {anchor_id} for later execution")
    return True


def get_queued_anchors() -> list[str]:
    """Get list of queued anchor IDs."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT key FROM user_preferences
        WHERE key LIKE 'queued_anchor_%'
    """)

    rows = cursor.fetchall()
    conn.close()

    return [row['key'].replace('queued_anchor_', '') for row in rows]


def clear_queued_anchors() -> int:
    """Clear all queued anchors. Returns count cleared."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_preferences
        WHERE key LIKE 'queued_anchor_%'
    """)

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected
