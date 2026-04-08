# Implementation Plan: URGENT — AI Escalating Voice Alarm

## Executive Summary

The specification defines a comprehensive mobile alarm app with 13 major subsystems. The current codebase (`src/test_server.py`) contains only a basic proof-of-concept HTTP server with partial implementations of:
- Minimal chain engine (incorrect anchor count)
- Basic parser with keyword extraction (no LLM adapter)
- Voice message templates (no TTS integration)
- Simple SQLite schema (incomplete)

**Estimated completion: ~20-25 implementation tasks across 8 weeks**

---

## Phase 1: Core Infrastructure (Week 1-2)

### 1.1 Database Layer
**Priority: P0 (Blocker for everything else)**

- [ ] Create `src/lib/database/__init__.py` - Database module init
- [ ] Create `src/lib/database/schema.py` - Full schema from spec Section 13
  - reminders, anchors, history, user_preferences, destination_adjustments, calendar_sync, custom_sounds
  - Add missing columns: origin_lat, origin_lng, origin_address, sound_category, selected_sound, custom_sound_path, calendar_event_id, tts_fallback, snoozed_to, missed_reason, adjustment_minutes, hit_count, miss_count, sync_token, is_connected, filename, original_name, file_path, duration_seconds
- [ ] Create `src/lib/database/migrations.py` - Sequential migration system
  - Migration versioning (schema_v1, schema_v2, etc.)
  - In-memory mode for tests
  - WAL mode, foreign keys enforcement
- [ ] Create `src/lib/database/models.py` - Pydantic/SQLAlchemy models
  - Reminder, Anchor, History, UserPreferences, DestinationAdjustment, CalendarSync, CustomSound models
- [ ] Create `src/lib/database/repositories.py` - Repository pattern
  - ReminderRepository, AnchorRepository, HistoryRepository, etc.
- [ ] **Tests**: `tests/unit/test_database.py`
  - TC-01 to TC-05 from Section 13

### 1.2 Chain Engine (Refactor/Complete)
**Priority: P0 (Blocker for reminder creation)**

Current `test_server.py` has incorrect anchor generation. Need complete reimplementation:

- [ ] Create `src/lib/chain_engine/__init__.py`
- [ ] Create `src/lib/chain_engine/engine.py`
  - `compute_escalation_chain(arrival_time, drive_duration)` - **FIX anchor count to match spec**:
    - buffer ≥25 min: 8 anchors at T-30, T-25, T-20, T-15, T-10, T-5, T-1, T-0
    - buffer 20-24 min: 7 anchors (skip T-30)
    - buffer 10-19 min: compressed 5 anchors (urgent, pushing, firm, critical, alarm)
    - buffer 5-9 min: 3 anchors (firm, critical, alarm)
    - buffer ≤4 min: 2 anchors (critical, alarm) or 1 (alarm only)
  - `validate_chain(arrival_time, drive_duration)` - add proper validation
  - `get_next_unfired_anchor(reminder_id)` - recovery function
  - `recompute_chain_after_snooze(reminder_id, snooze_duration)` - for Section 9
- [ ] **Tests**: `tests/unit/test_chain_engine.py`
  - TC-01 to TC-06 from Section 2
  - TC-01: 30 min → 8 anchors (8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00)
  - TC-02: 15 min → compressed 5 anchors
  - TC-03: 3 min → 3 anchors (T-3, T-1, T-0)
  - TC-04: Invalid chain rejection
  - TC-05: Next unfired anchor recovery
  - TC-06: Chain determinism

### 1.3 Adapter Interfaces
**Priority: P1 (Foundation for mocking/testing)**

- [ ] Create `src/lib/adapters/__init__.py`
- [ ] Create `src/lib/adapters/base.py` - Abstract base classes
  - `ILanguageModelAdapter` - interface for LLM parsing
  - `ITTSAdapter` - interface for TTS generation
  - `ICalendarAdapter` - interface for calendar integration
- [ ] Create `src/lib/adapters/llm.py`
  - `MiniMaxAdapter` - MiniMax API implementation
  - `AnthropicAdapter` - Anthropic API implementation
  - `KeywordExtractionAdapter` - fallback parser
- [ ] Create `src/lib/adapters/tts.py`
  - `ElevenLabsAdapter` - TTS implementation
- [ ] Create `src/lib/adapters/calendar.py`
  - `AppleCalendarAdapter` - EventKit implementation
  - `GoogleCalendarAdapter` - Google Calendar API

