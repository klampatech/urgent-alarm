# Implementation Plan — Urgent Voice Alarm App

## Overview

The current codebase (`src/test_server.py`) contains a basic HTTP test server with minimal implementations of the chain engine, keyword parser, and voice message templates. The specification is comprehensive, covering 13 major systems. This plan identifies all gaps and prioritizes tasks by dependencies.

---

## Priority 1: Foundation (Everything Depends On These)

### 1.1 Complete Database Schema Migration System
**Files to create:** `src/lib/db/migrations.py`, `src/lib/db/models.py`
**Status:** Partial — basic tables exist, missing complete schema, migrations, and FK enforcement

**Gaps:**
- Missing `calendar_sync` table
- Missing `custom_sounds` table  
- Missing columns: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path` on reminders
- Missing columns: `snoozed_to` on anchors
- Missing columns: `actual_arrival`, `missed_reason` on history
- No migration versioning system
- No WAL mode, no FK enforcement

**Tasks:**
1. Create migration runner with version tracking (`schema_version` table)
2. Create all spec-compliant tables in migration order
3. Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
4. Add all missing columns via migrations
5. Ensure cascade deletes work correctly

---

### 1.2 Test Harness Infrastructure
**Files to create:** `harness/scenario_harness.py`, `harness/test_runner.py`
**Status:** Not implemented

**Gaps:**
- No harness exists
- No test database setup
- No test fixtures

**Tasks:**
1. Create `scenario_harness.py` with scenario runner
2. Create `getInMemoryDatabase()` helper for tests
3. Create test fixtures for chain engine, parser, voice
4. Implement base test class with fresh DB per test

---

## Priority 2: Core Domain Logic (Chain Engine + Parser)

### 2.1 Chain Engine Completeness
**File to modify:** `src/test_server.py` (or split into `src/lib/chain.py`)
**Status:** Partial — basic anchor computation exists

**Gaps:**
- No `get_next_unfired_anchor()` function
- No TTS clip path tracking per anchor
- No fire_count increment on retry
- Chain not deterministic (depends on runtime clock in tests)
- No validation that `arrival_time > departure + minimum_drive_time`

**Tasks:**
1. Implement `get_next_unfired_anchor(reminder_id)` query
2. Add `tts_clip_path`, `tts_fallback`, `fire_count`, `snoozed_to` to anchor storage
3. Make chain computation pure (accept `now` as parameter for determinism)
4. Add chain validation: reject if `drive_duration > time_to_arrival`
5. Add unit tests for all test cases in spec Section 2.5

---

### 2.2 LLM Adapter + Parser Enhancement
**Files to create:** `src/lib/parser/llm_adapter.py`, `src/lib/parser/keyword_extractor.py`, `src/lib/parser/parser.py`
**Status:** Partial — basic keyword extraction in test_server

**Gaps:**
- No `ILanguageModelAdapter` interface
- No MiniMax or Anthropic API implementation
- No mock adapter for testing
- Keyword extraction is brittle, doesn't handle all spec formats
- No confidence scoring
- No user confirmation flow

**Tasks:**
1. Create `ILanguageModelAdapter` abstract interface
2. Create `MiniMaxAdapter` and `AnthropicAdapter` implementations
3. Create `MockLanguageModelAdapter` for tests with fixture responses
4. Improve keyword extractor to handle all formats in spec Section 3.3
5. Implement confidence scoring and fallback logic
6. Add `parse_and_confirm()` function that returns parsed fields for UI review
7. Implement "tomorrow" date resolution correctly
8. Add unit tests for all test cases in spec Section 3.5

---

## Priority 3: Voice & TTS System

### 3.1 TTS Adapter Interface + Cache
**Files to create:** `src/lib/tts/adapter.py`, `src/lib/tts/generator.py`, `src/lib/tts/cache_manager.py`
**Status:** Not implemented — only message templates exist

**Gaps:**
- No ElevenLabs adapter
- No `ITTSAdapter` interface
- No TTS clip generation
- No `/tts_cache/` directory management
- No cache invalidation on reminder delete
- No fallback when API unavailable

**Tasks:**
1. Create `ITTSAdapter` abstract interface
2. Create `ElevenLabsAdapter` implementation
3. Create `MockTTSAdapter` for tests
4. Create cache manager with `/tts_cache/{reminder_id}/` structure
5. Implement `generate_tts_for_anchors(reminder_id, anchors)` that pre-generates clips
6. Implement fallback: if TTS fails, mark `tts_fallback = true`, use notification text
7. Implement cache invalidation when reminder deleted
8. Add unit tests for all test cases in spec Section 4.5

---

### 3.2 Voice Personality Message Variations
**File to modify:** `src/test_server.py` (VOICE_PERSONALITIES)
**Status:** Partial — single template per tier

**Gaps:**
- Only 1 message variation per tier
- Spec requires minimum 3 variations per tier per personality
- No custom prompt mode

**Tasks:**
1. Expand each personality to have 3+ message templates per urgency tier
2. Add random selection (or round-robin) for variation
3. Implement custom prompt mode: user writes prompt appended to system prompt
4. Ensure existing reminders retain their personality at creation time

---

## Priority 4: Notification & Alarm Behavior

### 4.1 Notification Tier System
**Files to create:** `src/lib/notifications/tier_manager.py`, `src/lib/notifications/sound_player.py`
**Status:** Not implemented

**Gaps:**
- No notification tier mapping to sounds
- No DND awareness (silent vs. visual+vibration)
- No quiet hours enforcement
- No chain overlap serialization (queue new anchors)
- No T-0 alarm looping

**Tasks:**
1. Create notification tier definitions:
   - calm/casual → gentle chime
   - pointed/urgent → pointed beep
   - pushing/firm → urgent siren
   - critical/alarm → looping alarm
2. Create `SoundPlayer` that plays appropriate sound under TTS
3. Add DND check: if DND active, silent notification for early anchors, visual+vibration for final 5 min
4. Add quiet hours suppression (configurable, default 10pm-7am)
5. Queue anchors if another chain is firing (never overlap)
6. Loop T-0 alarm until user dismisses or snoozes
7. Format notification: destination, "X minutes remaining", voice icon

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration (Stub for Server)
**Files to create:** `src/lib/scheduling/notifee_client.py`, `src/lib/scheduling/recovery.py`
**Status:** Not implemented

**Note:** Since this is a Python test server (not React Native), we'll stub the scheduling interface and implement the logic that would integrate with Notifee.

**Tasks:**
1. Create `SchedulingService` interface (mock-able)
2. Create `schedule_anchor(anchor_id, timestamp)` function
3. Create `cancel_anchor(anchor_id)` function
4. Create recovery scan: on launch, fire overdue unfired anchors within 15-min grace window
5. Drop anchors > 15 minutes overdue and log `missed_reason = "background_task_killed"`
6. Re-register all pending anchors on app restart
7. Log warning if anchor fires > 60 seconds after scheduled time

---

## Priority 6: Calendar Integration

### 6.1 Calendar Adapters
**Files to create:** `src/lib/calendar/adapter.py`, `src/lib/calendar/apple_calendar.py`, `src/lib/calendar/google_calendar.py`
**Status:** Not implemented

**Tasks:**
1. Create `ICalendarAdapter` interface
2. Create `AppleCalendarAdapter` (stub for EventKit integration)
3. Create `GoogleCalendarAdapter` (stub for Google Calendar API)
4. Implement calendar sync on launch + every 15 minutes
5. Filter events with non-empty `location` field
6. Create suggestion card generation: "Parker Dr check-in — 9:00 AM — add departure reminder?"
7. Create reminder from suggestion with `calendar_event_id` set
8. Handle permission denial: show explanation banner with "Open Settings"
9. Handle sync failure gracefully (manual reminders still work)
10. Handle recurring events (generate reminder for each occurrence)

---

## Priority 7: Location Awareness

### 7.1 Location Check at Departure
**Files to create:** `src/lib/location/location_service.py`, `src/lib/location/geofence.py`
**Status:** Not implemented

**Tasks:**
1. Create `LocationService` interface
2. Create `CoreLocationAdapter` (stub for iOS) / `FusedLocationAdapter` (Android)
3. Implement single location check at departure anchor (T-drive_duration)
4. Compare current location to origin using 500m geofence radius
5. If user within 500m of origin → fire firm/critical anchor immediately instead of calm departure nudge
6. If user > 500m → proceed with normal chain
7. Request permission only at first location-aware reminder creation
8. If permission denied → create reminder without location awareness, show note
9. Do NOT store location history (single check only)

---

## Priority 8: Snooze & Dismissal

### 8.1 Snooze + Dismissal Flow
**Files to modify:** `src/test_server.py` (anchors), create `src/lib/snooze/manager.py`
**Status:** Partial — basic anchor firing exists

**Gaps:**
- No tap snooze (1 min)
- No tap-and-hold snooze (1, 3, 5, 10, 15 min)
- No chain re-computation after snooze
- No swipe-to-dismiss feedback prompt
- No TTS confirmation after snooze
- No snooze persistence across app restarts

**Tasks:**
1. Implement tap snooze: pause current anchor, re-fire after 1 minute
2. Implement tap-and-hold snooze: show duration picker, selected duration applied
3. Implement chain re-computation: shift remaining unfired anchors to `now + original_time_remaining`
4. Re-register snoozed anchors with Notifee (new timestamps)
5. Implement swipe-to-dismiss: show feedback prompt "You missed [destination] — was timing right?"
6. Handle "Yes" (timing right) → store positive feedback
7. Handle "No" → show "What was wrong?" (Left too early / Left too late / Other)
8. Implement TTS confirmation: "Okay, snoozed [X] minutes."
9. Persist snooze state so app restart doesn't lose snooze offset

---

## Priority 9: History & Stats

### 9.1 Stats Calculations + Feedback Loop
**Files to modify:** `src/test_server.py` (stats)
**Status:** Partial — basic hit rate exists

**Gaps:**
- No common miss window calculation
- No streak counter for recurring reminders
- No feedback loop adjustment (cap at +15 min)
- No 90-day retention/archiving

**Tasks:**
1. Implement hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
2. Implement feedback loop adjustment: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_min)`, capped at +15 min
3. Implement common miss window: identify most frequently missed urgency tier
4. Implement streak counter: increment on 'hit' for recurring, reset to 0 on 'miss'
5. Implement 90-day retention: archive data older than 90 days (but keep accessible)
6. Verify all stats are computable from history table (no separate stats store)

