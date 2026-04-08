# Implementation Plan — Urgent Alarm

## Overview

This plan maps the detailed specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to implementation tasks. 

**Current Implementation Status:** `src/test_server.py` contains a proof-of-concept server with basic chain computation, keyword parsing, voice templates, and HTTP endpoints for harness testing. It is NOT production-ready.

**Gap Summary:** 12 major components defined in the spec. Core logic (chain engine, parser) partially implemented as a monolith. Missing: modular architecture, LLM adapter, TTS integration, background scheduling, platform APIs, snooze/dismissal flow, sound library, and tests.

---

## Phase 1: Foundation (Data & Core Engine)

### 1.1 — Database Schema & Migrations ⬅️ DO FIRST
**Spec Section:** 13  
**Status:** PARTIAL (basic schema in `init_db()`)

**What's Done:**
- ✅ Basic 5-table schema (reminders, anchors, history, destination_adjustments, user_preferences)
- ✅ CASCADE delete on reminders → anchors
- ✅ UUID generation for IDs

**What's Missing:**
- [ ] **Schema columns missing from `reminders`:** `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`, `updated_at`
- [ ] **Schema columns missing from `anchors`:** `snoozed_to`, `tts_fallback`
- [ ] **Schema columns missing from `history`:** `actual_arrival`, `missed_reason`
- [ ] **Missing tables:** `custom_sounds`, `calendar_sync`
- [ ] **Missing:** Migration system with versioned sequential migrations
- [ ] **Missing:** `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL` configuration
- [ ] **Missing:** In-memory test database support (`Database.getInMemoryInstance()`)
- [ ] **Missing:** Indexes on frequently queried columns

**Tasks:**
1. Create `src/lib/db/__init__.py`
2. Create `src/lib/db/migrations.py` with sequential migration runner
3. Create `src/lib/db/schema.py` with full spec-compliant schema
4. Add PRAGMA configuration
5. Add migration tests

**Dependencies:** None  
**Tests:** `tests/test_migrations.py`

---

### 1.2 — Escalation Chain Engine
**Spec Section:** 2  
**Status:** PARTIAL (basic `compute_escalation_chain()` exists)

**What's Done:**
- ✅ Full 8-anchor chain for ≥25 min buffer
- ✅ Compressed chains for 10-24, 5-9, ≤5 min buffers
- ✅ `validate_chain()` function
- ✅ Anchor timestamps calculated correctly

**What's Missing:**
- [ ] **Move to modular structure:** `src/lib/chain/__init__.py`, `src/lib/chain/engine.py`
- [ ] **Missing:** `get_next_unfired_anchor(reminder_id)` function for scheduler recovery
- [ ] **Missing:** Anchor re-sorting after snooze
- [ ] **Bug:** Validation doesn't check `arrival_time > departure_time + minimum_drive_time` (spec says drive_duration can't exceed time_to_arrival)
- [ ] **Missing:** Chain determinism verification (same inputs → same output)
- [ ] **Missing:** Proper error handling for edge cases

**Tasks:**
1. Create `src/lib/chain/__init__.py`
2. Create `src/lib/chain/engine.py` with refactored `compute_escalation_chain()`
3. Add `get_next_unfired_anchor(reminder_id, db)` function
4. Add `recompute_chain_after_snooze(reminder_id, snooze_minutes, db)` function
5. Fix validation: `drive_duration` cannot exceed minutes between now and arrival
6. Add comprehensive tests for all 6 test scenarios (TC-01 through TC-06)

**Dependencies:** 1.1 (database schema)  
**Tests:** `tests/test_chain_engine.py`

---

## Phase 2: User Input & AI Integration

### 2.1 — Reminder Parser (LLM + Keyword Fallback)
**Spec Section:** 3  
**Status:** PARTIAL (basic `parse_reminder_natural()` with regex)

**What's Done:**
- ✅ Keyword extraction for destination, drive duration, arrival time
- ✅ Relative time parsing ("in 3 min")
- ✅ Tomorrow date resolution
- ✅ Confidence score calculation
- ✅ Basic "dryer in 3 min" → simple_countdown

**What's Missing:**
- [ ] **Missing:** `ILanguageModelAdapter` interface
- [ ] **Missing:** Mock adapter for tests (`MockLanguageModelAdapter`)
- [ ] **Missing:** LLM adapter for MiniMax/Anthropic API
- [ ] **Missing:** Keyword extraction improvements:
  - Handle "Parker Dr 9am, 30 min drive" (no "to")
  - Handle "check-in at 9am" (no explicit time keyword)
  - Better confidence scoring
- [ ] **Missing:** Unintelligible input rejection ("blah blah")
- [ ] **Missing:** Confirmation card data structure with field editing