---

## Phase 2: Core Features (Week 2-4)

### 2.1 Reminder Parsing
**Priority: P1**

- [ ] Create `src/lib/parser/__init__.py`
- [ ] Create `src/lib/parser/nl_parser.py`
  - `NaturalLanguageParser` class
  - LLM adapter integration
  - Keyword extraction fallback
  - Manual field correction support
- [ ] Create `src/lib/parser/mocks.py`
  - `MockLanguageModelAdapter` - for testing
- [ ] **Tests**: `tests/unit/test_parser.py`
  - TC-01 to TC-07 from Section 3
  - Parse "30 minute drive to Parker Dr, check-in at 9am"
  - Parse "dryer in 3 min" as simple_countdown
  - Parse "meeting tomorrow 2pm, 20 min drive"
  - LLM API failure fallback
  - Manual field correction
  - Unintelligible input rejection
  - Mock adapter verification

### 2.2 Voice & TTS Generation
**Priority: P1**

- [ ] Create `src/lib/voice/__init__.py`
- [ ] Create `src/lib/voice/tts_service.py`
  - TTS generation at reminder creation
  - Cache management (`/tts_cache/{reminder_id}/`)
  - Cache invalidation on delete
  - Fallback to system sounds
- [ ] Create `src/lib/voice/mocks.py`
  - `MockTTSAdapter` - writes silent file for tests
- [ ] Create `src/lib/voice/message_generator.py`
  - `VoiceMessageGenerator` class
  - Personality-aware message generation
  - Message variations (3 per tier per personality)
- [ ] Create `src/lib/voice/personalities.py`
  - Built-in voice personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
  - Custom personality support
- [ ] **Tests**: `tests/unit/test_voice.py`
  - TC-01 to TC-05 from Section 4
  - TTS clip generation
  - Cache playback
  - TTS fallback on API failure
  - Cache cleanup on delete
  - Mock TTS in tests

### 2.3 Notification & Alarm Behavior
**Priority: P1**

- [ ] Create `src/lib/notifications/__init__.py`
- [ ] Create `src/lib/notifications/notification_service.py`
  - `NotificationService` class
  - Notification tier escalation (gentle → beep → siren → alarm)
  - DND awareness
  - Quiet hours suppression
  - Overdue anchor handling (15-min rule)
  - Chain overlap serialization
  - T-0 alarm looping
- [ ] Create `src/lib/notifications/sounds.py`
  - Sound tier mapping
- [ ] **Tests**: `tests/unit/test_notifications.py`
  - TC-01 to TC-06 from Section 5
  - DND early anchor suppression
  - DND final 5-minute override
  - Quiet hours suppression
  - Overdue anchor drop (15-min rule)
  - Chain overlap serialization
  - T-0 alarm loops until action

### 2.4 Snooze & Dismissal Flow
**Priority: P1**

- [ ] Create `src/lib/snooze/__init__.py`
- [ ] Create `src/lib/snooze/snooze_service.py`
  - `SnoozeService` class
  - Tap snooze (1 minute)
  - Tap-and-hold custom snooze (1, 3, 5, 10, 15 min)
  - Chain re-computation on snooze
  - Snooze persistence across restarts
- [ ] Create `src/lib/snooze/dismissal.py`
  - `DismissalService` class
  - Feedback prompt handling
  - Feedback data storage
- [ ] **Tests**: `tests/unit/test_snooze.py`
  - TC-01 to TC-06 from Section 9
  - Tap snooze
  - Custom snooze
  - Chain re-computation after snooze
  - Dismissal feedback - timing correct
  - Dismissal feedback - timing off
  - Snooze persistence after restart

---

## Phase 3: Background & Platform (Week 3-5)

### 3.1 Background Scheduling
**Priority: P1**

- [ ] Create `src/lib/scheduler/__init__.py`
- [ ] Create `src/lib/scheduler/scheduler_service.py`
  - Notifee integration (conceptual - React Native bridge)
  - iOS: BGAppRefreshTask, BGProcessingTask
  - Android: WorkManager
  - Recovery scan on launch
  - Re-registration after crash
- [ ] Create `src/lib/scheduler/anchor_manager.py`
  - Anchor firing logic
  - Late fire warning (>60s delay)
- [ ] **Tests**: `tests/unit/test_scheduler.py`
  - TC-01 to TC-06 from Section 6
  - Anchor scheduling
  - Background fire with app closed
  - Recovery scan on launch
  - Overdue anchor drop
  - Pending anchors re-registered
  - Late fire warning

