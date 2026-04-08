# Urgent Voice Alarm - Implementation Plan

## Project Overview

The Urgent Voice Alarm app helps users make time-sensitive appointments by providing adaptive escalation chains with AI-generated voice nudges. The system computes a timeline from departure to arrival and speaks with escalating urgency as the deadline approaches.

**Current State:** Only a Python test server exists (`src/test_server.py`) with partial implementations of chain engine, parser, and voice templates. The full mobile app (React Native/Flutter) has not been started.

---

## Gap Analysis Summary

| Spec Section | Feature | Status |
|--------------|---------|--------|
| 13 | Data Persistence (SQLite schema) | ⚠️ Partial |
| 2 | Escalation Chain Engine | ⚠️ Partial |
| 3 | Reminder Parsing | ⚠️ Partial |
| 10 | Voice Personality | ⚠️ Partial |
| 11 | History & Stats | ⚠️ Partial |
| 4 | Voice & TTS Generation | ❌ Missing |
| 5 | Notification & Alarm Behavior | ❌ Missing |
| 6 | Background Scheduling | ❌ Missing |
| 7 | Calendar Integration | ❌ Missing |
| 8 | Location Awareness | ❌ Missing |
| 9 | Snooze & Dismissal Flow | ❌ Missing |
| 12 | Sound Library | ❌ Missing |
| 14 | Tests | ❌ Missing |
| - | Harness Infrastructure | ❌ Missing |
| - | Mobile App UI | ❌ Missing |

---

## Prioritized Task List

### Phase 1: Foundation (Data & Core Logic)

#### 1.1 [HIGH] Complete SQLite Schema
**Spec:** Section 13 (Data Persistence)

**Missing from current `src/test_server.py`:**
- `origin_lat`, `origin_lng`, `origin_address` in reminders table
- `calendar_event_id` in reminders
- `tts_fallback` boolean in anchors
- `snoozed_to` timestamp in anchors
- `actual_arrival` in history
- `missed_reason` in history
- `updated_at` in destination_adjustments
- `custom_sounds` table
- `calendar_sync` table
- `user_preferences` key/value table

**Tasks:**
- [ ] Create `src/lib/database/migrations.py` for versioned migrations
- [ ] Add missing columns to reminders table
- [ ] Add missing fields to anchors table
- [ ] Add missing fields to history table
- [ ] Create custom_sounds table
- [ ] Create calendar_sync table
- [ ] Enable foreign keys and WAL mode
- [ ] Create `src/lib/database/queries.py` with all CRUD operations

---

#### 1.2 [HIGH] Complete Escalation Chain Engine
**Spec:** Section 2 (Escalation Chain Engine)

**Current gaps:**
- Compressed chain logic for 10-24 min buffers is incorrect
- Missing `get_next_unfired_anchor()` function
- Anchors not sorted by timestamp in DB
- Missing retry/fire_count logic

**Tasks:**
- [ ] Fix compressed chain logic (buffer 10-24: urgent, pushing, firm, critical, alarm)
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Ensure anchors are sorted by timestamp
- [ ] Implement fire_count increment logic
- [ ] Add unit tests for TC-01 through TC-06

---

#### 1.3 [HIGH] Complete Reminder Parser
**Spec:** Section 3 (Reminder Parsing & Creation)

**Current gaps:**
- Limited keyword extraction patterns
- No LLM adapter interface
- No mock LLM adapter
- No confidence scoring display

**Tasks:**
- [ ] Create `src/lib/parsing/llm_adapter.py` interface
- [ ] Create `src/lib/parsing/mock_llm_adapter.py` for testing
- [ ] Create `src/lib/parsing/keyword_extractor.py` with enhanced patterns:
  - "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
  - "tomorrow", relative time handling
  - "dryer in 3 min" → simple_countdown
- [ ] Create `src/lib/parsing/parser.py` unified adapter with fallback
- [ ] Add unit tests for TC-01 through TC-07

---

### Phase 2: Voice & Notifications

#### 2.1 [HIGH] Voice & TTS Generation
**Spec:** Section 4 (Voice & TTS Generation)

