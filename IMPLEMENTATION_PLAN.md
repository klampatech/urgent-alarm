# Implementation Plan — Urgent Voice Alarm App

## Overview

The current codebase contains a basic HTTP test server (`src/test_server.py`) with partial implementations of core systems. The specification defines 13 major systems. **Critical bugs found in chain engine** that must be fixed before proceeding.

**Gap Analysis Date:** 2026-04-08 (Re-verified)

**Analyzed By:** pi-coding-agent

**Chain Engine Bugs Verified:** ✅ Confirmed via live test

| Buffer | Expected | Actual | Status |
|--------|----------|--------|--------|
| 30 min | 8 anchors, T-30...T-0 | 8 anchors ✓ | ✅ Working |
| 10 min | 4 anchors: T-10, T-5, T-1, T-0 | urgent@08:55 (should be T-10=08:50), pushing@09:00 (should be T-5=08:55) | ❌ BROKEN |
| 3 min | 3 anchors: T-2, T-1, T-0 | 2 anchors only (missing critical) | ❌ BROKEN |
| 6 min | 3 anchors, no duplicates | DUPLICATE T-5 timestamps (firm@08:55, critical@08:55) | ❌ BROKEN |

---

## Executive Summary

After thorough analysis of `specs/*.md` vs `src/*`:

| Category | Status | Gap Count |
|----------|--------|-----------|
| Core Logic | ⚠️ Partial | 1 critical bug, 2 incomplete |
| Adapters (LLM/TTS) | ❌ Missing | 2 not implemented |
| Infrastructure | ⚠️ Partial | 1 incomplete, 1 missing |
| Mobile Features | ❌ Missing | 5 not implemented |
| Test Infrastructure | ❌ Missing | 1 blocking item |

**Critical Path:** Chain engine bugs → Test harness → Database schema → Remaining features

---

## Current State (as of 2026-04-08):
| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| HTTP Test Server | `src/test_server.py` | ~627 lines, 11 functions | Partial - has bugs |
| Chain Engine | `src/test_server.py` lines 101-180 | ⚠️ **BUGGY** | Wrong anchor timestamps, duplicate times |
| Keyword Parser | `src/test_server.py` lines 183-270 | ⚠️ Partial | Limited regex, missing edge cases |
| Voice Templates | `src/test_server.py` lines 273-380 | ⚠️ Partial | 1 variation per tier, needs 3+ |
| Stats Calculator | `src/test_server.py` lines 383-400 | ⚠️ Partial | Basic hit rate only |
| DB Schema | `src/test_server.py` lines 19-97 | ⚠️ Partial | Missing columns, no FK enforcement |
| Test Harness | `harness/` | ❌ **EMPTY** | BLOCKS all validation |
| Lib Modules | `src/lib/` | ❌ **EMPTY** | No module structure |
| Scenarios | `scenarios/` | 15 YAML files | Ready but cannot run |
| Tests | `tests/` | ❌ **MISSING** | None exist |

---

## ⚠️ CRITICAL BUGS FOUND (Must Fix First)

### Bug 1: Chain Engine Produces Wrong Timestamps

**Severity:** Critical - Breaks core functionality

**Issue:** The chain engine computes anchor timestamps incorrectly, producing duplicate times and wrong urgency tiers.

**Examples (live test output):**
```python
# 10-min buffer - WRONG output:
urgent: 2026-04-09T08:55:00  (should be 08:50:00 - T-10)
pushing: 2026-04-09T09:00:00  (WRONG - arrival is T-0!)
critical: 2026-04-09T08:59:00
alarm: 2026-04-09T09:00:00    (duplicate timestamp with pushing!)

# 3-min buffer - WRONG output (2 anchors):
firm: 2026-04-09T08:58:00, alarm: 2026-04-09T09:00:00
# MISSING critical anchor at 08:59:00

# 6-min buffer - WRONG output (duplicate timestamp):
firm: 2026-04-09T08:55:00, critical: 2026-04-09T08:55:00  (DUPLICATE!)
```

**Spec says (Section 2.4):**
- 30-min buffer → 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00 ✅ (works)
- 10-min buffer → 4 anchors: 8:50, 8:55, 8:59, 9:00 ❌ (broken)
- 3-min buffer → 3 anchors: 8:57, 8:59, 9:00 ❌ (missing critical)

**Root Cause:** The anchor generation logic uses `drive_duration - X` but doesn't correctly handle compressed chains.

