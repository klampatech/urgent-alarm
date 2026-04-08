# Implementation Plan — Urgent Voice Alarm App

## Overview

The current codebase contains a basic HTTP test server (`src/test_server.py`) with partial implementations of core systems. The specification defines 13 major systems. This plan identifies all gaps and prioritizes tasks by dependencies.

**Current State (as of 2026-04-08):**
| Component | Location | Status |
|-----------|----------|--------|
| HTTP Test Server | `src/test_server.py` | ~650 lines, functional basic endpoints |
| Chain Engine | `src/test_server.py` (lines 101-180) | Partial - basic computation, some edge cases not handled |
| Keyword Parser | `src/test_server.py` (lines 183-270) | Partial - regex extraction, limited patterns |
| Voice Templates | `src/test_server.py` (lines 273-380) | Partial - 1 variation per tier per personality |
| Stats Calculator | `src/test_server.py` (lines 383-400) | Partial - basic hit rate |
| DB Schema | `src/test_server.py` (lines 19-97) | Partial - basic tables, missing columns |
| Test Harness | `harness/` | **EMPTY** - infrastructure not created yet |
| Lib Modules | `src/lib/` | **EMPTY** - no module structure |
| Scenarios | `scenarios/` | 15 YAML files ready (chain, parse, voice, history, stats) |
| Tests | `tests/` | Does not exist |

---

## Priority 1: Foundation (Critical — All Other Work Depends On These)

### 1.1 Complete Database Schema Migration System
**Files to create:** `src/lib/db/__init__.py`, `src/lib/db/connection.py`, `src/lib/db/migrations.py`

**Spec Reference:** Section 13 — Data Persistence

**Status:** ⚠️ Partial — basic tables exist, missing complete schema, migrations, and FK enforcement

**Gaps in Current Code:**
- Missing `calendar_sync` table
- Missing `custom_sounds` table
- Missing columns on `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`
- Missing columns on `anchors`: `tts_fallback`, `snoozed_to`
- Missing columns on `history`: `actual_arrival`, `missed_reason`
- No migration versioning system
- No WAL mode, no FK enforcement

**Tasks:**
- [ ] Create `schema_version` tracking table
- [ ] Create migration runner with sequential versioned migrations (v1, v2, etc.)
- [ ] Create all spec-compliant tables in migration order
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] Ensure cascade deletes work correctly (`ON DELETE CASCADE`)
- [ ] Create `DatabaseConnection` class with `getInMemoryInstance()` for tests
- [ ] All timestamps stored in ISO 8601 format (UTC internally)
- [ ] Generate UUID v4 for all primary keys

**Verification:**
- [ ] Fresh install applies all migrations in order
- [ ] In-memory test database starts empty with all migrations applied
- [ ] `reminders.id` is always a valid UUID v4
- [ ] Deleting a reminder cascades to delete its anchors

---

### 1.2 Test Harness Infrastructure
**Files to create:** `harness/scenario_harness.py`, `harness/fixtures/`

**Spec Reference:** Section 14 — Definition of Done

**Status:** ❌ **CRITICAL GAP** — harness directory is empty, this blocks all validation

**Gaps:**
- No scenario runner exists (scenario_harness.py does not exist)
- No test database setup
- No mock fixtures for LLM/TTS
- No assertion validators (http_status, db_record, llm_judge)
- 15 scenarios in `scenarios/` cannot be executed

**Tasks:**
- [ ] Create `ScenarioHarness` class that loads YAML scenarios from `scenarios/` directory
- [ ] Implement scenario step executor (HTTP API calls to test_server.py)
- [ ] Implement assertion validators:
  - `http_status` - validate HTTP status codes
  - `db_record` - validate database records exist with conditions
  - `llm_judge` - call LLM to evaluate output quality
