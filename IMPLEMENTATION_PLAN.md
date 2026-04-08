# Urgent Voice Alarm - Implementation Plan

## Project Overview

The Urgent Voice Alarm app helps users make time-sensitive appointments by providing adaptive escalation chains with AI-generated voice nudges. The system computes a timeline from departure to arrival and speaks with escalating urgency as the deadline approaches.

**Current State:** A Python test server (`src/test_server.py`) exists with partial implementations of chain engine, parser, and voice templates. 16 scenario files exist in `scenarios/`. The harness infrastructure (`harness/`) is EMPTY - no harness code exists yet.

---

## Gap Analysis Summary

| Spec Section | Feature | Code Status | Test Scenarios |
|--------------|---------|-------------|----------------|
| 2 | Escalation Chain Engine | ⚠️ Partial (bugs in compressed logic) | 4 scenarios |
| 3 | Reminder Parsing | ⚠️ Partial (basic keyword extraction) | 3 scenarios |
| 10 | Voice Personality | ⚠️ Partial (basic templates, no variations) | 3 scenarios |
| 11 | History & Stats | ⚠️ Partial (basic hit rate only) | 3 scenarios |
| 13 | Data Persistence | ⚠️ Partial (missing columns/tables) | 2 scenarios |
| 4 | Voice & TTS Generation | ❌ Missing (no adapter) | 0 scenarios |
| 5 | Notification & Alarm Behavior | ❌ Missing | 0 scenarios |
| 6 | Background Scheduling | ❌ Missing | 0 scenarios |
| 7 | Calendar Integration | ❌ Missing | 0 scenarios |
| 8 | Location Awareness | ❌ Missing | 0 scenarios |
| 9 | Snooze & Dismissal Flow | ❌ Missing | 0 scenarios |
| 12 | Sound Library | ❌ Missing | 0 scenarios |
| - | Harness Infrastructure | ❌ Missing (empty `harness/` dir) | 16 scenarios ready |
| - | Mobile App UI | ❌ Missing (React Native not started) | 0 scenarios |

---

## Current Code Issues (Must Fix)

### `src/test_server.py` - Specific Implementation Gaps

**Chain Engine Bugs (`compute_escalation_chain()`):**
1. Line ~91: Compressed logic for buffer 20-24 min uses wrong tier calculation
2. Line ~96: Compressed logic for buffer 10-24 min has incorrect minutes_before values
3. Line ~104: Minimum chain (≤5 min) needs to include 'critical' tier per spec
4. Missing: `get_next_unfired_anchor(reminder_id)` function
5. Missing: Deterministic chain computation (same inputs = same outputs)

**Parser Bugs (`parse_reminder_natural()`):**
1. Limited regex patterns for time extraction
2. No support for "tomorrow" date resolution edge cases
3. Missing LLM adapter interface (no mock-ability)
4. `reminder_type` not properly set based on input patterns

**Voice Templates (`VOICE_PERSONALITIES`):**
1. Only 1 template per tier per personality (needs 3+ per spec 10.3)
2. Missing 'custom' personality support
3. No variation selection logic (random or rotation)

**Database (`init_db()`):**
1. Missing columns per spec Section 13 schema
2. No migration versioning
3. No WAL mode
4. No foreign key enforcement

**Stats (`calculate_hit_rate()`):**
1. Basic implementation, missing trailing 7-day filter
2. Missing streak counter
3. Missing common miss window
4. No 90-day archival

---

## Prioritized Task List

### Phase 1: Foundation (Data & Core Logic)

#### 1.1 [CRITICAL] Create Harness Infrastructure
**Required before any scenario testing can occur**

**Current state:** `harness/` directory is EMPTY - no Python files exist

**Dependencies:** None (can start immediately)

