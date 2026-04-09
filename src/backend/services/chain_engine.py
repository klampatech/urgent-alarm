"""
Escalation Chain Engine Service

Per spec Section 2: Computes urgency anchor chains based on arrival time and drive duration.
Extracts chain computation logic from test_server.py for modularity and testability.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class UrgencyTier(str, Enum):
    """Urgency tiers per spec Section 2.3"""
    CALM = "calm"
    CASUAL = "casual"
    POINTED = "pointed"
    URGENT = "urgent"
    PUSHING = "pushing"
    FIRM = "firm"
    CRITICAL = "critical"
    ALARM = "alarm"


# Tier configuration per spec Section 2.3
TIER_CONFIG = {
    'calm': {'minutes_before': 30, 'order': 1},
    'casual': {'minutes_before': 25, 'order': 2},
    'pointed': {'minutes_before': 20, 'order': 3},
    'urgent': {'minutes_before': 15, 'order': 4},
    'pushing': {'minutes_before': 10, 'order': 5},
    'firm': {'minutes_before': 5, 'order': 6},
    'critical': {'minutes_before': 1, 'order': 7},
    'alarm': {'minutes_before': 0, 'order': 8},
}


@dataclass
class Anchor:
    """Represents a single escalation anchor"""
    urgency_tier: str
    timestamp: datetime
    minutes_before: int


@dataclass
class ChainValidation:
    """Result of chain validation"""
    valid: bool
    error: Optional[str] = None
    departure_time: Optional[datetime] = None


def compute_escalation_chain(arrival_time: datetime, drive_duration: int) -> list[Anchor]:
    """
    Compute escalation chain anchors based on arrival time and drive duration.

    Per spec Section 2.3 rules:
    - buffer >= 25 min: 8 anchors (full chain: calm, casual, pointed, urgent, pushing, firm, critical, alarm)
    - buffer 20-24 min: 7 anchors (skip calm: casual, pointed, urgent, pushing, firm, critical, alarm)
    - buffer 10-19 min: 5 anchors (compressed: urgent, pushing, firm, critical, alarm)
    - buffer 5-9 min: 3 anchors (short: firm, critical, alarm)
    - buffer <= 5 min: 2 anchors (minimum: firm, alarm) or 1 (alarm only for <= 1)

    Args:
        arrival_time: The target arrival time
        drive_duration: Total drive time in minutes

    Returns:
        List of Anchor objects sorted by timestamp (earliest first)
    """
    buffer_minutes = drive_duration
    anchors = []

    # Determine which tiers to include based on buffer time
    if buffer_minutes >= 25:
        # Full 8-anchor chain
        tiers = [
            ('calm', 30),
            ('casual', 25),
            ('pointed', 20),
            ('urgent', 15),
            ('pushing', 10),
            ('firm', 5),
            ('critical', 1),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 20:
        # Skip calm, start at casual (7 anchors)
        tiers = [
            ('casual', 25),
            ('pointed', 20),
            ('urgent', 15),
            ('pushing', 10),
            ('firm', 5),
            ('critical', 1),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 10:
        # Compressed: urgent, pushing, firm, critical, alarm (5 anchors)
        tiers = [
            ('urgent', 15),
            ('pushing', 10),
            ('firm', 5),
            ('critical', 1),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 5:
        # Short: firm, critical, alarm (3 anchors)
        tiers = [
            ('firm', 5),
            ('critical', 1),
            ('alarm', 0),
        ]
    else:
        # Minimum: firm + alarm (or just alarm if <= 1 min)
        if buffer_minutes > 1:
            tiers = [
                ('firm', min(buffer_minutes - 1, 5)),
                ('alarm', 0),
            ]
        else:
            tiers = [
                ('alarm', 0),
            ]

    # Build anchor objects (only valid positive minutes_before)
    for tier_name, minutes_before in tiers:
        if minutes_before < 0:
            continue
        anchor_time = arrival_time - timedelta(minutes=minutes_before)
        anchors.append(Anchor(
            urgency_tier=tier_name,
            timestamp=anchor_time,
            minutes_before=minutes_before,
        ))

    # Sort by timestamp (earliest first), then by minutes_before descending for ties
    anchors.sort(key=lambda a: (a.timestamp, -a.minutes_before))
    return anchors


def validate_chain(arrival_time: datetime, drive_duration: int) -> ChainValidation:
    """
    Validate that a valid escalation chain can be created.

    Per spec Section 2.4:
    - departure_time must be in the future
    - drive_duration must be positive

    Args:
        arrival_time: The target arrival time
        drive_duration: Total drive time in minutes

    Returns:
        ChainValidation with valid=True if chain is valid, or error details
    """
    departure_time = arrival_time - timedelta(minutes=drive_duration)

    if departure_time <= datetime.now():
        return ChainValidation(
            valid=False,
            error='departure_time_in_past',
            departure_time=departure_time
        )

    if drive_duration <= 0:
        return ChainValidation(
            valid=False,
            error='invalid_drive_duration',
            departure_time=departure_time
        )

    return ChainValidation(valid=True, departure_time=departure_time)


def get_chain_tier_count(drive_duration: int) -> int:
    """
    Get the number of anchors in a chain for a given drive duration.

    Useful for displaying chain info to users.

    Args:
        drive_duration: Total drive time in minutes

    Returns:
        Number of anchors that will be generated
    """
    if drive_duration >= 25:
        return 8
    elif drive_duration >= 20:
        return 7
    elif drive_duration >= 10:
        return 5
    elif drive_duration >= 5:
        return 3
    else:
        return 2 if drive_duration > 1 else 1