- [ ] Create `MockLanguageModelAdapter` for test fixtures
- [ ] Create `MockTTSAdapter` for test fixtures (writes silent audio file)
- [ ] Create `getInMemoryDatabase()` helper that resets between scenarios
- [ ] Write result to `/tmp/ralph-scenario-result.json` after run
- [ ] Support running single scenario or all scenarios
- [ ] Report pass/fail per assertion and overall scenario

**Verification:**
- [ ] `python3 -m pytest harness/` runs successfully (when tests exist)
- [ ] `python3 -m py_compile harness/scenario_harness.py src/test_server.py` passes
- [ ] All 15 scenarios in `scenarios/` execute without error

---

### 1.3 Refactor Monolithic test_server.py
**Files to create:** `src/lib/__init__.py`, `src/lib/*/` modules

**Status:** ⚠️ All code in single 650-line `test_server.py` — needs modularization

**Tasks:**
- [ ] Create `src/lib/__init__.py`
- [ ] Create `src/lib/chain/__init__.py`, `src/lib/chain/engine.py`
- [ ] Create `src/lib/parser/__init__.py`, `src/lib/parser/nl_parser.py`, `src/lib/parser/keyword_extractor.py`
- [ ] Create `src/lib/voice/__init__.py`, `src/lib/voice/personalities.py`
- [ ] Create `src/lib/stats/__init__.py`, `src/lib/stats/calculator.py`
- [ ] Create `src/lib/db/__init__.py`, `src/lib/db/connection.py`, `src/lib/db/migrations.py`
- [ ] Refactor `test_server.py` to import from `src/lib/` — keep as thin HTTP wrapper
- [ ] Ensure backward compatibility with existing API endpoints

**Verification:**
- [ ] `python3 -m py_compile src/lib/**/*.py` passes for all modules
- [ ] `python3 -m py_compile src/test_server.py` passes
- [ ] Server starts and serves existing endpoints after refactoring

---

## Priority 2: Core Domain Logic

### 2.1 Chain Engine Completeness
**File to create/modify:** `src/lib/chain/engine.py`

**Spec Reference:** Section 2 — Escalation Chain Engine

**Status:** ⚠️ Partial — basic anchor computation exists (lines 101-165)

**Gaps:**
- No `get_next_unfired_anchor()` function
- No TTS clip path tracking per anchor
- No fire_count increment on retry
- Chain not deterministic (depends on runtime clock in tests)
- No validation that `arrival_time > departure + minimum_drive_time`

**Tasks:**
- [ ] Implement `compute_escalation_chain(arrival_time, drive_duration)` — deterministic, pure function
- [ ] Implement `get_next_unfired_anchor(reminder_id)` query
- [ ] Add `tts_clip_path`, `tts_fallback`, `fire_count`, `snoozed_to` to anchor storage
- [ ] Add chain validation: reject if `drive_duration > time_to_arrival`
- [ ] Handle compressed chains per spec:
  - ≥25 min buffer: 8 anchors (full chain)
  - 20-24 min: 7 anchors (skip calm)
  - 10-19 min: 5 anchors (start at urgent)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - ≤5 min: 2 anchors (firm/alarm based on duration)
- [ ] Make chain computation pure (accept `now` as parameter for determinism)

**Acceptance Criteria (Spec Section 2.4):**
- [ ] Chain for "30 min drive, arrive 9am" produces 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "10 min drive, arrive 9am" produces 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "3 min drive, arrive 9am" produces 3 anchors: 8:57, 8:59, 9:00
- [ ] Chain with `drive_duration > arrival_time` is rejected with validation error
- [ ] `get_next_unfired_anchor` correctly returns the earliest unfired anchor after restart
- [ ] Anchors are sorted by timestamp ascending in database

**Test Scenarios:**
- [ ] TC-01: Full chain generation (≥25 min buffer)
- [ ] TC-02: Compressed chain (10-24 min buffer)
- [ ] TC-03: Minimum chain (≤5 min buffer)
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism

---

