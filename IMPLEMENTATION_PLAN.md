# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Project Overview

This plan addresses gaps between the specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) and the current codebase. The current implementation is a minimal test server with basic chain computation, keyword parsing, and SQLite storage. Most features from the spec are unimplemented.

---

## Phase 1: Foundation (Core Infrastructure)

### 1.1 Data Persistence Layer
**Priority: P0 — All other features depend on this**

**Current State:**
- Basic SQLite schema exists but incomplete
- Missing: calendar_sync, custom_sounds, full destination_adjustments
- Missing: migrations, WAL mode, foreign key enforcement

**Tasks:**
- [ ] Add complete database schema per spec Section 13:
  - [ ] anchors: add `tts_fallback`, `snoozed_to` columns
  - [ ] reminders: add `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`
  - [ ] history: add `actual_arrival`, `missed_reason`, update timestamps
  - [ ] destination_adjustments: add `updated_at` column
  - [ ] Create `calendar_sync` table (apple, google)
  - [ ] Create `custom_sounds` table
- [ ] Implement versioned migration system (schema_v1, schema_v2, etc.)
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Create `Database.getInMemoryInstance()` for tests

**Acceptance:** Fresh DB passes all migration tests; in-memory test DB works

---

### 1.2 LLM Adapter Interface
**Priority: P0 — Quick Add depends on this**

**Current State:**
- Basic keyword extraction exists
- No mock-able adapter interface

**Tasks:**
- [ ] Create `ILanguageModelAdapter` interface with methods:
  - `parse(input_text: str) -> ParsedReminder`
  - `set_mock_response(fixture: dict)`
  - `is_mock_mode() -> bool`
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` for direct Anthropic API
- [ ] Implement `KeywordExtractionAdapter` as fallback
- [ ] Implement `MockLanguageModelAdapter` for tests

**Acceptance:** All adapters pass interface contract tests

---

### 1.3 TTS Adapter Interface
**Priority: P1 — Voice output depends on this**

**Current State:**
- Voice message templates exist
- No TTS file generation or caching

**Tasks:**
- [ ] Create `ITTSAdapter` interface with methods:
  - `generate_clip(text: str, voice_id: str, output_path: str) -> str`
  - `set_mock_mode(enabled: bool)`
  - `is_available() -> bool`
- [ ] Implement `ElevenLabsAdapter` with API integration
- [ ] Implement `MockTTSAdapter` for tests (writes silent 1s file)
- [ ] Implement TTS cache manager:
  - [ ] `cache_path(reminder_id: str, anchor_id: str) -> str`
  - [ ] `get_cached_clip(reminder_id: str, anchor_id: str) -> str | None`
  - [ ] `invalidate_cache(reminder_id: str)`
  - [ ] `generate_all_clips(reminder_id: str, anchors: list) -> dict`
- [ ] Implement fallback logic: on TTS failure → system sound + notification text

**Acceptance:** Mock TTS generates clips; fallback works when mock disabled

---

## Phase 2: Core Features

### 2.1 Escalation Chain Engine
**Priority: P0 — Core app logic**

**Current State:**
- Basic `compute_escalation_chain()` exists
- Missing: `get_next_unfired_anchor()`, chain validation, determinism

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id: str) -> Anchor | None`
- [ ] Add chain validation per spec 2.3.8: reject `arrival_time <= departure_time + minimum_drive_time`
- [ ] Implement chain determinism (same inputs → same output for testing)
- [ ] Add `snooze_chain(reminder_id: str, snooze_minutes: int)`:
  - Shift remaining unfired anchors by snooze duration
  - Update `snoozed_to` column
  - Re-register with scheduler
- [ ] Add `recompute_chain_from_now(reminder_id: str)` for after-snooze recovery

**Acceptance:** All test scenarios from spec Section 2.5 pass

---

### 2.2 Reminder Parsing & Creation
**Priority: P0 — Primary user interaction**

**Current State:**
- Basic `parse_reminder_natural()` with keyword extraction
- No confirmation card / field editing

**Tasks:**
- [ ] Integrate LLM adapter into parser
- [ ] Implement fallback chain: LLM → keyword extraction → error
- [ ] Implement parsed result confirmation card:
  - Display extracted fields for user review
  - Allow manual field correction
  - Return confirmed values for chain creation
