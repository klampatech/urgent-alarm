# Implementation Plan — Urgent Alarm

## Overview

This plan maps the detailed specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to implementation tasks. The current codebase (`src/test_server.py`) contains only a minimal proof-of-concept — basic chain computation, keyword parsing, and HTTP endpoints for harness testing.

**Gap Summary:** 12 major components need implementation, spanning data persistence, AI integrations (LLM + TTS), background scheduling, platform APIs (calendar, location, notifications), and user interaction flows.

---

## Phase 1: Foundation (Data & Core Engine)

### 1.1 — Database Schema & Migrations
**Priority:** P0 (blocking everything else)  
**Spec Section:** 13

**Current State:** Basic schema in `test_server.py` with 5 tables  
**Target State:** Full spec-compliant schema with migration system

**Tasks:**
- [ ] Create `src/lib/db/migrations.py` with versioned migration runner
- [ ] Extend schema: add `reminders.origin_lat/lng/address`, `anchors.snoozed_to`, `history.missed_reason`, `calendar_sync`, `custom_sounds` tables
- [ ] Add `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL` configuration
- [ ] Add UUID v4 generation utility (`src/lib/db/uuid.py`)
- [ ] Add `Database.getInMemoryInstance()` for tests (isolated test DBs)
- [ ] Add cascade delete for reminders → anchors
- [ ] Write migration tests (fresh install, in-memory, cascade delete, FK enforcement)

**Dependencies:** None  
**Tests:** `tests/test_migrations.py`

---

### 1.2 — Escalation Chain Engine
**Priority:** P0 (core app logic)  
**Spec Section:** 2

**Current State:** `compute_escalation_chain()` in test_server.py (partial)  
**Target State:** Full spec-compliant chain engine with recovery functions

**Tasks:**
- [ ] Move chain engine to `src/lib/chain/engine.py`
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add full validation: `arrival_time > departure_time + minimum_drive_time`
- [ ] Implement compressed chain logic for buffers 10-24 min, 5-9 min, ≤5 min
- [ ] Ensure chain determinism (same inputs → same output for testing)
- [ ] Implement anchor re-sorting after snooze
- [ ] Write comprehensive tests for all 6 test scenarios (TC-01 through TC-06)

**Dependencies:** 1.1 (database schema for anchor storage)  
**Tests:** `tests/test_chain_engine.py`

---

## Phase 2: User Input & AI Integration

### 2.1 — Reminder Parser (LLM + Keyword Fallback)
**Priority:** P1 (user-facing feature)  
**Spec Section:** 3

**Current State:** `parse_reminder_natural()` with basic regex in test_server.py  
**Target State:** Mock-able LLM adapter with keyword fallback

**Tasks:**
- [ ] Create `src/lib/parser/adapters/base.py` with `ILanguageModelAdapter` interface
- [ ] Create `src/lib/parser/adapters/keyword_extractor.py` — enhance existing regex with:
  - Time extraction: "X min drive", "X-minute drive", "arrive at X", "check-in at X"
  - Duration extraction: all patterns from spec
  - Confidence scoring
  - "blah blah" rejection
- [ ] Create `src/lib/parser/adapters/llm_adapter.py` for MiniMax API (Anthropic-compatible)
  - System prompt for structured JSON extraction
  - API error handling with fallback to keyword extractor
- [ ] Create `src/lib/parser/mock_adapter.py` for test mode
- [ ] Implement `parse_reminder_natural()` in `src/lib/parser/parser.py` — unified entry point
- [ ] Implement confirmation card data structure (parsed fields with confidence scores)
- [ ] Write tests for all 7 test scenarios (TC-01 through TC-07)

**Dependencies:** None  
**Tests:** `tests/test_parser.py`

---

### 2.2 — Voice Personality System
**Priority:** P1 (user-facing feature)  
**Spec Section:** 10

**Current State:** `VOICE_PERSONALITIES` dict in test_server.py  
**Target State:** Extensible personality system with message variations