### 2.2 LLM Adapter + Parser Enhancement
**Files to create:** `src/lib/parser/`, split and enhance from `test_server.py` lines 167-250

**Spec Reference:** Section 3 — Reminder Parsing & Creation

**Status:** ⚠️ Partial — basic keyword extraction exists, brittle regex

**Gaps:**
- No `ILanguageModelAdapter` interface
- No MiniMax or Anthropic API implementation
- No mock adapter for testing
- Keyword extraction doesn't handle all spec formats
- No confidence scoring
- No user confirmation flow

**Tasks:**
- [ ] Create `ILanguageModelAdapter` abstract interface
- [ ] Create `MiniMaxAdapter` implementation (Anthropic-compatible endpoint)
- [ ] Create `AnthropicAdapter` implementation
- [ ] Create `MockLanguageModelAdapter` for tests with fixture responses
- [ ] Improve keyword extractor to handle all formats:
  - "X min drive" / "X-minute drive"
  - "in X minutes"
  - "arrive at X" / "check-in at X"
  - "Parker Dr 9am, 30 min drive"
- [ ] Implement confidence scoring and LLM fallback to keyword extraction
- [ ] Implement `parse_and_confirm()` returning parsed fields for UI review
- [ ] Handle "tomorrow" date resolution correctly
- [ ] Handle relative time ("in 3 minutes") vs absolute time ("at 9am")

**Acceptance Criteria (Spec Section 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] "dryer in 3 min" parses as simple_countdown
- [ ] "meeting tomorrow 2pm, 20 min drive" parses with correct date
- [ ] On API failure, keyword extraction produces best-effort parsed object
- [ ] User can edit any parsed field and confirm
- [ ] Empty/unintelligible input returns user-facing error

**Test Scenarios:**
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
**Files to create:** `src/lib/tts/`

**Spec Reference:** Section 4 — Voice & TTS Generation

**Status:** ❌ Not implemented — only message templates exist

**Gaps:**
- No ElevenLabs adapter
- No `ITTSAdapter` interface
- No TTS clip generation
- No `/tts_cache/` directory management
- No cache invalidation on reminder delete
- No fallback when API unavailable

**Tasks:**
- [ ] Create `ITTSAdapter` abstract interface
- [ ] Create `ElevenLabsAdapter` implementation with voice ID mapping
- [ ] Create `MockTTSAdapter` for tests (writes 1-second silent file)
- [ ] Create cache manager with `/tts_cache/{reminder_id}/` structure
- [ ] Implement `generate_tts_for_anchors(reminder_id, anchors, personality)` pre-generation
- [ ] Implement fallback: if TTS fails, mark `tts_fallback = true`, use notification text
- [ ] Implement cache invalidation when reminder deleted
- [ ] TTS generation completes within 30 seconds (ElevenLabs async with polling)

**Acceptance Criteria (Spec Section 4.4):**
- [ ] New reminder generates MP3 clips stored in `/tts_cache/{reminder_id}/`
- [ ] Playing anchor fires correct pre-generated clip from local cache
- [ ] When ElevenLabs API unavailable, fallback to system sound
- [ ] Reminder deletion removes all cached TTS files
- [ ] TTS generation uses correct voice ID for personality

**Test Scenarios:**
- [ ] TC-01: TTS clip generation at creation
- [ ] TC-02: Anchor fires from cache
- [ ] TC-03: TTS fallback on API failure
- [ ] TC-04: TTS cache cleanup on delete
- [ ] TC-05: Mock TTS in tests

---

### 3.2 Voice Personality Message Variations
**Files to modify:** `src/lib/voice/personalities.py` (expand from current `VOICE_PERSONALITIES`)

**Spec Reference:** Section 10 — Voice Personality System

**Status:** ⚠️ Partial — single template per tier, needs 3+ variations

**Gaps:**
- Only 1 message variation per tier (spec requires minimum 3)
- No custom prompt mode