**Current gaps:**
- No TTS adapter interface
- No mock TTS adapter
- No /tts_cache/ directory handling
- No actual ElevenLabs API integration
- No cache invalidation on delete

**Tasks:**
- [ ] Create `src/lib/voice/tts_adapter.py` interface (ITTSAdapter)
- [ ] Create `src/lib/voice/mock_tts_adapter.py` for testing
- [ ] Create `src/lib/voice/elevenlabs_adapter.py` for real API
- [ ] Create `src/lib/voice/cache_manager.py` for /tts_cache/
- [ ] Implement TTS cache invalidation on reminder delete
- [ ] Add unit tests for TC-01 through TC-05

---

#### 2.2 [HIGH] Complete Voice Personality System
**Spec:** Section 10 (Voice Personality System)

**Current gaps:**
- Only basic templates, no variations (need 3+ per tier)
- No custom personality prompt handling
- No personality storage in preferences
- No message generation with context

**Tasks:**
- [ ] Create `src/lib/voice/personality.py` with 5 built-in personalities
- [ ] Add 3+ message variations per tier per personality
- [ ] Create `src/lib/voice/message_generator.py` with variation selection
- [ ] Add custom personality prompt handling (max 200 chars)
- [ ] Create `src/lib/voice/personality_preferences.py` storage
- [ ] Add unit tests for TC-01 through TC-05

---

#### 2.3 [MEDIUM] Notification & Alarm Behavior
**Spec:** Section 5 (Notification & Alarm Behavior)

**Current gaps:**
- No DND handling
- No quiet hours
- No chain overlap serialization
- No TTS + notification sound tier escalation
- No T-0 alarm looping

**Tasks:**
- [ ] Create `src/lib/notifications/tier_escalation.py`
- [ ] Create `src/lib/notifications/dnd_handler.py`
- [ ] Create `src/lib/notifications/quiet_hours.py`
- [ ] Create `src/lib/notifications/chain_queue.py` for serialization
- [ ] Create `src/lib/notifications/alarm_loop.py`
- [ ] Add unit tests for TC-01 through TC-06

---

### Phase 3: Background & External Integrations

#### 3.1 [HIGH] Background Scheduling
**Spec:** Section 6 (Background Scheduling & Reliability)

**Current gaps:**
- No Notifee integration
- No BGAppRefreshTask/BGProcessingTask handlers
- No recovery scan on launch
- No pending anchor re-registration

**Tasks:**
- [ ] Create `src/lib/scheduling/notifee_client.py`
- [ ] Create `src/lib/scheduling/ios_background_tasks.py`
- [ ] Create `src/lib/scheduling/recovery_scan.py`
- [ ] Implement pending anchor re-registration on crash recovery
- [ ] Implement 15-minute grace window for overdue anchors
- [ ] Add late fire warning logging (>60s after scheduled)
- [ ] Add unit tests for TC-01 through TC-06

---

#### 3.2 [MEDIUM] Calendar Integration
**Spec:** Section 7 (Calendar Integration)

**Current gaps:**
- No Apple Calendar adapter (EventKit)
- No Google Calendar adapter
- No calendar sync scheduler
- No permission handling

**Tasks:**
- [ ] Create `src/lib/calendar/icalendar_adapter.py` interface
- [ ] Create `src/lib/calendar/apple_calendar_adapter.py` (EventKit)
- [ ] Create `src/lib/calendar/google_calendar_adapter.py`
- [ ] Create `src/lib/calendar/sync_scheduler.py`
- [ ] Create `src/lib/calendar/permission_handler.py`
- [ ] Add unit tests for TC-01 through TC-06

---

#### 3.3 [MEDIUM] Location Awareness
**Spec:** Section 8 (Location Awareness)

**Current gaps:**
- No CoreLocation/FusedLocationProvider integration
- No 500m geofence check
- No "LEAVE NOW" escalation logic
- No location permission request flow

**Tasks:**
- [ ] Create `src/lib/location/location_adapter.py` interface
- [ ] Create `src/lib/location/ios_location_adapter.py` (CoreLocation)
- [ ] Create `src/lib/location/android_location_adapter.py` (FusedLocationProvider)
- [ ] Create `src/lib/location/geofence_checker.py` (500m radius)
- [ ] Create `src/lib/location/leave_now_escalator.py`
- [ ] Add location permission request at first location-aware reminder
- [ ] Add unit tests for TC-01 through TC-05

