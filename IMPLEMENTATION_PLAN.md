# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Analysis Summary

The `test_server.py` provides a **partial proof-of-concept** with basic chain computation, keyword parsing, and voice message templates. The codebase lacks the full architecture required by the specification.

---

## Current State vs. Specification

| Spec Section | Current Implementation | Gap |
|--------------|------------------------|-----|
| 2. Escalation Chain Engine | Basic `compute_escalation_chain()` with some tier logic | Missing: chain validation, get_next_unfired_anchor, full tier compression logic |
| 3. Reminder Parsing | Keyword-only regex parser | Missing: LLM adapter interface, mock adapter, fallback confidence scoring |
| 4. Voice & TTS | Template strings only | Missing: ElevenLabs adapter, TTS caching, clip path management |
| 5. Notification/Alarm | None | Missing: escalation tiers, DND awareness, quiet hours, chain serialization |
| 6. Background Scheduling | None | Missing: Notifee integration, recovery scan, grace window logic |
| 7. Calendar Integration | None | Missing: Apple Calendar adapter, Google Calendar adapter |
| 8. Location Awareness | None | Missing: single-point check, geofencing, origin resolution |
| 9. Snooze & Dismissal | Partial anchor firing | Missing: chain recomputation, custom snooze picker, feedback prompts |
| 10. Voice Personality | 5 hardcoded templates | Missing: custom prompt support, tier-specific variations (3+ per tier) |
| 11. History/Stats | Basic hit rate | Missing: feedback loop adjustments, common miss window, streak counter |
| 12. Sound Library | None | Missing: built-in sounds, custom import, per-reminder selection |
| 13. Data Persistence | Basic tables | Missing: versioned migrations, in-memory test mode, WAL mode, cascade delete |
| 14. Tests | None | Missing: unit tests, integration tests |

---

## Task List (Prioritized)

### Phase 1: Foundation (Must be completed first)

#### 1.1 Create Python Package Structure
**Priority:** Critical | **Effort:** Low | **Dependencies:** None
- Create `src/lib/` directory with `__init__.py`
- Create `src/lib/core/` for chain engine, parser interfaces
- Create `src/lib/adapters/` for LLM, TTS, calendar, location
- Create `src/lib/db/` for database and migrations
- Create `src/lib/services/` for notification, sound, stats
- Create `src/lib/models/` for data classes

#### 1.2 Implement Database Layer
**Priority:** Critical | **Effort:** Medium | **Dependencies:** 1.1
- Implement versioned migration system (`migrations/` directory)
- Create full schema from spec (8 tables)
- Add WAL mode and foreign key enforcement
- Add `Database` class with `get_in_memory_instance()` for tests
- Add `Database.get_instance()` singleton for production
- Implement cascade delete behavior

**Acceptance Criteria:**
- [ ] Migrations run in order on fresh install
- [ ] In-memory database works for tests
- [ ] Cascade delete removes anchors when reminder deleted

#### 1.3 Complete Escalation Chain Engine
**Priority:** Critical | **Effort:** Medium | **Dependencies:** 1.2
- Refactor existing `compute_escalation_chain()` into `ChainEngine` class
- Implement all compression rules from spec (TC-01 through TC-06)
- Add `validate_chain()` with all validation errors
- Add `get_next_unfired_anchor(reminder_id)` for recovery
- Add deterministic chain generation for testability
- Write unit tests for all test scenarios in Section 2.5

**Acceptance Criteria:**
- [ ] All 6 test scenarios from spec pass
- [ ] Chain is deterministic (same inputs = same outputs)

---

### Phase 2: Core Features

#### 2.1 LLM Adapter Interface & Keyword Fallback
**Priority:** Critical | **Effort:** Medium | **Dependencies:** 1.1
- Create `ILanguageModelAdapter` abstract interface
- Implement `KeywordExtractionAdapter` (refactor existing logic)
- Implement `MiniMaxAdapter` for real API
- Implement `MockLanguageModelAdapter` for tests
- Add confidence scoring to all adapters
- Implement field correction support for confirmation card

**Acceptance Criteria:**
- [ ] Mock adapter returns fixture without API call
- [ ] Keyword fallback produces confidence < 1.0
- [ ] All 7 test scenarios from Section 3.5 pass

#### 2.2 TTS Adapter Interface & Caching
**Priority:** High | **Effort:** Medium | **Dependencies:** 1.1, 2.1
- Create `ITTSAdapter` abstract interface
- Implement `ElevenLabsAdapter` for real API
- Implement `MockTTSAdapter` for tests
- Implement `TTSCacheManager` for file caching
- Implement cache invalidation on reminder deletion
- Add fallback behavior on API failure

**Acceptance Criteria:**
- [ ] TTS clips cached to `/tts_cache/{reminder_id}/`
- [ ] Cache cleanup on reminder deletion
- [ ] All 5 test scenarios from Section 4.5 pass

#### 2.3 Voice Personality System
**Priority:** High | **Effort:** Medium | **Dependencies:** 1.1
- Create `VoicePersonality` enum and `PersonalityConfig` class
- Implement 5 built-in personalities with templates
- Add custom prompt support (max 200 chars)
- Implement message variation system (3+ templates per tier per personality)
- Create `VoiceMessageGenerator` service

**Acceptance Criteria:**
- [ ] All 5 personalities produce correct output
- [ ] Custom prompts modify tone appropriately
- [ ] 3+ distinct messages per tier per personality

#### 2.4 Snooze & Chain Recomputation
**Priority:** High | **Effort:** Medium | **Dependencies:** 1.3, 2.1
- Implement `ChainRecomputer` for snooze shifts
- Implement 1-min tap snooze
- Implement custom snooze picker (1, 3, 5, 10, 15 min)
- Add snooze persistence across app restarts
- Implement dismissal feedback flow
- Add feedback type handling (timing_right, left_too_early, left_too_late, other)