**Tasks:**
- [ ] Expand each personality (Coach, Assistant, Best Friend, No-nonsense, Calm) to 3+ templates per urgency tier
- [ ] Add random selection (or round-robin) for variation across generations
- [ ] Implement custom prompt mode: user writes prompt (max 200 chars) appended to system prompt
- [ ] Ensure existing reminders retain their personality at creation time

**Acceptance Criteria (Spec Section 10.4):**
- [ ] "Coach" personality at T-5 produces motivating message with exclamation
- [ ] "No-nonsense" personality at T-5 produces brief, direct message
- [ ] "Assistant" personality at T-5 produces calm, clear message
- [ ] Custom prompt modifies message tone appropriately
- [ ] Changing default personality does not affect existing reminders
- [ ] Each personality generates at least 3 message variations per urgency tier

**Test Scenarios:**
- [ ] TC-01: Coach personality messages
- [ ] TC-02: No-nonsense personality messages
- [ ] TC-03: Custom personality
- [ ] TC-04: Personality immutability for existing reminders
- [ ] TC-05: Message variation

---

## Priority 4: Notification & Alarm Behavior

### 4.1 Notification Tier System
**Files to create:** `src/lib/notifications/`

**Spec Reference:** Section 5 — Notification & Alarm Behavior

**Status:** ❌ Not implemented

**Tasks:**
- [ ] Create notification tier definitions:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm
- [ ] Create `SoundPlayer` that plays appropriate sound under TTS
- [ ] Add DND check: if DND active, silent notification for early anchors, visual+vibration for final 5 min
- [ ] Add quiet hours suppression (configurable, default 10pm-7am)
- [ ] Queue anchors if another chain is firing (never overlap)
- [ ] Loop T-0 alarm until user dismisses or snoozes
- [ ] Format notification: destination, "X minutes remaining", voice icon

**Acceptance Criteria (Spec Section 5.4):**
- [ ] Notification tier escalates with urgency
- [ ] System DND respected — early anchors silent, final 5 min visual+vibration
- [ ] Quiet hours suppress nudges between configured times
- [ ] Anchors skipped due to DND/quiet hours queued, fired when restriction ends (if within 15 min)
- [ ] Anchors >15 min overdue silently dropped
- [ ] Chain overlap serialized — new anchors queue until current chain completes
- [ ] T-0 alarm loops until user dismisses or snoozes

**Test Scenarios:**
- [ ] TC-01: DND — early anchor suppressed
- [ ] TC-02: DND — final 5-minute override
- [ ] TC-03: Quiet hours suppression
- [ ] TC-04: Overdue anchor drop (15 min rule)
- [ ] TC-05: Chain overlap serialization
- [ ] TC-06: T-0 alarm loops until action

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration (Stub for Python Server)
**Files to create:** `src/lib/scheduling/`

**Spec Reference:** Section 6 — Background Scheduling & Reliability

**Status:** ❌ Not implemented

**Note:** Python test server stubs the React Native Notifee integration.

**Tasks:**
- [ ] Create `SchedulingService` interface (mock-able)
- [ ] Create `schedule_anchor(anchor_id, timestamp)` function
- [ ] Create `cancel_anchor(anchor_id)` function
- [ ] Create recovery scan: on launch, fire overdue unfired anchors within 15-min grace window
- [ ] Drop anchors >15 minutes overdue and log `missed_reason = "background_task_killed"`
- [ ] Re-register all pending anchors on app restart
- [ ] Log warning if anchor fires >60 seconds after scheduled time

**Acceptance Criteria (Spec Section 6.4):**
- [ ] Reminder created with app in foreground schedules all anchors correctly
- [ ] Closing app does not prevent anchors from firing within 5 minutes
- [ ] After crash/force-kill, pending anchors re-registered on next launch
- [ ] Recovery scan fires only anchors within 15-minute grace window
- [ ] Missed anchors >15 min overdue dropped and logged
- [ ] Late firing (>60s) triggers warning log

