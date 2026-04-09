#!/usr/bin/env python3
"""
Sound Manager

Manages sound selection and playback:
- Bundle 5 built-in sounds per category (commute, routine, errand)
- Support MP3, WAV, M4A import (max 30 sec)
- Transcode and normalize imported sounds
- Per-reminder sound selection
- Custom sounds table in SQLite
- Fallback to category default on corrupted file
"""

import sqlite3
import os
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/urgent-alarm.db"


class SoundCategory(Enum):
    COMMUTE = "commute"
    ROUTINE = "routine"
    ERRAND = "errand"
    CUSTOM = "custom"


@dataclass
class Sound:
    """Represents a sound file."""
    id: str
    filename: str
    original_name: str
    category: SoundCategory
    file_path: str
    duration_seconds: Optional[float] = None
    is_built_in: bool = False


# Built-in sounds (these would be bundled with the app)
BUILT_IN_SOUNDS = {
    SoundCategory.COMMUTE: [
        {"id": "commute_1", "name": "gentle_ding", "duration": 5.0},
        {"id": "commute_2", "name": "soft_chime", "duration": 4.0},
        {"id": "commute_3", "name": "morning_bell", "duration": 6.0},
        {"id": "commute_4", "name": "car_horn_light", "duration": 3.0},
        {"id": "commute_5", "name": "traffic_alert", "duration": 4.0},
    ],
    SoundCategory.ROUTINE: [
        {"id": "routine_1", "name": "kitchen_timer", "duration": 5.0},
        {"id": "routine_2", "name": "alarm_classic", "duration": 8.0},
        {"id": "routine_3", "name": "wake_up_call", "duration": 6.0},
        {"id": "routine_4", "name": "daily_reminder", "duration": 4.0},
        {"id": "routine_5", "name": "check_in", "duration": 5.0},
    ],
    SoundCategory.ERRAND: [
        {"id": "errand_1", "name": "doorbell", "duration": 3.0},
        {"id": "errand_2", "name": "reminder_beep", "duration": 2.0},
        {"id": "errand_3", "name": "ping_notification", "duration": 1.0},
        {"id": "errand_4", "name": "task_complete", "duration": 4.0},
        {"id": "errand_5", "name": "quick_alert", "duration": 2.0},
    ],
}


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_built_in_sounds(category: SoundCategory) -> list[Sound]:
    """Get all built-in sounds for a category."""
    sounds = []
    for sound_data in BUILT_IN_SOUNDS.get(category, []):
        sounds.append(Sound(
            id=sound_data["id"],
            filename=sound_data["name"],
            original_name=sound_data["name"],
            category=category,
            file_path=f"/sounds/built_in/{sound_data['name']}.mp3",
            duration_seconds=sound_data["duration"],
            is_built_in=True
        ))
    return sounds