**Acceptance Criteria:**
- [ ] All 6 test scenarios from Section 9.5 pass
- [ ] Chain shifts correctly after snooze

#### 2.5 History & Stats with Feedback Loop
**Priority:** High | **Effort:** Medium | **Dependencies:** 1.2
- Implement `StatsCalculator` with hit rate, streak, common miss window
- Implement `FeedbackLoop` service for destination adjustments
- Add adjustment capping (+15 min max)
- Ensure all stats derived from history table

**Acceptance Criteria:**
- [ ] All 7 test scenarios from Section 11.5 pass
- [ ] Feedback loop adjusts drive_duration correctly

---

### Phase 3: Platform Integration

#### 3.1 Calendar Integration
**Priority:** Medium | **Effort:** High | **Dependencies:** 1.1, 1.2
- Create `ICalendarAdapter` abstract interface
- Implement `AppleCalendarAdapter` (EventKit)
- Implement `GoogleCalendarAdapter` (Google Calendar API)
- Implement calendar sync scheduler (15-min intervals)
- Add suggestion card generation
- Add permission denial handling

**Acceptance Criteria:**
- [ ] All 6 test scenarios from Section 7.5 pass
- [ ] Calendar permission denial shows explanation banner

#### 3.2 Location Awareness
**Priority:** Medium | **Effort:** Medium | **Dependencies:** 1.1
- Create `ILocationAdapter` abstract interface
- Implement `CoreLocationAdapter` for iOS
- Implement `MockLocationAdapter` for tests
- Implement 500m geofence check
- Implement immediate escalation when at origin
- Add permission-on-first-use behavior

**Acceptance Criteria:**
- [ ] All 5 test scenarios from Section 8.5 pass
- [ ] Only one location API call per reminder

#### 3.3 Notification & Alarm Behavior
**Priority:** Medium | **Effort:** High | **Dependencies:** 2.4, 3.2
- Implement escalation tiers (gentle chime → alarm loop)
- Implement DND awareness (silent early, visual/vibrate final 5 min)
- Implement quiet hours suppression
- Implement 15-minute overdue drop rule
- Implement chain overlap serialization
- Implement T-0 looping alarm

**Acceptance Criteria:**
- [ ] All 6 test scenarios from Section 5.5 pass

#### 3.4 Background Scheduling
**Priority:** Medium | **Effort:** High | **Dependencies:** 1.2, 2.4
- Implement `NotifeeScheduler` adapter
- Implement anchor registration per reminder
- Implement recovery scan on app launch
- Implement overdue anchor drop (15-min grace)
- Add late fire warning logging (>60s)

**Acceptance Criteria:**
- [ ] All 6 test scenarios from Section 6.5 pass

---

### Phase 4: Sound & Polish

#### 4.1 Sound Library
**Priority:** Low | **Effort:** Medium | **Dependencies:** 1.1, 1.2
- Create `SoundLibrary` with 4 categories (commute, routine, errand, custom)
- Implement 5 built-in sounds per category (placeholder files)
- Implement custom audio import (MP3, WAV, M4A, max 30s)
- Implement corrupted sound fallback
- Add per-reminder sound selection

**Acceptance Criteria:**
- [ ] All 5 test scenarios from Section 12.5 pass

#### 4.2 Reminder Types
**Priority:** Low | **Effort:** Medium | **Dependencies:** 1.3, 2.4
- Implement countdown_event (default)
- Implement simple_countdown
- Implement morning_routine (multi-anchor template)
- Implement standing_recurring (with streak tracking)

---

### Phase 5: Testing & Documentation

#### 5.1 Unit Tests
**Priority:** Critical | **Effort:** High | **Dependencies:** 1.3, 2.1-2.5
- Create `tests/` directory with proper structure
- Implement mock adapters for all interfaces
- Write tests for all acceptance criteria in Sections 2-12
- Achieve >80% code coverage on core modules

#### 5.2 Integration Tests
**Priority:** High | **Effort:** Medium | **Dependencies:** 5.1
- Test full reminder creation flow (parse → chain → TTS → persist)
- Test anchor firing sequence
- Test snooze recovery
- Test feedback loop end-to-end

#### 5.3 Refactor test_server.py
**Priority:** Medium | **Effort:** Low | **Dependencies:** 1.3, 2.1, 2.3
- Refactor `test_server.py` to use `src/lib/` modules
- Add missing endpoints for all features
- Update schema to match full spec

---

## Prioritization Rationale

1. **Phase 1** must come first because all other features depend on the chain engine and database.
2. **Phase 2** implements the core business logic that differentiates this app.
3. **Phase 3** handles platform integration — note that for a React Native app, much of this would be native module code, so the Python library should provide the orchestration logic.
4. **Phase 4** adds polish features.
5. **Phase 5** ensures quality and maintainability.

---

## Out of Scope for Python Library

The following are platform-specific and would be implemented in React Native, not in this Python library:

- Actual push notifications (Firebase/Notifee)
- Background task registration (BGTaskScheduler)
- Native calendar access (EventKit)
- Native location services (CoreLocation)
- Audio playback (react-native-sound)
- File system access for TTS cache
- Bluetooth audio routing

The Python library should provide interfaces and orchestration; platform bindings are out of scope.

---

## Definition of Done

All tasks are complete when:
1. All acceptance criteria from spec Sections 2-12 have corresponding passing tests
2. `test_server.py` exposes all functionality via HTTP endpoints
3. Code passes `python3 -m py_compile` on all files
4. All unit tests pass (`python3 -m pytest`)
