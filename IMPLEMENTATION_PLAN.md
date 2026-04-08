# Implementation Plan — Urgent Alarm

## Overview

This plan maps the detailed specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to implementation tasks, prioritizing based on dependencies and blocking relationships.

**Current Implementation Status:** `src/test_server.py` contains a proof-of-concept HTTP server with basic chain computation, keyword parsing, voice templates, and SQLite storage. The harness directory is empty. The modular architecture (`src/lib/`) does not exist.

---

## Gap Analysis Summary

| Component | Status | Coverage | Key Gaps |
|-----------|--------|----------|----------|
| Chain Engine | PARTIAL | ~65% | Missing `get_next_unfired_anchor()`, snooze recompute, validation bug |
| Reminder Parser | PARTIAL | ~40% | Missing LLM adapter, mock adapter, enhanced keyword extraction |
| Voice Personality | PARTIAL | ~50% | Missing message variations (3+ per tier), custom prompt support |
| TTS Generation | NOT STARTED | ~10% | Text generation only, no audio/file caching |
| Background Scheduling | NOT STARTED | 0% | Full implementation needed |
| Notifications | NOT STARTED | 0% | Full implementation needed |
| Calendar Integration | NOT STARTED | 0% | Full implementation needed |
| Location Awareness | NOT STARTED | 0% | Full implementation needed |
| Snooze & Dismissal | NOT STARTED | 0% | Full implementation needed |
| Stats & Feedback | PARTIAL | ~40% | Missing streak counter, miss window, cap enforcement |
| Sound Library | NOT STARTED | 0% | Full implementation needed |
| Database Schema | PARTIAL | ~60% | Missing columns, no migration system |
| Scenario Harness | NOT STARTED | 0% | Empty harness directory |

**Estimated Total Completion:** ~5-8%

---

## Verified Bugs in Current Implementation

1. **3-min buffer produces 2 anchors instead of 3** — Current: firm + alarm. Spec requires: firm + critical + alarm (TC-03)
2. **120-min validation passes** — Should fail with "drive_duration exceeds time_to_arrival" (TC-04)

---

## Priority 0: Critical Path (Must Do First)

### P0.1 — Scenario Harness ⬅️ HIGHEST PRIORITY
**Spec Section:** Harness Validation  
**Status:** NOT STARTED (blocking all validation)

**Why Critical:** Cannot validate any implementation without the harness. All 16 scenarios are defined but unrunnable.

**Files to Create:**
```
harness/
├── __init__.py
├── scenario_harness.py      # Main runner with --project argument
├── parser.py                # YAML scenario loader
├── client.py                # HTTP client for API calls
├── assertions.py            # http_status, db_record, llm_judge assertions
└── README.md
```

**Task Details:**

1. **`scenario_harness.py`** — Main entry point
   - Parse `--project` argument
   - Load scenarios from `scenarios/*.yaml` (or `/var/otto-scenarios/{project}/`)
   - For each scenario: execute trigger steps, run assertions, report PASS/FAIL
   - Support `sudo` for system scenario path
   - Handle `OTTO_SCENARIO_DIR` environment variable

2. **`parser.py`** — YAML loader
   - Load all `.yaml` files from configured directory
   - Parse `trigger.steps[]` for API sequences
   - Parse `assertions[]` for validation checks
   - Support `${variable}` substitution from `env` block

3. **`client.py`** — HTTP client
   - `POST /reminders`, `POST /parse`, `POST /voice/message`
   - `POST /history`, `POST /anchors/fire`
   - `GET /chain`, `GET /reminders`, `GET /stats/hit-rate`, `GET /health`

4. **`assertions.py`** — Validation assertions
   - `HTTPStatusAssertion` — verify response code matches expected
   - `DBRecordAssertion` — query SQLite directly at `/tmp/urgent-alarm.db`
   - `LLMJudgeAssertion` — call LLM to evaluate scenario success