**Tasks:**
- [ ] Move personality definitions to `src/lib/voice/personalities.py`
- [ ] Add message variations (minimum 3 per tier per personality) for variety
- [ ] Implement `CustomPersonality` class with user prompt support (max 200 chars)
- [ ] Implement `MessageGenerator` class that selects template + variations
- [ ] Create `src/lib/voice/manager.py` to load/store user preference
- [ ] Write tests for message variation (TC-05) and personality immutability (TC-04)

**Dependencies:** None  
**Tests:** `tests/test_voice_personalities.py`

---

### 2.3 — TTS Generation (ElevenLabs Adapter)
**Priority:** P2 (AI integration)  
**Spec Section:** 4

**Current State:** Message template generation only (no actual TTS)  
**Target State:** Mock-able ElevenLabs adapter with local file caching

**Tasks:**
- [ ] Create `src/lib/tts/adapters/base.py` with `ITTSAdapter` interface
- [ ] Create `src/lib/tts/adapters/elevenlabs_adapter.py`
  - ElevenLabs API integration
  - Voice ID mapping per personality
  - Custom style prompt support
- [ ] Create `src/lib/tts/mock_adapter.py` for tests (writes 1-sec silent file)
- [ ] Create `src/lib/tts/generator.py`:
  - Pre-generate all TTS clips at reminder creation
  - Save to `/tts_cache/{reminder_id}/{anchor_id}.mp3`
  - 30-second generation timeout with async polling
- [ ] Create `src/lib/tts/cache_manager.py`:
  - Cache invalidation on reminder delete
  - Corrupted file detection
- [ ] Implement fallback: system notification sound + notification text if TTS fails
- [ ] Write tests for clip generation (TC-01), cache cleanup (TC-04), mock adapter (TC-05)

**Dependencies:** 1.2 (chain engine for anchor list), 2.2 (voice personalities)  
**Tests:** `tests/test_tts.py`

---

## Phase 3: Platform Integration

### 3.1 — Background Scheduling (Notifee)
**Priority:** P0 (core reliability)  
**Spec Section:** 6

**Current State:** None  
**Target State:** Reliable background scheduling with crash recovery

**Tasks:**
- [ ] Create `src/lib/scheduler/adapters/base.py` with `ISchedulerAdapter` interface
- [ ] Create `src/lib/scheduler/adapters/notifee_adapter.py` (React Native)
  - Register individual anchor as background task with trigger timestamp
  - iOS: `BGAppRefreshTask` + `BGProcessingTask` for TTS pre-warming
- [ ] Create `src/lib/scheduler/adapters/mock_adapter.py` for tests
- [ ] Implement `recovery_scan()` on app launch:
  - Load unfired anchors from SQLite
  - Fire anchors within 15-minute grace window
  - Drop anchors >15 minutes overdue (log `missed_reason = "background_task_killed"`)
- [ ] Implement `re_register_pending_anchors()` on restart
- [ ] Implement `get_next_unfired_anchor()` recovery helper
- [ ] Add late fire detection (>60s after scheduled) with warning log
- [ ] Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 1.2 (chain engine), 1.1 (database)  
**Tests:** `tests/test_scheduler.py`

---

### 3.2 — Notification & Alarm Behavior
**Priority:** P1 (user-facing feature)  
**Spec Section:** 5

**Current State:** None  
**Target State:** Escalating notification system with DND/quiet hours support

**Tasks:**
- [ ] Create `src/lib/notifications/sound_tier.py` — mapping urgency tier → sound type
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm
- [ ] Create `src/lib/notifications/manager.py`:
  - DND detection and early anchor suppression (silent notification only)
  - Final 5-minute DND override (visual + vibration)
  - Quiet hours enforcement (10pm–7am default, configurable)
  - Chain overlap serialization (queue new anchors until current chain completes)
- [ ] Implement T-0 alarm looping until user dismiss/snooze
- [ ] Implement overdue anchor handling (15-min rule for DND/quiet hours)
- [ ] Notification display: destination label, time remaining, voice personality icon
- [ ] Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 3.1 (scheduler)  
**Tests:** `tests/test_notifications.py`