**Fix Required:** Rewrite `compute_escalation_chain()` with correct anchor selection logic per spec Section 2.3.

---

## Priority 1: Foundation (Critical — All Other Work Depends On These)

### 1.1 Fix Chain Engine Bugs
**File to modify:** `src/test_server.py` (lines 101-180)

**Spec Reference:** Section 2 — Escalation Chain Engine

**Status:** ❌ **CRITICAL BUGS** - Wrong timestamps, missing anchors, duplicate timestamps

**Current bugs:**
- `drive_duration - X` formula produces wrong timestamps for compressed chains
- Missing critical anchor for buffers ≤ 5 min
- Duplicate timestamps for buffers 5-9 min
- Violates `UNIQUE(reminder_id, timestamp)` DB constraint

**Required fixes (per spec Section 2.3):**
| Buffer Size | Anchors | Tiers | Example (30 min) |
|-------------|---------|-------|------------------|
| ≥25 min | 8 | calm, casual, pointed, urgent, pushing, firm, critical, alarm | Full chain |
| 20-24 min | 7 | casual, pointed, urgent, pushing, firm, critical, alarm | Skip calm |
| 10-19 min | 5 | urgent, pushing, firm, critical, alarm | Start at urgent |
| 5-9 min | 3 | firm, critical, alarm | Minimum compressed |
| 1-4 min | 3 | firm, critical, alarm | Very short |
| 0 min | 1 | alarm | Immediate |

**Tasks:**
- [ ] Rewrite anchor selection logic using absolute minutes_before thresholds, not relative
- [ ] Ensure no duplicate timestamps (critical for DB UNIQUE constraint)
- [ ] Ensure minimum chain (≤5 min) produces 3 anchors: T-(buffer-1), T-1, T-0
- [ ] Validate chain for 10-min buffer produces correct timestamps: T-10, T-5, T-1, T-0
- [ ] Add unit tests verifying all buffer sizes produce correct anchor counts and timestamps
- [ ] Ensure chain is deterministic (same inputs = same outputs)

**Verification:**
- [ ] `compute_escalation_chain(datetime(9am), 30)` produces 8 anchors with correct times
- [ ] `compute_escalation_chain(datetime(9am), 10)` produces 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] `compute_escalation_chain(datetime(9am), 3)` produces 3 anchors: 8:57, 8:59, 9:00
- [ ] No duplicate timestamps in any chain
- [ ] All anchors sorted by timestamp ascending

---

### 1.2 Complete Database Schema Migration System
**Files to create:** `src/lib/db/__init__.py`, `src/lib/db/connection.py`, `src/lib/db/migrations.py`

**Spec Reference:** Section 13 — Data Persistence

**Status:** ⚠️ Partial — basic tables exist, missing complete schema and FK enforcement

**Gaps in Current Code:**
- Missing `calendar_sync` table
- Missing `custom_sounds` table
- Missing columns on `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`, `tts_cache_dir`
- Missing columns on `anchors`: `tts_fallback`, `snoozed_to`
- Missing columns on `history`: `actual_arrival`, `missed_reason`
- No migration versioning system
- No WAL mode, no FK enforcement
- `reminders.drive_duration` stored as INTEGER but should track original vs adjusted duration separately

**Tasks:**
- [ ] Create `schema_version` tracking table
- [ ] Create migration runner with sequential versioned migrations (v1, v2, etc.)
- [ ] Create all spec-compliant tables in migration order
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] Ensure cascade deletes work correctly (`ON DELETE CASCADE`)
- [ ] Create `DatabaseConnection` class with `getInMemoryInstance()` for tests
- [ ] All timestamps stored in ISO 8601 format (UTC internally, displayed in local time)
- [ ] Generate UUID v4 for all primary keys
- [ ] Add `destination_adjustments` table for feedback loop

**Verification:**
- [ ] Fresh install applies all migrations in order, schema is current
- [ ] In-memory test database starts empty with all migrations applied
- [ ] `reminders.id` is always a valid UUID v4
- [ ] Deleting a reminder cascades to delete its anchors
- [ ] Foreign key violation returns error without crashing

---

### 1.3 Test Harness Infrastructure (BLOCKING)
**Files to create:** `harness/scenario_harness.py`, `harness/__init__.py`

**Spec Reference:** Section 14 — Definition of Done

**Status:** ❌ **CRITICAL GAP** — harness directory is empty, blocks ALL validation