**Acceptance Criteria:**
- [ ] `python3 harness/scenario_harness.py --project otto-matic` runs against `scenarios/*.yaml`
- [ ] Scenario parser loads all 16 YAML files
- [ ] HTTP assertions work against `localhost:8090`
- [ ] DB record assertions query SQLite directly
- [ ] Results printed with PASS/FAIL per scenario with details

**Dependencies:** None  
**Validation:** `python3 src/test_server.py &` then `sudo python3 harness/scenario_harness.py --project otto-matic`

---

### P0.2 — Modular Architecture Foundation
**Spec Section:** Overall Structure  
**Status:** NOT STARTED (blocking all production components)

**Why Critical:** The proof-of-concept is a monolith. All production code must be modular for testability, maintainability, and platform adaptation (React Native + Python backend).

**Directory Structure to Create:**
```
src/lib/
├── __init__.py
├── db/
│   ├── __init__.py
│   ├── connection.py          # Connection management, PRAGMA settings
│   ├── schema.py              # Full spec-compliant schema
│   └── migrations.py          # Versioned migration runner
├── chain/
│   ├── __init__.py
│   └── engine.py              # Escalation chain computation
├── parser/
│   ├── __init__.py
│   ├── parser.py              # Unified entry point
│   └── adapters/
│       ├── __init__.py
│       ├── base.py            # ILanguageModelAdapter interface
│       ├── keyword_extractor.py
│       ├── llm_adapter.py      # MiniMax API
│       └── mock_adapter.py    # For tests
├── voice/
│   ├── __init__.py
│   ├── personalities.py       # 5 built-in + custom
│   ├── message_generator.py   # Variation rotation
│   └── custom_personalities.py
├── tts/
│   ├── __init__.py
│   ├── generator.py           # Pre-generation logic
│   ├── cache_manager.py       # File management
│   └── adapters/
│       ├── __init__.py
│       ├── base.py            # ITTSAdapter interface
│       ├── elevenlabs_adapter.py
│       └── mock_adapter.py
├── scheduler/
│   ├── __init__.py
│   ├── registration.py        # Anchor registration
│   ├── recovery.py            # Recovery scan
│   └── adapters/
│       ├── __init__.py
│       ├── base.py            # ISchedulerAdapter interface
│       ├── notifee_adapter.py
│       └── mock_adapter.py
├── notifications/
│   ├── __init__.py
│   ├── manager.py             # DND, quiet hours, queue
│   ├── sound_tier.py         # Tier → sound mapping
│   └── alarm.py               # T-0 looping
├── calendar/
│   ├── __init__.py
│   ├── sync_manager.py
│   └── adapters/
│       ├── __init__.py
│       ├── base.py            # ICalendarAdapter interface
│       ├── apple_calendar_adapter.py
│       └── google_calendar_adapter.py
├── location/
│   ├── __init__.py
│   └── manager.py             # Single-check logic
├── snooze/
│   ├── __init__.py
│   ├── handlers.py            # Tap/tap-and-hold
│   ├── recomputation.py       # Chain shifting
│   ├── feedback.py            # Dismissal prompts
│   └── persistence.py
├── stats/
│   ├── __init__.py
│   ├── calculator.py          # Hit rate, streaks, miss window
│   ├── feedback_loop.py       # Adjustment formula
│   └── history_manager.py     # 90-day retention
└── sounds/
    ├── __init__.py
    ├── builtins.py            # Bundled audio references
    ├── importer.py            # Format validation
    └── manager.py             # Selection and fallback
```

**Dependencies:** P0.1 (harness needed to validate)  
**Validation:** `python3 -c "from src.lib import *"` — all imports succeed

---

## Priority 1: Core Engine (Foundation)

### 1.1 — Database Schema & Migrations
**Spec Section:** 13  
**Status:** PARTIAL (basic schema in test_server.py)

**What's Done:**
- ✅ Basic 5-table schema (`reminders`, `anchors`, `history`, `destination_adjustments`, `user_preferences`)
- ✅ CASCADE delete on reminders → anchors
- ✅ UUID generation for IDs

