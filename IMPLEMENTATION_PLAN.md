# Implementation Plan — Urgent Voice Alarm App

## Overview

The current codebase (`src/test_server.py`) contains a basic HTTP test server with minimal implementations of the chain engine, keyword parser, and voice message templates. The specification defines 13 major systems. This plan identifies all gaps and prioritizes tasks by dependencies.

**Current State:**
- `src/test_server.py` — Basic HTTP server with partial implementations
- `harness/` — Empty directory (needs infrastructure)
- `scenarios/` — 15 test scenario YAMLs exist
- `src/lib/` — Does not exist (all code is in single file)

---

## Priority 1: Foundation (Critical — All Other Work Depends On These)

### 1.1 Complete Database Schema Migration System
**Files to create:** `src/lib/db/__init__.py`, `src/lib/db/connection.py`, `src/lib/db/migrations.py`

**Spec Reference:** Section 13 — Data Persistence

**Status:** Partial — basic tables exist, missing complete schema, migrations, and FK enforcement

**Gaps in Current Code (`src/test_server.py`):**
- Missing `calendar_sync` table
- Missing `custom_sounds` table
- Missing columns on `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`, `sound_category`, `selected_sound`
- Missing columns on `anchors`: `tts_clip_path`, `tts_fallback`, `snoozed_to`
- Missing columns on `history`: `actual_arrival`, `missed_reason`
- No migration versioning system
- No WAL mode, no FK enforcement