**Gaps:**
- No scenario runner exists (`scenario_harness.py` does not exist)
- No test database setup
- No mock fixtures for LLM/TTS
- No assertion validators (http_status, db_record, llm_judge)
- 15 scenarios in `scenarios/` cannot be executed
- **Otto loop requirement:** Must write `{"pass": true/false}` to `/tmp/ralph-scenario-result.json`

**Required by Otto Loop:**
- Harness runs after each `git push` via: `sudo python3 harness/scenario_harness.py --project $(basename "$(git rev-parse --show-toplevel)")"`
- Harness must read scenarios from `/var/otto-scenarios/[project]/`
- Harness must write results to `/tmp/ralph-scenario-result.json`
- Scenario directory has `chmod 700` permissions (root only access)

**Tasks:**
- [ ] Create `ScenarioHarness` class that loads YAML scenarios
- [ ] Implement scenario step executor (HTTP API calls to test_server.py)
- [ ] Implement assertion validators:
  - `http_status` - validate HTTP status codes
  - `db_record` - validate database records exist with conditions  
  - `llm_judge` - call LLM to evaluate output quality
- [ ] Create `MockLanguageModelAdapter` for test fixtures
- [ ] Create `MockTTSAdapter` for test fixtures (writes silent audio file)
- [ ] Create `getInMemoryDatabase()` helper that resets between scenarios
- [ ] Write result to `/tmp/ralph-scenario-result.json` after run
- [ ] Support running single scenario or all scenarios from `/var/otto-scenarios/`
- [ ] Report pass/fail per assertion and overall scenario

**Verification:**
- [ ] `python3 -m pytest harness/` runs successfully (when tests exist)
- [ ] `python3 -m py_compile harness/scenario_harness.py src/test_server.py` passes
- [ ] All 15 scenarios in `scenarios/` execute without error
- [ ] `/tmp/ralph-scenario-result.json` contains valid JSON with pass/fail

---

### 1.4 Refactor Monolithic test_server.py
**Files to create:** `src/lib/__init__.py`, `src/lib/*/` modules

**Status:** ⚠️ All code in single 627-line `test_server.py` — needs modularization

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
**File to modify:** `src/lib/chain/engine.py`

**Spec Reference:** Section 2 — Escalation Chain Engine

**Status:** ⚠️ Partial — basic anchor computation exists, has bugs (see 1.1)

**Tasks (after fixing bugs in 1.1):**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` query
- [ ] Add TTS clip path tracking per anchor
- [ ] Add fire_count increment on retry
- [ ] Add chain validation: reject if `drive_duration > time_to_arrival`
- [ ] Handle compressed chains per spec (verify all buffer sizes)
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
**Files to create/modify:** `src/lib/parser/`

**Spec Reference:** Section 3 — Reminder Parsing & Creation

**Status:** ⚠️ Partial — basic keyword extraction exists, brittle regex

**Gaps:**
- No `ILanguageModelAdapter` interface
- No MiniMax or Anthropic API implementation
- No mock adapter for testing
- Keyword extraction doesn't handle all spec formats
- No confidence scoring per spec
- No user confirmation flow
- Missing reminder_type enum detection (countdown_event, simple_countdown, etc.)

**Current parser issues:**
- Doesn't detect "dryer in 3 min" as simple_countdown with arrival_time = now + 3min
- Doesn't handle "tomorrow" date resolution correctly
- Doesn't extract drive_duration from "Parker Dr 9am, 30 min drive" format well

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
- [ ] Detect reminder_type enum based on input patterns

**Acceptance Criteria (Spec Section 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] "dryer in 3 min" parses as simple_countdown with arrival_time = now + 3 minutes
- [ ] "meeting tomorrow 2pm, 20 min drive" parses with correct date
- [ ] On API failure, keyword extraction produces best-effort parsed object with confidence < 1.0
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

**Status:** ⚠️ Partial — basic hit rate exists, missing features

**Gaps:**
- No common miss window calculation
- No streak counter for recurring reminders
- No feedback loop adjustment (cap at +15 min)
- No 90-day retention/archiving
- No `actual_arrival` tracking (only `scheduled_arrival`)
- No `missed_reason` tracking

**Tasks:**
- [ ] Implement hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
- [ ] Implement feedback loop adjustment: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_min)`, capped at +15 min
- [ ] Implement common miss window: identify most frequently missed urgency tier
- [ ] Implement streak counter: increment on 'hit' for recurring, reset to 0 on 'miss'
- [ ] Implement 90-day retention: archive data older than 90 days
- [ ] Track `actual_arrival` for hit rate accuracy
- [ ] Track `missed_reason` (background_task_killed, dnd_suppressed, user_dismissed)

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

