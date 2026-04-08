# Urgent Voice Alarm - Implementation Plan

## Analysis Summary

**Spec Document:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md` (1024 lines, 14 sections)

**Current State:** Single Python file (`src/test_server.py`) with:
- Basic SQLite schema (partial - missing 15+ columns per spec)
- `compute_escalation_chain()` - partial implementation
- `parse_reminder_natural()` - keyword-only parser (no LLM)
- `generate_voice_message()` - 5 voice personalities, 8 tiers each
- `calculate_hit_rate()` - basic stats
- Basic REST API endpoints (8 endpoints)

**Coverage:** ~12% of spec requirements implemented.

**What's Missing:**
- All adapter interfaces (LLM, TTS, Calendar)
- Full database schema (missing tables and columns)
- Notification/alarm system
- Background scheduling (Notifee)
- Location awareness
- Snooze/dismissal with chain re-computation
- Sound library
- Test suite (69 scenarios required)
- Migration system

---

## Priority 1: Foundation (Must Complete First)

These tasks are dependencies for everything else.

### P1-T1: Database Schema & Migrations
**Spec:** Section 13 (Data Persistence)
**Status:** Partial - only 5 tables exist, missing 12+ columns and migration system

**Tasks:**
- [ ] Create `src/lib/database.py` with migration system
- [ ] Add `schema_migrations` table for version tracking
- [ ] Add missing `reminders` columns:
  - `origin_lat REAL`
  - `origin_lng REAL`
  - `origin_address TEXT`
  - `custom_sound_path TEXT`
  - `calendar_event_id TEXT`
- [ ] Add missing `anchors` columns:
  - `snoozed_to TEXT`
  - `tts_fallback BOOLEAN DEFAULT FALSE`
- [ ] Add missing `history` columns:
  - `actual_arrival TEXT`
  - `missed_reason TEXT`
- [ ] Add `calendar_sync` table (calendar_type, last_sync_at, sync_token, is_connected)
- [ ] Add `custom_sounds` table (id, filename, original_name, category, file_path, duration_seconds, created_at)
- [ ] Add `updated_at` to tables where missing
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Create in-memory test database helper
- [ ] Write migration tests (TC-01 through TC-05)

### P1-T2: Test Infrastructure
**Spec:** Section 14 (Definition of Done)
**Status:** No tests exist

**Tasks:**
- [ ] Create `tests/` directory structure
- [ ] Create `tests/conftest.py` with fixtures:
  - In-memory database fixture with fresh schema
  - Mock adapters for LLM, TTS, Calendar
  - Sample reminder data fixture
- [ ] Create `tests/test_chain_engine.py` (6 scenarios)
- [ ] Create `tests/test_parser.py` (7 scenarios)
- [ ] Create `tests/test_voice_personalities.py` (5 scenarios)
- [ ] Create `tests/test_stats.py` (7 scenarios)
- [ ] Create `tests/test_database.py` (5 scenarios)
- [ ] Run: `python3 -m pytest tests/ -v`

### P1-T3: Chain Engine Completion
**Spec:** Section 2 (Escalation Chain Engine)
**Status:** Partial - compression logic needs review

**Tasks:**
- [ ] Review and fix chain compression per spec:
  - ≥25 min: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
  - 20-24 min: 7 anchors (skip calm)
  - 10-19 min: 5 anchors (urgent, pushing, firm, critical, alarm)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - <5 min: 2-3 anchors (minimum)
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add deterministic seeding for unit test reproducibility
- [ ] Add validation: reject if drive_duration > arrival - now
- [ ] Write unit tests (TC-01 through TC-06)

---

## Priority 2: Adapter Interfaces & Parsing

### P2-T1: LLM Adapter Interface
**Spec:** Section 3 (Reminder Parsing & Creation)
**Status:** Only keyword extraction exists

**Tasks:**
- [ ] Create `src/lib/adapters/__init__.py`
- [ ] Create `src/lib/adapters/llm_adapter.py`:
  - Define `ILanguageModelAdapter` abstract base class
  - Implement `MiniMaxAdapter` (Anthropic-compatible)
  - Implement `AnthropicAdapter`
  - Implement `MockLLMAdapter` for testing
- [ ] Configure API selection via environment variable (`LLM_PROVIDER=minimax|anthropic`)
- [ ] Define system prompt for extraction schema
- [ ] Add confidence score to parse result
- [ ] Write adapter tests (TC-07)

### P2-T2: Parser Enhancement
**Spec:** Section 3

**Tasks:**
- [ ] Add `reminder_type` enum support (countdown_event, simple_countdown, morning_routine, standing_recurring)
- [ ] Support time formats: "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
- [ ] Handle "tomorrow" date resolution
- [ ] Implement LLM fallback to keyword extraction on API failure
- [ ] Return user-facing error for unintelligible input
- [ ] Write parser tests (TC-01 through TC-07)

### P2-T3: TTS Adapter Interface
**Spec:** Section 4 (Voice & TTS Generation)
**Status:** No TTS implementation

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py`:
  - Define `ITTSAdapter` abstract base class
  - Implement `ElevenLabsAdapter`
  - Implement `MockTTSAdapter` for testing
