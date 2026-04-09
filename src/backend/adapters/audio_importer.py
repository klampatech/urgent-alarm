#!/usr/bin/env python3
"""
Audio Importer Adapter

Handles importing custom audio files for sounds:
- Supports MP3, WAV, M4A import (max 30 sec)
- Transcode and normalize imported sounds
- Store in app sandbox with reference in custom_sounds table
- Fallback to category default on corrupted file
"""

import os
import logging
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
MAX_DURATION_SECONDS = 30
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB
SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a'}
NORMALIZED_FORMAT = '.mp3'
APP_SOUNDS_DIR = '/tmp/urgent_alarm_sounds'


@dataclass
class ImportResult:
    """Result of an audio import operation."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class AudioImportError(Exception):
    """Error during audio import."""
    pass


def _ensure_sounds_directory() -> str:
    """Ensure the sounds directory exists."""
    os.makedirs(APP_SOUNDS_DIR, exist_ok=True)
    return APP_SOUNDS_DIR


def _get_audio_duration(file_path: str) -> Optional[float]:
    """
    Get audio file duration using ffprobe.
    Returns duration in seconds or None if unable to determine.
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def _validate_audio_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that the audio file is valid and not corrupted.
    Returns (is_valid, error_message).
    """
    if not os.path.exists(file_path):
        return False, "File not found"

    # Check file size
    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large (max {MAX_FILE_SIZE_BYTES // 1024}KB)"

    if size == 0:
        return False, "File is empty"

    # Validate format by extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {ext}"

    # Validate audio is playable using ffprobe
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', file_path],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, "Audio file is corrupted or invalid"
    except FileNotFoundError:
        # ffprobe not available, skip validation
        logger.warning("ffprobe not available, skipping audio validation")
    except subprocess.TimeoutExpired:
        return False, "Audio validation timed out"

    return True, None


def _transcode_audio(input_path: str, output_path: str) -> bool:
    """
    Transcode audio to normalized format.
    Returns True on success, False on failure.
    """
    try:
        # Convert to MP3 with standard settings
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', input_path, '-acodec', 'libmp3lame',
             '-ab', '128k', '-ar', '44100', '-t', str(MAX_DURATION_SECONDS),
             output_path],
            capture_output=True,
            timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # ffmpeg not available, copy original file
        logger.warning("ffmpeg not available, using original file")
        try:
            shutil.copy2(input_path, output_path)
            return True
        except Exception:
            return False


def import_audio(
    original_filename: str,
    source_file_path: str,
    category: str = "custom"
) -> ImportResult:
    """
    Import an audio file for use as a custom sound.

    Args:
        original_filename: Original name of the file
        source_file_path: Path to the source audio file
        category: Category for the sound (commute, routine, errand, custom)

    Returns:
        ImportResult with success status and file path or error message
    """
    # Validate source file
    is_valid, error_message = _validate_audio_file(source_file_path)
    if not is_valid:
        logger.error(f"Audio validation failed: {error_message}")
        return ImportResult(success=False, error_message=error_message)

    # Get duration
    duration = _get_audio_duration(source_file_path)
    if duration and duration > MAX_DURATION_SECONDS:
        return ImportResult(
            success=False,
            error_message=f"Audio too long: {duration:.1f}s (max {MAX_DURATION_SECONDS}s)"
        )

    # Generate unique ID and destination path
    sounds_dir = _ensure_sounds_directory()
    sound_id = str(uuid.uuid4())
    dest_filename = f"{sound_id}{NORMALIZED_FORMAT}"
    dest_path = os.path.join(sounds_dir, dest_filename)

    # Transcode to normalized format
    if _transcode_audio(source_file_path, dest_path):
        # Get final duration if not already known
        if duration is None:
            duration = _get_audio_duration(dest_path)

        logger.info(f"Imported audio: {original_filename} -> {dest_path}")
        return ImportResult(
            success=True,
            file_path=dest_path,
            duration_seconds=duration
        )
    else:
        return ImportResult(
            success=False,
            error_message="Failed to process audio file"
        )


def delete_imported_audio(file_path: str) -> bool:
    """
    Delete an imported audio file.

    Args:
        file_path: Path to the audio file to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted audio file: {file_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to delete audio file: {e}")
    return False


def get_imported_audio_info(file_path: str) -> Optional[dict]:
    """
    Get information about an imported audio file.

    Args:
        file_path: Path to the audio file

    Returns:
        Dictionary with file info or None if not found
    """
    if not os.path.exists(file_path):
        return None

    try:
        stat = os.stat(file_path)
        duration = _get_audio_duration(file_path)

        return {
            'file_path': file_path,
            'size_bytes': stat.st_size,
            'duration_seconds': duration,
            'exists': True
        }
    except Exception as e:
        logger.error(f"Failed to get audio info: {e}")
        return None


# Convenience function for sound_manager integration
def import_for_sound_manager(
    original_filename: str,
    source_file_path: str
) -> Optional[Tuple[str, Optional[float]]]:
    """
    Convenience wrapper for sound_manager.py integration.

    Returns:
        Tuple of (file_path, duration_seconds) or None on failure
    """
    result = import_audio(original_filename, source_file_path)
    if result.success:
        return (result.file_path, result.duration_seconds)
    return None