def get_custom_sounds() -> list[Sound]:
    """Get all custom imported sounds."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM custom_sounds ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    sounds = []
    for row in rows:
        sounds.append(Sound(
            id=row['id'],
            filename=row['filename'],
            original_name=row['original_name'],
            category=SoundCategory(row['category']),
            file_path=row['file_path'],
            duration_seconds=row['duration_seconds'],
            is_built_in=False
        ))
    return sounds


def get_sound_by_id(sound_id: str) -> Optional[Sound]:
    """Get a sound by ID (checks both built-in and custom)."""
    # Check built-in first
    for category in SoundCategory:
        for sound_data in BUILT_IN_SOUNDS.get(category, []):
            if sound_data["id"] == sound_id:
                return Sound(
                    id=sound_data["id"],
                    filename=sound_data["name"],
                    original_name=sound_data["name"],
                    category=category,
                    file_path=f"/sounds/built_in/{sound_data['name']}.mp3",
                    duration_seconds=sound_data["duration"],
                    is_built_in=True
                )

    # Check custom sounds
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM custom_sounds WHERE id = ?
    """, (sound_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return Sound(
            id=row['id'],
            filename=row['filename'],
            original_name=row['original_name'],
            category=SoundCategory(row['category']),
            file_path=row['file_path'],
            duration_seconds=row['duration_seconds'],
            is_built_in=False
        )

    return None


def get_all_sounds_for_category(category: SoundCategory) -> list[Sound]:
    """Get all sounds for a category (built-in + custom)."""
    sounds = get_built_in_sounds(category)

    if category == SoundCategory.CUSTOM:
        # For custom category, only return custom imported sounds
        sounds = get_custom_sounds()
    else:
        # For other categories, also include custom sounds assigned to this category
        custom = get_custom_sounds()
        for c in custom:
            if c.category == category:
                sounds.append(c)

    return sounds


def import_custom_sound(
    original_filename: str,
    file_path: str,
    duration_seconds: Optional[float] = None
) -> Optional[Sound]:
    """
    Import a custom sound file.
    Returns the created Sound object or None on failure.
    """
    import uuid

    # Validate file exists
    if not os.path.exists(file_path):
        logger.error(f"Custom sound file not found: {file_path}")
        return None

    # Validate format
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ['.mp3', '.wav', '.m4a']:
        logger.error(f"Unsupported sound format: {ext}")
        return None

    # Validate duration (max 30 seconds)
    # In production, we'd analyze the file to get actual duration
    if duration_seconds and duration_seconds > 30:
        logger.error(f"Sound too long: {duration_seconds}s (max 30s)")
        return None

    # Generate unique ID
    sound_id = str(uuid.uuid4())

    # In production, we'd copy and transcode to app sandbox
    # For now, just store reference in database

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO custom_sounds (
            id, filename, original_name, category, file_path, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        sound_id,
        f"{sound_id}{ext}",
        original_filename,
        SoundCategory.CUSTOM.value,
        file_path,
        duration_seconds
    ))

    conn.commit()
    conn.close()

    logger.info(f"Imported custom sound: {original_filename}")

    return Sound(
        id=sound_id,
        filename=f"{sound_id}{ext}",
        original_name=original_filename,
        category=SoundCategory.CUSTOM,
        file_path=file_path,
        duration_seconds=duration_seconds,
        is_built_in=False
    )


def delete_custom_sound(sound_id: str) -> bool:
    """Delete a custom sound."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get file path before deleting
    cursor.execute("""
        SELECT file_path FROM custom_sounds WHERE id = ?
    """, (sound_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    file_path = row[0]

    # Delete from database
    cursor.execute("""
        DELETE FROM custom_sounds WHERE id = ?
    """, (sound_id,))

    conn.commit()
    conn.close()

    # In production, also delete the file
    # if os.path.exists(file_path):
    #     os.remove(file_path)

    logger.info(f"Deleted custom sound: {sound_id}")
    return True


def get_sound_for_reminder(reminder_id: str) -> Optional[Sound]:
    """Get the selected sound for a reminder."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT selected_sound FROM reminders WHERE id = ?
    """, (reminder_id,))
    row = cursor.fetchone()

    if not row or not row[0]:
        conn.close()
        return None

    conn.close()
    return get_sound_by_id(row[0])


def set_sound_for_reminder(reminder_id: str, sound_id: str) -> bool:
    """Set the selected sound for a reminder."""
    # Verify sound exists
    sound = get_sound_by_id(sound_id)
    if not sound:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reminders
        SET selected_sound = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (sound_id, reminder_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def get_default_sound(category: SoundCategory) -> Sound:
    """Get the default sound for a category."""
    built_in = get_built_in_sounds(category)
    if built_in:
        return built_in[0]

    # Fallback - shouldn't happen
    return Sound(
        id="default",
        filename="default",
        original_name="Default",
        category=category,
        file_path="/sounds/default.mp3",
        duration_seconds=5.0,
        is_built_in=True
    )


def validate_sound_file(file_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate a sound file.
    Returns (is_valid, error_message).
    """
    if not os.path.exists(file_path):
        return False, "File not found"

    # Check file size (max 1MB for 30 sec audio)
    size = os.path.getsize(file_path)
    if size > 1024 * 1024:
        return False, "File too large (max 1MB)"

    # Validate format by extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp3', '.wav', '.m4a']:
        return False, "Unsupported format"

    return True, None


# Sound playback helpers
def get_sound_playback_path(sound: Sound) -> str:
    """Get the full path for sound playback."""
    if sound.is_built_in:
        # Built-in sounds are bundled with app
        return f"assets/sounds/{sound.filename}.mp3"
    else:
        # Custom sounds are in app sandbox
        return sound.file_path


def should_fallback_to_default(sound: Sound) -> bool:
    """Check if we should fallback to default sound."""
    if sound.is_built_in:
        return False

    # Check if custom sound file exists
    if not os.path.exists(sound.file_path):
        logger.warning(f"Custom sound file missing: {sound.file_path}, falling back to default")
        return True

    return False