**What's Missing:**
- [ ] **Missing columns from `reminders`:** `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`, `updated_at`
- [ ] **Missing columns from `anchors`:** `snoozed_to`, `tts_fallback`
- [ ] **Missing columns from `history`:** `actual_arrival`, `missed_reason`
- [ ] **Missing tables:** `custom_sounds`, `calendar_sync`
- [ ] **Missing:** Migration system with sequential versioned migrations
- [ ] **Missing:** `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] **Missing:** In-memory test database support (`?mode=memory`)
- [ ] **Missing:** Indexes on frequently queried columns

**Tasks:**
1. Create `src/lib/db/schema.py` with complete spec-compliant schema
2. Create `src/lib/db/migrations.py` with migration runner
3. Create `src/lib/db/connection.py` with PRAGMA configuration
4. Write migration tests for all schema changes

**Dependencies:** P0.2  
**Tests:** `tests/test_migrations.py` — TC-01 through TC-05

---

### 1.2 — Escalation Chain Engine
**Spec Section:** 2  
**Status:** PARTIAL (basic `compute_escalation_chain()` in test_server.py)

**What's Done:**
- ✅ Full 8-anchor chain for ≥25 min buffer
- ✅ Compressed chains for 10-24, 5-9, ≤5 min buffers
- ✅ `validate_chain()` function

**What's Missing / Bugs:**
- [ ] **BUG:** 3-min buffer produces 2 anchors but spec requires 3 (firm + critical + alarm)
- [ ] **BUG:** 120-min validation passes but should fail with "drive_duration exceeds time_to_arrival"
- [ ] **Missing:** `get_next_unfired_anchor(reminder_id, db)` function
- [ ] **Missing:** `recompute_chain_after_snooze(reminder_id, snooze_minutes, db)` function
- [ ] **Missing:** Chain determinism verification
- [ ] **Move to modular:** `src/lib/chain/engine.py`

**Tasks:**
1. Create `src/lib/chain/engine.py` — refactor from test_server.py
2. Fix 3-min buffer: should produce firm + critical + alarm (not just firm + alarm)
3. Fix validation: drive_duration > time_to_arrival → reject
4. Add `get_next_unfired_anchor(reminder_id, db)` — returns earliest unfired anchor
5. Add `recompute_chain_after_snooze(reminder_id, snooze_minutes, db)` — shift remaining anchors
6. Write comprehensive tests for all 6 test scenarios

**Dependencies:** P0.2, 1.1  
**Tests:** `tests/test_chain_engine.py` — TC-01 through TC-06

---

## Priority 2: User Input & AI Integration

### 2.1 — Reminder Parser (LLM + Keyword Fallback)
**Spec Section:** 3  
**Status:** PARTIAL (basic regex in test_server.py)

**What's Done:**
- ✅ Keyword extraction for destination, duration, arrival time
- ✅ Relative time parsing ("in 3 min")
- ✅ Tomorrow date resolution
- ✅ Confidence score calculation

**What's Missing:**
- [ ] **Missing:** `ILanguageModelAdapter` interface
- [ ] **Missing:** Mock adapter for tests
- [ ] **Missing:** LLM adapter for MiniMax/Anthropic API
- [ ] **Missing:** Enhanced keyword extraction (handle "Parker Dr 9am" without "to")
- [ ] **Missing:** Unintelligible input rejection ("blah blah")
- [ ] **Missing:** Confirmation card data structure
- [ ] **Bug:** Simple countdown ("dryer in 3 min") sets `drive_duration=0` but `arrival_time` needs calculation

**Tasks:**
1. Create `src/lib/parser/adapters/base.py` — `ILanguageModelAdapter` interface
2. Create `src/lib/parser/adapters/keyword_extractor.py` — enhanced regex
3. Create `src/lib/parser/adapters/llm_adapter.py` — MiniMax API
4. Create `src/lib/parser/adapters/mock_adapter.py` — predefined fixture responses
5. Create `src/lib/parser/parser.py` — unified entry point
6. Write tests for all 7 scenarios

**Dependencies:** 1.1  
**Tests:** `tests/test_parser.py` — TC-01 through TC-07

---

### 2.2 — Voice Personality System
**Spec Section:** 10  
**Status:** PARTIAL (basic templates in test_server.py)

**What's Done:**
- ✅ 5 personality templates
- ✅ Message template per urgency tier

**What's Missing:**
- [ ] **Missing:** Message variations (3+ per tier per personality)
- [ ] **Missing:** `CustomPersonality` class with user prompt support
- [ ] **Missing:** `MessageGenerator` class with variation rotation
- [ ] **Missing:** ElevenLabs voice ID mapping per personality
- [ ] **Missing:** Message determinism (same inputs → same outputs for testing)

**Tasks:**
1. Create `src/lib/voice/personalities.py` — complete personality definitions with voice IDs
2. Add 3 message variations per tier per personality
3. Create `src/lib/voice/message_generator.py` — variation rotation with deterministic seed
4. Create `src/lib/voice/custom_personalities.py` — user prompt support (max 200 chars)
5. Write tests for TC-01 through TC-05

**Dependencies:** P0.2 (can parallelize with 1.x)  
**Tests:** `tests/test_voice_personalities.py` — TC-01 through TC-05

---

### 2.3 — TTS Generation (ElevenLabs Adapter)
**Spec Section:** 4  
**Status:** NOT STARTED (message generation only in test_server.py)

**What's Done:**
- ✅ Voice message text generation
- ✅ `generate_voice_message()` function

**What's Missing:**
- [ ] **Missing:** `ITTSAdapter` interface
- [ ] **Missing:** ElevenLabs API adapter with voice settings
- [ ] **Missing:** Mock adapter for tests
- [ ] **Missing:** TTS cache directory structure (`/tts_cache/{reminder_id}/`)
- [ ] **Missing:** Pre-generation at reminder creation
- [ ] **Missing:** Fallback to system notification sound
- [ ] **Missing:** Cache invalidation on reminder delete
- [ ] **Missing:** 30-second generation timeout with async polling

**Tasks:**
1. Create `src/lib/tts/adapters/base.py` — `ITTSAdapter` interface
2. Create `src/lib/tts/adapters/elevenlabs_adapter.py` — ElevenLabs API
3. Create `src/lib/tts/adapters/mock_adapter.py` — writes silent file for tests
4. Create `src/lib/tts/generator.py` — pre-generation for all anchors
5. Create `src/lib/tts/cache_manager.py` — file management, cleanup on delete
6. Implement fallback mechanism (system sound + notification text)
7. Write tests for TC-01 through TC-05

**Dependencies:** 1.2, 2.2  
**Tests:** `tests/test_tts.py` — TC-01 through TC-05

---

## Priority 3: Platform Integration

### 3.1 — Background Scheduling (Notifee)
**Spec Section:** 6  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/scheduler/adapters/base.py` — `ISchedulerAdapter` interface
2. Create `src/lib/scheduler/adapters/notifee_adapter.py` — Notifee implementation
3. Create `src/lib/scheduler/adapters/mock_adapter.py` — for tests
4. Create `src/lib/scheduler/registration.py` — register anchors with Notifee
5. Create `src/lib/scheduler/recovery.py` — `recovery_scan()` on app launch
6. Implement 15-minute grace window for overdue anchors
7. Write tests for TC-01 through TC-06

