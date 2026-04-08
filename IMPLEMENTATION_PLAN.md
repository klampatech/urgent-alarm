# Implementation Plan — Urgent Alarm

## Overview

This plan maps the detailed specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to implementation tasks. 

**Current Implementation Status:** `src/test_server.py` contains a proof-of-concept HTTP server with basic chain computation, keyword parsing, voice templates, and SQLite storage. It is **NOT production-ready** and is structured as a monolith.

**Gap Summary:** 15 major components defined in the spec. The entire modular architecture (`src/lib/`) does not exist. Only a basic test server exists. The scenario harness is also missing.

---

## Current Codebase State

### What Exists
- ✅ `src/test_server.py` - Monolithic proof-of-concept with:
  - Basic chain engine (`compute_escalation_chain()`)
  - Basic parser (`parse_reminder_natural()`)
  - Voice personality templates (`VOICE_PERSONALITIES`)
  - Basic SQLite schema (5 tables)
  - HTTP endpoints for testing
- ✅ `scenarios/*.yaml` - 15 validation scenario files
- ✅ `specs/*.md` - Full product and technical specification

### What's Missing (Critical)
- ❌ **Entire modular architecture** (`src/lib/`) does not exist
- ❌ **Scenario harness** (`harness/scenario_harness.py`) does not exist
- ❌ **No unit tests** (pytest or otherwise)
- ❌ **All spec components** are either PARTIAL or NOT STARTED

---

## Priority 0: Critical Path (Must Do First)

### P0.1 — Scenario Harness ⬅️ HIGHEST PRIORITY
**Spec Section:** Harness Validation  
**Status:** NOT STARTED (blocking all validation)

**Why Critical:** Cannot validate any implementation without the harness. All scenarios are defined but unrunnable.

**Tasks:**
1. Create `harness/scenario_harness.py` - main runner with argument parsing
2. Create `harness/parser.py` - YAML scenario loader
3. Create `harness/client.py` - HTTP client for API calls
4. Create `harness/assertions.py` - HTTP status, DB record, LLM judge assertions
5. Create `harness/__init__.py`
6. Add pytest integration
7. Test against existing scenarios

**Acceptance Criteria:**
- [ ] `python3 harness/scenario_harness.py --project urgent-alarm` runs against `scenarios/*.yaml`
- [ ] Scenario parser loads all 15 YAML files
- [ ] HTTP assertions work against `localhost:8090`
- [ ] DB record assertions query SQLite directly
- [ ] Results printed with PASS/FAIL per scenario

**Dependencies:** None  
**Tests:** Manual test run against existing scenarios

---

### P0.2 — Modular Architecture Foundation
**Spec Section:** Overall Structure  
**Status:** NOT STARTED (blocking all components)

**Why Critical:** The proof-of-concept is a monolith. All production code must be modular for testability, maintainability, and platform adaptation.

**Tasks:**
1. Create `src/lib/__init__.py` - package init
2. Create `src/lib/db/__init__.py` - database module
3. Create `src/lib/db/migrations.py` - versioned migration system
4. Create `src/lib/db/schema.py` - full spec-compliant schema with all columns
5. Create `src/lib/db/connection.py` - connection management with WAL mode
6. Create `src/lib/chain/__init__.py` - chain module
7. Create `src/lib/parser/__init__.py` - parser module
8. Create `src/lib/voice/__init__.py` - voice module
9. Create `src/lib/tts/__init__.py` - TTS module
10. Create `src/lib/scheduler/__init__.py` - scheduler module
11. Create `src/lib/notifications/__init__.py` - notifications module
12. Create `src/lib/calendar/__init__.py` - calendar module
13. Create `src/lib/location/__init__.py` - location module
14. Create `src/lib/snooze/__init__.py` - snooze module
15. Create `src/lib/stats/__init__.py` - stats module
16. Create `src/lib/sounds/__init__.py` - sounds module

**Dependencies:** P0.1 (harness needed to validate)  
**Tests:** All imports succeed, no circular dependencies

---

## Priority 1: Core Engine (Foundation)