- [ ] Configure API via environment variable (`ELEVENLABS_API_KEY`)
- [ ] Create TTS cache directory: `/tts_cache/{reminder_id}/`
- [ ] Implement clip generation at reminder creation
- [ ] Implement fallback to system sounds on API failure
- [ ] Add cache invalidation on reminder deletion
- [ ] Write TTS tests (TC-01 through TC-05)

### P2-T4: Voice Personality Enhancement
**Spec:** Section 10 (Voice Personality System)
**Status:** Templates exist, missing features

**Tasks:**
- [ ] Add custom prompt support (max 200 characters)
- [ ] Add message variations per tier (minimum 3 per tier per personality)
- [ ] Map each personality to distinct ElevenLabs voice ID
- [ ] Store selected personality in user_preferences
- [ ] Ensure existing reminders retain personality at creation time
- [ ] Write voice personality tests (TC-01 through TC-05)

---

## Priority 3: Core Business Logic

### P3-T1: Snooze & Dismissal Logic
**Spec:** Section 9 (Snooze & Dismissal Flow)
**Status:** Not implemented

**Tasks:**
- [ ] Implement chain re-computation after snooze
- [ ] Implement tap snooze (1 minute)
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Re-register snoozed anchors with new timestamps
- [ ] Implement TTS snooze confirmation: "Okay, snoozed X minutes"
- [ ] Persist snooze state for crash recovery
- [ ] Write snooze tests (TC-01 through TC-06)

### P3-T2: Feedback Loop
**Spec:** Section 11 (History, Stats & Feedback Loop)
**Status:** Partial - hit rate exists

**Tasks:**
- [ ] Implement dismissal feedback (timing_right, left_too_early, left_too_late, other)
- [ ] Store feedback in history table
- [ ] Adjust drive_duration: +2 minutes per "left_too_late", cap at +15
- [ ] Implement common_miss_window calculation
- [ ] Implement streak counter (increment on hit, reset on miss)
- [ ] Implement 90-day data retention policy
- [ ] Write feedback tests (TC-01 through TC-07)

### P3-T3: Stats Calculations
**Spec:** Section 11

**Tasks:**
- [ ] Verify weekly hit rate calculation
- [ ] Implement common miss window display
- [ ] Ensure all stats computable from history table alone
- [ ] Create stats API endpoints

---

## Priority 4: Notification & Sound System

### P4-T1: Notification System
**Spec:** Section 5 (Notification & Alarm Behavior)
**Status:** Not implemented

**Tasks:**
- [ ] Implement notification tier escalation sounds:
  - calm/casual: gentle chime
  - pointed/urgent: pointed beep
  - pushing/firm: urgent siren
  - critical/alarm: looping alarm
- [ ] Implement DND detection and handling
- [ ] Implement quiet hours (configurable, default 10pm-7am)
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping until user action
- [ ] Implement 15-minute overdue anchor drop rule
- [ ] Display notification: destination, time remaining, voice personality icon
- [ ] Write notification tests (TC-01 through TC-06)

### P4-T2: Sound Library
**Spec:** Section 12 (Sound Library)
**Status:** Not implemented

**Tasks:**
- [ ] Define sound categories: commute, routine, errand, custom
- [ ] Bundle 5 built-in sounds per category
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 seconds)
- [ ] Implement per-reminder sound selection
- [ ] Store sound selection in reminder record
- [ ] Implement corrupted sound fallback to category default
- [ ] Write sound library tests (TC-01 through TC-05)

---

## Priority 5: Platform Integration

