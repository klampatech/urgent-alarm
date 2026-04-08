# URGENT Alarm - Implementation Plan

## Gap Analysis Summary

| Spec Section | Status | Implementation Gap |
|-------------|--------|---------------------|
| 1. Overview | N/A | Reference document |
| 2. Escalation Chain Engine | ⚠️ Partial | Missing validation, `get_next_unfired_anchor()`, `snoozed_to` tracking |
| 3. Reminder Parsing | ⚠️ Partial | No LLM adapter interface, no mock, no MiniMax/Anthropic |
| 4. Voice & TTS | ❌ Missing | No TTS adapter, no caching, no ElevenLabs integration |
| 5. Notification & Alarm | ❌ Missing | No notification manager, no DND/quiet hours |
| 6. Background Scheduling | ❌ Missing | No scheduler, no Notifee, no recovery scan |
| 7. Calendar Integration | ❌ Missing | No Apple/Google calendar adapters |
| 8. Location Awareness | ❌ Missing | No location check, no geofence |
| 9. Snooze & Dismissal | ❌ Missing | No snooze flow, no feedback prompt |
| 10. Voice Personality | ⚠️ Partial | 1 template per tier, need 3 variations, no custom prompt |
| 11. History & Stats | ⚠️ Partial | Missing adjustment cap, miss window, streak counter |
| 12. Sound Library | ❌ Missing | No built-in sounds, no import, no fallback |
| 13. Data Persistence | ⚠️ Partial | Incomplete schema, no migrations |
| 14. Definition of Done | N/A | Testing reference |

---

## Phase 1: Foundation (Core Infrastructure)

### Task 1.1: Complete Database Schema & Migration System
**Files to create:** `src/lib/db.py`, `src/lib/migrations/` directory
**Dependencies:** None
**Priority:** P1
**Spec Reference:** Section 13

**Gaps in current `src/test_server.py`:**
- Missing `custom_sounds` table
- Missing `calendar_sync` table  
- Missing `updated_at` on `reminders`, `user_preferences`, `destination_adjustments`
- Missing `origin_lat`, `origin_lng`, `origin_address` on `reminders`
- Missing `calendar_event_id` on `reminders`
- Missing `custom_sound_path` on `reminders`
- Missing `tts_fallback`, `snoozed_to` on `anchors`
- Missing `actual_arrival`, `missed_reason` on `history`
- No migration versioning system