---

## Priority 10: Sound Library

### 10.1 Sound Library System
**Files to create:** `src/lib/sounds/library.py`, `src/lib/sounds/import_handler.py`
**Status:** Not implemented

**Tasks:**
1. Create sound categories: Commute (5 sounds), Routine (5 sounds), Errand (5 sounds), Custom (imported)
2. Bundle 5 built-in sounds per category (use placeholder audio files)
3. Implement custom audio import: MP3, WAV, M4A only, max 30 seconds
4. Transcode imported sounds to normalized format
5. Store custom sounds in app sandbox with reference in `custom_sounds` table
6. Implement per-reminder sound selection
7. Implement corrupted sound fallback: use category default, log error
8. Persist sound selection when reminder edited

---

## Priority 11: Integration Tests

### 11.1 Full Test Suite
**Files to create:** `tests/test_chain_engine.py`, `tests/test_parser.py`, `tests/test_tts.py`, `tests/test_integration.py`
**Status:** Not implemented

**Tasks:**
1. Unit tests for chain engine (all TC-01 through TC-06 from spec)
2. Unit tests for parser (all TC-01 through TC-07)
3. Unit tests for TTS adapter (all TC-01 through TC-05)
4. Unit tests for LLM adapter mock
5. Integration tests: parse → chain → TTS → persist flow
6. Integration tests: anchor schedule → fire → mark fired
7. Integration tests: snooze → recompute → re-register
8. Integration tests: dismiss → feedback → adjustment applied

