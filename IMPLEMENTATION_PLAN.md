# Urgent Alarm — Implementation Plan

## Analysis Summary

### Current State
- **test_server.py** contains a working HTTP server with:
  - Basic chain engine (`compute_escalation_chain`)
  - Natural language parser (`parse_reminder_natural`)
  - Voice personality message templates (5 personalities)
  - Partial SQLite schema (missing columns from spec)
  - Hit rate calculation
  - HTTP endpoints for basic operations

### What's Missing
The spec defines 13 major systems. The current code covers ~30% of requirements.

---

## Phase 1: Core Infrastructure & Testing (Foundation)

### 1.1 Database Schema Alignment
**Priority: P0 — All other systems depend on this**

| Task | Description |
|------|-------------|
| 1.1.1 | Add missing columns to `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id` |
| 1.1.2 | Add `snoozed_to` column to `anchors` table |
| 1.1.3 | Add `actual_arrival`, `missed_reason` columns to `history` table |
| 1.1.4 | Create `calendar_sync` table (apple/google sync state) |
| 1.1.5 | Create `custom_sounds` table |
| 1.1.6 | Add migration system with sequential versioning |
| 1.1.7 | Enable WAL mode and foreign keys |

**Acceptance:** All spec TC-01 through TC-05 for data persistence pass.

### 1.2 Interface Definitions
**Priority: P0 — Enables mocking in tests**

| Task | Description |
|------|-------------|
| 1.2.1 | Create `ILanguageModelAdapter` abstract class/interface |
| 1.2.2 | Create `ITTSAdapter` abstract class/interface |
| 1.2.3 | Create `ICalendarAdapter` abstract class/interface |
| 1.2.4 | Create in-memory test implementations for all adapters |
| 1.2.5 | Make LLM adapter configurable (MiniMax, Anthropic, mock) |

### 1.3 Test Harness Setup
**Priority: P0 — Required for validation**

| Task | Description |
|------|-------------|
| 1.3.1 | Create pytest fixtures for in-memory database |
| 1.3.2 | Add `harness/` test suite with chain engine tests |
| 1.3.3 | Add parser tests (all TC-01 through TC-07) |
| 1.3.4 | Add TTS adapter mock tests |
| 1.3.5 | Add database migration tests |
| 1.3.6 | Validate: `python3 -m pytest harness/ --v` passes |

---

## Phase 2: Chain Engine & Parser Enhancement

### 2.1 Chain Engine Completeness
**Priority: P1 — Core functionality**

| Task | Description |
|------|-------------|
| 2.1.1 | Implement `get_next_unfired_anchor(reminder_id)` for scheduler recovery |
| 2.1.2 | Add anchor sorting by timestamp in database |
| 2.1.3 | Validate `arrival_time > departure_time + minimum_drive_time` (spec TC-04) |
| 2.1.4 | Add test for chain determinism (TC-06) |
| 2.1.5 | Implement `snooze_recompute()` for re-centering anchors after snooze |

**Acceptance:** Spec TC-01 through TC-06 for escalation chain pass.

### 2.2 Parser Enhancement
**Priority: P1 — User-facing feature**

| Task | Description |
|------|-------------|
| 2.2.1 | Integrate LLM adapter into parser flow |
| 2.2.2 | Implement LLM API failure → keyword extraction fallback |
| 2.2.3 | Handle "tomorrow" date resolution (TC-03) |
| 2.2.4 | Handle "dryer in 3 min" as simple_countdown (TC-02) |
| 2.2.5 | Add confidence scoring for fallback responses |
| 2.2.6 | Implement manual field correction support |

**Acceptance:** Spec TC-01 through TC-07 for reminder parsing pass.

---

## Phase 3: Voice & TTS System

### 3.1 TTS Generation
**Priority: P1 — Critical for user experience**

