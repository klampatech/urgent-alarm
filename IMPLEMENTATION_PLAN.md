# URGENT Alarm - Implementation Plan

## Gap Analysis Summary

| Spec Section | Status | Priority |
|-------------|--------|----------|
| 1. Overview | N/A (reference) | - |
| 2. Escalation Chain Engine | ⚠️ Partial - missing validation, `get_next_unfired_anchor()` | P1 |
| 3. Reminder Parsing & Creation | ⚠️ Partial - no LLM adapter, limited keyword extraction | P1 |
| 4. Voice & TTS Generation | ⚠️ Partial - templates only, no TTS adapter | P2 |
| 5. Notification & Alarm Behavior | ❌ Not implemented | P2 |
| 6. Background Scheduling | ❌ Not implemented | P2 |
| 7. Calendar Integration | ❌ Not implemented | P3 |
| 8. Location Awareness | ❌ Not implemented | P3 |
| 9. Snooze & Dismissal Flow | ❌ Not implemented | P2 |
| 10. Voice Personality System | ⚠️ Partial - templates only, no variations | P1 |
| 11. History, Stats & Feedback Loop | ⚠️ Partial - hit rate only | P2 |
| 12. Sound Library | ❌ Not implemented | P3 |
| 13. Data Persistence | ⚠️ Partial - incomplete schema, no migrations | P1 |
| 14. Definition of Done | N/A (testing reference) | - |

---

## Phase 1: Foundation (Core Infrastructure)

### Task 1.1: Database Schema & Migrations
**Files to create:** `src/lib/db.py`, `src/lib/migrations/*.py`
**Dependencies:** None
**Priority:** P1

- [ ] Implement full schema per spec Section 13.3
- [ ] Add missing tables: `custom_sounds`, `calendar_sync`
- [ ] Add missing columns: `updated_at` on `user_preferences`, `origin_*` on `reminders`
- [ ] Create migration system with sequential versioning
- [ ] Enable foreign keys and WAL mode
- [ ] Add in-memory test mode support

### Task 1.2: Escalation Chain Engine Enhancement
**Files to modify:** `src/lib/chain_engine.py` (create)
**Dependencies:** Task 1.1
**Priority:** P1

- [ ] Implement `compute_escalation_chain()` with full spec logic
- [ ] Add chain compression rules per buffer duration:
  - ≥25 min: 8 anchors
  - 20-24 min: 7 anchors (skip calm)
  - 10-19 min: 5 anchors (urgent+)
  - 5-9 min: 3 anchors (firm+)
  - ≤5 min: 2 anchors (firm+, alarm)
- [ ] Implement `validate_chain()` with all error cases
- [ ] Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Add `get_earliest_unfired_anchor()` for recovery
- [ ] Unit tests for all test scenarios (TC-01 through TC-06)

### Task 1.3: Reminder Parsing with LLM Adapter
**Files to create:** `src/lib/parser.py`, `src/lib/adapters/llm_adapter.py`
**Dependencies:** Task 1.1
**Priority:** P1