**Test Scenarios:**
- [ ] TC-01: Anchor scheduling with Notifee
- [ ] TC-02: Background fire with app closed
- [ ] TC-03: Recovery scan on launch
- [ ] TC-04: Overdue anchor drop
- [ ] TC-05: Pending anchors re-registered on crash recovery
- [ ] TC-06: Late fire warning

---

## Priority 6: Calendar Integration

### 6.1 Calendar Adapters
**Files to create:** `src/lib/calendar/`

**Spec Reference:** Section 7 — Calendar Integration

**Status:** ❌ Not implemented

**Tasks:**
- [ ] Create `ICalendarAdapter` interface
- [ ] Create `AppleCalendarAdapter` (stub for EventKit integration)
- [ ] Create `GoogleCalendarAdapter` (stub for Google Calendar API)
- [ ] Implement calendar sync on launch + every 15 minutes
- [ ] Filter events with non-empty `location` field
- [ ] Create suggestion card: "Parker Dr check-in — 9:00 AM — add departure reminder?"
- [ ] Create reminder from suggestion with `calendar_event_id` set
- [ ] Handle permission denial: show explanation banner with "Open Settings"
- [ ] Handle recurring events (generate reminder for each occurrence)

**Acceptance Criteria (Spec Section 7.4):**
- [ ] Apple Calendar events with locations appear as suggestion cards within 2 min
- [ ] Google Calendar events with locations appear as suggestion cards within 2 min
- [ ] Confirming calendar suggestion creates countdown_event reminder
- [ ] Calendar permission denial shows explanation banner
- [ ] Calendar sync failure does not prevent manual reminder creation
- [ ] Recurring daily event generates reminder for each occurrence

**Test Scenarios:**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

## Priority 7: Location Awareness

### 7.1 Location Check at Departure
**Files to create:** `src/lib/location/`

**Spec Reference:** Section 8 — Location Awareness

**Status:** ❌ Not implemented

**Tasks:**
- [ ] Create `LocationService` interface
- [ ] Create location adapter stubs for iOS/Android
- [ ] Implement single location check at departure anchor (T-drive_duration)
- [ ] Compare current location to origin using 500m geofence radius
- [ ] If user within 500m of origin → fire firm/critical anchor immediately
- [ ] If user >500m → proceed with normal chain
- [ ] Request permission only at first location-aware reminder creation
- [ ] If permission denied → create reminder without location awareness, show note
- [ ] Do NOT store location history (single check only)

**Acceptance Criteria (Spec Section 8.4):**
- [ ] Departure anchor fires at scheduled time and performs one location check
- [ ] If user within 500m of origin, critical/urgent tier fires immediately
- [ ] If user >500m from origin, normal chain proceeds
- [ ] Location permission requested only when first creating location-aware reminder
- [ ] Denied permission results in reminder without location escalation
- [ ] No location history stored after comparison

**Test Scenarios:**
- [ ] TC-01: User still at origin at departure
- [ ] TC-02: User already left at departure
- [ ] TC-03: Location permission request
- [ ] TC-04: Location permission denied
- [ ] TC-05: Single location check only

---

## Priority 8: Snooze & Dismissal

### 8.1 Snooze + Dismissal Flow
**Files to create:** `src/lib/snooze/`

**Spec Reference:** Section 9 — Snooze & Dismissal Flow

**Status:** ⚠️ Partial — basic anchor firing exists, no snooze/dismissal

**Tasks:**
- [ ] Implement tap snooze: pause current anchor, re-fire after 1 minute
- [ ] Implement tap-and-hold snooze: show duration picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation: shift remaining unfired anchors
- [ ] Re-register snoozed anchors with new timestamps
- [ ] Implement swipe-to-dismiss: show feedback prompt
- [ ] Handle "Yes" (timing right) → store positive feedback
- [ ] Handle "No" → show "What was wrong?" (Left too early / Left too late / Other)
- [ ] Implement TTS confirmation: "Okay, snoozed [X] minutes."
- [ ] Persist snooze state so app restart doesn't lose snooze offset