---

### Phase 4: User Interaction

#### 4.1 [HIGH] Snooze & Dismissal Flow
**Spec:** Section 9 (Snooze & Dismissal Flow)

**Current gaps:**
- No tap/tap-and-hold snooze handlers
- No chain re-computation after snooze
- No Notifee re-registration after snooze
- No dismissal feedback flow
- No departure estimate adjustment

**Tasks:**
- [ ] Create `src/lib/interaction/snooze_handler.py` (tap = 1 min, tap-hold = custom)
- [ ] Create `src/lib/interaction/chain_recomputer.py`
- [ ] Create `src/lib/interaction/dismissal_feedback.py`
- [ ] Create `src/lib/interaction/feedback_storage.py`
- [ ] Implement departure estimate adjustment (+2 min per "left_too_late", cap +15)
- [ ] Add unit tests for TC-01 through TC-06

---

#### 4.2 [MEDIUM] Sound Library
**Spec:** Section 12 (Sound Library)

**Current gaps:**
- No built-in sounds
- No custom sound import
- No sound picker
- No fallback for corrupted sounds

**Tasks:**
- [ ] Create `src/lib/sounds/built_in_sounds.py` (5 per category)
- [ ] Create `src/lib/sounds/custom_import.py`
- [ ] Create `src/lib/sounds/sound_picker.py`
- [ ] Create `src/lib/sounds/fallback_handler.py`
- [ ] Add unit tests for TC-01 through TC-05

---

#### 4.3 [MEDIUM] History & Stats
**Spec:** Section 11 (History, Stats & Feedback Loop)

**Current gaps:**
- Incomplete hit_rate (trailing 7 days)
- No streak counter
- No common miss window
- No 90-day retention/archival

**Tasks:**
- [ ] Complete hit_rate calculation: `count(hit) / count(outcome != 'pending') * 100`
- [ ] Create `src/lib/stats/streak_counter.py`
- [ ] Create `src/lib/stats/common_miss_window.py`
- [ ] Create `src/lib/stats/archival.py` (90-day retention)
- [ ] Add unit tests for TC-01 through TC-07

---

### Phase 5: Mobile App & UI

#### 5.1 [HIGH] React Native App Structure
**Spec:** Mobile app requirements

**Tasks:**
- [ ] Initialize React Native project (or Flutter if preferred)
- [ ] Set up navigation (Stack + Tab)
- [ ] Create SQLite integration (react-native-sqlite-storage)
- [ ] Set up Notifee integration
- [ ] Create reminder list screen
- [ ] Create Quick Add screen (text/speech input)
- [ ] Create reminder confirmation card
- [ ] Create history screen with stats
- [ ] Create settings screen

---

#### 5.2 [MEDIUM] Calendar & Location Screens
**Tasks:**
- [ ] Create calendar sync settings screen
- [ ] Create suggestion cards UI
- [ ] Create location permission request flow
- [ ] Create origin address input

---

### Phase 6: Testing & Validation

#### 6.1 [HIGH] Unit Tests
**Tasks:**
- [ ] Chain engine determinism tests
- [ ] Parser fixture tests
- [ ] TTS adapter mock tests
- [ ] LLM adapter mock tests
- [ ] Keyword extraction tests
- [ ] Schema validation tests

---

#### 6.2 [MEDIUM] Integration Tests
**Tasks:**
- [ ] Full reminder creation flow (parse → chain → TTS → persist)
- [ ] Anchor firing flow (schedule → fire → mark fired)
- [ ] Snooze recovery flow (snooze → recompute → re-register)
- [ ] Feedback loop flow (dismiss → feedback → adjustment)

---

#### 6.3 [HIGH] Harness Infrastructure
**Tasks:**
- [ ] Create `harness/scenario_harness.py` (see AGENTS.md)
- [ ] Create scenario YAML format
- [ ] Create harness validation tests
- [ ] Document harness usage in README

---

## Dependency Graph