**Tasks:**
- [ ] Create `harness/__init__.py` - package init
- [ ] Create `harness/scenario_harness.py` - main entry point with CLI (`--project`, `--scenario-dir`, `--verbose`)
- [ ] Create `harness/lib/__init__.py` - lib package init
- [ ] Create `harness/lib/scenario_loader.py` - YAML scenario loader with metadata parsing
- [ ] Create `harness/lib/http_client.py` - HTTP client for API testing
- [ ] Create `harness/lib/db_checker.py` - SQLite assertion checker (verify records exist)
- [ ] Create `harness/lib/llm_judge.py` - LLM-based assertion judge (uses sonnet-4-20250514)
- [ ] Create `harness/lib/assertions.py` - assertion types (http_status, db_record, llm_judge)
- [ ] Add test runner with pass/fail reporting
- [ ] Add `/var/otto-scenarios/` directory setup (requires sudo)
- [ ] Add integration with OTTO_SCENARIO_DIR env var

**Reference:** AGENTS.md says: `sudo python3 harness/scenario_harness.py --project otto-matic`

---

#### 1.2 [HIGH] Complete SQLite Schema
**Spec:** Section 13 (Data Persistence)

**Current gaps in `src/test_server.py` `init_db()`:**
- Missing: `origin_lat`, `origin_lng`, `origin_address` in reminders
- Missing: `calendar_event_id` in reminders
- Missing: `tts_fallback` boolean in anchors
- Missing: `snoozed_to` timestamp in anchors
- Missing: `actual_arrival` in history
- Missing: `missed_reason` in history
- Missing: `updated_at` in destination_adjustments
- Missing: `custom_sounds` table
- Missing: `calendar_sync` table
- Missing: `migrations` table for version tracking
- Missing: WAL mode and foreign keys enforcement

**Tasks:**
- [ ] Create `src/lib/database/__init__.py`
- [ ] Create `src/lib/database/connection.py` with WAL mode + FK enforcement
- [ ] Create `src/lib/database/migrations.py` with versioned migrations (v1-vN)
- [ ] Refactor `init_db()` in test_server.py to use migrations
- [ ] Add missing columns: reminders (origin_lat, origin_lng, origin_address, calendar_event_id)
- [ ] Add missing fields: anchors (tts_fallback, snoozed_to)
- [ ] Add missing fields: history (actual_arrival, missed_reason)
- [ ] Add destination_adjustments.updated_at
- [ ] Create custom_sounds table
- [ ] Create calendar_sync table
- [ ] Update existing scenarios with correct field names if needed

---

#### 1.3 [HIGH] Fix Escalation Chain Engine
**Spec:** Section 2 (Escalation Chain Engine)

**Current bugs:**
1. Compressed chain logic is incorrect - spec says:
   - buffer ≥25 min: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
   - buffer 10-24 min: compressed (start at urgent) - **currently wrong**
   - buffer 5-9 min: firm, critical, alarm
   - buffer ≤5 min: minimum (firm, critical, alarm)
2. Missing `get_next_unfired_anchor()` function
3. Anchors not consistently sorted by timestamp

**Tasks:**
- [ ] Fix compressed chain logic: buffer 10-24 min should be (urgent, pushing, firm, critical, alarm)
- [ ] Fix compressed chain logic: buffer 20-24 min should include pushing tier
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Ensure anchors are sorted by timestamp
- [ ] Add fire_count increment logic
- [ ] Update existing scenarios with correct assertions

**Existing test scenarios:**
- `scenarios/chain-full-30min.yaml` (TC-01)
- `scenarios/chain-compressed-15min.yaml` (TC-02)
- `scenarios/chain-minimum-3min.yaml` (TC-03)
- `scenarios/chain-invalid-rejected.yaml` (TC-04)

---

#### 1.4 [HIGH] Complete Reminder Parser
**Spec:** Section 3 (Reminder Parsing & Creation)

**Current gaps:**
- Limited keyword extraction patterns
- No LLM adapter interface
- No mock LLM adapter for testing
- Missing "tomorrow" date resolution (partially done)
- Missing reminder_type enum handling (simple_countdown)

**Tasks:**
- [ ] Create `src/lib/parsing/llm_adapter.py` interface
- [ ] Create `src/lib/parsing/mock_llm_adapter.py` for testing
- [ ] Enhance `src/lib/parsing/keyword_extractor.py`:
  - "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
  - "dryer in 3 min" → simple_countdown
  - Better destination extraction