### 1.1 — Database Schema & Migrations ⬅️ DO FIRST
**Spec Section:** 13  
**Status:** PARTIAL (basic schema in `test_server.py`)

**What's Done:**
- ✅ Basic 5-table schema in `init_db()`
- ✅ CASCADE delete on reminders → anchors
- ✅ UUID generation for IDs

**What's Missing:**
- [ ] **Schema columns missing from `reminders`:** `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`, `updated_at`
- [ ] **Schema columns missing from `anchors`:** `snoozed_to`, `tts_fallback`
- [ ] **Schema columns missing from `history`:** `actual_arrival`, `missed_reason`
- [ ] **Missing tables:** `custom_sounds`, `calendar_sync`
- [ ] **Missing:** Migration system with versioned sequential migrations
- [ ] **Missing:** `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] **Missing:** In-memory test database support
- [ ] **Missing:** Indexes on frequently queried columns

**Tasks:**
1. Create `src/lib/db/schema.py` with full spec-compliant schema
2. Create `src/lib/db/migrations.py` with sequential migration runner
3. Add `src/lib/db/connection.py` with PRAGMA configuration
4. Add migration tests

**Dependencies:** P0.2  
**Tests:** `tests/test_migrations.py`

---

### 1.2 — Escalation Chain Engine
**Spec Section:** 2  
**Status:** PARTIAL (basic `compute_escalation_chain()` in test_server.py)

**What's Done:**
- ✅ Full 8-anchor chain for ≥25 min buffer
- ✅ Compressed chains for 10-24, 5-9, ≤5 min buffers
- ✅ `validate_chain()` function

**What's Missing:**
- [ ] **Move to modular structure:** `src/lib/chain/engine.py`
- [ ] **Missing:** `get_next_unfired_anchor(reminder_id)` function
- [ ] **Missing:** Anchor re-computation after snooze
- [ ] **Bug:** Validation doesn't check `drive_duration` can't exceed time_to_arrival
- [ ] **Missing:** Chain determinism verification
- [ ] **Missing:** Proper error handling for edge cases

**Tasks:**
1. Create `src/lib/chain/engine.py` - refactored from test_server.py
2. Add `get_next_unfired_anchor(reminder_id, db)` function
3. Add `recompute_chain_after_snooze(reminder_id, snooze_minutes, db)` function
4. Fix validation: drive_duration cannot exceed time between now and arrival
5. Add comprehensive tests for all 6 test scenarios

**Dependencies:** 1.1  
**Tests:** `tests/test_chain_engine.py`

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

**Tasks:**
1. Create `src/lib/parser/adapters/base.py` - `ILanguageModelAdapter` interface
2. Create `src/lib/parser/adapters/keyword_extractor.py` - enhanced regex
3. Create `src/lib/parser/adapters/llm_adapter.py` - MiniMax API
4. Create `src/lib/parser/mock_adapter.py` - for tests
5. Create `src/lib/parser/parser.py` - unified entry point
6. Write tests for all 7 scenarios

**Dependencies:** 1.1  
**Tests:** `tests/test_parser.py`

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
- [ ] **Missing:** ElevenLabs voice ID mapping

**Tasks:**
1. Create `src/lib/voice/personalities.py` - full personality definitions
2. Add 2+ message variations per tier per personality
3. Create `src/lib/voice/message_generator.py` - variation rotation
4. Create `src/lib/voice/custom_personalities.py` - user prompt support
5. Write tests for TC-01 through TC-05

**Dependencies:** None  
**Tests:** `tests/test_voice_personalities.py`

---

### 2.3 — TTS Generation (ElevenLabs Adapter)
**Spec Section:** 4  
**Status:** NOT STARTED (message generation only in test_server.py)

**What's Missing:**
- [ ] **Missing:** `ITTSAdapter` interface
- [ ] **Missing:** ElevenLabs API adapter
- [ ] **Missing:** Mock adapter for tests
- [ ] **Missing:** TTS cache directory structure
- [ ] **Missing:** Pre-generation at reminder creation
- [ ] **Missing:** Fallback to system notification sound
- [ ] **Missing:** Cache invalidation on delete
- [ ] **Missing:** 30-second generation timeout

**Tasks:**
1. Create `src/lib/tts/adapters/base.py` - `ITTSAdapter` interface
2. Create `src/lib/tts/adapters/elevenlabs_adapter.py`
3. Create `src/lib/tts/mock_adapter.py` - for tests
4. Create `src/lib/tts/generator.py` - pre-generation
5. Create `src/lib/tts/cache_manager.py` - file management
6. Implement fallback mechanism
7. Write tests for TC-01 through TC-05

**Dependencies:** 1.2, 2.2  
**Tests:** `tests/test_tts.py`

---

## Priority 3: Platform Integration

### 3.1 — Background Scheduling (Notifee)
**Spec Section:** 6  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/scheduler/adapters/base.py` - `ISchedulerAdapter` interface
2. Create `src/lib/scheduler/adapters/notifee_adapter.py`
3. Create `src/lib/scheduler/adapters/mock_adapter.py`
4. Create `src/lib/scheduler/recovery.py` - recovery_scan()
5. Create `src/lib/scheduler/registration.py` - re_register_pending_anchors()
6. Write tests for TC-01 through TC-06