- [ ] Handle reminder types: `countdown_event`, `simple_countdown`, `morning_routine`, `standing_recurring`
- [ ] Implement destination adjustment lookup during creation (feedback loop)

**Acceptance:** All test scenarios from spec Section 3.5 pass

---

### 2.3 Voice Personality System
**Priority: P1 — User experience**

**Current State:**
- Basic templates for 5 personalities
- No message variation, no custom prompts

**Tasks:**
- [ ] Expand templates per personality/tier (min 3 variations each)
- [ ] Implement message variation selection (random rotation)
- [ ] Implement custom prompt support:
  - Store custom prompt in user_preferences
  - Append to message generation system prompt
  - Max 200 characters validation
- [ ] Map personalities to ElevenLabs voice IDs:
  - Coach: voice_id_1
  - Assistant: voice_id_2
  - Best Friend: voice_id_3
  - No-nonsense: voice_id_4
  - Calm: voice_id_5

**Acceptance:** All test scenarios from spec Section 10.5 pass

---

### 2.4 Snooze & Dismissal Flow
**Priority: P1 — Critical user interaction**

**Current State:**
- No snooze implementation
- No feedback prompts

**Tasks:**
- [ ] Implement tap snooze (1 minute default)
- [ ] Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation on snooze
- [ ] Implement snooze persistence (survive app restart)
- [ ] Implement dismissal feedback flow:
  - Show "You missed [destination] — was the timing right?" prompt
  - On "No": show "What was wrong?" with options
  - Store feedback in history table
- [ ] Implement TTS snooze confirmation: "Okay, snoozed [X] minutes"

**Acceptance:** All test scenarios from spec Section 9.5 pass

---

### 2.5 History, Stats & Feedback Loop
**Priority: P1 — Learning system**

**Current State:**
- Basic `calculate_hit_rate()` exists
- Incomplete destination_adjustments

**Tasks:**
- [ ] Implement `calculate_hit_rate(days: int = 7) -> float` per spec 11.3.1
- [ ] Implement `get_common_miss_window(destination: str) -> str | None`
- [ ] Implement streak counter:
  - Increment on hit for recurring reminders
  - Reset on miss
  - Store in destination_adjustments or separate streak table
- [ ] Implement feedback loop adjustment:
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
  - Cap at +15 minutes
- [ ] Implement 90-day retention / archival logic

**Acceptance:** All test scenarios from spec Section 11.5 pass

---

## Phase 3: System Integration

### 3.1 Background Scheduling & Reliability
**Priority: P2 — Reliability**

**Tasks:**
- [ ] Implement Notifee adapter (or equivalent):
  - Register each anchor as individual background task
  - Handle iOS BGAppRefreshTask + BGProcessingTask
  - Handle Android WorkManager
- [ ] Implement recovery scan on app launch:
  - Find all overdue unfired anchors
  - Fire those within 15-minute grace window
  - Drop those >15 minutes overdue
  - Log with `missed_reason`
- [ ] Implement pending anchor re-registration after crash
- [ ] Add late fire warning (>60s after scheduled)

**Acceptance:** All test scenarios from spec Section 6.5 pass

---

### 3.2 Notification & Alarm Behavior
**Priority: P2 — User experience**

**Tasks:**
- [ ] Implement notification tier escalation:
  - Gentle chime (calm/casual)
  - Pointed beep (pointed/urgent)
  - Urgent siren (pushing/firm)
  - Looping alarm (critical/alarm)
- [ ] Implement DND awareness:
  - Early anchors: silent notification
  - Final 5 minutes: visual override + vibration
- [ ] Implement quiet hours:
  - User-configurable start/end (default 10pm–7am)
  - Suppress nudges during quiet hours
  - Queue and fire after quiet hours (if within 15 min)
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] Implement T-0 alarm looping until user action

**Acceptance:** All test scenarios from spec Section 5.5 pass

---

### 3.3 Calendar Integration
**Priority: P2 — Convenience feature**