| Task | Description |
|------|-------------|
| 3.1.1 | Implement ElevenLabs adapter conforming to `ITTSAdapter` |
| 3.1.2 | Add TTS cache directory creation (`/tts_cache/{reminder_id}/`) |
| 3.1.3 | Implement pre-generation of all anchor clips at reminder creation |
| 3.1.4 | Add TTS fallback to notification sound on API failure |
| 3.1.5 | Implement TTS cache invalidation on reminder deletion |
| 3.1.6 | Add voice ID mapping per personality |

**Acceptance:** Spec TC-01 through TC-05 for TTS pass.

### 3.2 Voice Personality Message Generation
**Priority: P2**

| Task | Description |
|------|-------------|
| 3.2.1 | Add 3+ message variations per tier per personality |
| 3.2.2 | Implement custom prompt mode (max 200 chars) |
| 3.2.3 | Add tests for message generation with different personalities |

---

## Phase 4: Notification & Alarm Behavior

### 4.1 Notification Escalation
**Priority: P1 — Core UX**

| Task | Description |
|------|-------------|
| 4.1.1 | Implement notification tier escalation (gentle → siren → alarm) |
| 4.1.2 | Add DND-aware notification behavior |
| 4.1.3 | Implement quiet hours suppression (default 10pm–7am) |
| 4.1.4 | Add post-DND/quiet-hours catch-up queuing |
| 4.1.5 | Implement 15-minute overdue anchor drop rule |
| 4.1.6 | Add chain overlap serialization (queue during active chain) |

**Acceptance:** Spec TC-01 through TC-06 for notification behavior pass.

### 4.2 T-0 Alarm Looping
**Priority: P1**

| Task | Description |
|------|-------------|
| 4.2.1 | Implement looping alarm until user action |
| 4.2.2 | Add vibration on alarm tier |

---

## Phase 5: Snooze & Dismissal Flow

### 5.1 Snooze Implementation
**Priority: P1**

| Task | Description |
|------|-------------|
| 5.1.1 | Implement tap-snooze (1 minute default) |
| 5.1.2 | Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min) |
| 5.1.3 | Implement chain re-computation after snooze |
| 5.1.4 | Add TTS snooze confirmation ("Okay, snoozed X minutes") |
| 5.1.5 | Persist snoozed timestamps for app restart recovery |

**Acceptance:** Spec TC-01 through TC-06 for snooze pass.

### 5.2 Dismissal & Feedback
**Priority: P1**

| Task | Description |
|------|-------------|
| 5.2.1 | Implement swipe-to-dismiss feedback prompt |
| 5.2.2 | Add "timing_right" / "left_too_early" / "left_too_late" / "other" feedback types |
| 5.2.3 | Store feedback in history table |
| 5.2.4 | Trigger drive_duration adjustment on "left_too_late" |

---

## Phase 6: Background Scheduling

### 6.1 Notifee Integration
**Priority: P1 — Requires reliability**

| Task | Description |
|------|-------------|
| 6.1.1 | Create Notifee adapter for background scheduling |
| 6.1.2 | Register each anchor as individual background task |
| 6.1.3 | Implement recovery scan on app launch |
| 6.1.4 | Add 15-minute grace window for overdue anchors |
| 6.1.5 | Re-register pending anchors after crash/termination |
| 6.1.6 | Log late firing warnings (>60s after scheduled) |

**Acceptance:** Spec TC-01 through TC-06 for background scheduling pass.

---

## Phase 7: Calendar Integration

### 7.1 Calendar Adapters
**Priority: P2 — Nice to have**

| Task | Description |
|------|-------------|
| 7.1.1 | Implement Apple Calendar adapter (EventKit) |
| 7.1.2 | Implement Google Calendar adapter (Google Calendar API) |
| 7.1.3 | Add calendar sync scheduler (launch + 15 min + background) |
| 7.1.4 | Filter events with non-empty location |
| 7.1.5 | Create suggestion card display for calendar events |
| 7.1.6 | Handle permission denial with explanation banner |
| 7.1.7 | Add recurring event handling |

**Acceptance:** Spec TC-01 through TC-06 for calendar integration pass.