**Tasks:**
- [ ] Create `src/lib/db.py` with full schema from spec Section 13.3
- [ ] Create `src/lib/migrations/` directory with versioned migrations
- [ ] Add `create_migration()` helper for adding new migrations
- [ ] Enable foreign keys (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Add in-memory test mode (`Database.get_in_memory_instance()`)
- [ ] Add UUID v4 generation helper
- [ ] Write unit tests for migration TC-01 through TC-05

**Acceptance Criteria (Section 13.4):**
- Fresh install applies all migrations in order
- In-memory test database is fresh with all migrations applied
- `reminders.id` is always valid UUID v4
- Deleting a reminder cascades to delete its anchors
- Foreign key violation returns error without crashing

---

### Task 1.2: Enhance Escalation Chain Engine
**Files to modify:** `src/lib/chain_engine.py` (create new)
**Dependencies:** Task 1.1
**Priority:** P1
**Spec Reference:** Section 2

**Gaps in current `src/test_server.py`:**
- Missing `validate_chain()` for `arrival_time > departure_time + minimum_drive_time`
- Missing `get_next_unfired_anchor(reminder_id)` function
- Missing `get_earliest_unfired_anchor()` for recovery scan
- Missing anchor sorting guarantee
- Missing `snoozed_to` field handling

**⚠️ Known Bugs (must fix):**
- 10-min buffer: pushing anchor fires at 9:00 (T-0) instead of 8:50 (T-10)
- 3-min buffer: only produces 2 anchors instead of 3 (should be: 8:57 firm, 8:59 critical, 9:00 alarm)
- Anchors are not consistently sorted by timestamp

**Tasks:**
- [ ] Create `src/lib/chain_engine.py` with:
  - `compute_escalation_chain(arrival_time, drive_duration)` with full compression rules
  - `validate_chain(arrival_time, drive_duration)` per spec Section 2.3.8
  - `get_next_unfired_anchor(reminder_id)` per spec Section 2.3.6
  - `get_earliest_unfired_anchor()` for recovery
  - `recompute_chain_after_snooze(reminder_id, snooze_duration)` for Task 3.1
- [ ] Implement chain compression rules:
  - ≥25 min: 8 anchors (calm → alarm)
  - 20-24 min: 7 anchors (casual → alarm)
  - 15-19 min: 6 anchors (pointed → alarm)
  - 10-14 min: 5 anchors (urgent → alarm)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - ≤5 min: 3 anchors (firm, critical, alarm) per spec TC-03
- [ ] **BUG FIX:** Ensure anchors are sorted by timestamp ascending
- [ ] **BUG FIX:** Fix 10-min buffer to produce: 8:50 (pushing), 8:55 (urgent), 8:59 (critical), 9:00 (alarm)
- [ ] **BUG FIX:** Fix 3-min buffer to produce 3 anchors: 8:57 (firm), 8:59 (critical), 9:00 (alarm)
- [ ] Write unit tests for all test scenarios TC-01 through TC-06

**Acceptance Criteria (Section 2.4):**
- [ ] Chain for "30 min drive, arrive 9am" produces 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "10 min drive, arrive 9am" produces 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "3 min drive, arrive 9am" produces 3 anchors: 8:57, 8:59, 9:00
- [ ] Chain with `drive_duration > arrival_time` is rejected
- [ ] `get_next_unfired_anchor` correctly returns earliest unfired anchor
- [ ] Anchors are sorted by timestamp ascending

---

### Task 1.3: Create LLM Adapter Interface & Implementations
**Files to create:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/minimax_adapter.py`, `src/lib/adapters/anthropic_adapter.py`, `src/lib/adapters/mock_llm_adapter.py`
**Dependencies:** Task 1.1
**Priority:** P1
**Spec Reference:** Section 3

**Gaps in current `src/test_server.py`:**
- No `ILanguageModelAdapter` interface
- No `MiniMaxAdapter` implementation
- No `AnthropicAdapter` implementation
- No mock adapter for testing
- Keyword parsing has limited date/time handling

**Tasks:**
- [ ] Create `src/lib/adapters/__init__.py`
- [ ] Create `ILanguageModelAdapter` abstract base class with:
  - `parse_reminder(text: str) -> ParsedReminder`
  - `parse_calendar_event(event_text: str) -> ParsedEvent`
  - `mock_mode` property
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` as alternative
- [ ] Create `MockLLMAdapter` for testing with fixture responses
- [ ] Enhance `parse_reminder_natural()` keyword fallback:
  - Handle all formats per spec Section 3.3.5
  - Return confidence score
  - Handle "tomorrow" date resolution
- [ ] Unit tests for TC-01 through TC-07

**Acceptance Criteria (Section 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] "dryer in 3 min" parses as simple_countdown
- [ ] "meeting tomorrow 2pm, 20 min drive" resolves to correct date
- [ ] On API failure, keyword extraction runs with confidence < 1.0
- [ ] User can edit parsed fields before confirming
- [ ] Empty input returns user-facing error

---

## Phase 2: Voice & Message Generation

### Task 2.1: Enhance Voice Personality System
**Files to create:** `src/lib/voice_personalities.py` (replace simple templates)
**Dependencies:** Task 1.1
**Priority:** P1
**Spec Reference:** Section 10

**Gaps in current `src/test_server.py`:**
- Only 1 template per tier per personality (spec requires minimum 3 per tier)
- No custom prompt mode (max 200 chars)
- No personality storage/retrieval in user_preferences
- No message variation logic

**Tasks:**
- [ ] Define all 5 built-in personalities with:
  - `voice_id` (ElevenLabs ID)
  - `system_prompt` fragment
  - 3+ message templates per urgency tier
- [ ] Add `CustomPersonality` class with user-written prompt
- [ ] Implement `select_random_template(templates)` for variation
- [ ] Add `get_personalities()` and `get_default_personality()` functions
- [ ] Add `set_default_personality(personality)` function
- [ ] Write unit tests for TC-01 through TC-05

**Acceptance Criteria (Section 10.4):**
- [ ] "Coach" at T-5 produces motivational message with "!"
- [ ] "No-nonsense" at T-5 produces brief, direct message
- [ ] "Assistant" at T-5 produces polite, helpful message
- [ ] Custom prompt modifies message tone appropriately
- [ ] Changing default personality doesn't affect existing reminders
- [ ] Each personality generates 3+ distinct message variations per tier

---

### Task 2.2: Create TTS Adapter with Caching
**Files to create:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/elevenlabs_adapter.py`, `src/lib/adapters/mock_tts_adapter.py`
**Dependencies:** Task 2.1, Task 1.1
**Priority:** P2
**Spec Reference:** Section 4

**Gaps in current `src/test_server.py`:**
- No `ITTSAdapter` interface
- No `ElevenLabsAdapter` implementation
- No mock TTS adapter
- No TTS caching system (`/tts_cache/{reminder_id}/`)
- No fallback behavior for TTS failures

**Tasks:**
- [ ] Create `ITTSAdapter` abstract base class with:
  - `generate_clip(text, voice_id, urgency_tier) -> str` (returns file path)
  - `mock_mode` property
- [ ] Implement `ElevenLabsAdapter` with:
  - Voice selection based on personality
  - Async generation with polling (max 30 seconds)
  - API configuration via environment variable
- [ ] Create `MockTTSAdapter` that writes 1-second silent file
- [ ] Implement TTS cache directory structure:
  - `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- [ ] Implement `invalidate_cache(reminder_id)` for reminder deletion
- [ ] Implement fallback: system sound + notification text on TTS failure
- [ ] Unit tests for TC-01 through TC-05

**Acceptance Criteria (Section 4.4):**
- [ ] New reminder generates 8 MP3 clips in cache directory
- [ ] Playing anchor fires correct pre-generated clip from local cache
- [ ] TTS failure falls back to system sound + notification text
- [ ] Reminder deletion removes all cached TTS files
- [ ] TTS generation uses correct voice ID for personality

---

### Task 2.3: Create Message Generation Service
**Files to create:** `src/lib/message_generator.py`
**Dependencies:** Task 2.1, Task 2.2
**Priority:** P1
**Spec Reference:** Section 4

**Tasks:**
- [ ] Create `MessageGenerator` service with:
  - `generate_message(personality, urgency_tier, destination, drive_duration, minutes_remaining)`
  - Integration with voice personality system for template selection
  - Integration with TTS adapter for clip generation
- [ ] Handle pluralization and edge cases
- [ ] Create `generate_all_anchors(reminder)` for batch generation
- [ ] Unit tests for message content and TTS integration

---

## Phase 3: Interaction & State Management

### Task 3.1: Implement Snooze & Dismissal Flow
**Files to create:** `src/lib/snooze_manager.py`
**Dependencies:** Task 1.2, Task 3.3
**Priority:** P2
**Spec Reference:** Section 9

**Gaps in current `src/test_server.py`:**
- No snooze implementation
- No chain re-computation after snooze
- No swipe-to-dismiss feedback prompt
- No feedback storage

**Tasks:**
- [ ] Implement `SnoozeManager` with:
  - `tap_snooze(anchor_id, duration=1)` - default 1 minute
  - `custom_snooze(anchor_id, duration)` - picker: 1, 3, 5, 10, 15 min
  - `recompute_chain_after_snooze(reminder_id, snooze_duration)` - shifts remaining anchors
  - `dismiss_with_feedback(anchor_id, timing_correct, feedback_type)` - for Task 11
- [ ] Update `anchors` table with `snoozed_to` field
- [ ] Implement TTS confirmation: "Okay, snoozed X minutes"
- [ ] Ensure snooze state persists across app restarts
- [ ] Unit tests for TC-01 through TC-06

**Acceptance Criteria (Section 9.4):**
- [ ] Tap snooze pauses current anchor, re-fires after 1 minute
- [ ] Custom snooze picker allows 1, 3, 5, 10, 15 minute selection
- [ ] Chain re-computation shifts all remaining anchors by snooze duration
- [ ] Feedback prompt appears on swipe-dismiss
- [ ] TTS confirms snooze: "Okay, snoozed 3 minutes"
- [ ] After custom snooze and app restart, remaining anchors fire at adjusted times

---

### Task 3.2: Implement History, Stats & Feedback Loop
**Files to create:** `src/lib/stats.py`, `src/lib/history.py`
**Dependencies:** Task 1.1
**Priority:** P2
**Spec Reference:** Section 11

**Gaps in current `src/test_server.py`:**
- `calculate_hit_rate()` exists but needs enhancement
- Missing destination adjustment cap (+15 min max)
- Missing common miss window identification
- Missing streak counter for recurring reminders
- Missing history pruning (90 days)

**Tasks:**
- [ ] Implement `calculate_hit_rate(days=7)` with trailing window
- [ ] Implement `get_destination_adjustment(destination)` with cap logic:
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
  - Cap at +15 minutes
- [ ] Implement `update_destination_adjustment(destination, outcome, feedback_type)`
- [ ] Implement `get_common_miss_window(destination)` - most frequently missed tier
- [ ] Implement `get_streak_counter(reminder_id)` for recurring reminders
- [ ] Implement `prune_old_history(days=90)` for data retention
- [ ] Add `actual_arrival` and `missed_reason` to history storage
- [ ] Unit tests for TC-01 through TC-07

**Acceptance Criteria (Section 11.4):**
- [ ] Weekly hit rate displays correctly (4 hits, 1 miss = 80%)
- [ ] After 3 "left too late" events, +6 minutes added to drive_duration
- [ ] Feedback loop cap at +15 minutes
- [ ] "Common miss window" correctly identifies most missed tier
- [ ] Streak increments on hit, resets on miss
- [ ] Stats derived from history table alone

---

### Task 3.3: Implement Notification & Alarm Behavior
**Files to create:** `src/lib/notification_manager.py`
**Dependencies:** Task 2.2, Task 3.1
**Priority:** P2
**Spec Reference:** Section 5

**Gaps in current `src/test_server.py`:**
- No notification manager exists
- No DND detection and handling
- No quiet hours suppression
- No chain overlap serialization
- No T-0 alarm looping

**Tasks:**
- [ ] Create `NotificationManager` with:
  - `fire_anchor(anchor_id)` - main entry point
  - `get_notification_tier(urgency_tier)` - maps to sound type
  - `check_dnd_status()` - detect DND mode
  - `check_quiet_hours()` - check quiet hours setting
  - `should_queue_anchor(anchor)` - for overlap serialization
- [ ] Implement notification tier escalation:
  - Gentle chime (calm/casual)
  - Pointed beep (pointed/urgent)
  - Urgent siren (pushing/firm)
  - Looping alarm (critical/alarm)
- [ ] Implement DND handling:
  - Early anchors: silent notification only
  - Final 5 minutes: visual override + vibration
- [ ] Implement quiet hours (default 10pm–7am, configurable)
- [ ] Implement post-DND catch-up with 15-minute grace window
- [ ] Implement anchor drop for >15 minutes overdue
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] Implement T-0 alarm looping until user action
- [ ] Unit tests for TC-01 through TC-06