**Tasks:**
1. Create `src/lib/parser/__init__.py`
2. Create `src/lib/parser/adapters/base.py` with `ILanguageModelAdapter` interface
3. Create `src/lib/parser/adapters/keyword_extractor.py` with enhanced regex
4. Create `src/lib/parser/adapters/llm_adapter.py` for MiniMax API
5. Create `src/lib/parser/mock_adapter.py` for tests
6. Create `src/lib/parser/parser.py` with unified entry point
7. Create `src/lib/parser/confirmation_card.py` with editable fields
8. Write tests for all 7 scenarios (TC-01 through TC-07)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_parser.py`

---

### 2.2 — Voice Personality System
**Spec Section:** 10  
**Status:** PARTIAL (basic templates exist in `VOICE_PERSONALITIES`)

**What's Done:**
- ✅ 5 personality templates: coach, assistant, best_friend, no_nonsense, calm
- ✅ Message template per urgency tier (8 tiers)
- ✅ `generate_voice_message()` function

**What's Missing:**
- [ ] **Missing:** Message variations (minimum 3 per tier per personality)
- [ ] **Missing:** `CustomPersonality` class with user prompt support (max 200 chars)
- [ ] **Missing:** `MessageGenerator` class with template selection and variation rotation
- [ ] **Missing:** ElevenLabs voice ID mapping per personality
- [ ] **Missing:** System prompt fragments for message generation

**Tasks:**
1. Create `src/lib/voice/__init__.py`
2. Create `src/lib/voice/personalities.py` with full personality definitions
3. Add 2+ message variations per tier per personality
4. Create `src/lib/voice/message_generator.py` with variation rotation
5. Create `src/lib/voice/custom_personalities.py` with user prompt support
6. Create `src/lib/voice/manager.py` to load/store user preference
7. Write tests for message variation (TC-05) and personality immutability (TC-04)

**Dependencies:** None  
**Tests:** `tests/test_voice_personalities.py`

---

### 2.3 — TTS Generation (ElevenLabs Adapter)
**Spec Section:** 4  
**Status:** NOT STARTED (message generation only)

**What's Missing:**
- [ ] **Missing:** `ITTSAdapter` interface
- [ ] **Missing:** ElevenLabs API adapter
- [ ] **Missing:** Mock adapter for tests (writes 1-sec silent file)
- [ ] **Missing:** TTS cache directory structure (`/tts_cache/{reminder_id}/`)
- [ ] **Missing:** Pre-generation at reminder creation time
- [ ] **Missing:** Fallback to system notification sound if TTS fails
- [ ] **Missing:** Cache invalidation on reminder delete
- [ ] **Missing:** 30-second generation timeout

**Tasks:**
1. Create `src/lib/tts/__init__.py`
2. Create `src/lib/tts/adapters/base.py` with `ITTSAdapter` interface
3. Create `src/lib/tts/adapters/elevenlabs_adapter.py`
4. Create `src/lib/tts/mock_adapter.py` for tests
5. Create `src/lib/tts/generator.py` for pre-generation
6. Create `src/lib/tts/cache_manager.py` for file management
7. Implement fallback mechanism
8. Write tests for TC-01 through TC-05

**Dependencies:** 1.2 (chain engine), 2.2 (voice personalities)  
**Tests:** `tests/test_tts.py`

---

## Phase 3: Platform Integration

### 3.1 — Background Scheduling (Notifee)
**Spec Section:** 6  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** `ISchedulerAdapter` interface
- [ ] **Missing:** Notifee adapter (React Native)
- [ ] **Missing:** Mock adapter for tests
- [ ] **Missing:** Recovery scan on app launch
- [ ] **Missing:** Re-registration of pending anchors after crash
- [ ] **Missing:** 15-minute grace window for overdue anchors
- [ ] **Missing:** Late fire detection (>60s) with warning log

**Tasks:**
1. Create `src/lib/scheduler/__init__.py`
2. Create `src/lib/scheduler/adapters/base.py` with `ISchedulerAdapter` interface
3. Create `src/lib/scheduler/adapters/notifee_adapter.py`
4. Create `src/lib/scheduler/adapters/mock_adapter.py`
5. Create `src/lib/scheduler/recovery.py` with recovery_scan()
6. Create `src/lib/scheduler/registration.py` with re_register_pending_anchors()
7. Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 1.2 (chain engine), 1.1 (database)  
**Tests:** `tests/test_scheduler.py`

---

### 3.2 — Notification & Alarm Behavior
**Spec Section:** 5  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** Sound tier mapping (urgency tier → sound type)
- [ ] **Missing:** DND detection and early anchor suppression
- [ ] **Missing:** Final 5-minute DND override (visual + vibration)
- [ ] **Missing:** Quiet hours enforcement (10pm-7am default, configurable)
- [ ] **Missing:** Chain overlap serialization (queue new anchors)
- [ ] **Missing:** T-0 alarm looping until user dismiss/snooze
- [ ] **Missing:** 15-minute overdue anchor drop rule
- [ ] **Missing:** Notification display with destination, time remaining, personality icon

**Tasks:**
1. Create `src/lib/notifications/__init__.py`
2. Create `src/lib/notifications/sound_tier.py` with tier → sound mapping
3. Create `src/lib/notifications/manager.py` with DND/quiet hours handling
4. Create `src/lib/notifications/queue.py` for chain overlap serialization
5. Create `src/lib/notifications/alarm.py` for T-0 looping
6. Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 3.1 (scheduler)  
**Tests:** `tests/test_notifications.py`

---

### 3.3 — Calendar Integration
**Spec Section:** 7  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** `ICalendarAdapter` interface
- [ ] **Missing:** Apple Calendar adapter (EventKit)
- [ ] **Missing:** Google Calendar adapter (Google Calendar API)
- [ ] **Missing:** Sync manager (every 15 min, on launch)
- [ ] **Missing:** Suggestion card generation for events with locations
- [ ] **Missing:** Recurring event handling
- [ ] **Missing:** Permission denial handling
- [ ] **Missing:** Graceful degradation (sync failure → error banner)

**Tasks:**
1. Create `src/lib/calendar/__init__.py`
2. Create `src/lib/calendar/adapters/base.py` with `ICalendarAdapter` interface
3. Create `src/lib/calendar/adapters/apple_calendar_adapter.py`
4. Create `src/lib/calendar/adapters/google_calendar_adapter.py`
5. Create `src/lib/calendar/sync_manager.py`
6. Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_calendar.py`