**Acceptance Criteria (Spec Section 9.4):**
- [ ] Tap snooze pauses current anchor and re-fires after 1 minute
- [ ] Custom snooze picker allows 1, 3, 5, 10, 15 minute selection
- [ ] Chain re-computation after snooze shifts remaining anchors by snooze duration
- [ ] Feedback prompt appears on swipe-dismiss with destination label
- [ ] "Left too late" feedback increases drive_duration by 2 min
- [ ] TTS confirms snooze: "Okay, snoozed [X] minutes"
- [ ] After custom snooze and app restart, remaining anchors fire at adjusted times

**Test Scenarios:**
- [ ] TC-01: Tap snooze
- [ ] TC-02: Custom snooze
- [ ] TC-03: Chain re-computation after snooze
- [ ] TC-04: Dismissal feedback — timing correct
- [ ] TC-05: Dismissal feedback — timing off (left too late)
- [ ] TC-06: Snooze persistence after restart

---

## Priority 9: History & Stats

### 9.1 Stats Calculations + Feedback Loop
**Files to create/modify:** `src/lib/stats/`

**Spec Reference:** Section 11 — History, Stats & Feedback Loop

**Status:** ⚠️ Partial — basic hit rate exists (lines 352-370), missing features

**Gaps:**
- No common miss window calculation
- No streak counter for recurring reminders
- No feedback loop adjustment (cap at +15 min)
- No 90-day retention/archiving

**Tasks:**
- [ ] Implement hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
- [ ] Implement feedback loop adjustment: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_min)`, capped at +15 min
- [ ] Implement common miss window: identify most frequently missed urgency tier
- [ ] Implement streak counter: increment on 'hit' for recurring, reset to 0 on 'miss'
- [ ] Implement 90-day retention: archive data older than 90 days

**Acceptance Criteria (Spec Section 11.4):**
- [ ] Weekly hit rate displays correctly: 4 hits and 1 miss = 80%
- [ ] After 3 "Left too late" events for "Parker Dr", next reminder adds 6 minutes
- [ ] Feedback loop caps at +15 minutes after 8+ late events
- [ ] "Common miss window" correctly identifies most frequently missed tier
- [ ] Streak increments on hit, resets on miss
- [ ] Stats computable from history table alone

**Test Scenarios:**
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
**Files to create:** `src/lib/sounds/`

**Spec Reference:** Section 12 — Sound Library

**Status:** ❌ Not implemented

**Tasks:**
- [ ] Create sound categories: Commute (5 sounds), Routine (5 sounds), Errand (5 sounds), Custom (imported)
- [ ] Bundle 5 built-in sounds per category (placeholder audio files)
- [ ] Implement custom audio import: MP3, WAV, M4A only, max 30 seconds
- [ ] Transcode imported sounds to normalized format
- [ ] Store custom sounds in app sandbox with reference in `custom_sounds` table
- [ ] Implement per-reminder sound selection
- [ ] Implement corrupted sound fallback: use category default, log error
- [ ] Persist sound selection when reminder edited

**Acceptance Criteria (Spec Section 12.4):**
- [ ] Built-in sounds play without network access
- [ ] Custom MP3 import appears in sound picker
- [ ] Imported sound plays under TTS at anchor fire
- [ ] Corrupted custom sound fallback shows error, uses category default
- [ ] Sound selection persists when reminder edited

**Test Scenarios:**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## 🚨 Critical Path (Start Here)

**Before any other work, Priority 1 MUST be completed.**

```
IMMEDIATE (Day 1):
├── 1.2 Test Harness Infrastructure ← BLOCKING ALL VALIDATION
│   └── 15 scenarios in scenarios/ cannot be executed
└── 1.1 Database Schema + Migrations
    └── All other features depend on correct DB schema
        ↓