**Acceptance Criteria (Section 5.4):**
- [ ] DND suppresses early anchor sound, plays silent notification
- [ ] DND final 5 minutes fires with visual override + vibration
- [ ] Quiet hours suppress anchors, queue for post-quiet-hours
- [ ] Overdue anchor (>15 min) is dropped and logged
- [ ] Chain overlap queues new anchors until current chain completes
- [ ] T-0 alarm loops until user dismisses or snoozes

---

## Phase 4: Background & External Integration

### Task 4.1: Create Background Scheduling & Reliability
**Files to create:** `src/lib/scheduler.py`, `src/lib/adapters/notifee_adapter.py`
**Dependencies:** Task 1.2, Task 3.3
**Priority:** P2
**Spec Reference:** Section 6

**Tasks:**
- [ ] Create `NotifeeAdapter` for iOS/Android:
  - `schedule_anchor(anchor)` - register with OS scheduler
  - `cancel_anchor(anchor_id)` - cancel scheduled task
  - `cancel_all_anchors(reminder_id)` - cancel entire chain
- [ ] Implement `BackgroundScheduler` with:
  - `schedule_chain(reminder_id)` - register all anchors
  - `reschedule_unfired_anchors(reminder_id)` - after app restart
  - `recovery_scan()` - on app launch, fire overdue within grace window
  - `log_late_fire(anchor_id, seconds_late)` - warning for >60s late