- [ ] Create `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible)
- [ ] Implement `AnthropicAdapter` as alternative
- [ ] Create mock adapter for testing
- [ ] Implement keyword extraction fallback per spec Section 3.4
- [ ] Handle all date/time formats including "tomorrow"
- [ ] Unit tests for all test scenarios (TC-01 through TC-07)

---

## Phase 2: Voice & Message Generation

### Task 2.1: Voice Personality System Enhancement
**Files to modify:** `src/lib/voice_personalities.py` (create)
**Dependencies:** Task 1.1
**Priority:** P1

- [ ] Define all 5 personalities with voice IDs
- [ ] Add message templates for each tier (minimum 3 variations per tier)
- [ ] Implement custom prompt mode (max 200 chars)
- [ ] Add personality storage/retrieval
- [ ] Unit tests for message variation (TC-05)

### Task 2.2: TTS Adapter with Caching
**Files to create:** `src/lib/adapters/tts_adapter.py`
**Dependencies:** Task 2.1
**Priority:** P2

- [ ] Create `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` with voice selection
- [ ] Create mock TTS adapter for testing
- [ ] Implement TTS cache (`/tts_cache/{reminder_id}/`)
- [ ] Add fallback behavior (system sound + notification text)
- [ ] Implement cache invalidation on reminder delete
- [ ] Unit tests for all test scenarios (TC-01 through TC-05)

### Task 2.3: Message Generation Service
**Files to create:** `src/lib/message_generator.py`
**Dependencies:** Task 2.1, Task 2.2
**Priority:** P1

- [ ] Create `generate_message()` that combines personality + tier + context
- [ ] Support all urgency tiers with proper formatting
- [ ] Handle pluralization and edge cases
- [ ] Integration with TTS adapter for clip generation

---

## Phase 3: Interaction & State Management

### Task 3.1: Snooze & Dismissal Flow
**Files to create:** `src/lib/snooze_manager.py`
**Dependencies:** Task 1.2, Task 3.3
**Priority:** P2

- [ ] Implement tap snooze (1 min default)
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze
- [ ] Implement swipe-to-dismiss with feedback prompt
- [ ] Store feedback with destination adjustment tracking
- [ ] Persist snooze state across app restarts
- [ ] Unit tests for all test scenarios (TC-01 through TC-06)

### Task 3.2: History, Stats & Feedback Loop
**Files to create:** `src/lib/stats.py`, `src/lib/history.py`
**Dependencies:** Task 1.1
**Priority:** P2

- [ ] Implement hit rate calculation per spec (trailing 7 days)
- [ ] Implement destination adjustment logic (2 min per late, cap +15)
- [ ] Implement common miss window identification
- [ ] Implement streak counter for recurring reminders
- [ ] Add history pruning for data older than 90 days
- [ ] Unit tests for all test scenarios (TC-01 through TC-07)

### Task 3.3: Notification & Alarm Behavior
**Files to create:** `src/lib/notification_manager.py`
**Dependencies:** Task 2.2, Task 3.1
**Priority:** P2

- [ ] Implement notification tier escalation (gentle → beep → siren → alarm)
- [ ] Implement DND detection and handling
- [ ] Implement quiet hours suppression
- [ ] Implement post-DND catch-up firing (15-min grace window)
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping until user action
- [ ] Unit tests for all test scenarios (TC-01 through TC-06)

---

## Phase 4: Background & External Integration

### Task 4.1: Background Scheduling & Reliability
**Files to create:** `src/lib/scheduler.py`
**Dependencies:** Task 1.2, Task 3.3
**Priority:** P2

- [ ] Create Notifee adapter for iOS/Android
- [ ] Implement anchor registration per spec
- [ ] Implement recovery scan on app launch
- [ ] Implement pending anchor re-registration after crash
- [ ] Implement late fire warning logging
- [ ] Add BGTaskScheduler (iOS) and WorkManager (Android) support
- [ ] Unit tests for all test scenarios (TC-01 through TC-06)

### Task 4.2: Calendar Integration
**Files to create:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/apple_calendar.py`, `src/lib/adapters/google_calendar.py`
**Dependencies:** Task 1.1, Task 3.1
**Priority:** P3