### P5-T1: Calendar Adapter
**Spec:** Section 7 (Calendar Integration)
**Status:** Not implemented

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py`:
  - Define `ICalendarAdapter` interface
  - Implement `AppleCalendarAdapter` (EventKit)
  - Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement calendar sync (on launch, every 15 min, background)
- [ ] Filter events with non-empty location field
- [ ] Implement suggestion cards for calendar events
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully
- [ ] Handle sync failure gracefully
- [ ] Write calendar tests (TC-01 through TC-06)

### P5-T2: Location Awareness
**Spec:** Section 8 (Location Awareness)
**Status:** Not implemented

**Tasks:**
- [ ] Store origin (address or current location at creation)
- [ ] Implement single location check at departure anchor
- [ ] Implement 500m geofence comparison
- [ ] Implement immediate escalation if user still at origin
- [ ] Request location permission at first location-aware reminder
- [ ] Implement fallback when permission denied
- [ ] Ensure no location history is stored
- [ ] Write location tests (TC-01 through TC-05)

### P5-T3: Background Scheduling
**Spec:** Section 6 (Background Scheduling & Reliability)
**Status:** Not implemented

**Tasks:**
- [ ] (React Native) Install and configure notifee
- [ ] Register each anchor as individual background task
- [ ] Implement iOS BGAppRefreshTask / BGProcessingTask
- [ ] Implement recovery scan on app launch
- [ ] Implement overdue anchor handling (15-minute grace window)
- [ ] Implement late fire warning (>60 seconds)
- [ ] Re-register pending anchors on crash recovery
- [ ] Write background scheduling tests (TC-01 through TC-06)

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
├── P2-T3: TTS Adapter Interface
└── P2-T4: Voice Personality Enhancement

Phase 3: Business Logic
├── P3-T1: Snooze & Dismissal Logic
├── P3-T2: Feedback Loop
└── P3-T3: Stats Calculations

Phase 4: User Experience
├── P4-T1: Notification System
└── P4-T2: Sound Library

Phase 5: Platform Integration
├── P5-T1: Calendar Adapter
├── P5-T2: Location Awareness
└── P5-T3: Background Scheduling
```

---

## Test Coverage Requirements

Per Section 14, every acceptance criterion must have passing tests.

| Section | Test Scenarios | Status |
|---------|----------------|--------|
| 2 - Chain Engine | TC-01 through TC-06 | 0/6 |
| 3 - Parser | TC-01 through TC-07 | 0/7 |
| 4 - TTS | TC-01 through TC-05 | 0/5 |
| 5 - Notifications | TC-01 through TC-06 | 0/6 |
| 6 - Background | TC-01 through TC-06 | 0/6 |
| 7 - Calendar | TC-01 through TC-06 | 0/6 |
| 8 - Location | TC-01 through TC-05 | 0/5 |
| 9 - Snooze | TC-01 through TC-06 | 0/6 |
| 10 - Voice | TC-01 through TC-05 | 0/5 |
| 11 - Stats | TC-01 through TC-07 | 0/7 |
| 12 - Sound | TC-01 through TC-05 | 0/5 |
| 13 - Database | TC-01 through TC-05 | 0/5 |
| **Total** | **69 scenarios** | **0/69** |

---

## Directory Structure (Target)

```
src/
├── __init__.py
├── test_server.py          # Current server (keep for harness)
├── lib/
│   ├── __init__.py
│   ├── database.py         # Schema, migrations, connections
│   ├── chain_engine.py     # Escalation chain computation
│   ├── parser.py           # LLM + keyword parsing
│   ├── voice.py            # TTS and voice personality
│   ├── notifications.py    # Notification & alarm behavior
│   ├── snooze.py           # Snooze & dismissal logic
│   ├── stats.py            # History & stats calculations
│   ├── sound_library.py    # Sound management
│   └── adapters/
│       ├── __init__.py
│       ├── base.py         # Abstract interfaces
│       ├── llm_adapter.py  # LLM (MiniMax, Anthropic)
│       ├── tts_adapter.py  # TTS (ElevenLabs)
│       └── calendar_adapter.py  # Calendar integration
tests/
├── __init__.py
├── conftest.py             # Fixtures
├── test_chain_engine.py
├── test_parser.py
├── test_voice_personalities.py
├── test_stats.py
├── test_database.py
├── test_notifications.py
├── test_snooze.py
├── test_sound_library.py
├── test_location.py
├── test_calendar.py
└── test_background.py
```

---

## Open Questions (Pending Clarification)

1. **Platform:** React Native or Flutter? (Spec mentions both)
2. **TTS Caching:** Local filesystem or in-memory for tests?
3. **Database Path:** `/tmp/urgent-alarm.db` or app-specific storage?
4. **API Keys:** Environment variables for MiniMax, ElevenLabs?
5. **iOS/Android Parity:** Focus on iOS first or dual-platform?
6. **Background Scheduling:** This is a mobile-specific feature - how to test in Python harness?

---

## Quick Start Commands

```bash
# Run existing server
python3 src/test_server.py

# Run tests (once created)
python3 -m pytest tests/ -v

# Typecheck (if added)
python3 -m py_compile src/lib/*.py

# Lint
python3 -m py_compile src/test_server.py
```