- [ ] Add "tomorrow" date resolution (already in test_server.py, verify correctness)
- [ ] Add unit tests for TC-01 through TC-07

**Existing test scenarios:**
- `scenarios/parse-natural-language.yaml` (TC-01)
- `scenarios/parse-simple-countdown.yaml` (TC-02)
- `scenarios/parse-tomorrow.yaml` (TC-03)

---

### Phase 2: Voice & Notifications

#### 2.1 [HIGH] Voice & TTS Generation
**Spec:** Section 4 (Voice & TTS Generation)

**Current state:** Only basic message templates exist, no actual TTS

**Tasks:**
- [ ] Create `src/lib/voice/tts_adapter.py` interface (ITTSAdapter)
- [ ] Create `src/lib/voice/mock_tts_adapter.py` for testing
- [ ] Create `src/lib/voice/elevenlabs_adapter.py` for real API
- [ ] Create `src/lib/voice/cache_manager.py` for /tts_cache/
- [ ] Implement TTS cache invalidation on reminder delete
- [ ] Add `/tts/generate` endpoint to test_server.py
- [ ] Add unit tests for TC-01 through TC-05

---

#### 2.2 [HIGH] Complete Voice Personality System
**Spec:** Section 10 (Voice Personality System)

**Current gaps:**
- Only basic templates, no variations (need 3+ per tier)
- No custom personality prompt handling
- No personality storage in preferences

**Tasks:**
- [ ] Create `src/lib/voice/personality.py` with 5 built-in personalities
- [ ] Add 3+ message variations per tier per personality
- [ ] Create `src/lib/voice/message_generator.py` with variation selection
- [ ] Add custom personality prompt handling (max 200 chars)
- [ ] Create `src/lib/voice/personality_preferences.py` storage
- [ ] Add `/voice/message` endpoint with variation support
- [ ] Add unit tests for TC-01 through TC-05

**Existing test scenarios:**
- `scenarios/voice-coach-personality.yaml` (TC-01)
- `scenarios/voice-no-nonsense.yaml` (TC-02)
- `scenarios/voice-all-personalities.yaml`

---

#### 2.3 [MEDIUM] Notification & Alarm Behavior
**Spec:** Section 5 (Notification & Alarm Behavior)

**Current state:** Not implemented

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

**Current state:** Not implemented

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

**Current state:** Not implemented

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

**Current state:** Not implemented

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

**Current state:** Not implemented

**Tasks:**
- [ ] Create `src/lib/interaction/snooze_handler.py` (tap = 1 min, tap-hold = custom)
- [ ] Create `src/lib/interaction/chain_recomputer.py`
- [ ] Create `src/lib/interaction/dismissal_feedback.py`
- [ ] Create `src/lib/interaction/feedback_storage.py`
- [ ] Implement departure estimate adjustment (+2 min per "left_too_late", cap +15)
- [ ] Add `/snooze` and `/dismiss` endpoints to test_server.py
- [ ] Add unit tests for TC-01 through TC-06

---

#### 4.2 [MEDIUM] Sound Library
**Spec:** Section 12 (Sound Library)

**Current state:** Not implemented

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
- Hit rate calculation incomplete (needs trailing 7 days)
- No streak counter
- No common miss window
- No 90-day retention/archival
- Missing `actual_arrival`, `missed_reason` in history

**Tasks:**
- [ ] Complete hit_rate calculation: `count(hit) / count(outcome != 'pending') * 100`
- [ ] Create `src/lib/stats/streak_counter.py`
- [ ] Create `src/lib/stats/common_miss_window.py`
- [ ] Create `src/lib/stats/archival.py` (90-day retention)
- [ ] Add `/stats/streak` endpoint
- [ ] Add `/stats/common-miss-window` endpoint
- [ ] Add unit tests for TC-01 through TC-07