**Dependencies:** 1.2, 1.1  
**Tests:** `tests/test_scheduler.py`

---

### 3.2 — Notification & Alarm Behavior
**Spec Section:** 5  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/notifications/sound_tier.py` - tier → sound mapping
2. Create `src/lib/notifications/manager.py` - DND/quiet hours handling
3. Create `src/lib/notifications/queue.py` - chain overlap serialization
4. Create `src/lib/notifications/alarm.py` - T-0 looping
5. Write tests for TC-01 through TC-06

**Dependencies:** 3.1  
**Tests:** `tests/test_notifications.py`

---

### 3.3 — Calendar Integration
**Spec Section:** 7  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/calendar/adapters/base.py` - `ICalendarAdapter` interface
2. Create `src/lib/calendar/adapters/apple_calendar_adapter.py`
3. Create `src/lib/calendar/adapters/google_calendar_adapter.py`
4. Create `src/lib/calendar/sync_manager.py`
5. Write tests for TC-01 through TC-06

**Dependencies:** 1.1  
**Tests:** `tests/test_calendar.py`

---

### 3.4 — Location Awareness
**Spec Section:** 8  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/location/adapters/ios_adapter.py`
2. Create `src/lib/location/adapters/android_adapter.py`
3. Create `src/lib/location/manager.py` - single-check logic
4. Write tests for TC-01 through TC-05

**Dependencies:** 3.1  
**Tests:** `tests/test_location.py`

---

## Priority 4: User Interaction

### 4.1 — Snooze & Dismissal Flow
**Spec Section:** 9  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/snooze/handlers.py` - tap/tap-and-hold logic
2. Create `src/lib/snooze/recomputation.py` - chain shifting
3. Create `src/lib/snooze/feedback.py` - dismissal prompts
4. Create `src/lib/snooze/persistence.py` - restart recovery
5. Write tests for TC-01 through TC-06

**Dependencies:** 3.1, 2.2, 2.3  
**Tests:** `tests/test_snooze.py`

---

### 4.2 — History, Stats & Feedback Loop
**Spec Section:** 11  
**Status:** PARTIAL (basic hit rate in test_server.py)

**What's Done:**
- ✅ `calculate_hit_rate()` function
- ✅ Basic `destination_adjustments` updates

**What's Missing:**
- [ ] **Missing:** Streak counter
- [ ] **Missing:** Common miss window identification
- [ ] **Missing:** `actual_arrival` tracking
- [ ] **Missing:** 90-day retention policy
- [ ] **Missing:** Adjustment formula with +15 min cap

**Tasks:**
1. Create `src/lib/stats/calculator.py` - hit rate, streaks, miss window
2. Create `src/lib/stats/feedback_loop.py` - adjustment formula
3. Create `src/lib/stats/history_manager.py` - 90-day retention
4. Write tests for TC-01 through TC-07

**Dependencies:** 1.1  
**Tests:** `tests/test_stats.py`

---

### 4.3 — Sound Library
**Spec Section:** 12  
**Status:** NOT STARTED