- [ ] Use BGTaskScheduler (iOS) and WorkManager (Android)
- [ ] Implement pending anchor re-registration after crash
- [ ] Implement 15-minute grace window logic
- [ ] Unit tests for TC-01 through TC-06

**Acceptance Criteria (Section 6.4):**
- [ ] Reminder creation schedules all anchors in Notifee
- [ ] App closure doesn't prevent anchors from firing within 5 minutes
- [ ] Recovery scan on launch fires only anchors within grace window
- [ ] Missed anchors >15 min overdue are dropped and logged
- [ ] Pending anchors re-registered on crash recovery
- [ ] Late fire (>60s) triggers warning log entry

---

### Task 4.2: Create Calendar Integration
**Files to create:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/apple_calendar.py`, `src/lib/adapters/google_calendar.py`
**Dependencies:** Task 1.1, Task 3.1
**Priority:** P3
**Spec Reference:** Section 7

**Tasks:**
- [ ] Create `ICalendarAdapter` interface with:
  - `sync_events()` - fetch events with locations
  - `get_events_with_locations()` - filter events
  - `is_connected()` - check connection status
- [ ] Implement `AppleCalendarAdapter` using EventKit (iOS)
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement `CalendarSyncService` with:
  - Sync on app launch
  - Sync every 15 minutes while app is open
  - Background refresh integration
- [ ] Generate suggestion cards for events with locations
- [ ] Handle permission denial with explanation + "Open Settings" action
- [ ] Implement recurring event handling
- [ ] Unit tests for TC-01 through TC-06

**Acceptance Criteria (Section 7.4):**
- [ ] Apple Calendar events with locations appear as suggestion cards
- [ ] Google Calendar events with locations appear as suggestion cards
- [ ] Confirming suggestion creates countdown_event reminder
- [ ] Permission denial shows explanation banner
- [ ] Calendar sync failure doesn't prevent manual reminder creation
- [ ] Recurring daily event generates reminder for each occurrence

---

### Task 4.3: Create Location Awareness
**Files to create:** `src/lib/location_manager.py`
**Dependencies:** Task 1.2, Task 4.1
**Priority:** P3
**Spec Reference:** Section 8

**Tasks:**
- [ ] Create `LocationManager` with:
  - `check_location_at_departure(reminder_id)` - single check at anchor fire
  - `set_origin(reminder_id, address_or_coordinates)`
  - `is_at_origin(current_location, origin, radius_meters=500)`
- [ ] Implement single CoreLocation (iOS) / FusedLocationProvider (Android) call
- [ ] Implement 500m geofence radius check
- [ ] Implement immediate escalation if user still at origin:
  - Fire T-5 (firm) anchor instead of departure anchor
- [ ] Request permission only at first location-aware reminder
- [ ] Handle permission denial gracefully (create reminder without location)
- [ ] Ensure no location history storage
- [ ] Unit tests for TC-01 through TC-05

**Acceptance Criteria (Section 8.4):**
- [ ] Departure anchor performs one location check
- [ ] User at origin (<500m) triggers immediate firm tier
- [ ] User already left (>500m) proceeds normal chain
- [ ] Location permission requested only at first location-aware reminder
- [ ] Denied permission creates reminder without location escalation
- [ ] No location history stored after comparison

---

### Task 4.4: Create Sound Library
**Files to create:** `src/lib/sound_library.py`
**Dependencies:** Task 1.1
**Priority:** P3
**Spec Reference:** Section 12

**Tasks:**
- [ ] Create `SoundLibrary` with:
  - `get_built_in_sounds(category)` - return 5 sounds per category
  - `get_sound_path(sound_id)` - resolve file path
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom sound import:
  - File picker integration
  - Format validation (MP3, WAV, M4A)
  - Duration validation (max 30 seconds)
- [ ] Implement audio transcoding to normalized format
- [ ] Implement `import_custom_sound(file)` - copy to app sandbox
- [ ] Implement corrupted sound fallback to category default
- [ ] Persist sound selection on reminder edit
- [ ] Unit tests for TC-01 through TC-05

**Acceptance Criteria (Section 12.4):**
- [ ] Built-in sounds play without network access
- [ ] Custom MP3 import appears in sound picker
- [ ] Imported sound plays correctly under TTS
- [ ] Corrupted sound fallback shows error, uses category default
- [ ] Sound selection persists when reminder is edited

---

## Phase 5: Refactoring & Testing

### Task 5.1: Refactor test_server.py to Use New Modules
**Files to modify:** `src/test_server.py`
**Dependencies:** Tasks 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.2
**Priority:** P2

**Tasks:**
- [ ] Import chain engine from `src/lib/chain_engine.py`
- [ ] Import parser from `src/lib/adapters/llm_adapter.py`
- [ ] Import voice personalities from `src/lib/voice_personalities.py`
- [ ] Import message generator from `src/lib/message_generator.py`
- [ ] Import stats from `src/lib/stats.py`
- [ ] Keep HTTP handler but delegate to library modules
- [ ] Ensure backward compatibility for existing endpoints
- [ ] Run lint check: `python3 -m py_compile src/test_server.py`

---

### Task 5.2: Create Scenario Harness
**Files to create:** `harness/scenario_harness.py`
**Dependencies:** None (can run parallel with other tasks)
**Priority:** P0
**Spec Reference:** Validation framework

**Tasks:**
- [ ] Create `harness/scenario_harness.py` that:
  - Reads scenario YAML files from configurable directory (`/var/otto-scenarios/{project}/`)
  - Supports `api_sequence` trigger type with HTTP steps
  - Executes HTTP requests against the test server
  - Validates assertions:
    - `http_status` - validates response status code
    - `db_record` - queries SQLite directly
    - `llm_judge` - calls configured LLM for judgment
  - Reports PASS/FAIL for each scenario
- [ ] Support environment variable: `OTTO_SCENARIO_DIR` for custom scenario directory
- [ ] Command-line: `python3 harness/scenario_harness.py --project {project}`
- [ ] Exit code 0 on all PASS, non-zero on any FAIL
- [ ] Unit tests for harness core functionality

**Acceptance Criteria:**
- [ ] All 15 scenario YAML files in `scenarios/` execute successfully
- [ ] HTTP status assertions work correctly
- [ ] DB record assertions query SQLite correctly
- [ ] LLM judge assertions call configured model
- [ ] Exit code reflects overall test result

---

### Task 5.3: Create Integration Tests
**Files to create:** `tests/` directory
**Dependencies:** Tasks 1.1, 1.2, 1.3, 2.3, 3.1, 3.2, 3.3
**Priority:** P1

**Tasks:**
- [ ] Create `tests/test_chain_engine.py` - unit tests for chain computation
- [ ] Create `tests/test_parser.py` - unit tests for parsing
- [ ] Create `tests/test_voice_personalities.py` - unit tests for messages
- [ ] Create `tests/test_snooze.py` - unit tests for snooze flow
- [ ] Create `tests/test_stats.py` - unit tests for stats calculations
- [ ] Create `tests/test_integration.py` - integration tests
- [ ] Run test suite: `python3 -m pytest tests/`

---

## Task Dependency Graph

```
Phase 1 (Foundation)
├── Task 1.1: Database Schema & Migrations
│   └── → All other tasks depend on this
├── Task 1.2: Escalation Chain Engine
│   └── → Task 4.1 (background scheduling)
├── Task 1.3: LLM Adapter
    └── → Task 5.1 (refactor test_server)

