#!/usr/bin/env python3
"""
Location Adapter

Provides single-point location check at departure time:
- Single CoreLocation/FusedLocationProvider call at departure trigger
- 500m geofence radius for "at origin"
- Escalate to firm/critical if still at origin
- No location history stored
"""

import sqlite3
import logging
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/urgent-alarm.db"

# Geofence radius in meters
GEOFENCE_RADIUS_METERS = 500


@dataclass
class Location:
    """Represents a geographic location."""
    latitude: float
    longitude: float
    address: Optional[str] = None


@dataclass
class LocationCheckResult:
    """Result of a location check."""
    is_at_origin: bool
    distance_meters: float
    current_location: Optional[Location]
    origin_location: Optional[Location]


class ILocationAdapter(ABC):
    """Interface for location adapters."""

    @abstractmethod
    def is_permission_granted(self) -> bool:
        """Check if location permission is granted."""
        pass

    @abstractmethod
    def request_permission(self) -> bool:
        """Request location permission (returns True if granted)."""
        pass

    @abstractmethod
    def get_current_location(self) -> Optional[Location]:
        """Get the current device location."""
        pass

    @abstractmethod
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate distance between two locations in meters."""
        pass


class LocationAdapter(ILocationAdapter):
    """Location adapter using CoreLocation (iOS) / FusedLocationProvider (Android)."""

    def is_permission_granted(self) -> bool:
        """Check if location permission is granted."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value FROM user_preferences WHERE key = 'location_permission'
        """)
        row = cursor.fetchone()
        conn.close()

        return row and row[0] == 'granted'

    def request_permission(self) -> bool:
        """Request location permission (returns True if granted)."""
        # In production, this would trigger native permission dialog
        # For testing, we store a preference
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences (key, value)
            VALUES ('location_permission', 'granted')
        """)

        conn.commit()
        conn.close()

        logger.info("Location permission granted")
        return True

    def get_current_location(self) -> Optional[Location]:
        """Get the current device location."""
        # In production, this would call CoreLocation/FusedLocationProvider
        # For testing, return a mock location
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value FROM user_preferences WHERE key = 'mock_current_location'
        """)
        row = cursor.fetchone()
        conn.close()

        if row:
            # Parse mock location from JSON
            import json
            data = json.loads(row[0])
            return Location(
                latitude=data['lat'],
                longitude=data['lng'],
                address=data.get('address')
            )

        return None

    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate distance between two locations in meters using Haversine formula."""
        import math

        R = 6371000  # Earth's radius in meters

        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lng = math.radians(loc2.longitude - loc1.longitude)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


def get_location_adapter() -> LocationAdapter:
    """Get the location adapter instance."""
    return LocationAdapter()


def check_departure_location(
    reminder_id: str,
    origin_location: Optional[Location] = None
) -> LocationCheckResult:
    """
    Check location at departure anchor fire.
    Returns whether user is still at origin and should escalate.
    """
    adapter = get_location_adapter()

    # If no origin location provided, get from reminder
    if not origin_location:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT origin_lat, origin_lng, origin_address
            FROM reminders WHERE id = ?
        """, (reminder_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0] and row[1]:
            origin_location = Location(
                latitude=row[0],
                longitude=row[1],
                address=row[2]
            )

    # If still no origin, can't check location
    if not origin_location:
        return LocationCheckResult(
            is_at_origin=False,
            distance_meters=float('inf'),
            current_location=None,
            origin_location=None
        )

    # Get current location
    current = adapter.get_current_location()
    if not current:
        # If we can't get current location, assume not at origin
        return LocationCheckResult(
            is_at_origin=False,
            distance_meters=float('inf'),
            current_location=None,
            origin_location=origin_location
        )

    # Calculate distance
    distance = adapter.calculate_distance(current, origin_location)

    # Check if within geofence
    is_at_origin = distance <= GEOFENCE_RADIUS_METERS

    logger.info(
        f"Location check for reminder {reminder_id}: "
        f"distance={distance:.1f}m, at_origin={is_at_origin}"
    )

    return LocationCheckResult(
        is_at_origin=is_at_origin,
        distance_meters=distance,
        current_location=current,
        origin_location=origin_location
    )


def should_escalate_at_departure(reminder_id: str) -> bool:
    """
    Determine if departure anchor should escalate to firm/critical tier.
    Returns True if user is still at origin and should get urgent message.
    """
    result = check_departure_location(reminder_id)
    return result.is_at_origin


def set_origin_for_reminder(
    reminder_id: str,
    latitude: float,
    longitude: float,
    address: Optional[str] = None
) -> bool:
    """Set origin location for a reminder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reminders
        SET origin_lat = ?, origin_lng = ?, origin_address = ?,
            updated_at = datetime('now')
        WHERE id = ?
    """, (latitude, longitude, address, reminder_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    return affected > 0


def use_current_location_as_origin(reminder_id: str) -> bool:
    """Use the current device location as the origin for a reminder."""
    adapter = get_location_adapter()

    # Request permission if not granted
    if not adapter.is_permission_granted():
        granted = adapter.request_permission()
        if not granted:
            logger.warning("Location permission not granted")
            return False

    # Get current location
    current = adapter.get_current_location()
    if not current:
        logger.warning("Could not get current location")
        return False

    # Set as origin
    return set_origin_for_reminder(
        reminder_id,
        current.latitude,
        current.longitude,
        current.address
    )


# Mock location for testing
def set_mock_current_location(latitude: float, longitude: float, address: Optional[str] = None) -> None:
    """Set mock current location for testing."""
    import json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    data = json.dumps({'lat': latitude, 'lng': longitude, 'address': address})

    cursor.execute("""
        INSERT OR REPLACE INTO user_preferences (key, value)
        VALUES ('mock_current_location', ?)
    """, (data,))

    conn.commit()
    conn.close()