**Dependencies:** 1.2, 1.1  
**Tests:** `tests/test_scheduler.py` — TC-01 through TC-06

---

### 3.2 — Notification & Alarm Behavior
**Spec Section:** 5  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/notifications/sound_tier.py` — tier → sound mapping
2. Create `src/lib/notifications/manager.py` — DND/quiet hours handling
3. Create `src/lib/notifications/queue.py` — chain overlap serialization
4. Create `src/lib/notifications/alarm.py` — T-0 looping until action
5. Write tests for TC-01 through TC-06

**Dependencies:** 3.1  
**Tests:** `tests/test_notifications.py` — TC-01 through TC-06

---

### 3.3 — Calendar Integration
**Spec Section:** 7  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/calendar/adapters/base.py` — `ICalendarAdapter` interface
2. Create `src/lib/calendar/adapters/apple_calendar_adapter.py` — EventKit
3. Create `src/lib/calendar/adapters/google_calendar_adapter.py` — Google Calendar API
4. Create `src/lib/calendar/sync_manager.py` — sync on launch, every 15 min
5. Implement suggestion cards for events with locations
6. Write tests for TC-01 through TC-06

**Dependencies:** 1.1  
**Tests:** `tests/test_calendar.py` — TC-01 through TC-06

---

### 3.4 — Location Awareness
**Spec Section:** 8  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/location/adapters/ios_adapter.py` — CoreLocation
2. Create `src/lib/location/adapters/android_adapter.py` — FusedLocationProvider
3. Create `src/lib/location/manager.py` — single-check at departure anchor
4. Implement 500m geofence comparison
5. Immediate escalation if user still at origin at departure time
6. Write tests for TC-01 through TC-05

**Dependencies:** 3.1  
**Tests:** `tests/test_location.py` — TC-01 through TC-05

---

## Priority 4: User Interaction

### 4.1 — Snooze & Dismissal Flow
**Spec Section:** 9  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/snooze/handlers.py` — tap (1 min) / tap-and-hold (custom)
2. Create `src/lib/snooze/recomputation.py` — chain shifting after snooze
3. Create `src/lib/snooze/feedback.py` — dismissal prompts, "timing right?" flow
4. Create `src/lib/snooze/persistence.py` — restart recovery with snooze offsets
5. Write tests for TC-01 through TC-06