### 3.2 Location Awareness
**Priority: P2**

- [ ] Create `src/lib/location/__init__.py`
- [ ] Create `src/lib/location/location_service.py`
  - Single-point location check at departure
  - 500m geofence radius
  - Origin location resolution
  - Permission handling
  - No continuous tracking
- [ ] Create `src/lib/location/platform.py`
  - iOS: CoreLocation
  - Android: FusedLocationProvider
- [ ] **Tests**: `tests/unit/test_location.py`
  - TC-01 to TC-05 from Section 8
  - User still at origin → escalate immediately
  - User already left → normal chain
  - Location permission request
  - Location permission denied
  - Single location check only

### 3.3 Calendar Integration
**Priority: P2**

- [ ] Create `src/lib/calendar/__init__.py`
- [ ] Create `src/lib/calendar/calendar_service.py`
  - Calendar sync (app launch + every 15 min)
  - Suggestion card generation
  - Standing/recurring event handling
- [ ] Create `src/lib/calendar/platform_adapters.py`
  - Apple Calendar (EventKit)
  - Google Calendar API
- [ ] **Tests**: `tests/unit/test_calendar.py`
  - TC-01 to TC-06 from Section 7
  - Apple Calendar event suggestion
  - Google Calendar event suggestion
  - Suggestion → reminder creation
  - Permission denial handling
  - Sync failure graceful degradation
  - Recurring event handling

---

## Phase 4: Analytics & Extras (Week 4-6)

### 4.1 History & Stats
**Priority: P2**

- [ ] Create `src/lib/stats/__init__.py`
- [ ] Create `src/lib/stats/stats_service.py`
  - Hit rate calculation (trailing 7 days)
  - Streak counter (standing/recurring reminders)
  - Common miss window identification
  - Feedback loop drive duration adjustment (cap at +15 min)
- [ ] Create `src/lib/stats/feedback_loop.py`
  - `DestinationAdjustmentService` class
  - Adjustment calculation
- [ ] **Tests**: `tests/unit/test_stats.py`
  - TC-01 to TC-07 from Section 11
  - Hit rate calculation
  - Feedback loop drive duration adjustment
  - Feedback loop cap
  - Common miss window identification
  - Streak increment on hit
  - Streak reset on miss
  - Stats derived from history table

### 4.2 Sound Library
**Priority: P3**

- [ ] Create `src/lib/sounds/__init__.py`
- [ ] Create `src/lib/sounds/sound_library.py`
  - Built-in sounds per category (Commute, Routine, Errand, Custom)
  - Custom audio import (MP3, WAV, M4A, max 30 sec)
  - Sound selection per reminder
  - Corrupted sound fallback
- [ ] Create `src/lib/sounds/platform.py`
  - File import handling
  - Transcoding to normalized format
- [ ] **Tests**: `tests/unit/test_sounds.py`
  - TC-01 to TC-05 from Section 12
  - Built-in sound playback
  - Custom sound import
  - Custom sound playback
  - Corrupted sound fallback
  - Sound persistence on edit

### 4.3 Voice Personality System
**Priority: P2 (Already partially in test_server.py, need refactor)**

- [ ] Refactor `VOICE_PERSONALITIES` to `src/lib/voice/personalities.py`
- [ ] Add message variations (3 per tier per personality)
- [ ] Custom personality prompt support
- [ ] **Tests**: `tests/unit/test_personalities.py`
  - TC-01 to TC-05 from Section 10
  - Coach personality messages
  - No-nonsense personality messages
  - Custom personality
  - Personality immutability for existing reminders
  - Message variation

---

## Phase 5: Integration & App Shell (Week 6-8)

### 5.1 Reminder CRUD Service
**Priority: P1**

- [ ] Create `src/lib/reminders/__init__.py`
- [ ] Create `src/lib/reminders/reminder_service.py`
  - `ReminderService` class
  - Create reminder (parse → chain → TTS → persist)
  - Update reminder
  - Delete reminder (cascade to anchors, TTS cache)
  - List reminders
  - Get reminder by ID
- [ ] **Tests**: `tests/unit/test_reminder_service.py`

### 5.2 API Server (Refactor test_server.py)
**Priority: P1**

- [ ] Refactor `src/test_server.py`
  - Use new lib modules
  - Fix chain engine to match spec
  - Add missing endpoints
  - Remove duplicate code