**Before any other work, Priority 1 MUST be completed in this order:**

```
IMMEDIATE (Day 1):
├── 1.1 Fix Chain Engine Bugs ← CRITICAL (wrong timestamps, duplicates)
│   └── Rewrites compute_escalation_chain() with correct logic
│
├── 1.3 Test Harness Infrastructure ← BLOCKING ALL VALIDATION
│   └── 15 scenarios in scenarios/ cannot be executed
│   └── Must write /tmp/ralph-scenario-result.json for Otto loop
│
└── 1.1 (completed) + 1.3 (completed)
        ↓
DAY 2:
└── 1.2 Database Schema + Migrations
    └── All other features depend on correct DB schema
        ↓
DAY 3:
└── 1.4 Refactor test_server.py → move logic to src/lib/
        ↓
DAY 4+:
├── 2.2 LLM Adapter + Parser (enhanced)
├── 3.2 Voice Personality Variations
└── Continue with remaining priorities...
```

**Why 1.1 (Chain Engine) is CRITICAL:**
- Current implementation produces WRONG timestamps and DUPLICATE times
- Violates `UNIQUE(reminder_id, timestamp)` DB constraint
- Causes data integrity failures

**Why 1.3 (Test Harness) is blocking:**
- The `harness/` directory is empty
- Without `scenario_harness.py`, there is NO WAY to run the 15 validation scenarios
- Otto loop cannot validate any work without harness
- Otto loop depends on `/tmp/ralph-scenario-result.json` written by harness

---

## Verification: Chain Engine Bugs Confirmed

Run this Python to verify bugs:
```python
from datetime import datetime, timedelta
# (use compute_escalation_chain from test_server.py)
arrival = datetime(2026, 4, 9, 9, 0, 0)
```

**Actual output vs expected:**

| Buffer | Expected | Actual | Status |
|--------|----------|--------|--------|
| 30 min | 8 anchors, T-30...T-0 | 8 anchors ✓ | Working |
| 10 min | 4 anchors: T-10, T-5, T-1, T-0 | 4 anchors but WRONG times (urgent@T-5, pushing@T-0, critical@T-9) | ❌ BROKEN |
| 3 min | 3 anchors: T-2, T-1, T-0 | 2 anchors only (missing critical) | ❌ BROKEN |
| 6 min | 3 anchors, no duplicates | 3 anchors but DUPLICATE T-5 timestamps | ❌ BROKEN |

---

## Detailed Gap Analysis

### Database Schema Gaps (vs Spec Section 13)
| Table | Column | Status |
|-------|--------|--------|
| reminders | origin_lat, origin_lng | ❌ Missing |
| reminders | origin_address | ❌ Missing |
| reminders | calendar_event_id | ❌ Missing |
| reminders | custom_sound_path | ❌ Missing |
| anchors | tts_fallback | ❌ Missing |
| anchors | snoozed_to | ❌ Missing |
| history | actual_arrival | ❌ Missing |
| history | missed_reason | ❌ Missing |
| user_preferences | updated_at | ❌ Missing |
| destination_adjustments | updated_at | ❌ Missing |
| **calendar_sync** | table | ❌ Missing |
| **custom_sounds** | table | ❌ Missing |
| All | WAL mode | ❌ Not enabled |
| All | FK enforcement | ❌ Not enabled |

### Parser Gaps (vs Spec Section 3)
| Feature | Status |
|---------|--------|
| ILanguageModelAdapter interface | ❌ Missing |
| MiniMax API adapter | ❌ Missing |
| Anthropic API adapter | ❌ Missing |
| MockLanguageModelAdapter | ❌ Missing |
| Keyword extraction for all formats | ⚠️ Partial |
| Confidence scoring | ⚠️ Partial |
| reminder_type enum detection | ❌ Missing |
| User confirmation flow | ❌ Missing |

### TTS Gaps (vs Spec Section 4)
| Feature | Status |
|---------|--------|
| ITTSAdapter interface | ❌ Missing |
| ElevenLabs adapter | ❌ Missing |
| MockTTSAdapter | ❌ Missing |
| TTS cache management | ❌ Missing |
| Cache invalidation on delete | ❌ Missing |
| Fallback on API failure | ❌ Missing |

