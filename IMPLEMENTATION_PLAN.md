# Urgent Voice Alarm - Implementation Plan

## Analysis Summary

**Spec Document:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md` (1024 lines, 14 sections)

**Current State:** Minimal Python HTTP server in `src/test_server.py` with:
- Basic SQLite database schema (partial)
- `compute_escalation_chain()` function
- `parse_reminder_natural()` keyword parser
- `generate_voice_message()` with 5 voice personalities
- Basic REST API endpoints

**Coverage:** ~15% of spec requirements implemented.

---

## Priority 1: Core Infrastructure (Must Have First)

These tasks are dependencies for everything else.

### P1-T1: Database Schema & Migrations
**Spec:** Section 13 (Data Persistence)
**Status:** Partial schema exists, missing columns and migration system

**Tasks:**
- [ ] Create migration system with sequential versioning (schema_v1, v2, etc.)
- [ ] Add missing columns to `reminders` table:
  - `origin_lat REAL`
  - `origin_lng REAL`
  - `origin_address TEXT`
  - `custom_sound_path TEXT`
  - `calendar_event_id TEXT`
- [ ] Add missing columns to `anchors` table:
  - `snoozed_to TEXT`
  - `tts_fallback BOOLEAN DEFAULT FALSE`
- [ ] Add missing columns to `history` table:
  - `actual_arrival TEXT`
  - `missed_reason TEXT`
- [ ] Add `calendar_sync` table for sync state
- [ ] Add `custom_sounds` table for imported audio
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Enable foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Add `updated_at` columns where missing
- [ ] Create in-memory test database helper

### P1-T2: Unit Test Infrastructure
**Spec:** Section 14 (Definition of Done)
**Status:** No tests exist

**Tasks:**
- [ ] Create `tests/` directory structure
- [ ] Set up pytest configuration
- [ ] Create `tests/conftest.py` with in-memory DB fixtures
- [ ] Create `tests/test_chain_engine.py`
- [ ] Create `tests/test_parser.py`
- [ ] Create `tests/test_voice_personalities.py`
- [ ] Create `tests/test_stats.py`
- [ ] Create `tests/test_database.py`

### P1-T3: Chain Engine Completion
**Spec:** Section 2 (Escalation Chain Engine)
**Status:** Partial implementation, missing key functions

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Ensure chain determinism (add seed parameter if needed)
- [ ] Fix compressed chain logic per spec:
  - ≥25 min: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
  - 20-24 min: 7 anchors (skip calm, start casual)
  - 10-19 min: 5 anchors (urgent, pushing, firm, critical, alarm)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - <5 min: 2-3 anchors (minimum)
- [ ] Add validation: reject if `arrival_time - drive_duration` is in the past
- [ ] Add unit tests for all chain scenarios (TC-01 through TC-06)

---

## Priority 2: Parsing & LLM Integration

### P2-T1: LLM Adapter Interface
**Spec:** Section 3 (Reminder Parsing & Creation)
**Status:** Only keyword extraction exists

**Tasks:**
- [ ] Create `src/lib/adapters/llm_adapter.py` with `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` class (Anthropic-compatible)
- [ ] Implement `AnthropicAdapter` class
- [ ] Create `MockLLMAdapter` for testing
- [ ] Add configurable API selection via environment variable
- [ ] Define system prompt for extraction schema

### P2-T2: Parser Enhancement
**Spec:** Section 3

**Tasks:**
- [ ] Add confidence score to parse result
- [ ] Handle `reminder_type` enum: countdown_event, simple_countdown, morning_routine, standing_recurring
- [ ] Add keyword extraction fallback when LLM fails
- [ ] Support time formats: "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
- [ ] Handle "tomorrow" date resolution
- [ ] Add unit tests for all parse scenarios (TC-01 through TC-07)

---

## Priority 3: Voice & TTS System

### P3-T1: TTS Adapter Interface
**Spec:** Section 4 (Voice & TTS Generation)
**Status:** No TTS implementation

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py` with `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` class
- [ ] Create `MockTTSAdapter` for testing
- [ ] Create TTS cache directory structure: `/tts_cache/{reminder_id}/`
- [ ] Implement clip generation at reminder creation
- [ ] Implement fallback to system sounds on API failure
- [ ] Add cache invalidation on reminder deletion

### P3-T2: Voice Personality Enhancement
**Spec:** Section 10 (Voice Personality System)
**Status:** Basic templates exist, missing features

**Tasks:**
- [ ] Add custom prompt support (max 200 characters)
- [ ] Add message variations per tier (minimum 3 per tier per personality)
- [ ] Store selected personality in user_preferences
- [ ] Ensure existing reminders retain personality at creation time
- [ ] Map each personality to distinct ElevenLabs voice ID

---

## Priority 4: Notification & Alarm Behavior

### P4-T1: Notification System
**Spec:** Section 5 (Notification & Alarm Behavior)

**Tasks:**
- [ ] Implement notification tier escalation sounds:
  - calm/casual: gentle chime
  - pointed/urgent: pointed beep
  - pushing/firm: urgent siren
  - critical/alarm: looping alarm
- [ ] Implement DND detection and handling
- [ ] Implement quiet hours (configurable start/end, default 10pm-7am)
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping until user action
- [ ] Implement 15-minute overdue anchor drop rule
- [ ] Display notification: destination, time remaining, voice personality icon