DAY 2:
└── 1.3 Refactor test_server.py → move logic to src/lib/
        ↓
DAY 3+:
├── 2.1 Chain Engine (complete)
├── 2.2 LLM Adapter + Parser
└── Continue with remaining priorities...
```

**Why 1.2 is blocking:** The `harness/` directory is empty. Without `scenario_harness.py`, there is NO WAY to run the 15 validation scenarios in `scenarios/`. This means you cannot verify ANY implementation.

---

## Implementation Order (Dependencies)

```
Priority 1: Foundation
├── 1.2 Test Harness Infrastructure ← DO FIRST (blocking)
├── 1.1 Database Schema + Migrations
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
    │   ├── llm_adapter.py      # ILanguageModelAdapter interface
    │   ├── keyword_extractor.py # Fallback keyword parsing
    │   └── nl_parser.py        # Main parser service
    ├── tts/
    │   ├── __init__.py
    │   ├── adapter.py          # ITTSAdapter interface
    │   ├── elevenlabs.py       # ElevenLabs implementation
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
├── README.md                   # Scenario documentation
├── chain-full-30min.yaml       # TC-01: Full 8-anchor chain
├── chain-compressed-15min.yaml # TC-02: Compressed chain
├── chain-minimum-3min.yaml     # TC-03: Minimum chain
├── chain-invalid-rejected.yaml # TC-04: Invalid chain rejection
├── parse-natural-language.yaml # TC-01: Full NL parse
├── parse-simple-countdown.yaml # TC-02: Simple countdown parse
├── parse-tomorrow.yaml        # TC-03: Tomorrow date resolution
├── voice-coach-personality.yaml # TC-01: Coach voice generation
├── voice-no-nonsense.yaml      # TC-02: No-nonsense voice generation
├── voice-all-personalities.yaml # All 5 personalities
├── history-record-outcome.yaml # Record outcome
├── history-record-miss-feedback.yaml # TC-05: Record miss with feedback
├── stats-hit-rate.yaml         # TC-01: Hit rate calculation
├── reminder-creation-cascade-delete.yaml # TC-03: Cascade delete anchors
└── reminder-creation-crud.yaml # Full CRUD workflow

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

## Status Summary

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| 1.1 | Database Schema + Migrations | ⚠️ Partial | Basic tables exist, missing columns/constraints |
| **1.2** | **Test Harness Infrastructure** | ❌ **BLOCKING** | **Must be created first - 15 scenarios cannot run** |
| 1.3 | Refactor Monolithic test_server.py | ⚠️ In single file | All logic in 650-line file |
| 2.1 | Chain Engine Completeness | ⚠️ Partial | Missing edge cases and helper functions |
| 2.2 | LLM Adapter + Parser Enhancement | ⚠️ Partial | Basic regex, needs LLM integration |
| 3.1 | TTS Adapter + Cache | ❌ Not implemented | Message templates only, no audio |
| 3.2 | Voice Personality Variations | ⚠️ 1 variation | Needs 3+ per tier per spec |
| 4.1 | Notification Tier System | ❌ Not implemented | No sound tiers, DND, quiet hours |
| 5.1 | Background Scheduling | ❌ Not implemented | No Notifee integration |
| 6.1 | Calendar Adapters | ❌ Not implemented | No EventKit/Google Calendar |
| 7.1 | Location Check at Departure | ❌ Not implemented | No location services |
| 8.1 | Snooze + Dismissal Flow | ❌ Not implemented | No snooze/dismiss handlers |
| 9.1 | History & Stats | ⚠️ Partial | Basic hit rate, missing feedback loop |
| 10.1 | Sound Library | ❌ Not implemented | No sound categories or import |

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
