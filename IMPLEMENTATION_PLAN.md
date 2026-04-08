# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Analysis Summary

The project has a basic HTTP server (`src/test_server.py`) implementing core features but is missing critical components from the specification. There's also a `harness/` directory referenced but not yet explored for the scenario testing framework.

---

## Priority 1: Foundation & Bug Fixes

### 1.1 Fix Escalation Chain Engine (CRITICAL BUG)
**Current state:** Implementation has incorrect anchor calculations. For a 30-min drive, `firm` is placed at `drive_duration - 25 = T-5` instead of T-25.

**Spec requirement:**
- Full chain (≥25 min): T-30, T-25, T-20, T-15, T-10, T-5, T-1, T-0
- Compressed (10-24 min): Skip calm/casual, start at urgent
- Short (5-9 min): Start at pushing
- Minimum (≤5 min): Firm, critical, alarm only

**Action:** Rewrite `compute_escalation_chain()` to match spec exactly.

**Files:** `src/test_server.py`

---

### 1.2 Enhance Data Persistence Layer
**Current state:** Basic tables exist but missing columns per spec.

**Missing columns per spec:**
- `reminders`: origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id, updated_at
- `anchors`: tts_fallback, snoozed_to
- `history`: actual_arrival, missed_reason
- `user_preferences`: updated_at
- New tables: `calendar_sync`, `custom_sounds`

**Missing features:**
- Migration system (sequential, versioned)
- In-memory SQLite mode for tests (`?mode=memory`)
- WAL journal mode
- Foreign key enforcement (`PRAGMA foreign_keys = ON`)

**Action:** Create `src/lib/database.py` with schema definitions, migrations, and connection management.

---

### 1.3 Add Interface Abstractions for Testability
**Spec requirement:** All external adapters (LLM, TTS, Calendar, Location) must be mock-able.

**Action:** Create interface files:
- `src/lib/interfaces/llm_adapter.py` - ILanguageModelAdapter interface
- `src/lib/interfaces/tts_adapter.py` - ITTSAdapter interface
- `src/lib/interfaces/calendar_adapter.py` - ICalendarAdapter interface
- `src/lib/interfaces/location_adapter.py` - ILocationAdapter interface

Each interface should have a mock implementation for tests.

---

## Priority 2: Core Features

### 2.1 Natural Language Parser with LLM Fallback
**Current state:** Basic keyword extraction only.

**Spec requirement:**
- LLM adapter supporting MiniMax/Anthropic API
- Fallback to keyword extraction on API failure
- Confidence score in parsed result
- Support for: destination, arrival_time, drive_duration, reminder_type

**Action:** Create `src/lib/parser.py` with:
- `NaturalLanguageParser` class using configurable adapter
- `KeywordExtractor` fallback
- Support for "Parker Dr 9am, 30 min drive", "dryer in 3 min", "meeting tomorrow 2pm"

---

### 2.2 Voice Message Generation with Variations
**Current state:** Single template per tier per personality (would sound robotic).

**Spec requirement:** Minimum 3 message variations per tier per personality.

**Action:** Expand `src/lib/voice.py`:
- Add message variation pools for each personality/tier combination
- Implement random selection (or round-robin for determinism)
- Add custom prompt mode (max 200 chars)

---

### 2.3 History, Stats & Feedback Loop
**Current state:** Basic hit rate only.

**Missing per spec:**
- `destination_adjustments` table populated correctly
- Feedback loop: +2 min per late miss, capped at +15 min
- Common miss window identification
- Streak counter for recurring reminders
- Stats derived from history table (single source of truth)

**Action:** Create `src/lib/stats.py` with:
- `calculate_hit_rate(days=7)` - existing, needs fixing
- `get_destination_adjustment(destination)` - returns adjustment minutes
- `get_common_miss_window(destination)` - returns most-missed tier
- `get_streak(reminder_id)` - current streak count
- `apply_feedback(outcome, feedback_type, destination)` - updates adjustments

---

## Priority 3: External Integrations

### 3.1 TTS Adapter (ElevenLabs)
**Spec requirement:** Pre-generate all TTS clips at reminder creation, cache locally.

**Action:** Create `src/lib/adapters/tts_adapter.py`:
- ElevenLabs adapter implementing ITTSAdapter
- Mock adapter for tests
- Cache management (invalidate on reminder delete)
- Fallback behavior on API failure (mark anchor tts_fallback=true)

