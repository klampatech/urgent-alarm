# Urgent Voice Alarm — Implementation Plan

## Analysis Summary

**Spec file:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md`

**Current state:** The `src/test_server.py` provides a basic functional prototype with:
- Simple chain engine (needs `get_next_unfired_anchor`)
- Basic keyword-based parser (no LLM adapter interface)
- SQLite database with partial schema
- Hard-coded voice messages (no per-tier variations)
- HTTP test endpoints

**Missing:** Everything else — adapters, services, background scheduling, calendar integration, location awareness, snooze/dismissal, sound library, stats, and comprehensive testing.

---

## Phase 1: Foundation (Core Logic & Database)

### 1.1 [HIGH] Database Schema & Migrations
- **Owner:** Core
- **Details:** Complete the SQLite schema per spec Section 13.3
- **Tasks:**
  - Add `custom_sounds` table
  - Add `calendar_sync` table  
  - Add origin fields to `reminders`: `origin_lat`, `origin_lng`, `origin_address`
  - Add `missed_reason`, `actual_arrival` to `history`
  - Add `tts_fallback`, `snoozed_to` to `anchors`
  - Add sound fields to `reminders`: `sound_category`, `selected_sound`, `custom_sound_path`
  - Add `calendar_event_id` to `reminders`
  - Enable foreign keys and WAL mode
  - Implement sequential migration system (schema_v1, v2, etc.)
- **Dependencies:** None

### 1.2 [HIGH] Chain Engine - Completeness
- **Owner:** Core
- **Details:** Complete implementation per spec Section 2.3
- **Tasks:**
  - Implement `get_next_unfired_anchor(reminder_id)` function
  - Add snoozed anchor tracking (`snoozed_to` field usage)
  - Add retry counter logic
  - Ensure chain computation is deterministic (enable unit testing)
  - Add validation: `arrival_time > departure_time + minimum_drive_time`
- **Acceptance:** TC-05 (next unfired anchor), TC-06 (determinism)
- **Dependencies:** 1.1

---

## Phase 2: Adapters & Interfaces

### 2.1 [HIGH] LLM Adapter Interface
- **Owner:** Parser
- **Details:** Create `ILanguageModelAdapter` interface and implementations per spec Section 3.3
- **Tasks:**
  - Define `ILanguageModelAdapter` abstract class
  - Implement `MiniMaxAdapter` (Anthropic-compatible API)
  - Implement `AnthropicAdapter`  
  - Implement `MockLanguageModelAdapter` for testing
  - Add system prompt configuration for extraction schema
  - Configure via environment variable (`LLM_PROVIDER`, `LLM_API_KEY`)
- **Dependencies:** None (pure interface)

### 2.2 [HIGH] TTS Adapter Interface  
- **Owner:** Voice/TTS
- **Details:** Create `ITTSAdapter` interface and implementations per spec Section 4.3
- **Tasks:**
  - Define `ITTSAdapter` abstract class
  - Implement `ElevenLabsAdapter`
  - Implement `MockTTSAdapter` for testing (writes 1-sec silent file)
  - Configure via environment variable (`ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`)
  - Implement TTS cache directory management: `/tts_cache/{reminder_id}/`
  - Implement cache invalidation on reminder deletion
- **Dependencies:** None (pure interface)

### 2.3 [MEDIUM] Keyword Extraction Fallback
- **Owner:** Parser  
- **Details:** Enhance existing keyword extraction per spec Section 3.3
- **Tasks:**
  - Add regex patterns: "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
  - Implement "tomorrow" date resolution
  - Return confidence score for fallback parsing
  - Handle "blah blah" rejection with user-facing error
- **Dependencies:** None (can be standalone)

---

## Phase 3: Services & Business Logic

### 3.1 [HIGH] Reminder Parsing Service
- **Owner:** Parser
- **Details:** End-to-end parsing with LLM + keyword fallback per spec Section 3
- **Tasks:**
  - Create `ReminderParser` service that orchestrates LLM adapter + keyword fallback
  - Display parsed interpretation for user confirmation
  - Support manual field correction before chain creation
  - Extract: `destination`, `arrival_time`, `drive_duration`, `reminder_type`
  - Handle reminder types: `countdown_event`, `simple_countdown`, `morning_routine`, `standing_recurring`
- **Dependencies:** 2.1, 2.3

### 3.2 [HIGH] Notification & Alarm Service
- **Owner:** Notifications
- **Details:** Implement escalation and behavior per spec Section 5
- **Tasks:**
  - Implement notification tier escalation: gentle chime → pointed beep → urgent siren → looping alarm
  - Implement DND awareness (silent notifications early, visual + vibration in final 5 min)
  - Implement quiet hours suppression (configurable, default 10pm-7am)
  - Queue anchors skipped due to DND/quiet hours for post-restriction firing
  - Drop anchors >15 minutes overdue silently
  - Implement chain overlap serialization (queue new anchors until current chain completes)
  - Implement T-0 alarm looping until user action
  - Display: destination label, time remaining, voice personality icon
- **Dependencies:** 1.2

### 3.3 [HIGH] Snooze & Dismissal Service
- **Owner:** Notifications
- **Details:** Implement per spec Section 9
- **Tasks:**
  - Implement tap snooze (1 minute)
  - Implement tap-and-hold with custom duration picker (1, 3, 5, 10, 15 min)
  - Implement chain re-computation after snooze (shift remaining anchors)
  - Re-register snoozed anchors with Notifee
  - Implement swipe dismiss with feedback prompt
  - Store feedback in SQLite
  - TTS snooze confirmation: "Okay, snoozed X minutes"
  - Persist snooze across app restarts
- **Dependencies:** 1.2, 3.2

### 3.4 [MEDIUM] Voice Personality Service
- **Owner:** Voice/TTS
- **Details:** Complete per spec Section 10.3
- **Tasks:**
  - Define 5 personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
  - Implement tier-specific message templates (minimum 3 variations per tier)
  - Support custom prompt mode (max 200 characters)
  - Store personality in user preferences
  - Ensure existing reminders retain creation-time personality
- **Dependencies:** 1.1

### 3.5 [MEDIUM] Stats & Feedback Loop Service
- **Owner:** Stats
- **Details:** Implement per spec Section 11.3
- **Tasks:**
  - Calculate weekly hit rate from history table
  - Implement feedback loop: adjust `drive_duration` for destination on "left_too_late" (+2 min, cap +15)
  - Calculate common miss window (most frequently missed urgency tier)
  - Implement streak counter for standing/recurring reminders
  - Archive data older than 90 days
- **Dependencies:** 1.1

---

## Phase 4: External Integrations

### 4.1 [HIGH] Background Scheduling Service
- **Owner:** Scheduler
- **Details:** Implement per spec Section 6 using Notifee architecture
- **Tasks:**
  - Register each anchor as individual background task
  - Implement recovery scan on app launch (fire anchors within 15-min grace window)
  - Drop anchors >15 min overdue, log with `missed_reason = "background_task_killed"`
  - Re-register pending anchors on crash recovery
  - Log warning if anchor fires >60s after scheduled time
  - (Note: Full Notifee implementation requires mobile-specific code)
- **Dependencies:** 1.2, 3.2

### 4.2 [MEDIUM] Calendar Integration
- **Owner:** Calendar
- **Details:** Implement per spec Section 7
- **Tasks:**
  - Define `ICalendarAdapter` interface
  - Implement `AppleCalendarAdapter` (EventKit)
  - Implement `GoogleCalendarAdapter` (Google Calendar API)
  - Implement calendar sync scheduler (on launch, every 15 min, background refresh)
  - Create suggestion cards for events with locations
  - Handle calendar permission denial with explanation banner
  - Handle sync failure gracefully (continue with manual reminders)
- **Dependencies:** 1.1

### 4.3 [MEDIUM] Location Awareness Service
- **Owner:** Location
- **Details:** Implement per spec Section 8
- **Tasks:**
  - Single location check at departure anchor only
  - Store origin: user-specified address OR current device location at creation
  - Implement 500m geofence comparison
  - If user within 500m at departure → fire firm/critical anchor immediately
  - Request location permission at first location-aware reminder creation
  - Handle denied permission gracefully (reminder without location escalation)
  - Zero location history retention
- **Dependencies:** 1.1

---

## Phase 5: Sound Library

### 5.1 [LOW] Sound Library
- **Owner:** Sound
- **Details:** Implement per spec Section 12
- **Tasks:**
  - Bundle 5 built-in sounds per category: Commute, Routine, Errand
  - Implement custom audio import (MP3, WAV, M4A, max 30 seconds)
  - Implement file picker integration
  - Transcode and normalize imported audio
  - Store in `custom_sounds` table
  - Implement per-reminder sound selection UI
  - Implement corrupted sound fallback (use category default + error log)
- **Dependencies:** 1.1

---

## Phase 6: Testing

### 6.1 [HIGH] Unit Tests - Core
- **Owner:** Testing
- **Details:** Unit tests for core components
- **Tasks:**
  - Chain engine determinism test (TC-06)
  - Chain engine full/compressed/minimum tests (TC-01 to TC-04)
  - `get_next_unfired_anchor` test (TC-05)
  - Parser unit tests (TC-01 to TC-07)
  - Keyword extraction fallback tests
  - Mock LLM adapter test (TC-07)
  - Mock TTS adapter test (TC-05)
  - Database schema validation tests
  - Migration sequence tests
- **Dependencies:** 1.1, 1.2, 2.1, 2.2

### 6.2 [MEDIUM] Integration Tests
- **Owner:** Testing
- **Details:** Full flow integration tests
- **Tasks:**
  - Create reminder flow: parse → chain → TTS → persist
  - Anchor firing flow: schedule → fire → mark fired
  - Snooze recovery flow: snooze → recompute → re-register
  - Feedback loop flow: dismiss → feedback → adjustment
  - Stats computation from history table
- **Dependencies:** 3.1, 3.3, 3.5

---

## Priority Summary

| Priority | Task | Phase |
|----------|------|-------|
| HIGH | Database Schema & Migrations | 1.1 |
| HIGH | Chain Engine Completeness | 1.2 |
| HIGH | LLM Adapter Interface | 2.1 |
| HIGH | TTS Adapter Interface | 2.2 |
| HIGH | Reminder Parsing Service | 3.1 |
| HIGH | Notification & Alarm Service | 3.2 |
| HIGH | Snooze & Dismissal Service | 3.3 |
| HIGH | Background Scheduling Service | 4.1 |
| HIGH | Unit Tests - Core | 6.1 |
| MEDIUM | Keyword Extraction Fallback | 2.3 |
| MEDIUM | Voice Personality Service | 3.4 |
| MEDIUM | Stats & Feedback Loop Service | 3.5 |
| MEDIUM | Calendar Integration | 4.2 |
| MEDIUM | Location Awareness Service | 4.3 |
| MEDIUM | Integration Tests | 6.2 |
| LOW | Sound Library | 5.1 |

---

## Notes

- **Mobile-specific code** (Notifee, EventKit, CoreLocation) requires React Native/Flutter implementation — not included in Python prototype
- **Graceful degradation** must be implemented throughout: LLM fails → keyword extraction; TTS fails → system sound + notification text
- **Mock adapters** are essential for testing without real API calls