**Dependencies:** 3.1, 2.2, 2.3  
**Tests:** `tests/test_snooze.py` — TC-01 through TC-06

---

### 4.2 — History, Stats & Feedback Loop
**Spec Section:** 11  
**Status:** PARTIAL (basic hit rate in test_server.py)

**What's Done:**
- ✅ `calculate_hit_rate()` function
- ✅ Basic `destination_adjustments` updates

**What's Missing:**
- [ ] **Missing:** Streak counter for recurring reminders
- [ ] **Missing:** Common miss window identification
- [ ] **Missing:** `actual_arrival` tracking
- [ ] **Missing:** 90-day retention policy with archive
- [ ] **Missing:** Adjustment formula with +15 min cap
- [ ] **Missing:** Stats derived entirely from history table (no separate stats table)

**Tasks:**
1. Create `src/lib/stats/calculator.py` — hit rate, streaks, miss window
2. Create `src/lib/stats/feedback_loop.py` — adjustment formula with cap
3. Create `src/lib/stats/history_manager.py` — 90-day retention
4. Write tests for TC-01 through TC-07

**Dependencies:** 1.1  
**Tests:** `tests/test_stats.py` — TC-01 through TC-07

---

### 4.3 — Sound Library
**Spec Section:** 12  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/sounds/builtins.py` — bundled audio references
2. Create `src/lib/sounds/importer.py` — format validation (MP3, WAV, M4A), max 30 sec
3. Create `src/lib/sounds/manager.py` — selection and fallback
4. Write tests for TC-01 through TC-05

**Dependencies:** 1.1  
**Tests:** `tests/test_sounds.py` — TC-01 through TC-05

---

## Implementation Order Summary

```
Priority 0: Critical Path
├── P0.1 Scenario Harness ← HIGHEST (unblock all validation)
└── P0.2 Modular Architecture Foundation

Priority 1: Core Engine
├── 1.1 Database Schema & Migrations
└── 1.2 Escalation Chain Engine (fix bugs: 3-min buffer, validation)

Priority 2: User Input & AI
├── 2.1 Reminder Parser (can parallelize with 1.x)
├── 2.2 Voice Personality System (can parallelize)
└── 2.3 TTS Generation (depends on 1.2, 2.2)