---

### 3.4 — Location Awareness
**Spec Section:** 8  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** iOS adapter (CoreLocation)
- [ ] **Missing:** Android adapter (FusedLocationProvider)
- [ ] **Missing:** Single-point location check at departure
- [ ] **Missing:** Origin resolution (user address or creation-time location)
- [ ] **Missing:** 500m geofence comparison
- [ ] **Missing:** Immediate escalation if still at origin
- [ ] **Missing:** Permission request at first location-aware reminder

**Tasks:**
1. Create `src/lib/location/__init__.py`
2. Create `src/lib/location/adapters/ios_adapter.py`
3. Create `src/lib/location/adapters/android_adapter.py`
4. Create `src/lib/location/manager.py` with single-check logic
5. Write tests for all 5 scenarios (TC-01 through TC-05)

**Dependencies:** 3.1 (scheduler)  
**Tests:** `tests/test_location.py`

---

## Phase 4: User Interaction

### 4.1 — Snooze & Dismissal Flow
**Spec Section:** 9  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** Tap snooze (1 minute) with TTS confirmation
- [ ] **Missing:** Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] **Missing:** Chain re-computation after snooze
- [ ] **Missing:** Snoozed anchor re-registration with Notifee
- [ ] **Missing:** Swipe-to-dismiss feedback prompt
- [ ] **Missing:** Feedback sub-prompt ("Left too early", "Left too late", "Other")
- [ ] **Missing:** Snooze persistence across app restart

**Tasks:**
1. Create `src/lib/snooze/__init__.py`
2. Create `src/lib/snooze/handlers.py` with tap/tap-and-hold logic
3. Create `src/lib/snooze/recomputation.py` for chain shifting
4. Create `src/lib/snooze/feedback.py` for dismissal prompts
5. Create `src/lib/snooze/persistence.py` for restart recovery
6. Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 3.1 (scheduler), 2.2 (voice personalities), 2.3 (TTS)  
**Tests:** `tests/test_snooze.py`

---

### 4.2 — History, Stats & Feedback Loop
**Spec Section:** 11  
**Status:** PARTIAL (basic `calculate_hit_rate()`, `destination_adjustments`)

**What's Done:**
- ✅ Hit rate calculation for trailing 7 days
- ✅ Basic destination_adjustments update on miss/hit

**What's Missing:**
- [ ] **Missing:** Streak counter (increment on hit, reset on miss)
- [ ] **Missing:** Common miss window identification
- [ ] **Missing:** `actual_arrival` tracking
- [ ] **Missing:** 90-day retention policy
- [ ] **Missing:** All stats computed from history table (no separate stats store)
- [ ] **Missing:** Adjustment formula: `stored + (late_count * 2)` capped at +15 min