**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/mock_tts.py`

---

### 3.2 Calendar Integration
**Spec requirement:** Apple Calendar (EventKit) and Google Calendar API.

**Action:** Create:
- `src/lib/adapters/apple_calendar_adapter.py`
- `src/lib/adapters/google_calendar_adapter.py`
- Both implement `ICalendarAdapter`

**Features:**
- Sync on launch and every 15 minutes
- Only events with locations trigger suggestions
- Recurring events handled
- Permission denial handling with explanation banner

---

### 3.3 Location Awareness
**Spec requirement:** Single check at departure trigger only. No continuous tracking.

**Action:** Create `src/lib/adapters/location_adapter.py`:
- CoreLocation/FusedLocationProvider single-call implementation
- Geofence radius: 500 meters
- On departure anchor: if within 500m of origin → fire critical tier immediately
- Location permission requested at first location-aware reminder (not on launch)
- No location history retained

---

## Priority 4: Notification & Alarm Behavior

### 4.1 Notification System
**Spec requirement:**
- Tier escalation: gentle chime → pointed beep → urgent siren → looping alarm
- DND: early anchors = silent notification; final 5 min = visual + vibration override
- Quiet hours: suppress between set times (default 10pm–7am)
- Overdue anchors: queue, drop if >15 min overdue

**Action:** Create `src/lib/notifications.py`:
- `NotificationManager` class
- Tier-to-sound mapping
- DND awareness
- Quiet hours configuration

---

### 4.2 Snooze & Dismissal Flow
**Spec requirement:**
- Tap: snooze 1 min
- Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- Swipe dismiss: feedback prompt
- Chain re-computation on snooze
- TTS confirmation: "Okay, snoozed [X] minutes"

**Action:** Create `src/lib/snooze.py`:
- `SnoozeManager` class
- `recompute_chain_after_snooze(reminder_id, snooze_duration)`
- Feedback prompt integration
- Persistence of snoozed timestamps

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration
**Spec requirement:** Reliable background scheduling via BGTaskScheduler (iOS) / WorkManager (Android).

**Action:** Create `src/lib/scheduler.py`:
- Register each anchor as individual Notifee task
- Recovery scan on app launch (fire anchors within 15-min grace window)
- Re-register pending anchors after crash/force-kill
- Log late fires (>60s after scheduled)

**Note:** This is React Native specific. For Python server, implement equivalent with `schedule` library or background task queue.

---

## Priority 6: Sound Library

### 6.1 Sound System
**Spec requirement:**
- Built-in sounds per category (commute, routine, errand, custom)
- Custom audio import (MP3, WAV, M4A, max 30 seconds)
- Per-reminder sound selection
- Corrupted file fallback to category default

**Action:** Create `src/lib/sounds.py`:
- `SoundLibrary` class
- Built-in sound paths
- Import handling
- Fallback logic

---

## Priority 7: API Expansion

### 7.1 Expand HTTP API
**Current endpoints:**
- GET /health, /chain, /reminders, /stats/hit-rate
- POST /reminders, /parse, /voice/message, /history, /anchors/fire

**Add per spec:**
- GET/PUT/DELETE /reminders/{id}
- GET /anchors/{reminder_id}
- POST /reminders/{id}/snooze
- DELETE /reminders/{id}/dismiss
- GET /stats/common-miss-window
- GET /stats/streaks
- POST /sounds/import
- GET /sounds
- Calendar sync endpoints

---

## Priority 8: Testing Infrastructure

### 8.1 Add Tests
**Per spec TC scenarios (Sections 2-13):**
- Chain engine tests (TC-01 through TC-06)
- Parser tests (TC-01 through TC-07)
- TTS tests (TC-01 through TC-05)
- Notification tests (TC-01 through TC-06)
- Stats tests (TC-01 through TC-07)
- Database tests (TC-01 through TC-05)

**Action:** Create `tests/` directory with pytest test files:
- `tests/test_chain_engine.py`
- `tests/test_parser.py`
- `tests/test_voice.py`
- `tests/test_stats.py`
- `tests/test_database.py`

---

## Implementation Order

```
Phase 1: Foundation (do first)
├── 1.1 Fix escalation chain engine (bug fix)
├── 1.2 Enhance data persistence
└── 1.3 Add interface abstractions

Phase 2: Core Logic
├── 2.1 Natural language parser
├── 2.2 Voice message variations
└── 2.3 History/stats/feedback loop

Phase 3: External Integrations
├── 3.1 TTS adapter
├── 3.2 Calendar adapters
└── 3.3 Location adapter

Phase 4: UI Logic
├── 4.1 Notification system
└── 4.2 Snooze/dismissal

Phase 5: Background & Sound
├── 5.1 Scheduler
└── 6.1 Sound library

Phase 7: API & Testing
├── 7.1 Expand API
└── 8.1 Add tests
```

---

## Notes

- Spec file: `specs/urgent-voice-alarm-app-2026-04-08.md` (concept)
- Spec file: `specs/urgent-voice-alarm-app-2026-04-08.spec.md` (detailed requirements)
- Current code: `src/test_server.py` (basic HTTP server)
- No `src/lib/` directory yet - must be created
- Spec mentions React Native but this is a Python implementation for testing harness
- All external service integrations (LLM, TTS, Calendar, Location) must be mock-able for tests