# Urgent Voice Alarm - Implementation Plan

## Analysis Summary

**Spec Size:** 1024 lines covering 13 major subsystems  
**Current Codebase:** Single `src/test_server.py` file with ~500 lines  
**Gap:** 90%+ of spec not implemented

The current codebase is a minimal HTTP test server for harness validation. It provides basic scaffolding but lacks the modular architecture, adapter interfaces, and most features specified in the requirements.

---

## Priority 1: Foundation (Must Implement First)

### 1.1 Modular Architecture Structure
**Files to create:** `src/lib/core/`, `src/lib/adapters/`, `src/lib/models/`, `src/lib/services/`

- [ ] Create `src/lib/__init__.py`
- [ ] Create `src/lib/core/__init__.py`, `chain_engine.py`, `validators.py`
- [ ] Create `src/lib/adapters/__init__.py`, `base.py` (adapter interfaces)
- [ ] Create `src/lib/models/__init__.py`, `reminder.py`, `anchor.py`, `history.py`
- [ ] Create `src/lib/services/__init__.py`, `notification.py`, `audio.py`

**Reasoning:** All subsequent work depends on proper interfaces for mocking and testing.

### 1.2 Database Schema & Migrations
**File to update:** `src/lib/core/database.py`

- [ ] Full schema migration system with version tracking
- [ ] All required tables per spec Section 13:
  - `reminders` (complete columns)
  - `anchors` (complete columns)
  - `history`
  - `destination_adjustments`
  - `user_preferences`
  - `calendar_sync`
  - `custom_sounds`
  - `schema_version` table
- [ ] In-memory mode for tests
- [ ] Cascade delete enforcement

**Schema validation test cases from spec:**
- TC-01: Migration sequence
- TC-02: In-memory test database
- TC-03: Cascade delete
- TC-04: Foreign key enforcement
- TC-05: UUID generation

### 1.3 Chain Engine (Refactor)
**File to update:** `src/lib/core/chain_engine.py`

- [ ] Full 8-anchor chain for buffer >= 25 min
- [ ] Compressed chains for all buffer ranges per spec Section 2.3
- [ ] `get_next_unfired_anchor()` function
- [ ] Chain determinism (testable)
- [ ] Validation: arrival_time > departure_time + minimum_drive_time

**Test cases from spec:**
- TC-01: Full chain (30 min buffer)
- TC-02: Compressed chain (15 min buffer)
- TC-03: Minimum chain (3 min buffer)
- TC-04: Invalid chain rejection
- TC-05: Next unfired anchor recovery
- TC-06: Chain determinism

---

## Priority 2: Core Business Logic

### 2.1 LLM Adapter Interface
**File to create:** `src/lib/adapters/llm_adapter.py`

- [ ] `ILanguageModelAdapter` abstract interface
- [ ] `MiniMaxAdapter` implementation
- [ ] `AnthropicAdapter` implementation  
- [ ] `MockLLMAdapter` for testing
- [ ] Keyword extraction fallback

**Test cases from spec:**
- TC-01: Full natural language parse
- TC-02: Simple countdown parse
- TC-03: Tomorrow date resolution
- TC-04: LLM API failure fallback
- TC-05: Manual field correction
- TC-06: Unintelligible input rejection
- TC-07: Mock adapter in tests

### 2.2 TTS Adapter Interface
**File to create:** `src/lib/adapters/tts_adapter.py`

- [ ] `ITTSAdapter` abstract interface
- [ ] `ElevenLabsAdapter` implementation
- [ ] `MockTTSAdapter` for testing
- [ ] Clip caching to `/tts_cache/{reminder_id}/`
- [ ] Cache invalidation on reminder delete
- [ ] Fallback to system sounds

**Test cases from spec:**
- TC-01: TTS clip generation at creation
- TC-02: Anchor fires from cache
- TC-03: TTS fallback on API failure
- TC-04: TTS cache cleanup on delete
- TC-05: Mock TTS in tests

### 2.3 Voice Personality System
**File to create:** `src/lib/services/voice_personality.py`

- [ ] 5 built-in personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
- [ ] Custom prompt support (max 200 chars)
- [ ] Minimum 3 message variations per tier per personality
- [ ] Personality stored in user preferences

**Test cases from spec:**
- TC-01: Coach personality messages
- TC-02: No-nonsense personality messages
- TC-03: Custom personality
- TC-04: Personality immutability for existing reminders
- TC-05: Message variation

---

## Priority 3: Features

### 3.1 Snooze & Dismissal Flow
**File to create:** `src/lib/services/snooze.py`