---

## Priority 12: UI Layer (Future)

These are out of scope for the Python test server but would be needed for the actual React Native/Flutter app:

- Quick Add UI (text/speech input)
- Reminder confirmation card with editable fields
- History tab with weekly hit rate, streak, common miss window
- Settings for voice personality, quiet hours, calendar integration
- Sound picker UI
- Calendar tab with suggestion cards
- Notification interaction (tap, tap-hold, swipe)

---

## Implementation Order (Dependencies)

```
1. Foundation
   ├── 1.1 Database Schema + Migrations
   └── 1.2 Test Harness Infrastructure
           ↓
2. Core Domain
   ├── 2.1 Chain Engine (complete)
   └── 2.2 LLM Adapter + Parser (enhanced)
           ↓
3. Voice & TTS
   ├── 3.1 TTS Adapter + Cache
   └── 3.2 Voice Personality Variations
           ↓
4. Notifications + Scheduling
   ├── 4.1 Notification Tier System
   └── 5.1 Background Scheduling (Notifee stubs)
           ↓
6. Calendar + Location
   ├── 6.1 Calendar Adapters
   └── 7.1 Location Check at Departure
           ↓
7. Snooze + Dismissal
   └── 8.1 Snooze + Dismissal Flow
           ↓
8. Stats + Sounds
   ├── 9.1 History & Stats (enhanced)
   └── 10.1 Sound Library
           ↓
9. Tests
   └── 11.1 Full Test Suite
```