```
Phase 1: Foundation
├── 1.1 SQLite Schema (blocking everything)
├── 1.2 Chain Engine (blocks 2.1, 4.1)
└── 1.3 Parser (blocks 2.1)

Phase 2: Voice & Notifications
├── 2.1 TTS Generation (depends on 1.1, 1.3)
├── 2.2 Voice Personality (depends on 1.1)
└── 2.3 Notification Behavior (depends on 2.1)

Phase 3: Background & External
├── 3.1 Background Scheduling (depends on 1.1, 1.2)
├── 3.2 Calendar Integration (depends on 1.1)
└── 3.3 Location Awareness (depends on 1.1)

Phase 4: User Interaction
├── 4.1 Snooze & Dismissal (depends on 3.1)
├── 4.2 Sound Library (depends on 1.1)
└── 4.3 History & Stats (depends on 1.1, 4.1)

Phase 5: Mobile App
└── 5.1 App Structure (depends on 1.1, 2.1, 2.2, 2.3, 3.1)

Phase 6: Testing
├── 6.1 Unit Tests (depends on all Phase 1-4 features)
├── 6.2 Integration Tests (depends on 6.1)
└── 6.3 Harness (independent, can run early)
```

---

## Quick Wins (Can Start Immediately)

1. **Add unit tests to existing chain engine** - Test determinism, compressed chains
2. **Enhance keyword extractor** - More patterns for natural language
3. **Add message variations** - 3+ per tier per personality
4. **Create harness infrastructure** - `harness/scenario_harness.py`

---

## File Structure (Target)

```
src/
├── lib/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── migrations.py
│   │   └── queries.py
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── llm_adapter.py
│   │   ├── mock_llm_adapter.py
│   │   ├── keyword_extractor.py
│   │   └── parser.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── tts_adapter.py
│   │   ├── mock_tts_adapter.py
│   │   ├── elevenlabs_adapter.py
│   │   ├── cache_manager.py
│   │   ├── personality.py
│   │   └── message_generator.py
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── tier_escalation.py
│   │   ├── dnd_handler.py
│   │   ├── quiet_hours.py
│   │   ├── chain_queue.py
│   │   └── alarm_loop.py
│   ├── scheduling/
│   │   ├── __init__.py
│   │   ├── notifee_client.py
│   │   ├── ios_background_tasks.py
│   │   └── recovery_scan.py
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── icalendar_adapter.py
│   │   ├── apple_calendar_adapter.py
│   │   ├── google_calendar_adapter.py
│   │   ├── sync_scheduler.py
│   │   └── permission_handler.py
│   ├── location/
│   │   ├── __init__.py
│   │   ├── location_adapter.py
│   │   ├── ios_location_adapter.py
│   │   ├── android_location_adapter.py
│   │   ├── geofence_checker.py
│   │   └── leave_now_escalator.py
│   ├── interaction/
│   │   ├── __init__.py
│   │   ├── snooze_handler.py
│   │   ├── chain_recomputer.py
│   │   ├── dismissal_feedback.py
│   │   └── feedback_storage.py
│   ├── sounds/
│   │   ├── __init__.py
│   │   ├── built_in_sounds.py
│   │   ├── custom_import.py
│   │   ├── sound_picker.py
│   │   └── fallback_handler.py
│   └── stats/
│       ├── __init__.py
│       ├── hit_rate.py
│       ├── streak_counter.py
│       ├── common_miss_window.py
│       └── archival.py
├── test_server.py
└── __init__.py
harness/
├── __init__.py
├── scenario_harness.py
└── scenarios/
    ├── chain_engine_test.yaml
    ├── parser_test.yaml
    └── ...
tests/
├── unit/
│   ├── test_chain_engine.py
│   ├── test_parser.py
│   ├── test_tts.py
│   └── ...
└── integration/
    ├── test_reminder_creation.py
    └── ...
```

---

## Notes

- The spec is comprehensive and well-structured. Follow the test scenarios (TC-01, etc.) as acceptance criteria.
- Every feature should have a corresponding test.
- Use interfaces (e.g., `ILanguageModelAdapter`, `ITTSAdapter`) for mock-ability.
- All timestamps in ISO 8601 format (UTC internally, displayed in local time).
- Foreign keys enabled, WAL mode for SQLite.