Phase 2 (Voice & Message Generation)
├── Task 2.1: Voice Personality System
│   └── → Task 2.2 (TTS adapter)
└── Task 2.2: TTS Adapter
    └── → Task 2.3 (message generator)
    └── → Task 3.3 (notification manager)

Phase 3 (Interaction & State Management)
├── Task 3.1: Snooze & Dismissal
│   └── → Task 4.2 (calendar integration)
├── Task 3.2: History & Stats
└── Task 3.3: Notification Manager
    └── → Task 4.1 (background scheduling)

Phase 4 (External Integration)
├── Task 4.1: Background Scheduling
├── Task 4.2: Calendar Integration
├── Task 4.3: Location Awareness
└── Task 4.4: Sound Library

Phase 5 (Refactoring & Testing)
├── Task 5.1: Refactor test_server.py
│   └── depends on: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.2
├── Task 5.2: Create Scenario Harness
│   └── depends on: none (can be parallel)
└── Task 5.3: Integration Tests
    └── depends on: all above
```

---

## Acceptance Criteria Mapping

| Spec Section | Task(s) | Key Criteria |
|--------------|---------|--------------|
| 2. Escalation Chain | Task 1.2 | 8 anchors for ≥25 min, compression rules, validation |
| 3. Reminder Parsing | Task 1.3 | LLM adapter, mock, keyword fallback |
| 4. Voice & TTS | Task 2.2, 2.3 | TTS caching, fallback, zero runtime latency |
| 5. Notification | Task 3.3 | DND handling, quiet hours, T-0 loop |
| 6. Background | Task 4.1 | Notifee integration, recovery scan |
| 7. Calendar | Task 4.2 | Apple/Google adapters, suggestion cards |
| 8. Location | Task 4.3 | Single check, 500m geofence, immediate escalation |
| 9. Snooze | Task 3.1 | Tap/custom snooze, chain recompute, feedback |
| 10. Voice Personality | Task 2.1 | 3+ variations per tier, custom prompt |
| 11. History & Stats | Task 3.2 | Hit rate, feedback loop, streak, miss window |
| 12. Sound Library | Task 4.4 | Built-in sounds, import, fallback |
| 13. Data Persistence | Task 1.1 | Full schema, migrations, in-memory tests |

---

## Current File Structure

```
/
├── src/
│   ├── test_server.py          # Monolithic HTTP server (needs refactoring)
│   └── lib/                    # MISSING - all modules need to be created
│       ├── __init__.py
│       ├── db.py               # Task 1.1
│       ├── chain_engine.py     # Task 1.2
│       ├── voice_personalities.py  # Task 2.1
│       ├── message_generator.py     # Task 2.3
│       ├── snooze_manager.py        # Task 3.1
│       ├── stats.py                 # Task 3.2
│       ├── history.py                # Task 3.2
│       ├── notification_manager.py   # Task 3.3
│       ├── scheduler.py              # Task 4.1
│       ├── sound_library.py           # Task 4.4
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── llm_adapter.py        # Task 1.3
│       │   ├── minimax_adapter.py    # Task 1.3
│       │   ├── anthropic_adapter.py  # Task 1.3
│       │   ├── mock_llm_adapter.py   # Task 1.3
│       │   ├── tts_adapter.py        # Task 2.2
│       │   ├── elevenlabs_adapter.py # Task 2.2
│       │   ├── mock_tts_adapter.py   # Task 2.2
│       │   ├── calendar_adapter.py   # Task 4.2
│       │   ├── apple_calendar.py      # Task 4.2
│       │   ├── google_calendar.py    # Task 4.2
│       │   └── notifee_adapter.py    # Task 4.1
│       └── migrations/
│           ├── __init__.py
│           ├── base.py
│           ├── v001_initial_schema.py
│           └── v002_add_missing_tables.py
├── tests/                      # MISSING - Task 5.2
│   ├── __init__.py
│   ├── test_chain_engine.py
│   ├── test_parser.py
│   ├── test_voice_personalities.py
│   ├── test_snooze.py
│   ├── test_stats.py
│   └── test_integration.py
├── specs/
│   ├── urgent-voice-alarm-app-2026-04-08.md
│   └── urgent-voice-alarm-app-2026-04-08.spec.md
├── harness/
│   └── scenario_harness.py     # MISSING - Task 5.2
├── IMPLEMENTATION_PLAN.md       # This file
└── AGENTS.md
```

---

## Critical Gaps Summary

The following items are **MISSING** entirely and need to be created from scratch:

| Item | Priority | Status |
|------|----------|--------|
| `harness/scenario_harness.py` | P0 | MISSING - core test infrastructure |
| `src/lib/` directory & all modules | P1 | MISSING - all library code |
| `tests/` directory | P1 | MISSING - unit tests |
| Chain engine bug fixes | P1 | BUGS in compression logic |
| LLM adapter interface | P1 | MISSING - required for testability |
| TTS adapter interface | P2 | MISSING |
| Calendar adapters | P3 | MISSING |

---

## Implementation Notes

1. **Interface-First Design**: Create all adapter interfaces before implementations for testability.

2. **Deterministic Chain Computation**: Chain engine must be pure functions - same inputs always produce same outputs.

3. **Graceful Degradation**: Every external service (LLM, TTS, Calendar, Location) must have a fallback.

4. **SQLite Persistence**: All anchor state must be persisted so app crashes don't lose scheduling state.

5. **TTS Pre-Generation**: All voice clips generated at reminder creation, never at runtime.

6. **30-Second TTS Budget**: TTS generation for a single reminder must complete within 30 seconds.

7. **No Location History**: Location data is used once at departure trigger and discarded.