- [ ] Create `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement calendar sync (on launch, every 15 min, background)
- [ ] Generate suggestion cards for events with locations
- [ ] Handle permission denial with explanation banner
- [ ] Implement recurring event handling
- [ ] Unit tests for all test scenarios (TC-01 through TC-06)

### Task 4.3: Location Awareness
**Files to create:** `src/lib/location_manager.py`
**Dependencies:** Task 1.2, Task 4.1
**Priority:** P3

- [ ] Implement single location check at departure anchor
- [ ] Support origin address or current device location
- [ ] Implement 500m geofence radius check
- [ ] Implement immediate escalation if user still at origin
- [ ] Request permission only at first location-aware reminder
- [ ] Handle permission denial gracefully
- [ ] Ensure no location history storage
- [ ] Unit tests for all test scenarios (TC-01 through TC-05)

### Task 4.4: Sound Library
**Files to create:** `src/lib/sound_library.py`
**Dependencies:** Task 1.1
**Priority:** P3

- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom sound import (MP3, WAV, M4A, max 30 sec)
- [ ] Implement file picker integration
- [ ] Implement audio transcoding to normalized format
- [ ] Implement corrupted sound fallback
- [ ] Implement sound persistence on reminder edit
- [ ] Unit tests for all test scenarios (TC-01 through TC-05)

---

## Phase 5: Cleanup & Testing

### Task 5.1: Refactor test_server.py
**Files to modify:** `src/test_server.py`
**Dependencies:** All above
**Priority:** P2

- [ ] Extract core logic to `src/lib/` modules
- [ ] Create proper abstractions for adapters
- [ ] Update test server to use refactored modules
- [ ] Ensure backward compatibility for existing endpoints

### Task 5.2: Integration Testing
**Files to create:** `tests/integration/`
**Dependencies:** All above
**Priority:** P1

- [ ] Create integration test harness
- [ ] Test full reminder creation flow (parse → chain → TTS → schedule)
- [ ] Test anchor firing flow (schedule → fire → update → next)
- [ ] Test snooze and recovery flow
- [ ] Test feedback loop integration

### Task 5.3: Documentation
**Files to create:** `docs/`
**Dependencies:** All above
**Priority:** P3

- [ ] Document adapter interfaces
- [ ] Document migration system
- [ ] Document voice personality configuration
- [ ] Document API endpoints

---

## Task Dependency Graph

```
Phase 1 (Foundation)
├── Task 1.1: Database Schema & Migrations
│   └── → All other tasks depend on this
├── Task 1.2: Escalation Chain Engine Enhancement
│   └── → Task 4.1 (background scheduling)
├── Task 1.3: Reminder Parsing with LLM Adapter
│   └── → Task 4.2 (calendar integration)

Phase 2 (Voice & Message Generation)
├── Task 2.1: Voice Personality System Enhancement
│   └── → Task 2.2 (TTS adapter)
├── Task 2.2: TTS Adapter with Caching
│   └── → Task 3.3 (notification manager)
└── Task 2.3: Message Generation Service
    └── → Task 2.2 (TTS adapter)

Phase 3 (Interaction & State Management)
├── Task 3.1: Snooze & Dismissal Flow
│   └── → Task 4.2 (calendar integration)
├── Task 3.2: History, Stats & Feedback Loop
└── Task 3.3: Notification & Alarm Behavior
    └── → Task 4.1 (background scheduling)

Phase 4 (External Integration)
├── Task 4.1: Background Scheduling
├── Task 4.2: Calendar Integration
├── Task 4.3: Location Awareness
└── Task 4.4: Sound Library

Phase 5 (Cleanup & Testing)
├── Task 5.1: Refactor test_server.py
└── Task 5.2: Integration Testing
└── Task 5.3: Documentation
```

---

## Acceptance Criteria Mapping

Each task maps to spec acceptance criteria. For implementation:

| Spec Criterion | Task(s) |
|----------------|---------|
| Section 2: All ACs | Task 1.2 |
| Section 3: All ACs | Task 1.3 |
| Section 4: All ACs | Task 2.2, Task 2.3 |
| Section 5: All ACs | Task 3.3 |
| Section 6: All ACs | Task 4.1 |
| Section 7: All ACs | Task 4.2 |
| Section 8: All ACs | Task 4.3 |
| Section 9: All ACs | Task 3.1 |
| Section 10: All ACs | Task 2.1 |
| Section 11: All ACs | Task 3.2 |
| Section 12: All ACs | Task 4.4 |
| Section 13: All ACs | Task 1.1 |

---

## Implementation Notes

1. **Interface-First Design**: Create all adapter interfaces (`ILanguageModelAdapter`, `ITTSAdapter`, `ICalendarAdapter`) before implementations for testability.

2. **Deterministic Chain Computation**: The chain engine must be pure functions for unit testing — same inputs always produce same outputs.

3. **Graceful Degradation**: Every external service (LLM, TTS, Calendar, Location) must have a fallback. Never fail silently without logging.

4. **SQLite Persistence**: All anchor state must be persisted so app crashes don't lose scheduling state.

5. **TTS Pre-Generation**: All voice clips generated at reminder creation, never at runtime.

6. **30-Second TTS Budget**: TTS generation for a single reminder must complete within 30 seconds (async + polling).