- [ ] Add endpoints:
  - `GET /anchors/{reminder_id}` - List anchors for reminder
  - `POST /reminders/{id}/cancel` - Cancel reminder
  - `GET /stats/streak` - Streak counter
  - `GET /stats/common-miss-window` - Common miss window
  - `POST /reminders/{id}/snooze` - Snooze reminder
  - `POST /reminders/{id}/dismiss` - Dismiss with feedback
  - `GET /calendar/suggestions` - Calendar suggestions

### 5.3 App Configuration
**Priority: P3**

- [ ] Create `src/lib/config.py`
  - Environment variables for API keys
  - Default preferences
  - Sound library paths

---

## Task Dependencies

```
Phase 1 (Core Infrastructure)
├── 1.1 Database Layer ──────────┐
│   └── Required by ALL modules  │
├── 1.2 Chain Engine ───────────┤
│   └── Required by Reminder CRUD (5.1) │
└── 1.3 Adapter Interfaces ──────┘
    └── Required by: Parser (2.1), Voice (2.2), Calendar (3.3)

Phase 2 (Core Features)
├── 2.1 Parser ──────────────────┼──┐
├── 2.2 Voice ──────────────────┤  ├──→ 5.1 Reminder CRUD
├── 2.3 Notifications ──────────┤  │
└── 2.4 Snooze ─────────────────┘──┘

Phase 3 (Platform)
├── 3.1 Scheduler ──────────────┼──┐
├── 3.2 Location ───────────────┤  ├──→ 5.2 API Server
└── 3.3 Calendar ────────────────┘  │

Phase 4 (Analytics)
├── 4.1 Stats ───────────────────┤
└── 4.2 Sound Library ───────────┴──→ 5.2 API Server

Phase 5 (Integration)
└── 5.1 + 5.2 ────────────────────→ Complete app
```

---

## Verification Checklist

After each phase, run:

```bash
# Lint
python3 -m py_compile src/test_server.py
python3 -m py_compile src/lib/**/*.py

# Unit tests (once test files exist)
python3 -m pytest tests/unit/ -v

# Integration test
python3 src/test_server.py &
sleep 2
curl http://localhost:8090/health
curl "http://localhost:8090/chain?arrival=2026-04-09T09:00:00&duration=30"
```

---

## Spec Acceptance Criteria Coverage

| Section | Criteria Count | Tests Implemented | Status |
|---------|----------------|-------------------|--------|
| 2. Chain Engine | 6 | 0 | ❌ Not started |
| 3. Parser | 7 | 0 | ❌ Not started |
| 4. Voice/TTS | 5 | 0 | ❌ Not started |
| 5. Notifications | 6 | 0 | ❌ Not started |
| 6. Scheduler | 6 | 0 | ❌ Not started |
| 7. Calendar | 6 | 0 | ❌ Not started |
| 8. Location | 6 | 0 | ❌ Not started |
| 9. Snooze | 7 | 0 | ❌ Not started |
| 10. Personality | 6 | 0 | ❌ Not started |
| 11. Stats | 7 | 0 | ❌ Not started |
| 12. Sound Library | 5 | 0 | ❌ Not started |
| 13. Database | 5 | 0 | ❌ Not started |
| **Total** | **72** | **0** | **0%** |

---

## Current Codebase Analysis

### test_server.py Issues

1. **Chain Engine Bug**: Returns wrong anchor count
   - Current: Uses custom tier mapping
   - Spec requires: 8 anchors at T-30, T-25, T-20, T-15, T-10, T-5, T-1, T-0

2. **Missing `get_next_unfired_anchor`**: Not implemented

3. **No LLM Adapter**: Only keyword extraction exists

4. **No TTS Adapter**: Only message templates exist, no actual TTS

5. **Incomplete Schema**: Missing columns from spec

6. **No Tests**: No unit test coverage

### Recommended First Fix

The chain engine in `test_server.py` needs immediate correction to match spec:

```python
# Current (WRONG):
if buffer_minutes >= 25:
    tiers = [('calm', drive_duration), ...]  # Wrong minute offsets

# Should be:
if buffer_minutes >= 30:  # buffer, not duration
    tiers = [(30), (25), (20), (15), (10), (5), (1), (0)]
```

---

## Next Action

Start with **Phase 1.2: Chain Engine** - this is the core of the app and all other features depend on correct anchor generation. Fix the anchor count bug and add the `get_next_unfired_anchor` function.