### P4-T2: Sound Library
**Spec:** Section 12 (Sound Library)

**Tasks:**
- [ ] Define sound categories: commute, routine, errand, custom
- [ ] Bundle 5 built-in sounds per category
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 seconds)
- [ ] Implement per-reminder sound selection
- [ ] Store sound selection in reminder record
- [ ] Implement corrupted sound fallback to category default

---

## Priority 5: Background Scheduling

### P5-T1: Notifee Integration
**Spec:** Section 6 (Background Scheduling & Reliability)

**Tasks:**
- [ ] (React Native) Install and configure notifee package
- [ ] Register each anchor as individual background task
- [ ] Implement iOS BGAppRefreshTask / BGProcessingTask
- [ ] Implement recovery scan on app launch
- [ ] Implement overdue anchor handling (15-minute grace window)
- [ ] Implement late fire warning (>60 seconds)
- [ ] Re-register pending anchors on crash recovery

---

## Priority 6: Calendar & Location Integration

### P6-T1: Calendar Adapter
**Spec:** Section 7 (Calendar Integration)

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py` with `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement calendar sync (on launch, every 15 minutes, background refresh)
- [ ] Filter events with non-empty location field
- [ ] Implement suggestion cards for calendar events
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully
- [ ] Handle sync failure gracefully

### P6-T2: Location Awareness
**Spec:** Section 8 (Location Awareness)

**Tasks:**
- [ ] Store origin (address or current location at creation)
- [ ] Implement single location check at departure anchor
- [ ] Implement 500m geofence comparison
- [ ] Implement immediate escalation if user still at origin
- [ ] Request location permission at first location-aware reminder
- [ ] Implement fallback when permission denied
- [ ] Ensure no location history is stored

---

## Priority 7: Snooze, Dismissal & Feedback

### P7-T1: Snooze & Dismissal
**Spec:** Section 9 (Snooze & Dismissal Flow)

**Tasks:**
- [ ] Implement tap snooze (1 minute)
- [ ] Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze
- [ ] Re-register snoozed anchors with Notifee
- [ ] Implement TTS snooze confirmation: "Okay, snoozed X minutes"
- [ ] Implement swipe-to-dismiss with feedback prompt
- [ ] Persist snooze state for crash recovery

### P7-T2: Feedback Loop
**Spec:** Section 11 (History, Stats & Feedback Loop)

**Tasks:**
- [ ] Implement dismissal feedback: "timing_right", "left_too_early", "left_too_late", "other"
- [ ] Store feedback in history table
- [ ] Adjust drive_duration for destination: +2 minutes per "left_too_late", cap at +15
- [ ] Implement common miss window calculation
- [ ] Implement streak counter for recurring reminders
- [ ] Implement 90-day data retention policy

---

## Priority 8: Stats & History

### P8-T1: Stats Calculations
**Spec:** Section 11

**Tasks:**
- [ ] Implement weekly hit rate: `hits / (total - pending) * 100`
- [ ] Implement common miss window display
- [ ] Implement streak counter (increment on hit, reset on miss)
- [ ] Ensure all stats computable from history table alone
- [ ] Create stats API endpoints

---

## Implementation Order Summary

```
Phase 1: Foundation
├── P1-T1: Database Schema & Migrations
├── P1-T2: Test Infrastructure
└── P1-T3: Chain Engine Completion

Phase 2: Core Logic
├── P2-T1: LLM Adapter Interface
├── P2-T2: Parser Enhancement
├── P3-T1: TTS Adapter Interface
└── P3-T2: Voice Personality Enhancement

Phase 3: User Experience
├── P4-T1: Notification System
├── P4-T2: Sound Library
├── P7-T1: Snooze & Dismissal
└── P7-T2: Feedback Loop

Phase 4: Background & Platform
├── P5-T1: Notifee Integration
├── P6-T1: Calendar Adapter
└── P6-T2: Location Awareness

Phase 5: Polish
└── P8-T1: Stats & History
```

---

## Open Questions (Pending Clarification)

1. **Platform decision:** Is this React Native or Flutter? (Spec mentions both)
2. **Database location:** Use `/tmp/urgent-alarm.db` or app-specific storage?
3. **API configuration:** Environment variables for API keys (MiniMax, ElevenLabs)?
4. **iOS/Android parity:** Focus on iOS first or dual-platform?
5. **TTS caching:** Local file storage or in-memory for this test server?

---

## Test Coverage Requirements

Per Section 14 (Definition of Done), every acceptance criterion must have passing tests:

- **Section 2:** 6 test scenarios (TC-01 through TC-06)
- **Section 3:** 7 test scenarios (TC-01 through TC-07)
- **Section 4:** 5 test scenarios (TC-01 through TC-05)
- **Section 5:** 6 test scenarios (TC-01 through TC-06)
- **Section 6:** 6 test scenarios (TC-01 through TC-06)
- **Section 7:** 6 test scenarios (TC-01 through TC-06)
- **Section 8:** 5 test scenarios (TC-01 through TC-05)
- **Section 9:** 6 test scenarios (TC-01 through TC-06)
- **Section 10:** 5 test scenarios (TC-01 through TC-05)
- **Section 11:** 7 test scenarios (TC-01 through TC-07)
- **Section 12:** 5 test scenarios (TC-01 through TC-05)
- **Section 13:** 5 test scenarios (TC-01 through TC-05)

**Total: 69 test scenarios required**