---

### 3.3 — Calendar Integration
**Priority:** P2 (optional feature)  
**Spec Section:** 7

**Current State:** None  
**Target State:** Apple Calendar + Google Calendar integration

**Tasks:**
- [ ] Create `src/lib/calendar/adapters/base.py` with `ICalendarAdapter` interface
- [ ] Create `src/lib/calendar/adapters/apple_calendar_adapter.py` (EventKit)
- [ ] Create `src/lib/calendar/adapters/google_calendar_adapter.py` (Google Calendar API)
- [ ] Create `src/lib/calendar/sync_manager.py`:
  - Sync on app launch + every 15 minutes
  - Filter events with non-empty `location` field
  - Generate suggestion cards for events without existing reminder
- [ ] Implement `calendar_sync` table updates (last_sync_at, sync_token)
- [ ] Implement permission denial handling with explanation banner + settings link
- [ ] Implement recurring event handling (daily/weekly occurrences)
- [ ] Implement graceful degradation (calendar sync failure → error banner, manual reminders still work)
- [ ] Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_calendar.py`

---

### 3.4 — Location Awareness
**Priority:** P3 (optional feature)  
**Spec Section:** 8

**Current State:** None  
**Target State:** Single-point location check at departure trigger

**Tasks:**
- [ ] Create `src/lib/location/adapters/ios_adapter.py` (CoreLocation)
- [ ] Create `src/lib/location/adapters/android_adapter.py` (FusedLocationProvider)
- [ ] Create `src/lib/location/manager.py`:
  - Single location API call at departure anchor fire (not continuous)
  - Origin resolution: user-specified address OR current location at creation
  - 500m geofence radius check
  - Immediate escalation (fire T-5/T-1 instead of departure) if still at origin
- [ ] Implement permission request at first location-aware reminder creation
- [ ] Handle denied permission: create reminder without location awareness + note
- [ ] Ensure no location history storage (single comparison only)
- [ ] Write tests for all 5 scenarios (TC-01 through TC-05)

**Dependencies:** 3.1 (scheduler)  
**Tests:** `tests/test_location.py`

---

## Phase 4: User Interaction

### 4.1 — Snooze & Dismissal Flow
**Priority:** P1 (core user interaction)  
**Spec Section:** 9

**Current State:** None  
**Target State:** Full snooze + feedback flow

**Tasks:**
- [ ] Implement tap snooze (1 minute) with TTS confirmation "Okay, snoozed 1 minute"
- [ ] Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 minutes)
- [ ] Implement chain re-computation: shift remaining anchors to `now + original_time_remaining`
- [ ] Implement snoozed anchor re-registration with Notifee
- [ ] Implement swipe-to-dismiss feedback prompt: "You missed [destination] — was the timing right?"
- [ ] Implement feedback sub-prompt: "What was wrong? [Left too early] [Left too late] [Other]"
- [ ] Implement TTS snooze confirmation: "Okay, snoozed [X] minutes"
- [ ] Implement snooze persistence (app killed → re-registration uses snoozed timestamps)
- [ ] Write tests for all 6 scenarios (TC-01 through TC-06)

**Dependencies:** 3.1 (scheduler), 2.2 (voice personalities), 2.3 (TTS)  
**Tests:** `tests/test_snooze.py`

---

### 4.2 — History, Stats & Feedback Loop
**Priority:** P1 (core learning system)  
**Spec Section:** 11

**Current State:** `calculate_hit_rate()` in test_server.py (partial)  
**Target State:** Full stats system with feedback learning

**Tasks:**
- [ ] Create `src/lib/stats/calculator.py`:
  - Hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` (trailing 7 days)
  - Streak counter: increment on hit, reset on miss for recurring reminders
  - Common miss window: identify most-frequently-missed urgency tier