**Tasks:**
1. Create `src/lib/stats/__init__.py`
2. Create `src/lib/stats/calculator.py` with hit rate, streaks, miss window
3. Create `src/lib/stats/feedback_loop.py` with adjustment formula
4. Create `src/lib/stats/history_manager.py` with 90-day retention
5. Update `src/lib/stats/queries.py` to derive all stats from history
6. Write tests for all 7 scenarios (TC-01 through TC-07)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_stats.py`

---

### 4.3 — Sound Library
**Spec Section:** 12  
**Status:** NOT STARTED

**What's Missing:**
- [ ] **Missing:** Built-in sounds (5 per category: commute, routine, errand)
- [ ] **Missing:** Custom sound importer (MP3, WAV, M4A, max 30 sec)
- [ ] **Missing:** Transcoding to normalized format
- [ ] **Missing:** Per-reminder sound selection override
- [ ] **Missing:** Corrupted file fallback
- [ ] **Missing:** Sound persistence on reminder edit

**Tasks:**
1. Create `src/lib/sounds/__init__.py`
2. Create `src/lib/sounds/builtins.py` with bundled audio references
3. Create `src/lib/sounds/importer.py` with format validation
4. Create `src/lib/sounds/manager.py` with selection and fallback
5. Write tests for all 5 scenarios (TC-01 through TC-05)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_sounds.py`

---

## Phase 5: Integration & Testing

### 5.1 — Scenario Harness
**Status:** PARTIAL (scenarios exist in `scenarios/*.yaml`, harness directory empty)

**What's Done:**
- ✅ 14 scenario files in `scenarios/` directory
- ✅ Scenario format with triggers, assertions (http_status, db_record, llm_judge)

**What's Missing:**
- [ ] **Missing:** `harness/scenario_harness.py` - the test runner
- [ ] **Missing:** YAML scenario parser
- [ ] **Missing:** HTTP client for API calls
- [ ] **Missing:** Database assertion checker
- [ ] **Missing:** LLM judge integration

**Tasks:**
1. Create `harness/__init__.py`
2. Create `harness/scenario_harness.py` - main runner
3. Create `harness/parser.py` for YAML scenarios
4. Create `harness/client.py` for HTTP calls
5. Create `harness/assertions.py` for db_record checks
6. Create `harness/judge.py` for llm_judge assertions
7. Add pytest integration

**Dependencies:** Core modules (chain, parser, stats)  
**Tests:** Run against existing scenarios

---

### 5.2 — Acceptance Criteria Mapping
**Spec Section:** 14  
**Status:** NOT STARTED

**Tasks:**
1. Review all 42 acceptance criteria from spec sections 2-13
2. Map each criterion to test files
3. Ensure every criterion has at least one passing test
4. Add checklist to each test file docstring

---

### 5.3 — App Structure (React Native Shell)
**Status:** NOT STARTED

**Tasks:**
1. Create `src/App.tsx` React Native entry point
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
Phase 1: Foundation (1 week)
├── 1.1 Database Schema & Migrations  ← DO FIRST
└── 1.2 Escalation Chain Engine

Phase 2: User Input & AI (1 week)
├── 2.1 Reminder Parser (LLM + Keyword)
├── 2.2 Voice Personality System
└── 2.3 TTS Generation

Phase 3: Platform Integration (2 weeks)
├── 3.1 Background Scheduling
├── 3.2 Notification & Alarm Behavior
├── 3.3 Calendar Integration
└── 3.4 Location Awareness

Phase 4: User Interaction (1 week)
├── 4.1 Snooze & Dismissal Flow
├── 4.2 History, Stats & Feedback Loop
└── 4.3 Sound Library

Phase 5: Integration & Testing (1 week)
├── 5.1 Scenario Harness
├── 5.2 Acceptance Criteria Mapping
└── 5.3 App Structure (React Native Shell)
```

---

## Current Gaps Summary

| Component | Status | Test Scenarios |
|-----------|--------|----------------|
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
| 5.1 Scenario Harness | PARTIAL | 0/14 |
| 5.2 Acceptance Criteria | NOT STARTED | 0/42 |
| 5.3 React Native App | NOT STARTED | 0/0 |

**Total:** ~16% implementation complete (2 partial, 9 not started)

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ElevenLabs API rate limits | Delays reminder creation | Mock adapter + fallback |
| Background task killed by OS | Missed anchors | Recovery scan + 15-min grace |
| LLM parsing failure | Bad reminder data | Keyword fallback with confidence |
| Calendar API errors | Broken sync | Graceful degradation |
| Location permission denied | No location escalation | Create without, show note |
| TTS generation timeout | No voice clips | Fallback to notification sound |

---

## Success Criteria

- [ ] All 42 acceptance criteria from spec sections 2-13 have passing tests
- [ ] Chain engine produces correct anchors for all buffer sizes
- [ ] LLM adapter is fully mock-able for CI
- [ ] TTS caching eliminates runtime API calls
- [ ] Background scheduling survives app termination
- [ ] Recovery scan handles overdue anchors correctly
- [ ] Feedback loop adjusts drive duration with +15 min cap
- [ ] DND/quiet hours suppress early anchors correctly
- [ ] Snooze re-computation shifts all remaining anchors
