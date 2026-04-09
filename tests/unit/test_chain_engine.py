"""
Unit tests for Chain Engine Service

Per spec Section 14: Tests for chain engine determinism and edge cases.
TC-01 through TC-06 test scenarios per spec Section 2.5.
"""

import pytest
from datetime import datetime, timedelta
from backend.services.chain_engine import (
    compute_escalation_chain,
    validate_chain,
    get_chain_tier_count,
    UrgencyTier,
    Anchor,
    ChainValidation,
)


class TestComputeEscalationChain:
    """Tests for compute_escalation_chain function"""

    def test_full_chain_8_anchors(self):
        """TC-01: Full chain with buffer >= 25 min should have 8 anchors"""
        arrival = datetime.now() + timedelta(hours=2)  # 2 hours from now
        drive = 30  # 30 min drive = 90 min buffer (2h - 30m)

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 8
        # Verify all tiers present in order
        tiers = [a.urgency_tier for a in anchors]
        assert tiers == ['calm', 'casual', 'pointed', 'urgent', 'pushing', 'firm', 'critical', 'alarm']

    def test_compressed_chain_7_anchors(self):
        """TC-02: Buffer 20-24 min should have 7 anchors (skip calm)"""
        arrival = datetime.now() + timedelta(hours=1)
        drive = 20  # 40 min buffer

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 7
        tiers = [a.urgency_tier for a in anchors]
        assert 'calm' not in tiers
        assert tiers[0] == 'casual'

    def test_short_chain_5_anchors(self):
        """TC-03: Buffer 10-19 min should have 5 anchors (compressed)"""
        arrival = datetime.now() + timedelta(minutes=30)
        drive = 15  # 15 min buffer

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 5
        tiers = [a.urgency_tier for a in anchors]
        # Uses fixed minutes_before: urgent(15), pushing(10), firm(5), critical(1), alarm(0)
        assert tiers == ['urgent', 'pushing', 'firm', 'critical', 'alarm']

    def test_minimum_chain_3_anchors(self):
        """TC-04: Buffer 5-9 min should have 3 anchors"""
        arrival = datetime.now() + timedelta(minutes=15)
        drive = 7  # 7 min buffer

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 3
        tiers = [a.urgency_tier for a in anchors]
        # Uses fixed: firm(5), critical(1), alarm(0)
        assert tiers == ['firm', 'critical', 'alarm']

    def test_minimum_chain_2_anchors(self):
        """TC-05: Buffer 2-5 min should have 2 anchors (firm, alarm)"""
        arrival = datetime.now() + timedelta(minutes=10)
        drive = 3  # 3 min buffer

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 2
        tiers = [a.urgency_tier for a in anchors]
        assert tiers == ['firm', 'alarm']

    def test_minimum_chain_1_anchor(self):
        """TC-06: Buffer <= 1 min should have 1 anchor (alarm only)"""
        arrival = datetime.now() + timedelta(minutes=5)
        drive = 1  # 1 min buffer

        anchors = compute_escalation_chain(arrival, drive)

        assert len(anchors) == 1
        assert anchors[0].urgency_tier == 'alarm'

    def test_anchors_sorted_by_timestamp(self):
        """Anchors should be sorted by timestamp, earliest first (tiebreaker by minutes_before desc)"""
        arrival = datetime.now() + timedelta(hours=1)
        drive = 20

        anchors = compute_escalation_chain(arrival, drive)

        for i in range(len(anchors) - 1):
            # If timestamps are equal, higher minutes_before comes first
            if anchors[i].timestamp == anchors[i + 1].timestamp:
                assert anchors[i].minutes_before > anchors[i + 1].minutes_before
            else:
                assert anchors[i].timestamp < anchors[i + 1].timestamp

    def test_alarm_always_at_arrival(self):
        """Alarm anchor should always be at arrival time (minutes_before=0)"""
        arrival = datetime(2025, 1, 1, 9, 0, 0)
        drive = 30

        anchors = compute_escalation_chain(arrival, drive)

        alarm_anchor = next(a for a in anchors if a.urgency_tier == 'alarm')
        assert alarm_anchor.timestamp == arrival
        assert alarm_anchor.minutes_before == 0

    def test_determinism_same_inputs_same_output(self):
        """Same inputs should always produce the same anchors"""
        arrival = datetime(2025, 1, 1, 9, 0, 0)
        drive = 25

        anchors1 = compute_escalation_chain(arrival, drive)
        anchors2 = compute_escalation_chain(arrival, drive)

        assert len(anchors1) == len(anchors2)
        for a1, a2 in zip(anchors1, anchors2):
            assert a1.urgency_tier == a2.urgency_tier
            assert a1.timestamp == a2.timestamp
            assert a1.minutes_before == a2.minutes_before


class TestValidateChain:
    """Tests for validate_chain function"""

    def test_valid_chain_returns_true(self):
        """Valid chain should return valid=True"""
        arrival = datetime.now() + timedelta(hours=2)
        drive = 30

        result = validate_chain(arrival, drive)

        assert result.valid is True
        assert result.error is None

    def test_departure_in_past_returns_false(self):
        """Departure time in the past should return valid=False"""
        arrival = datetime.now() - timedelta(minutes=10)  # Already passed
        drive = 30

        result = validate_chain(arrival, drive)

        assert result.valid is False
        assert result.error == 'departure_time_in_past'

    def test_zero_drive_duration_returns_false(self):
        """Zero drive duration should return valid=False"""
        arrival = datetime.now() + timedelta(hours=1)
        drive = 0

        result = validate_chain(arrival, drive)

        assert result.valid is False
        assert result.error == 'invalid_drive_duration'

    def test_negative_drive_duration_returns_false(self):
        """Negative drive duration should return valid=False"""
        arrival = datetime.now() + timedelta(hours=1)
        drive = -5

        result = validate_chain(arrival, drive)

        assert result.valid is False
        assert result.error == 'invalid_drive_duration'


class TestGetChainTierCount:
    """Tests for get_chain_tier_count helper function"""

    def test_buffer_25_plus(self):
        """Buffer >= 25 returns 8"""
        assert get_chain_tier_count(25) == 8
        assert get_chain_tier_count(30) == 8
        assert get_chain_tier_count(60) == 8

    def test_buffer_20_to_24(self):
        """Buffer 20-24 returns 7"""
        assert get_chain_tier_count(20) == 7
        assert get_chain_tier_count(24) == 7

    def test_buffer_10_to_19(self):
        """Buffer 10-19 returns 5"""
        assert get_chain_tier_count(10) == 5
        assert get_chain_tier_count(19) == 5

    def test_buffer_5_to_9(self):
        """Buffer 5-9 returns 3"""
        assert get_chain_tier_count(5) == 3
        assert get_chain_tier_count(9) == 3

    def test_buffer_2_to_4(self):
        """Buffer 2-4 returns 2"""
        assert get_chain_tier_count(2) == 2
        assert get_chain_tier_count(4) == 2

    def test_buffer_0_to_1(self):
        """Buffer 0-1 returns 1"""
        assert get_chain_tier_count(0) == 1
        assert get_chain_tier_count(1) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])