**Tasks:**
1. Create `src/lib/sounds/builtins.py` - bundled audio references
2. Create `src/lib/sounds/importer.py` - format validation
3. Create `src/lib/sounds/manager.py` - selection and fallback
4. Write tests for TC-01 through TC-05

**Dependencies:** 1.1  
**Tests:** `tests/test_sounds.py`

---

## Priority 5: Integration & Testing

### 5.1 — React Native App Structure
**Status:** NOT STARTED

**Tasks:**
1. Create `src/App.tsx` - React Native entry point
2. Create `src/screens/QuickAddScreen.tsx`
3. Create `src/screens/RemindersListScreen.tsx`
4. Create `src/screens/HistoryScreen.tsx`
5. Create `src/screens/SettingsScreen.tsx`
6. Create `src/lib/react-native/` adapters for platform APIs

**Dependencies:** Phases 1-4 complete  
**Tests:** E2E smoke tests

---

## Implementation Order Summary

```
Priority 0: Critical Path
├── P0.1 Scenario Harness ← HIGHEST (unblock validation)
└── P0.2 Modular Architecture Foundation

Priority 1: Core Engine
├── 1.1 Database Schema & Migrations
└── 1.2 Escalation Chain Engine

Priority 2: User Input & AI
├── 2.1 Reminder Parser
├── 2.2 Voice Personality System
└── 2.3 TTS Generation

Priority 3: Platform Integration
├── 3.1 Background Scheduling
├── 3.2 Notification & Alarm Behavior
├── 3.3 Calendar Integration
└── 3.4 Location Awareness

Priority 4: User Interaction
├── 4.1 Snooze & Dismissal Flow
├── 4.2 History, Stats & Feedback Loop
└── 4.3 Sound Library

Priority 5: Integration
└── 5.1 React Native App Structure
```

---

## Current Gaps Summary

| Component | Status | Test Scenarios |
|-----------|--------|----------------|
| P0.1 Scenario Harness | NOT STARTED | 0/15 (blocking) |
| P0.2 Modular Architecture | NOT STARTED | 0 |
| 1.1 Database & Migrations | PARTIAL | 0/5 |
| 1.2 Chain Engine | PARTIAL | 2/6 |
| 2.1 Reminder Parser | PARTIAL | 1/7 |
| 2.2 Voice Personality | PARTIAL | 0/5 |
| 2.3 TTS Generation | NOT STARTED | 0/5 |
| 3.1 Background Scheduling | NOT STARTED | 0/6 |
| 3.2 Notifications | NOT STARTED | 0/6 |
| 3.3 Calendar | NOT STARTED | 0/6 |
| 3.4 Location | NOT STARTED | 0/5 |
| 4.1 Snooze & Dismissal | NOT STARTED | 0/6 |
| 4.2 Stats & Feedback | PARTIAL | 2/7 |
| 4.3 Sound Library | NOT STARTED | 0/5 |
| 5.1 React Native App | NOT STARTED | 0 |

**Total:** ~5% implementation complete (3 partial, 11 not started)

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No harness = can't validate | Critical | Implement P0.1 first |
| Modular structure missing | High | Implement P0.2 early |
| ElevenLabs API rate limits | Medium | Mock adapter + fallback |
| Background task killed by OS | Medium | Recovery scan + 15-min grace |
| LLM parsing failure | Medium | Keyword fallback with confidence |

---

## Success Criteria

- [ ] Scenario harness runs all 15 scenarios and reports PASS/FAIL
- [ ] Modular architecture in `src/lib/` with all modules implemented
- [ ] All 42 acceptance criteria from spec sections 2-13 have passing tests
- [ ] Chain engine produces correct anchors for all buffer sizes
- [ ] LLM adapter is fully mock-able for CI
- [ ] TTS caching eliminates runtime API calls
- [ ] Background scheduling survives app termination
- [ ] Recovery scan handles overdue anchors correctly
- [ ] Feedback loop adjusts drive duration with +15 min cap
- [ ] DND/quiet hours suppress early anchors correctly
- [ ] Snooze re-computation shifts all remaining anchors