- [ ] Tap snooze (1 minute)
- [ ] Tap-and-hold custom snooze (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze: shift remaining anchors
- [ ] Re-register with Notifee (simulated in test server)
- [ ] Swipe-to-dismiss feedback prompt
- [ ] TTS confirmation: "Okay, snoozed X minutes"
- [ ] Persistence after app restart

**Test cases from spec:**
- TC-01: Tap snooze
- TC-02: Custom snooze
- TC-03: Chain re-computation after snooze
- TC-04: Dismissal feedback — timing correct
- TC-05: Dismissal feedback — timing off (left too late)
- TC-06: Snooze persistence after restart

### 3.2 Notification & Alarm Behavior
**File to create:** `src/lib/services/notification.py`

- [ ] Tier-based notification sounds (gentle chime → alarm loop)
- [ ] DND awareness (silent notification vs visual override + vibration)
- [ ] Quiet hours suppression (configurable, default 10pm-7am)
- [ ] 15-minute overdue anchor drop rule
- [ ] Chain overlap serialization (queue new anchors)
- [ ] T-0 alarm loops until user action
- [ ] Notification display: destination, time remaining, personality icon

**Test cases from spec:**
- TC-01: DND — early anchor suppressed
- TC-02: DND — final 5-minute override
- TC-03: Quiet hours suppression
- TC-04: Overdue anchor drop (15 min rule)
- TC-05: Chain overlap serialization
- TC-06: T-0 alarm loops until action

### 3.3 History, Stats & Feedback Loop
**File to create:** `src/lib/services/stats.py`

- [ ] Hit rate calculation (trailing 7 days)
- [ ] Feedback loop: adjust drive_duration for destination (+2 min per miss, cap +15)
- [ ] Common miss window identification
- [ ] Streak counter for recurring reminders
- [ ] All stats computable from history table

**Test cases from spec:**
- TC-01: Hit rate calculation
- TC-02: Feedback loop — drive duration adjustment
- TC-03: Feedback loop cap
- TC-04: Common miss window identification
- TC-05: Streak increment on hit
- TC-06: Streak reset on miss
- TC-07: Stats derived from history table

### 3.4 Background Scheduling & Reliability
**File to create:** `src/lib/services/scheduler.py`

- [ ] Anchor registration (simulated for test server)
- [ ] Recovery scan on app launch
- [ ] 15-minute grace window enforcement
- [ ] Overdue anchor drop + logging
- [ ] Pending anchor re-registration on crash recovery
- [ ] Late fire warning (>60 seconds)

**Test cases from spec:**
- TC-01: Anchor scheduling
- TC-02: Background fire with app closed
- TC-03: Recovery scan on launch
- TC-04: Overdue anchor drop
- TC-05: Pending anchors re-registered on crash recovery
- TC-06: Late fire warning

---

## Priority 4: Integrations

### 4.1 Calendar Integration
**File to create:** `src/lib/adapters/calendar_adapter.py`

- [ ] `ICalendarAdapter` interface
- [ ] `AppleCalendarAdapter` (EventKit)
- [ ] `GoogleCalendarAdapter` (Google Calendar API)
- [ ] `MockCalendarAdapter` for testing
- [ ] Event sync (launch, every 15 min, background refresh)
- [ ] Suggestion cards for events with locations
- [ ] Recurring event handling

**Test cases from spec:**
- TC-01: Apple Calendar event suggestion
- TC-02: Google Calendar event suggestion
- TC-03: Suggestion → reminder creation
- TC-04: Permission denial handling
- TC-05: Sync failure graceful degradation
- TC-06: Recurring event handling

### 4.2 Location Awareness
**File to create:** `src/lib/adapters/location_adapter.py`

- [ ] `ILocationAdapter` interface
- [ ] `CoreLocationAdapter` (iOS)
- [ ] `FusedLocationAdapter` (Android)
- [ ] `MockLocationAdapter` for testing
- [ ] Single location check at departure anchor
- [ ] 500m geofence radius
- [ ] Immediate escalation if user still at origin
- [ ] Permission request on first location-aware reminder

**Test cases from spec:**
- TC-01: User still at origin at departure
- TC-02: User already left at departure
- TC-03: Location permission request
- TC-04: Location permission denied
- TC-05: Single location check only

### 4.3 Sound Library
**File to create:** `src/lib/services/sound_library.py`

- [ ] Built-in sound categories: Commute (5), Routine (5), Errand (5), Custom
- [ ] Custom audio import (MP3, WAV, M4A, max 30 sec)
- [ ] Per-reminder sound selection
- [ ] Corrupted sound fallback

**Test cases from spec:**
- TC-01: Built-in sound playback
- TC-02: Custom sound import
- TC-03: Custom sound playback
- TC-04: Corrupted sound fallback
- TC-05: Sound persistence on edit

---

## Priority 5: Test Infrastructure

### 5.1 Test Harnesses
**Files to create:** `harness/scenario_harness.py`, `harness/test_reminder_parsing.py`, etc.

- [ ] Scenario harness for sudo-based testing
- [ ] Unit tests for each module
- [ ] Integration tests for adapter chains
- [ ] Database migration tests

### 5.2 Scenario Definitions
**Directory:** `/var/otto-scenarios/otto-matic/`

- [ ] Scenario YAML files for each major feature
- [ ] Test scenarios from spec Sections 2-13

---

## Implementation Order

```
Phase 1: Foundation
  1.1 Modular structure
  1.2 Database schema/migrations
  1.3 Chain engine refactor

Phase 2: Core Business Logic
  2.1 LLM adapter interface
  2.2 TTS adapter interface
  2.3 Voice personality system

Phase 3: Features
  3.1 Snooze & dismissal flow
  3.2 Notification & alarm behavior
  3.3 History, stats & feedback loop
  3.4 Background scheduling

Phase 4: Integrations
  4.1 Calendar integration
  4.2 Location awareness
  4.3 Sound library

Phase 5: Test Infrastructure
  5.1 Test harnesses
  5.2 Scenario definitions
```

---

## Notes

- This plan targets the Python test server (`src/test_server.py`) for harness validation
- Mobile app implementation (React Native/Flutter) is future work
- All adapter interfaces should be mock-able for testing
- Chain engine must be deterministic for unit testing
- Database schema must support in-memory mode for tests