### Notification Gaps (vs Spec Section 5)
| Feature | Status |
|---------|--------|
| Sound tier escalation | ❌ Missing |
| DND awareness | ❌ Missing |
| Quiet hours | ❌ Missing |
| Chain overlap serialization | ❌ Missing |
| T-0 alarm looping | ❌ Missing |

### Background Scheduling Gaps (vs Spec Section 6)
| Feature | Status |
|---------|--------|
| Notifee/WorkManager | ❌ Missing |
| Recovery scan | ❌ Missing |
| Grace window (15 min) | ❌ Missing |
| Late fire logging | ❌ Missing |

### Calendar Integration Gaps (vs Spec Section 7)
| Feature | Status |
|---------|--------|
| ICalendarAdapter interface | ❌ Missing |
| Apple Calendar adapter | ❌ Missing |
| Google Calendar adapter | ❌ Missing |
| Calendar sync logic | ❌ Missing |
| Suggestion cards | ❌ Missing |

### Location Gaps (vs Spec Section 8)
| Feature | Status |
|---------|--------|
| LocationService interface | ❌ Missing |
| Geofence comparison (500m) | ❌ Missing |
| Origin capture at creation | ❌ Missing |

### Snooze Gaps (vs Spec Section 9)
| Feature | Status |
|---------|--------|
| Tap snooze (1 min) | ❌ Missing |
| Custom snooze picker | ❌ Missing |
| Chain re-computation | ❌ Missing |
| Feedback prompt | ❌ Missing |
| TTS confirmation | ❌ Missing |

### Voice Personality Gaps (vs Spec Section 10)
| Feature | Status |
|---------|--------|
| 3+ variations per tier | ❌ Missing (only 1) |
| Custom prompt mode | ❌ Missing |
| ElevenLabs voice mapping | ❌ Missing |

### Stats Gaps (vs Spec Section 11)
| Feature | Status |
|---------|--------|
| Hit rate calculation | ⚠️ Partial |
| Feedback loop (adjustment) | ❌ Missing |
| Common miss window | ❌ Missing |
| Streak counter | ❌ Missing |
| 90-day retention | ❌ Missing |

### Sound Library Gaps (vs Spec Section 12)
| Feature | Status |
|---------|--------|
| Sound library structure | ❌ Missing |
| Built-in sounds (15 total) | ❌ Missing |
| Custom import | ❌ Missing |
| Corrupted file fallback | ❌ Missing |

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
├── __init__.py
├── scenario_harness.py         # Main test runner
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
| **1.1** | **Fix Chain Engine Bugs** | ❌ **CRITICAL** | **Wrong timestamps, duplicates** |
| 1.2 | Database Schema + Migrations | ⚠️ Partial | Basic tables exist, missing columns |
| **1.3** | **Test Harness Infrastructure** | ❌ **BLOCKING** | **Must be created - Otto loop blocked** |
| 1.4 | Refactor Monolithic test_server.py | ⚠️ In single file | All logic in 627-line file |
| 2.1 | Chain Engine Completeness | ⚠️ Partial | Depends on 1.1 fix |
| 2.2 | LLM Adapter + Parser Enhancement | ⚠️ Partial | Limited regex, needs LLM |
| 3.1 | TTS Adapter + Cache | ❌ Not implemented | No audio generation |
| 3.2 | Voice Personality Variations | ⚠️ 1 variation | Needs 3+ per spec |
| 4.1 | Notification Tier System | ❌ Not implemented | No sound tiers, DND |
| 5.1 | Background Scheduling | ❌ Not implemented | No Notifee |
| 6.1 | Calendar Adapters | ❌ Not implemented | No EventKit |
| 7.1 | Location Check at Departure | ❌ Not implemented | No location |
| 8.1 | Snooze + Dismissal Flow | ⚠️ Partial | Basic firing only |
| 9.1 | History & Stats | ⚠️ Partial | Missing feedback loop |
| 10.1 | Sound Library | ❌ Not implemented | No sounds |

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
- Priority 1 (Foundation) MUST be completed before any other work — all other components depend on the database schema and correct chain computation.
- **Chain engine bugs are CRITICAL** — they cause data integrity failures and must be fixed before any integration testing.
- **Test harness is BLOCKING** — Otto loop cannot validate any work without it.
- The 15 existing scenarios in `scenarios/` validate the current partial implementations. They should all pass once the corresponding systems are complete.
- All tests must pass before a task can be marked complete (per Otto loop rules).