**Existing test scenarios:**
- `scenarios/history-record-outcome.yaml`
- `scenarios/history-record-miss-feedback.yaml`
- `scenarios/stats-hit-rate.yaml`

---

### Phase 5: Mobile App & UI

#### 5.1 [HIGH] React Native App Structure
**Spec:** Mobile app requirements

**Tasks:**
- [ ] Initialize React Native project
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

## Dependency Graph

```
Phase 1: Foundation
├── 1.1 Harness Infrastructure ──────────────────┐  (unblocks ALL scenario testing)
├── 1.2 SQLite Schema ─────────────────────────────┼── (foundation for all features)
├── 1.3 Chain Engine ──────────────────────────────┼── (blocks: 2.1, 3.1, 4.1)
└── 1.4 Parser ────────────────────────────────────┴── (blocks: 2.1)

Phase 2: Voice & Notifications
├── 2.1 TTS Generation ──────────────────────────────┼── (depends on 1.2, 1.4)
├── 2.2 Voice Personality ──────────────────────────┼── (depends on 1.2)
└── 2.3 Notification Behavior ──────────────────────┴── (depends on 2.1)

Phase 3: Background & External
├── 3.1 Background Scheduling ─────────────────────┬── (depends on 1.2, 1.3)
├── 3.2 Calendar Integration ────────────────────────┼── (depends on 1.2)
└── 3.3 Location Awareness ────────────────────────┴── (depends on 1.2)

Phase 4: User Interaction
├── 4.1 Snooze & Dismissal ─────────────────────────┬── (depends on 1.3)
├── 4.2 Sound Library ─────────────────────────────┴── (depends on 1.2)
└── 4.3 History & Stats ───────────────────────────── (depends on 1.2, 4.1)

Phase 5: Mobile App
└── 5.1 App Structure (React Native) ────────────────── (depends on all above)
```

---

## Quick Wins (Can Start Immediately, No Dependencies)

1. **Create harness infrastructure** - `harness/scenario_harness.py` - **unblocks all 16 scenario tests**
2. **Fix chain engine bugs** - compressed chain logic in `compute_escalation_chain()` is incorrect
3. **Add message variations** - 3+ variations per tier per personality in `VOICE_PERSONALITIES`
4. **Enhance keyword extractor** - more regex patterns in `parse_reminder_natural()`
5. **Complete SQLite schema** - add missing columns to `init_db()`

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
└── lib/
    ├── __init__.py
    ├── scenario_loader.py
    ├── http_client.py
    ├── db_checker.py
    ├── llm_judge.py
    └── assertions.py
scenarios/
├── chain-full-30min.yaml          # Section 2, TC-01
├── chain-compressed-15min.yaml    # Section 2, TC-02
├── chain-minimum-3min.yaml        # Section 2, TC-03
├── chain-invalid-rejected.yaml    # Section 2, TC-04
├── parse-natural-language.yaml    # Section 3, TC-01
├── parse-simple-countdown.yaml    # Section 3, TC-02
├── parse-tomorrow.yaml            # Section 3, TC-03
├── voice-coach-personality.yaml    # Section 10, TC-01
├── voice-no-nonsense.yaml         # Section 10, TC-02
├── voice-all-personalities.yaml   # Section 10
├── history-record-outcome.yaml   # Section 11
├── history-record-miss-feedback.yaml  # Section 11, TC-05
├── stats-hit-rate.yaml            # Section 11, TC-01
├── reminder-creation-crud.yaml    # Section 13
├── reminder-creation-cascade-delete.yaml  # Section 13, TC-03
└── README.md
```

---

## Notes

- The spec is comprehensive and well-structured. Follow the test scenarios (TC-01, etc.) as acceptance criteria.
- Every feature should have a corresponding test scenario.
- Use interfaces (e.g., `ILanguageModelAdapter`, `ITTSAdapter`) for mock-ability.
- All timestamps in ISO 8601 format (UTC internally, displayed in local time).
- Foreign keys enabled, WAL mode for SQLite.
- **CRITICAL:** The harness infrastructure (Phase 1.1) must be built first to enable any testing.