---

## Quick Wins (Can Be Done in Parallel with Foundation)

- Expand voice personality templates to 3+ variations per tier
- Improve keyword extractor regex patterns
- Add `get_next_unfired_anchor()` query
- Implement basic chain re-computation for snooze
- Add hit rate calculation with trailing 7-day window

---

## File Structure (Target)

```
src/
├── test_server.py              # HTTP API server (existing, will expand)
└── lib/
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py       # Database connection management
    │   ├── migrations.py        # Migration runner
    │   └── models.py           # Data models (optional, for type hints)
    ├── chain/
    │   ├── __init__.py
    │   ├── engine.py           # Escalation chain computation
    │   └── validator.py        # Chain validation
    ├── parser/
    │   ├── __init__.py
    │   ├── llm_adapter.py     # ILanguageModelAdapter interface
    │   ├── minimax_adapter.py  # MiniMax implementation
    │   ├── anthropic_adapter.py # Anthropic implementation
    │   ├── keyword_extractor.py # Fallback keyword parsing
    │   └── parser.py           # Main parser service
    ├── tts/
    │   ├── __init__.py
    │   ├── adapter.py          # ITTSAdapter interface
    │   ├── elevenlabs.py       # ElevenLabs implementation
    │   ├── generator.py         # TTS generation orchestration
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
├── scenario_harness.py        # Main test runner
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

specs/
├── urgent-voice-alarm-app-2026-04-08.md
└── urgent-voice-alarm-app-2026-04-08.spec.md
```

---

## Verification Checklist

After implementing each priority, verify:

- [ ] Priority 1: Fresh install applies all migrations in order
- [ ] Priority 1: In-memory test database starts empty and migrations apply
- [ ] Priority 2: Chain for "30 min drive, arrive 9am" produces 8 anchors
- [ ] Priority 2: Chain for "10 min drive, arrive 9am" produces 4 anchors
- [ ] Priority 2: `get_next_unfired_anchor` correctly returns earliest unfired
- [ ] Priority 2: Parser handles all spec test cases (TC-01 through TC-07)
- [ ] Priority 3: TTS cache exists at `/tts_cache/{reminder_id}/` with MP3 files
- [ ] Priority 3: Each personality generates 3+ message variations per tier
- [ ] Priority 4: Notification tier sounds escalate correctly
- [ ] Priority 4: DND respects silent/visual+vibration rules
- [ ] Priority 5: Recovery scan fires overdue anchors within 15-min window
- [ ] Priority 5: Anchors > 15 min overdue are dropped and logged
- [ ] Priority 6: Calendar events with locations appear as suggestion cards
- [ ] Priority 7: Location check triggers at departure anchor only
- [ ] Priority 8: Tap snooze re-fires after 1 minute, chain re-computed
- [ ] Priority 8: Feedback prompt appears on swipe-dismiss
- [ ] Priority 9: Hit rate calculates correctly (4 hits, 1 miss = 80%)
- [ ] Priority 9: Feedback loop caps at +15 minutes
- [ ] Priority 10: Built-in sounds play without network
- [ ] Priority 10: Custom MP3 import appears in sound picker
- [ ] All: Tests pass for corresponding spec acceptance criteria