**Tasks:**
- [ ] Create `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement calendar sync scheduler:
  - On app launch
  - Every 15 minutes while app open
  - Via background refresh
- [ ] Implement suggestion cards:
  - Show for events with location
  - Allow "Add Reminder" confirmation
- [ ] Handle permission denial gracefully
- [ ] Handle sync failure gracefully (continue with manual reminders)

**Acceptance:** All test scenarios from spec Section 7.5 pass

---

### 3.4 Location Awareness
**Priority: P3 — Advanced feature**

**Tasks:**
- [ ] Implement single-point location check at departure anchor:
  - Get origin from reminder (user-specified or device location at creation)
  - Get current location via CoreLocation/FusedLocationProvider
  - Compare with 500m geofence radius
- [ ] Implement escalation on origin detection:
  - If within 500m at departure: fire firm/critical tier immediately
  - If left (>500m): proceed with normal chain
- [ ] Request location permission only at first location-aware reminder
- [ ] Handle permission denied gracefully
- [ ] Do NOT store location history (single check only)

**Acceptance:** All test scenarios from spec Section 8.5 pass

---

### 3.5 Sound Library
**Priority: P3 — Customization**

**Tasks:**
- [ ] Define sound categories: Commute (5), Routine (5), Errand (5), Custom
- [ ] Bundle built-in sounds with app
- [ ] Implement custom audio import:
  - Support MP3, WAV, M4A (max 30 seconds)
  - Transcode to normalized format
  - Store in app sandbox
- [ ] Implement per-reminder sound selection
- [ ] Implement corrupted/missing sound fallback
- [ ] Associate custom sounds with user (persist across reinstalls)

**Acceptance:** All test scenarios from spec Section 12.5 pass

---

## Phase 4: Testing & Polish

### 4.1 Test Coverage
**Priority: Ongoing**

**Tasks:**
- [ ] Unit tests for chain engine (all spec TC-01 through TC-06)
- [ ] Unit tests for parser (all spec TC-01 through TC-07)
- [ ] Unit tests for TTS adapter (mock mode)
- [ ] Unit tests for voice personality messages (variation tests)
- [ ] Unit tests for snooze & dismissal
- [ ] Unit tests for stats calculations
- [ ] Integration tests for full reminder creation flow
- [ ] Database migration tests

**Run tests:** `python3 -m pytest harness/` (or manual harness test)

---

### 4.2 Error Handling & Graceful Degradation
**Priority: P2**

**Tasks:**
- [ ] Implement fallback chain for all external dependencies:
  - LLM failure → keyword extraction
  - TTS failure → system sound + notification text
  - Calendar failure → continue with manual reminders
  - Location failure → create reminder without location escalation
- [ ] Log all errors with context
- [ ] Surface actionable error messages to user
- [ ] Never crash on external dependency failure

---

### 4.3 Definition of Done Verification
**Priority: P1**

**Tasks:**
- [ ] Verify all acceptance criteria from Sections 2–13 have passing tests
- [ ] Verify harness/scenario validation passes
- [ ] Final lint check: `python3 -m py_compile harness/scenario_harness.py src/test_server.py`

---

## Implementation Order (Dependency Graph)

```
Phase 1 (Foundation):
├─ 1.1 Database Layer (P0)
│   └─ Enables: everything
├─ 1.2 LLM Adapter (P0)
│   └─ Enables: 2.2 Reminder Parsing
└─ 1.3 TTS Adapter (P1)
    └─ Enables: 2.3 Voice Personality

Phase 2 (Core Features):
├─ 2.1 Chain Engine (P0) ← most critical
│   └─ Enables: 2.4 Snooze
├─ 2.2 Reminder Parsing (P0)
│   └─ Uses: 1.1, 1.2
├─ 2.3 Voice Personality (P1)
│   └─ Uses: 1.3
├─ 2.4 Snooze & Dismissal (P1)
│   └─ Uses: 2.1
└─ 2.5 Stats & Feedback (P1)
    └─ Uses: 1.1

Phase 3 (Integration):
├─ 3.1 Background Scheduling (P2)
├─ 3.2 Notification Behavior (P2)
├─ 3.3 Calendar Integration (P2)
├─ 3.4 Location Awareness (P3)
└─ 3.5 Sound Library (P3)

Phase 4 (Testing):
├─ 4.1 Test Coverage
├─ 4.2 Error Handling
└─ 4.3 Definition of Done
```

---

## Notes

- **No React Native/Flutter UI** — this codebase is a Python backend/test server per current structure
- **In-memory SQLite** should be used for all tests per spec 13.3.3
- **UUID v4** required for all primary keys per spec 13.3.6
- **ISO 8601 timestamps** in UTC internally, local time for display
- **External APIs** (ElevenLabs, Anthropic, Google Calendar) require env var configuration

---

*Generated: 2026-04-08*