- [ ] Create `src/lib/stats/feedback_loop.py`:
  - Adjustment formula: `adjusted_drive_duration = stored + (late_count * 2)` capped at +15 min
  - Store adjustments in `destination_adjustments` table
- [ ] Create `src/lib/stats/history_manager.py`:
  - Record completion: reminder_id, destination, scheduled_arrival, actual_arrival, outcome, feedback_type
  - 90-day retention policy (archive older data)
- [ ] Ensure all stats computable from history table (no separate stats store)
- [ ] Write tests for all 7 scenarios (TC-01 through TC-07)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_stats.py`

---

### 4.3 — Sound Library
**Priority:** P2 (optional feature)  
**Spec Section:** 12

**Current State:** None  
**Target State:** Sound selection and custom import

**Tasks:**
- [ ] Create `src/lib/sounds/builtins.py` with 5 sounds per category (commute, routine, errand) — bundled audio files
- [ ] Create `src/lib/sounds/importer.py`:
  - Support MP3, WAV, M4A (max 30 seconds)
  - Transcode to normalized format
  - Store in app sandbox
  - Custom sounds table update
- [ ] Create `src/lib/sounds/manager.py`:
  - Per-reminder sound selection override
  - Corrupted file detection with fallback to category default
  - Sound persistence on reminder edit
- [ ] Create `src/lib/sounds/library.db` or SQLite table for custom_sounds tracking
- [ ] Write tests for all 5 scenarios (TC-01 through TC-05)

**Dependencies:** 1.1 (database)  
**Tests:** `tests/test_sounds.py`

---

## Phase 5: Integration & Testing

### 5.1 — Definition of Done — Acceptance Criteria Mapping
**Priority:** P1  
**Spec Section:** 14

**Tasks:**
- [ ] Review all acceptance criteria from sections 2–13
- [ ] Ensure every criterion has at least one passing test
- [ ] Add acceptance criteria checklist to each test file docstring

---

### 5.2 — App Structure (React Native Shell)
**Priority:** P2

**Tasks:**
- [ ] Create `src/App.tsx` React Native entry point
- [ ] Create `src/screens/QuickAddScreen.tsx` — text/speech input
- [ ] Create `src/screens/RemindersListScreen.tsx` — active reminders
- [ ] Create `src/screens/HistoryScreen.tsx` — stats and history
- [ ] Create `src/screens/SettingsScreen.tsx` — voice personality, quiet hours, calendar
- [ ] Create `src/lib/react-native/` adapters for platform-specific APIs
- [ ] Wire up all modules to app screens

**Dependencies:** Phases 1-4 complete  
**Tests:** `tests/test_integration.py` (e2e smoke tests)

---

## Implementation Order Summary

```
Phase 1: Foundation (2 weeks)
├── 1.1 Database Schema & Migrations  ← DO FIRST
└── 1.2 Escalation Chain Engine

Phase 2: User Input & AI (2 weeks)
├── 2.1 Reminder Parser (LLM + Keyword)
├── 2.2 Voice Personality System
└── 2.3 TTS Generation

Phase 3: Platform Integration (2 weeks)
├── 3.1 Background Scheduling
├── 3.2 Notification & Alarm Behavior
├── 3.3 Calendar Integration
└── 3.4 Location Awareness

Phase 4: User Interaction (2 weeks)
├── 4.1 Snooze & Dismissal Flow
├── 4.2 History, Stats & Feedback Loop
└── 4.3 Sound Library

Phase 5: Integration & Testing (1 week)
├── 5.1 Acceptance Criteria Mapping
└── 5.2 App Structure (React Native Shell)
```

---

## Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ElevenLabs API rate limits during TTS generation | Delays reminder creation | Mock adapter + fallback to notification sound |
| Background task killed by OS (iOS) | Missed anchors | Recovery scan + 15-min grace window |
| LLM parsing failure | Bad reminder data | Keyword fallback with confidence score < 1.0 |
| Calendar API errors | Broken sync | Graceful degradation + error banner |
| Location permission denied | No location escalation | Create reminder without, show note |

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