---

## Phase 8: Location Awareness

### 8.1 Location Check
**Priority: P2**

| Task | Description |
|------|-------------|
| 8.1.1 | Request location permission at first location-aware reminder |
| 8.1.2 | Implement single location check at departure anchor |
| 8.1.3 | Use 500m geofence for "at origin" comparison |
| 8.1.4 | If at origin, fire firm/critical tier immediately instead of departure |
| 8.1.5 | Store origin as lat/lng or address |
| 8.1.6 | Do not store location history beyond comparison |

**Acceptance:** Spec TC-01 through TC-05 for location awareness pass.

---

## Phase 9: History, Stats & Feedback Loop

### 9.1 Stats Calculation
**Priority: P2**

| Task | Description |
|------|-------------|
| 9.1.1 | Implement correct hit rate formula (trailing 7 days) |
| 9.1.2 | Implement streak counter for recurring reminders |
| 9.1.3 | Calculate "common miss window" (most missed urgency tier) |
| 9.1.4 | Add feedback loop: late_count × 2 min adjustment, capped at +15 |
| 9.1.5 | Implement 90-day data retention with archive |

**Acceptance:** Spec TC-01 through TC-07 for history/stats pass.

---

## Phase 10: Sound Library

### 10.1 Sound System
**Priority: P3**

| Task | Description |
|------|-------------|
| 10.1.1 | Bundle 5 built-in sounds per category (commute, routine, errand) |
| 10.1.2 | Implement custom audio import (MP3, WAV, M4A, max 30s) |
| 10.1.3 | Add sound picker UI per reminder |
| 10.1.4 | Implement corrupted sound fallback to category default |
| 10.1.5 | Persist sound selection in reminder record |

**Acceptance:** Spec TC-01 through TC-05 for sound library pass.

---

## Phase 11: Integration Tests

### 11.1 E2E Test Coverage
**Priority: P2**

| Task | Description |
|------|-------------|
| 11.1.1 | Full reminder creation flow test (parse → chain → TTS → persist) |
| 11.1.2 | Anchor firing sequence test |
| 11.1.3 | Snooze recovery test |
| 11.1.4 | Feedback loop end-to-end test |
| 11.1.5 | Chain overlap serialization test |

---

## Task Count by Priority

| Priority | Tasks | Phase |
|----------|-------|-------|
| P0 | 19 | 1 |
| P1 | 23 | 2-6 |
| P2 | 19 | 7-11 |
| **Total** | **61** | |

---

## Dependencies Graph

```
Phase 1 (Infrastructure)
  ├── 1.1 DB Schema
  └── 1.2 Interfaces
       └── 1.3 Test Harness

Phase 2 (Chain + Parser) ← Phase 1
  ├── 2.1 Chain Engine
  └── 2.2 Parser

Phase 3 (Voice/TTS) ← Phase 1, 2
  ├── 3.1 TTS Generation
  └── 3.2 Voice Messages

Phase 4 (Notifications) ← Phase 1, 2
  ├── 4.1 Notification Escalation
  └── 4.2 Alarm Looping

Phase 5 (Snooze/Dismissal) ← Phase 1, 2, 4
  ├── 5.1 Snooze
  └── 5.2 Feedback

Phase 6 (Background) ← Phase 1, 2, 4
  └── 6.1 Notifee

Phase 7 (Calendar) ← Phase 1
  └── 7.1 Adapters

Phase 8 (Location) ← Phase 1
  └── 8.1 Location Check

Phase 9 (Stats) ← Phase 1, 5
  └── 9.1 Stats

Phase 10 (Sound) ← Phase 1
  └── 10.1 Library

Phase 11 (Integration) ← All previous
  └── 11.1 E2E
```

---

## Next Steps

1. **Immediate:** Start Phase 1 tasks in order (1.1 → 1.2 → 1.3)
2. Create branch for implementation
3. Run `python3 -m pytest harness/` to validate after each phase
4. Commit after each phase completion