**Tasks:**
1. [ ] Create `schema_version` tracking table
2. [ ] Create migration runner with sequential versioned migrations
3. [ ] Create all spec-compliant tables in migration order
4. [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
5. [ ] Ensure cascade deletes work correctly (`ON DELETE CASCADE`)
6. [ ] Create `DatabaseConnection` class with `getInMemoryInstance()` for tests
7. [ ] All timestamps stored in ISO 8601 format (UTC internally)
8. [ ] Generate UUID v4 for all primary keys

**Verification:**
- [ ] Fresh install applies all migrations in order
- [ ] In-memory test database starts empty with all migrations applied
- [ ] `reminders.id` is always a valid UUID v4
- [ ] Deleting a reminder cascades to delete its anchors

---

### 1.2 Test Harness Infrastructure
**Files to create:** `harness/scenario_harness.py`, `harness/fixtures/__init__.py`, `harness/fixtures/mock_llm.py`, `harness/fixtures/mock_tts.py`

**Spec Reference:** Section 1.2 (from existing plan), Section 14 — Definition of Done

**Status:** Not implemented — harness directory is empty

**Gaps:**
- No scenario runner exists
- No test database setup
- No mock fixtures for LLM/TTS

**Tasks:**
1. [ ] Create `ScenarioHarness` class that loads and runs YAML scenarios
2. [ ] Implement scenario step executor (HTTP API calls)
3. [ ] Implement assertion validators (http_status, db_record, llm_judge)
4. [ ] Create `MockLanguageModelAdapter` for test fixtures
5. [ ] Create `MockTTSAdapter` for test fixtures (writes silent audio file)
6. [ ] Create `getInMemoryDatabase()` helper that resets between scenarios
7. [ ] Write result to `/tmp/ralph-scenario-result.json` after run

**Verification:**
- [ ] `python3 -m pytest harness/` runs successfully
- [ ] `python3 -m py_compile harness/scenario_harness.py src/test_server.py` passes
- [ ] All 15 scenarios in `scenarios/` directory execute

---

### 1.3 Refactor Monolithic test_server.py
**Files to create:** `src/lib/__init__.py`, split existing code into modules

**Status:** All code is in single 800-line `test_server.py`

**Tasks:**
1. [ ] Create `src/lib/chain/__init__.py`, `src/lib/chain/engine.py`
2. [ ] Create `src/lib/parser/__init__.py`, `src/lib/parser/nl_parser.py`
3. [ ] Create `src/lib/voice/__init__.py`, `src/lib/voice/personalities.py`
4. [ ] Create `src/lib/stats/__init__.py`, `src/lib/stats/calculator.py`
5. [ ] Move HTTP handlers to `src/api/` module
6. [ ] Keep `test_server.py` as thin HTTP wrapper that imports from `src/lib/`

**Verification:**
- [ ] All imports work after refactoring
- [ ] Existing tests still pass

---

## Priority 2: Core Domain Logic

### 2.1 Chain Engine Completeness
**File to create/modify:** `src/lib/chain/engine.py`

**Spec Reference:** Section 2 — Escalation Chain Engine

**Status:** Partial — basic anchor computation exists in `test_server.py`

**Gaps:**
- No `get_next_unfired_anchor()` function
- No TTS clip path tracking per anchor
- No fire_count increment on retry
- Chain not deterministic (depends on runtime clock in tests)
- No validation that `arrival_time > departure + minimum_drive_time`

**Tasks:**
1. [ ] Implement `compute_escalation_chain(arrival_time, drive_duration)` — deterministic, pure function
2. [ ] Implement `get_next_unfired_anchor(reminder_id)` query
3. [ ] Add `tts_clip_path`, `tts_fallback`, `fire_count`, `snoozed_to` to anchor storage
4. [ ] Add chain validation: reject if `drive_duration > time_to_arrival`
5. [ ] Handle compressed chains per spec:
   - ≥25 min buffer: 8 anchors (full chain)
   - 20-24 min: 7 anchors (skip calm)
   - 10-19 min: 5 anchors (start at urgent)
   - 5-9 min: 3 anchors (firm, critical, alarm)
   - ≤5 min: 2 anchors (firm/alarm based on duration)
6. [ ] Make chain computation pure (accept `now` as parameter for determinism)

**Acceptance Criteria (Spec Section 2.4):**
- [ ] Chain for "30 min drive, arrive 9am" produces 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "10 min drive, arrive 9am" produces 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "3 min drive, arrive 9am" produces 3 anchors: 8:57, 8:59, 9:00
- [ ] Chain with `drive_duration > arrival_time` is rejected with validation error
- [ ] `get_next_unfired_anchor` correctly returns the earliest unfired anchor after restart
- [ ] Anchors are sorted by timestamp ascending in database

**Test Cases (Spec Section 2.5):**
- [ ] TC-01: Full chain generation (≥25 min buffer)
- [ ] TC-02: Compressed chain (10-24 min buffer)
- [ ] TC-03: Minimum chain (≤5 min buffer)
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism

---

### 2.2 LLM Adapter + Parser Enhancement
**Files to create:** `src/lib/parser/__init__.py`, `src/lib/parser/llm_adapter.py`, `src/lib/parser/keyword_extractor.py`, `src/lib/parser/nl_parser.py`

**Spec Reference:** Section 3 — Reminder Parsing & Creation

**Status:** Partial — basic keyword extraction exists in `test_server.py`

**Gaps:**
- No `ILanguageModelAdapter` interface
- No MiniMax or Anthropic API implementation
- No mock adapter for testing
- Keyword extraction is brittle, doesn't handle all spec formats
- No confidence scoring
- No user confirmation flow

**Tasks:**
1. [ ] Create `ILanguageModelAdapter` abstract interface
2. [ ] Create `MiniMaxAdapter` implementation (Anthropic-compatible endpoint)
3. [ ] Create `AnthropicAdapter` implementation
4. [ ] Create `MockLanguageModelAdapter` for tests with fixture responses
5. [ ] Improve keyword extractor to handle all formats:
   - "X min drive"
   - "X-minute drive"
   - "in X minutes"
   - "arrive at X"
   - "check-in at X"
   - "Parker Dr 9am, 30 min drive"
6. [ ] Implement confidence scoring and LLM fallback to keyword extraction
7. [ ] Implement `parse_and_confirm()` returning parsed fields for UI review
8. [ ] Handle "tomorrow" date resolution correctly
9. [ ] Handle relative time ("in 3 minutes") vs absolute time ("at 9am")

**Acceptance Criteria (Spec Section 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses to destination = "Parker Dr check-in", arrival_time = today's 9:00 AM, drive_duration = 30
- [ ] "dryer in 3 min" parses as simple_countdown with drive_duration = 0 and arrival_time = now + 3 minutes
- [ ] "meeting tomorrow 2pm, 20 min drive" parses with arrival_time = next day's 2:00 PM
- [ ] On API failure, keyword extraction produces best-effort parsed object with confidence_score < 1.0
- [ ] User can edit any parsed field and confirm
- [ ] Empty/unintelligible input ("blah blah") returns user-facing error

**Test Cases (Spec Section 3.5):**
- [ ] TC-01: Full natural language parse
- [ ] TC-02: Simple countdown parse
- [ ] TC-03: Tomorrow date resolution
- [ ] TC-04: LLM API failure fallback
- [ ] TC-05: Manual field correction
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

## Priority 3: Voice & TTS System

### 3.1 TTS Adapter Interface + Cache
**Files to create:** `src/lib/tts/__init__.py`, `src/lib/tts/adapter.py`, `src/lib/tts/generator.py`, `src/lib/tts/cache_manager.py`

**Spec Reference:** Section 4 — Voice & TTS Generation

**Status:** Not implemented — only message templates exist in `VOICE_PERSONALITIES`

**Gaps:**
- No ElevenLabs adapter
- No `ITTSAdapter` interface
- No TTS clip generation
- No `/tts_cache/` directory management
- No cache invalidation on reminder delete
- No fallback when API unavailable

**Tasks:**
1. [ ] Create `ITTSAdapter` abstract interface
2. [ ] Create `ElevenLabsAdapter` implementation with voice ID mapping
3. [ ] Create `MockTTSAdapter` for tests (writes 1-second silent file)
4. [ ] Create cache manager with `/tts_cache/{reminder_id}/` structure
5. [ ] Implement `generate_tts_for_anchors(reminder_id, anchors, personality)` pre-generation
6. [ ] Implement fallback: if TTS fails, mark `tts_fallback = true`, use notification text
7. [ ] Implement cache invalidation when reminder deleted
8. [ ] TTS generation completes within 30 seconds (ElevenLabs async with polling)

**Acceptance Criteria (Spec Section 4.4):**
- [ ] New reminder generates MP3 clips (one per anchor) stored in `/tts_cache/{reminder_id}/`
- [ ] Playing anchor fires correct pre-generated clip from local cache
- [ ] When ElevenLabs API unavailable, fallback to system sound + notification text
- [ ] Reminder deletion removes all cached TTS files for that reminder
- [ ] TTS generation uses correct voice ID for selected personality

**Test Cases (Spec Section 4.5):**
- [ ] TC-01: TTS clip generation at creation
- [ ] TC-02: Anchor fires from cache
- [ ] TC-03: TTS fallback on API failure
- [ ] TC-04: TTS cache cleanup on delete
- [ ] TC-05: Mock TTS in tests

---

### 3.2 Voice Personality Message Variations
**Files to create/modify:** `src/lib/voice/personalities.py` (expand from current `VOICE_PERSONALITIES` in test_server.py)

**Spec Reference:** Section 10 — Voice Personality System

**Status:** Partial — single template per tier

**Gaps:**
- Only 1 message variation per tier
- Spec requires minimum 3 variations per tier per personality
- No custom prompt mode

**Tasks:**
1. [ ] Expand each personality (Coach, Assistant, Best Friend, No-nonsense, Calm) to have 3+ message templates per urgency tier
2. [ ] Add random selection (or round-robin) for variation across generations
3. [ ] Implement custom prompt mode: user writes prompt (max 200 chars) appended to system prompt
4. [ ] Ensure existing reminders retain their personality at creation time
5. [ ] Add "Calm" personality (gentle-only, no aggression)

**Acceptance Criteria (Spec Section 10.4):**
- [ ] "Coach" personality at T-5 produces motivating message with exclamation
- [ ] "No-nonsense" personality at T-5 produces brief, direct message
- [ ] "Assistant" personality at T-5 produces calm, clear message
- [ ] Custom prompt modifies message tone appropriately
- [ ] Changing default personality does not affect existing reminders
- [ ] Each personality generates at least 3 message variations per urgency tier

**Test Cases (Spec Section 10.5):**
- [ ] TC-01: Coach personality messages
- [ ] TC-02: No-nonsense personality messages
- [ ] TC-03: Custom personality
- [ ] TC-04: Personality immutability for existing reminders
- [ ] TC-05: Message variation

---

## Priority 4: Notification & Alarm Behavior

### 4.1 Notification Tier System
**Files to create:** `src/lib/notifications/__init__.py`, `src/lib/notifications/tier_manager.py`, `src/lib/notifications/sound_player.py`

**Spec Reference:** Section 5 — Notification & Alarm Behavior

**Status:** Not implemented

**Gaps:**
- No notification tier mapping to sounds
- No DND awareness (silent vs. visual+vibration)
- No quiet hours enforcement
- No chain overlap serialization (queue new anchors)
- No T-0 alarm looping

**Tasks:**
1. [ ] Create notification tier definitions:
   - calm/casual → gentle chime
   - pointed/urgent → pointed beep
   - pushing/firm → urgent siren
   - critical/alarm → looping alarm
2. [ ] Create `SoundPlayer` that plays appropriate sound under TTS
3. [ ] Add DND check: if DND active, silent notification for early anchors, visual+vibration for final 5 min
4. [ ] Add quiet hours suppression (configurable, default 10pm-7am)
5. [ ] Queue anchors if another chain is firing (never overlap)
6. [ ] Loop T-0 alarm until user dismisses or snoozes
7. [ ] Format notification: destination, "X minutes remaining", voice icon

**Acceptance Criteria (Spec Section 5.4):**
- [ ] Notification tier escalates with urgency
- [ ] System DND respected — early anchors silent, final 5 min visual+vibration
- [ ] Quiet hours suppress all nudges between configured times
- [ ] Anchors skipped due to DND/quiet hours queued, fired when restriction ends (if within 15 min)
- [ ] Anchors >15 min overdue silently dropped
- [ ] Chain overlap serialized — new anchors queue until current chain completes
- [ ] T-0 alarm loops until user dismisses or snoozes

**Test Cases (Spec Section 5.5):**
- [ ] TC-01: DND — early anchor suppressed
- [ ] TC-02: DND — final 5-minute override
- [ ] TC-03: Quiet hours suppression
- [ ] TC-04: Overdue anchor drop (15 min rule)
- [ ] TC-05: Chain overlap serialization
- [ ] TC-06: T-0 alarm loops until action

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration (Stub for Python Server)
**Files to create:** `src/lib/scheduling/__init__.py`, `src/lib/scheduling/notifee_client.py`, `src/lib/scheduling/recovery.py`

**Spec Reference:** Section 6 — Background Scheduling & Reliability

**Status:** Not implemented

**Note:** Since this is a Python test server (not React Native), stub the scheduling interface and implement the logic that would integrate with Notifee.

**Tasks:**
1. [ ] Create `SchedulingService` interface (mock-able)
2. [ ] Create `schedule_anchor(anchor_id, timestamp)` function
3. [ ] Create `cancel_anchor(anchor_id)` function
4. [ ] Create recovery scan: on launch, fire overdue unfired anchors within 15-min grace window
5. [ ] Drop anchors >15 minutes overdue and log `missed_reason = "background_task_killed"`
6. [ ] Re-register all pending anchors on app restart
7. [ ] Log warning if anchor fires >60 seconds after scheduled time

**Acceptance Criteria (Spec Section 6.4):**
- [ ] Reminder created with app in foreground schedules all anchors correctly
- [ ] Closing app does not prevent anchors from firing within 5 minutes
- [ ] After crash/force-kill, pending anchors re-registered on next launch
- [ ] Recovery scan fires only anchors within 15-minute grace window
- [ ] Missed anchors >15 min overdue dropped and logged
- [ ] Late firing (>60s) triggers warning log

**Test Cases (Spec Section 6.5):**
- [ ] TC-01: Anchor scheduling with Notifee
- [ ] TC-02: Background fire with app closed
- [ ] TC-03: Recovery scan on launch
- [ ] TC-04: Overdue anchor drop
- [ ] TC-05: Pending anchors re-registered on crash recovery
- [ ] TC-06: Late fire warning

---

## Priority 6: Calendar Integration

### 6.1 Calendar Adapters
**Files to create:** `src/lib/calendar/__init__.py`, `src/lib/calendar/adapter.py`, `src/lib/calendar/apple_calendar.py`, `src/lib/calendar/google_calendar.py`

**Spec Reference:** Section 7 — Calendar Integration

**Status:** Not implemented

**Tasks:**
1. [ ] Create `ICalendarAdapter` interface
2. [ ] Create `AppleCalendarAdapter` (stub for EventKit integration)
3. [ ] Create `GoogleCalendarAdapter` (stub for Google Calendar API)
4. [ ] Implement calendar sync on launch + every 15 minutes
5. [ ] Filter events with non-empty `location` field
6. [ ] Create suggestion card: "Parker Dr check-in — 9:00 AM — add departure reminder?"
7. [ ] Create reminder from suggestion with `calendar_event_id` set
8. [ ] Handle permission denial: show explanation banner with "Open Settings"
9. [ ] Handle sync failure gracefully (manual reminders still work)
10. [ ] Handle recurring events (generate reminder for each occurrence)

**Acceptance Criteria (Spec Section 7.4):**
- [ ] Apple Calendar events with locations appear as suggestion cards within 2 min
- [ ] Google Calendar events with locations appear as suggestion cards within 2 min
- [ ] Confirming calendar suggestion creates countdown_event reminder
- [ ] Calendar permission denial shows explanation banner
- [ ] Calendar sync failure does not prevent manual reminder creation
- [ ] Recurring daily event generates reminder for each occurrence

**Test Cases (Spec Section 7.5):**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

## Priority 7: Location Awareness

### 7.1 Location Check at Departure
**Files to create:** `src/lib/location/__init__.py`, `src/lib/location/location_service.py`, `src/lib/location/geofence.py`

**Spec Reference:** Section 8 — Location Awareness

**Status:** Not implemented

**Tasks:**
1. [ ] Create `LocationService` interface
2. [ ] Create `CoreLocationAdapter` (stub for iOS) / `FusedLocationAdapter` (Android)
3. [ ] Implement single location check at departure anchor (T-drive_duration)
4. [ ] Compare current location to origin using 500m geofence radius
5. [ ] If user within 500m of origin → fire firm/critical anchor immediately
6. [ ] If user >500m → proceed with normal chain
7. [ ] Request permission only at first location-aware reminder creation
8. [ ] If permission denied → create reminder without location awareness, show note
9. [ ] Do NOT store location history (single check only)

**Acceptance Criteria (Spec Section 8.4):**
- [ ] Departure anchor fires at scheduled time and performs one location check
- [ ] If user within 500m of origin, critical/urgent tier fires immediately
- [ ] If user >500m from origin, normal chain proceeds
- [ ] Location permission requested only when first creating location-aware reminder
- [ ] Denied permission results in reminder without location escalation
- [ ] No location history stored after comparison

**Test Cases (Spec Section 8.5):**
- [ ] TC-01: User still at origin at departure
- [ ] TC-02: User already left at departure
- [ ] TC-03: Location permission request
- [ ] TC-04: Location permission denied
- [ ] TC-05: Single location check only

---

## Priority 8: Snooze & Dismissal

### 8.1 Snooze + Dismissal Flow
**Files to create:** `src/lib/snooze/__init__.py`, `src/lib/snooze/manager.py`

**Spec Reference:** Section 9 — Snooze & Dismissal Flow

**Status:** Partial — basic anchor firing exists

**Gaps:**
- No tap snooze (1 min)
- No tap-and-hold snooze (1, 3, 5, 10, 15 min)
- No chain re-computation after snooze
- No swipe-to-dismiss feedback prompt
- No TTS confirmation after snooze
- No snooze persistence across app restarts

**Tasks:**
1. [ ] Implement tap snooze: pause current anchor, re-fire after 1 minute
2. [ ] Implement tap-and-hold snooze: show duration picker, selected duration applied
3. [ ] Implement chain re-computation: shift remaining unfired anchors to `now + original_time_remaining`
4. [ ] Re-register snoozed anchors with new timestamps
5. [ ] Implement swipe-to-dismiss: show feedback prompt "You missed [destination] — was timing right?"
6. [ ] Handle "Yes" (timing right) → store positive feedback
7. [ ] Handle "No" → show "What was wrong?" (Left too early / Left too late / Other)
8. [ ] Implement TTS confirmation: "Okay, snoozed [X] minutes."
9. [ ] Persist snooze state so app restart doesn't lose snooze offset

**Acceptance Criteria (Spec Section 9.4):**
- [ ] Tap snooze pauses current anchor and re-fires after 1 minute
- [ ] Custom snooze picker allows 1, 3, 5, 10, 15 minute selection
- [ ] Chain re-computation after snooze shifts remaining anchors by snooze duration
- [ ] Feedback prompt appears on swipe-dismiss with destination label
- [ ] "Left too late" feedback increases drive_duration for this destination by 2 min
- [ ] TTS confirms snooze: "Okay, snoozed [X] minutes"
- [ ] After custom snooze and app restart, remaining anchors fire at adjusted times

**Test Cases (Spec Section 9.5):**
- [ ] TC-01: Tap snooze
- [ ] TC-02: Custom snooze
- [ ] TC-03: Chain re-computation after snooze
- [ ] TC-04: Dismissal feedback — timing correct
- [ ] TC-05: Dismissal feedback — timing off (left too late)
- [ ] TC-06: Snooze persistence after restart

---

## Priority 9: History & Stats

### 9.1 Stats Calculations + Feedback Loop
**Files to create/modify:** `src/lib/stats/__init__.py`, `src/lib/stats/calculator.py`, `src/lib/stats/feedback_loop.py`

**Spec Reference:** Section 11 — History, Stats & Feedback Loop

**Status:** Partial — basic hit rate exists

**Gaps:**
- No common miss window calculation
- No streak counter for recurring reminders
- No feedback loop adjustment (cap at +15 min)
- No 90-day retention/archiving

**Tasks:**
1. [ ] Implement hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
2. [ ] Implement feedback loop adjustment: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_min)`, capped at +15 min
3. [ ] Implement common miss window: identify most frequently missed urgency tier
4. [ ] Implement streak counter: increment on 'hit' for recurring, reset to 0 on 'miss'
5. [ ] Implement 90-day retention: archive data older than 90 days (but keep accessible)
6. [ ] Verify all stats computable from history table (no separate stats store)

**Acceptance Criteria (Spec Section 11.4):**
- [ ] Weekly hit rate displays correctly: 4 hits and 1 miss = 80%
- [ ] After 3 "Left too late" events for "Parker Dr", next reminder adds 6 minutes
- [ ] Feedback loop caps at +15 minutes after 8+ late events
- [ ] "Common miss window" correctly identifies most frequently missed tier
- [ ] Streak increments on hit, resets on miss
- [ ] Stats computable from history table alone

**Test Cases (Spec Section 11.5):**
- [ ] TC-01: Hit rate calculation
- [ ] TC-02: Feedback loop — drive duration adjustment
- [ ] TC-03: Feedback loop cap
- [ ] TC-04: Common miss window identification
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table

---

## Priority 10: Sound Library

### 10.1 Sound Library System
**Files to create:** `src/lib/sounds/__init__.py`, `src/lib/sounds/library.py`, `src/lib/sounds/import_handler.py`

**Spec Reference:** Section 12 — Sound Library

**Status:** Not implemented

**Tasks:**
1. [ ] Create sound categories: Commute (5 sounds), Routine (5 sounds), Errand (5 sounds), Custom (imported)
2. [ ] Bundle 5 built-in sounds per category (placeholder audio files)
3. [ ] Implement custom audio import: MP3, WAV, M4A only, max 30 seconds
4. [ ] Transcode imported sounds to normalized format
5. [ ] Store custom sounds in app sandbox with reference in `custom_sounds` table
6. [ ] Implement per-reminder sound selection
7. [ ] Implement corrupted sound fallback: use category default, log error
8. [ ] Persist sound selection when reminder edited

**Acceptance Criteria (Spec Section 12.4):**
- [ ] Built-in sounds play without network access
- [ ] Custom MP3 import appears in sound picker
- [ ] Imported sound plays under TTS at anchor fire
- [ ] Corrupted custom sound fallback shows error, uses category default
- [ ] Sound selection persists when reminder edited

**Test Cases (Spec Section 12.5):**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Priority 11: Integration Tests

### 11.1 Full Test Suite
**Files to create:** `tests/__init__.py`, `tests/test_chain_engine.py`, `tests/test_parser.py`, `tests/test_tts.py`, `tests/test_integration.py`

**Spec Reference:** Section 14 — Definition of Done

**Status:** Not implemented

**Tasks:**
1. [ ] Unit tests for chain engine (all TC-01 through TC-06 from spec)
2. [ ] Unit tests for parser (all TC-01 through TC-07 from spec)
3. [ ] Unit tests for TTS adapter (all TC-01 through TC-05 from spec)
4. [ ] Unit tests for LLM adapter mock
5. [ ] Integration tests: parse → chain → TTS → persist flow
6. [ ] Integration tests: anchor schedule → fire → mark fired
7. [ ] Integration tests: snooze → recompute → re-register
8. [ ] Integration tests: dismiss → feedback → adjustment applied

**Verification:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All acceptance criteria have corresponding passing tests

---

## Implementation Order (Dependencies)

```
Priority 1: Foundation
├── 1.1 Database Schema + Migrations
├── 1.2 Test Harness Infrastructure
└── 1.3 Refactor Monolithic test_server.py
        ↓
Priority 2: Core Domain
├── 2.1 Chain Engine (complete)
└── 2.2 LLM Adapter + Parser (enhanced)
        ↓
Priority 3: Voice & TTS
├── 3.1 TTS Adapter + Cache
└── 3.2 Voice Personality Variations
        ↓
Priority 4-5: Notifications + Scheduling
├── 4.1 Notification Tier System
└── 5.1 Background Scheduling (Notifee stubs)
        ↓
Priority 6-7: Calendar + Location
├── 6.1 Calendar Adapters
└── 7.1 Location Check at Departure
        ↓
Priority 8: Snooze + Dismissal
└── 8.1 Snooze + Dismissal Flow
        ↓
Priority 9-10: Stats + Sounds
├── 9.1 History & Stats (enhanced)
└── 10.1 Sound Library
        ↓
Priority 11: Tests
└── 11.1 Full Test Suite
```

---

## Target File Structure

```
src/
├── test_server.py              # HTTP API server (existing, thin wrapper)
└── lib/
    ├── __init__.py
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py       # Database connection management
    │   └── migrations.py       # Migration runner
    ├── chain/
    │   ├── __init__.py
    │   └── engine.py           # Escalation chain computation
    ├── parser/
    │   ├── __init__.py
    │   ├── llm_adapter.py     # ILanguageModelAdapter interface
    │   ├── keyword_extractor.py # Fallback keyword parsing
    │   └── nl_parser.py       # Main parser service
    ├── tts/
    │   ├── __init__.py
    │   ├── adapter.py          # ITTSAdapter interface
    │   ├── elevenlabs.py       # ElevenLabs implementation
    │   ├── generator.py        # TTS generation orchestration
    │   └── cache_manager.py    # TTS file cache management
    ├── notifications/
    │   ├── __init__.py
    │   ├── tier_manager.py     # Notification tier logic
    │   └── sound_player.py     # Sound playback under TTS
    ├── scheduling/
    │   ├── __init__.py
    │   ├── notifee_client.py   # Notifee integration (stub)
    │   └── recovery.py         # Recovery scan logic
    ├── calendar/
    │   ├── __init__.py
    │   ├── adapter.py          # ICalendarAdapter interface
    │   ├── apple_calendar.py   # Apple Calendar (EventKit stub)
    │   └── google_calendar.py  # Google Calendar API stub
    ├── location/
    │   ├── __init__.py
    │   ├── location_service.py # Location check interface
    │   └── geofence.py         # 500m radius comparison
    ├── snooze/
    │   ├── __init__.py
    │   └── manager.py          # Snooze + dismissal handling
    ├── stats/
    │   ├── __init__.py
    │   ├── calculator.py       # Hit rate, streaks
    │   └── feedback_loop.py    # Destination adjustments
    └── sounds/
        ├── __init__.py
        ├── library.py          # Sound categories + built-in
        └── import_handler.py   # Custom audio import

harness/
├── scenario_harness.py          # Main test runner
└── fixtures/
    ├── __init__.py
    ├── mock_llm.py             # Mock LLM responses
    └── mock_tts.py             # Mock TTS generation

tests/
├── __init__.py
├── test_chain_engine.py
├── test_parser.py
├── test_tts.py
└── test_integration.py

scenarios/
├── README.md
├── chain-full-30min.yaml
├── chain-compressed-15min.yaml
├── chain-minimum-3min.yaml
├── chain-invalid-rejected.yaml
├── parse-natural-language.yaml
├── parse-simple-countdown.yaml
├── parse-tomorrow.yaml
├── voice-coach-personality.yaml
├── voice-no-nonsense.yaml
├── voice-all-personalities.yaml
├── history-record-outcome.yaml
├── history-record-miss-feedback.yaml
├── stats-hit-rate.yaml
├── reminder-creation-cascade-delete.yaml
└── reminder-creation-crud.yaml

specs/
├── urgent-voice-alarm-app-2026-04-08.md
└── urgent-voice-alarm-app-2026-04-08.spec.md
```

---

## Quick Wins (Can Be Done in Parallel with Foundation)

These tasks have minimal dependencies and can be started immediately:

1. **Expand voice personality templates to 3+ variations per tier** — Only touches `VOICE_PERSONALITIES` in test_server.py
2. **Improve keyword extractor regex patterns** — Only touches `parse_reminder_natural()`
3. **Add `get_next_unfired_anchor()` query** — Small addition to chain engine
4. **Implement basic chain re-computation for snooze** — Logic-only, no new interfaces
5. **Add hit rate calculation with trailing 7-day window** — Already partially exists

---

## Open Questions (From Spec)

These require product decisions before implementation:

1. **Speaker vs. Bluetooth**: Should nudges play through phone speaker or auto-connect to last-used Bluetooth audio? (Spec: "speaker-only in v1")
2. **Voice reply**: Can user respond to nudges ("snooze 5 min" spoken)? (Spec: "future consideration")
3. **Gentle mode**: Calm-only nudges for users who don't want aggression? (Spec: "Calm" personality covers this)
4. **Smart home integration**: Hue lights pulse red in final minute? (Spec: "out of scope for v1")
5. **Per-reminder personality override**: Can each reminder have a different personality? (Spec: "out of scope — same personality for all anchors in a reminder")

---

## Notes

- The Python test server is a **reference implementation** for scenario testing. The actual React Native/Flutter app would implement these systems natively.
- Priority 1 (Foundation) MUST be completed before any other work — all other components depend on the database schema.
- The 15 existing scenarios in `scenarios/` validate the current partial implementations. They should all pass once the corresponding systems are complete.
- All tests must pass before a task can be marked complete (per Otto loop rules).