Priority 3: Platform Integration
├── 3.1 Background Scheduling (depends on 1.2)
├── 3.2 Notification & Alarm (depends on 3.1)
├── 3.3 Calendar Integration (depends on 1.1)
└── 3.4 Location Awareness (depends on 3.1)

Priority 4: User Interaction
├── 4.1 Snooze & Dismissal (depends on 3.1, 2.2, 2.3)
├── 4.2 Stats & Feedback (depends on 1.1)
└── 4.3 Sound Library (depends on 1.1)
```

---

## Current Gaps Detail

| Component | Status | Test Scenarios | Notes |
|-----------|--------|----------------|-------|
| P0.1 Scenario Harness | NOT STARTED | 0/16 | BLOCKING — cannot validate anything |
| P0.2 Modular Architecture | NOT STARTED | 0 | `src/lib/` does not exist |
| 1.1 Database & Migrations | PARTIAL | 0/5 | Missing columns, no migration system |
| 1.2 Chain Engine | PARTIAL | 2/6 | **BUGS:** 3-min → 2 anchors (need 3), 120-min validation passes (should fail) |
| 2.1 Reminder Parser | PARTIAL | 1/7 | Missing LLM adapter, mock adapter |
| 2.2 Voice Personality | PARTIAL | 0/5 | Missing message variations, custom prompt support |
| 2.3 TTS Generation | NOT STARTED | 0/5 | Text generation only, no audio generation |
| 3.1 Background Scheduling | NOT STARTED | 0/6 | Full implementation needed |
| 3.2 Notifications | NOT STARTED | 0/6 | Full implementation needed |
| 3.3 Calendar | NOT STARTED | 0/6 | Full implementation needed |
| 3.4 Location | NOT STARTED | 0/5 | Full implementation needed |
| 4.1 Snooze & Dismissal | NOT STARTED | 0/6 | Full implementation needed |
| 4.2 Stats & Feedback | PARTIAL | 2/7 | Missing streaks, miss window, cap |
| 4.3 Sound Library | NOT STARTED | 0/5 | Full implementation needed |

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No harness = can't validate | Critical | Implement P0.1 first |
| Modular structure missing | High | Implement P0.2 early |
| Chain engine bugs | High | Fix in 1.2 - 3-min buffer, validation |
| ElevenLabs API rate limits | Medium | Mock adapter + fallback |
| Background task killed by OS | Medium | Recovery scan + 15-min grace |
| LLM parsing failure | Medium | Keyword fallback with confidence |
| TTS generation timeout | Medium | Async polling + fallback to system sound |

---

## Success Criteria

- [ ] Scenario harness runs all 16 scenarios and reports PASS/FAIL per scenario
- [ ] Modular architecture in `src/lib/` with all modules implemented
- [ ] Chain engine produces correct anchors for all buffer sizes (TC-01 through TC-06)
- [ ] **FIXED:** 3-min buffer produces exactly 3 anchors: firm, critical, alarm
- [ ] **FIXED:** 120-min validation rejects with "drive_duration exceeds time_to_arrival"
- [ ] LLM adapter is fully mock-able for CI
- [ ] TTS caching eliminates runtime API calls
- [ ] Background scheduling survives app termination
- [ ] Recovery scan handles overdue anchors correctly (15-min grace window)
- [ ] Feedback loop adjusts drive duration with +15 min cap
- [ ] DND/quiet hours suppress early anchors correctly
- [ ] Snooze re-computation shifts all remaining anchors
- [ ] Hit rate calculation: `hits / (hits + misses) * 100` for trailing 7 days
- [ ] Database uses WAL mode and foreign key enforcement
- [ ] All timestamps stored in ISO 8601 format (UTC internally)

---

## Validation Commands

After implementing, run these to get immediate feedback:

```bash
# Lint (Python syntax check)
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Start the demo server
python3 src/test_server.py &

# Run harness against scenarios
sudo python3 harness/scenario_harness.py --project otto-matic

# Or test with local scenarios
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project otto-matic

# Run pytest if tests exist
python3 -m pytest harness/
```
