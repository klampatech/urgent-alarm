# Urgent Alarm — Implementation Plan

## Analysis Summary

**Current State:** `src/test_server.py` provides a basic Python server with:
- Core chain engine (incomplete)
- Keyword-based parser (no LLM adapter)
- Pre-written voice message templates
- Basic SQLite schema
- HTTP test endpoints

**Gap Analysis:** The implementation covers ~15% of spec requirements. Major areas are missing entirely.

---

## Priority 1: Foundation (Must Have First)

### 1.1 Database & Schema Migration System
**Priority:** Critical — all other components depend on data persistence

| Task | Description |
|------|-------------|
| `DB-1` | Create migration system with versioned migrations (`migrations/` directory) |
| `DB-2` | Implement full schema from spec §13.2 (all 7 tables) |
| `DB-3` | Add missing columns: `reminders.custom_sound_path`, `origin_lat/lng`, `origin_address`, `calendar_event_id` |
| `DB-4` | Add missing columns: `anchors.tts_fallback`, `snoozed_to` |
| `DB-5` | Enable foreign key enforcement and WAL mode |
| `DB-6` | Create `Database.get_in_memory_instance()` for tests |
| `DB-7` | Write migration tests (TC-01 through TC-05 from spec) |

**Dependencies:** None
**Tests Required:** TC-01 through TC-05 (§13.5)

---

### 1.2 Chain Engine Service
**Priority:** Critical — core app functionality

| Task | Description |
|------|-------------|
| `CE-1` | Refactor chain computation to deterministic, testable service class |
| `CE-2` | Implement `get_next_unfired_anchor(reminder_id)` function |
| `CE-3` | Implement chain validation: `arrival_time > departure_time + minimum_drive_time` |
| `CE-4` | Write unit tests for all 6 test scenarios (TC-01 through TC-06) |
| `CE-5` | Verify chain determinism (same inputs = same outputs) |

**Dependencies:** DB-1, DB-2
**Tests Required:** TC-01 through TC-06 (§2.5)

---

### 1.3 LLM Adapter Interface
**Priority:** High — enables natural language parsing

| Task | Description |
|------|-------------|
| `LLM-1` | Create `ILanguageModelAdapter` interface (abstract class) |
| `LLM-2` | Implement `MiniMaxAdapter` with environment variable configuration |
| `LLM-3` | Implement `AnthropicAdapter` as alternative |
| `LLM-4` | Create `MockLanguageModelAdapter` for testing |
| `LLM-5` | Implement keyword extraction fallback with regex patterns |
| `LLM-6` | Write parser tests (TC-01 through TC-07) |

**Dependencies:** None
**Tests Required:** TC-01 through TC-07 (§3.5)

---

## Priority 2: Core App Logic

### 2.1 TTS Adapter Interface
**Priority:** High — voice output generation

| Task | Description |
|------|-------------|
| `TTS-1` | Create `ITTSAdapter` interface (abstract class) |
| `TTS-2` | Implement `ElevenLabsAdapter` with environment variable configuration |
| `TTS-3` | Create `MockTTSAdapter` for testing (writes silent file) |
| `TTS-4` | Implement TTS cache directory structure: `/tts_cache/{reminder_id}/` |
| `TTS-5` | Implement cache invalidation on reminder deletion |
| `TTS-6` | Implement fallback mechanism (system sound + notification text) |
| `TTS-7` | Write TTS tests (TC-01 through TC-05) |

**Dependencies:** DB-2, LLM-1
**Tests Required:** TC-01 through TC-05 (§4.5)

---

### 2.2 Reminder Creation Flow
**Priority:** High — user-facing creation

| Task | Description |
|------|-------------|
| `RC-1` | Implement full reminder creation: parse → chain → TTS → persist |
| `RC-2` | Display parsed interpretation confirmation card |
| `RC-3` | Implement manual field correction before confirm |
| `RC-4` | Generate TTS clips for all anchors at creation time |
| `RC-5` | Write integration tests for full creation flow |

**Dependencies:** CE-1, LLM-1, TTS-1
**Tests Required:** End-to-end creation flow

---

### 2.3 Voice Personality System
**Priority:** High — defines app voice/feel

| Task | Description |
|------|-------------|
| `VP-1` | Implement `VoicePersonalityService` with 5 built-in personalities |
| `VP-2` | Add message variation (minimum 3 templates per tier per personality) |
| `VP-3` | Implement custom prompt mode (max 200 chars) |
| `VP-4` | Store selected personality in user_preferences |
| `VP-5` | Ensure existing reminders retain original personality |
| `VP-6` | Write personality tests (TC-01 through TC-05) |

**Dependencies:** TTS-1
**Tests Required:** TC-01 through TC-05 (§10.5)

---

### 2.4 Notification & Alarm Behavior
**Priority:** High — user notification system

| Task | Description |
|------|-------------|
| `NB-1` | Implement notification tier escalation logic (gentle → siren → alarm) |
| `NB-2` | Implement DND awareness (silent pre-5min, visual override final 5min) |
| `NB-3` | Implement quiet hours suppression (configurable start/end) |
| `NB-4` | Implement overdue anchor queue (max 15 min before drop) |
| `NB-5` | Implement chain overlap serialization (queue and wait) |
| `NB-6` | Implement T-0 alarm looping until user action |
| `NB-7` | Write notification tests (TC-01 through TC-06) |

**Dependencies:** CE-1, TTS-1
**Tests Required:** TC-01 through TC-06 (§5.5)

---

## Priority 3: Background & Reliability

### 3.1 Background Scheduling
**Priority:** Critical — app must fire reminders when backgrounded

| Task | Description |
|------|-------------|
| `BG-1` | Implement Notifee integration for anchor scheduling |
| `BG-2` | Register each anchor as individual background task |
| `BG-3` | Implement iOS BGAppRefreshTask / BGProcessingTask |
| `BG-4` | Implement recovery scan on app launch |
| `BG-5` | Re-register pending anchors after crash/termination |
| `BG-6` | Log late firing warnings (>60s after scheduled) |
| `BG-7` | Write background tests (TC-01 through TC-06) |

**Dependencies:** CE-1, DB-2
**Tests Required:** TC-01 through TC-06 (§6.5)

---

### 3.2 Snooze & Dismissal Flow
**Priority:** High — user interaction with reminders

| Task | Description |
|------|-------------|
| `SD-1` | Implement tap snooze (1 minute) |
| `SD-2` | Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min) |
| `SD-3` | Implement chain re-computation after snooze |
| `SD-4` | Re-register snoozed anchors with Notifee |
| `SD-5` | Implement dismissal feedback prompt |
| `SD-6` | Store feedback and trigger departure estimate adjustment |
| `SD-7` | Write snooze/dismissal tests (TC-01 through TC-06) |

**Dependencies:** CE-1, BG-1
**Tests Required:** TC-01 through TC-06 (§9.5)

---

### 3.3 Calendar Integration
**Priority:** Medium — optional but valuable

| Task | Description |
|------|-------------|
| `CI-1` | Create `ICalendarAdapter` interface |
| `CI-2` | Implement `AppleCalendarAdapter` via EventKit |
| `CI-3` | Implement `GoogleCalendarAdapter` via Google Calendar API |
| `CI-4` | Implement calendar sync (launch + every 15 min + background) |
| `CI-5` | Generate suggestion cards for events with locations |
| `CI-6` | Handle permission denial with explanation banner |
| `CI-7` | Handle sync failure graceful degradation |
| `CI-8` | Write calendar tests (TC-01 through TC-06) |

**Dependencies:** DB-2, RC-1
**Tests Required:** TC-01 through TC-06 (§7.5)

---

## Priority 4: Advanced Features

### 4.1 Location Awareness
**Priority:** Medium — optional enhancement

| Task | Description |
|------|-------------|
| `LA-1` | Implement single location check at departure anchor |
| `LA-2` | Resolve origin from user-specified address or device location |
| `LA-3` | Implement geofence comparison (500m radius) |
| `LA-4` | Implement immediate escalation if user still at origin |
| `LA-5` | Request location permission at first location-aware reminder |
| `LA-6` | Write location tests (TC-01 through TC-05) |

**Dependencies:** BG-1, CE-1
**Tests Required:** TC-01 through TC-05 (§8.5)

---

### 4.2 History, Stats & Feedback Loop
**Priority:** Medium — learning system

| Task | Description |
|------|-------------|
| `HS-1` | Implement hit rate calculation (trailing 7 days) |
| `HS-2` | Implement streak counter (increment on hit, reset on miss) |
| `HS-3` | Implement common miss window identification |
| `HS-4` | Implement feedback loop adjustment (2 min per late, cap 15 min) |
| `HS-5` | Implement 90-day retention/archival |
| `HS-6` | Write stats tests (TC-01 through TC-07) |

**Dependencies:** DB-2, SD-5
**Tests Required:** TC-01 through TC-07 (§11.5)

---

### 4.3 Sound Library
**Priority:** Low — nice to have

| Task | Description |
|------|-------------|
| `SL-1` | Bundle 5 built-in sounds per category (commute, routine, errand) |
| `SL-2` | Implement custom sound import (MP3, WAV, M4A, max 30 sec) |
| `SL-3` | Implement sound selection per reminder |
| `SL-4` | Implement corrupted sound fallback |
| `SL-5` | Write sound library tests (TC-01 through TC-05) |

**Dependencies:** DB-2
**Tests Required:** TC-01 through TC-05 (§12.5)

---

## Priority 5: Testing & Integration

### 5.1 Unit Test Suite
**Priority:** Critical — all acceptance criteria must pass

| Task | Description |
|------|-------------|
| `UT-1` | Chain engine determinism tests |
| `UT-2` | Parser fixtures and mock tests |
| `UT-3` | TTS adapter mock tests |
| `UT-4` | LLM adapter mock tests |
| `UT-5` | Keyword extraction tests |
| `UT-6` | Schema validation tests |
| `UT-7` | Voice personality tests |

**Dependencies:** CE-1, LLM-1, TTS-1, VP-1
**Command:** `pytest harness/` (from AGENTS.md)

---

### 5.2 Integration Test Suite
**Priority:** Critical — full flows must work

| Task | Description |
|------|-------------|
| `IT-1` | Full reminder creation flow (parse → chain → TTS → persist) |
| `IT-2` | Anchor firing flow (schedule → fire → mark fired) |
| `IT-3` | Snooze recovery flow (snooze → recompute → re-register) |
| `IT-4` | Feedback loop (dismiss → feedback → adjustment applied) |

**Dependencies:** All Priority 1-4 tasks

---

### 5.3 E2E Tests (Detox)
**Priority:** Medium — user-facing validation

| Task | Description |
|------|-------------|
| `E2E-1` | Quick Add flow (text/speech input) |
| `E2E-2` | Reminder confirmation flow |
| `E2E-3` | Anchor firing sequence |
| `E2E-4` | Snooze interaction |
| `E2E-5` | Dismissal feedback |
| `E2E-6` | Settings navigation |
| `E2E-7` | Sound library browsing |

**Dependencies:** All app UI components (future React Native/Flutter work)

---

## Task Dependency Graph

```
Priority 1: Foundation
├── DB-1 → DB-2 → DB-7 (Database)
├── CE-1 → CE-5 (Chain Engine)
│   └── Requires: DB-1, DB-2
└── LLM-1 → LLM-6 (LLM Adapter)
    └── Requires: DB-1

Priority 2: Core App Logic
├── TTS-1 → TTS-7 (TTS Adapter)
│   └── Requires: DB-2, LLM-1
├── RC-1 → RC-5 (Reminder Creation)
│   └── Requires: CE-1, LLM-1, TTS-1
├── VP-1 → VP-6 (Voice Personality)
│   └── Requires: TTS-1
└── NB-1 → NB-7 (Notification Behavior)
    └── Requires: CE-1, TTS-1

Priority 3: Background & Reliability
├── BG-1 → BG-7 (Background Scheduling)
│   └── Requires: CE-1, DB-2
├── SD-1 → SD-7 (Snooze/Dismissal)
│   └── Requires: CE-1, BG-1
└── CI-1 → CI-8 (Calendar Integration)
    └── Requires: DB-2, RC-1

Priority 4: Advanced Features
├── LA-1 → LA-6 (Location Awareness)
│   └── Requires: BG-1, CE-1
├── HS-1 → HS-6 (History/Stats)
│   └── Requires: DB-2, SD-5
└── SL-1 → SL-5 (Sound Library)
    └── Requires: DB-2

Priority 5: Testing
├── UT-1 → UT-7 (Unit Tests)
│   └── Requires: CE-1, LLM-1, TTS-1, VP-1
├── IT-1 → IT-4 (Integration Tests)
│   └── Requires: All Priority 1-4
└── E2E-1 → E2E-7 (E2E Tests)
    └── Requires: All app UI
```

---

## Implementation Order

1. **Phase 1 (Foundation):** DB-1 → DB-2 → CE-1 → LLM-1
2. **Phase 2 (Core):** TTS-1 → RC-1 → VP-1 → NB-1
3. **Phase 3 (Reliability):** BG-1 → SD-1 → CI-1
4. **Phase 4 (Advanced):** LA-1 → HS-1 → SL-1
5. **Phase 5 (Testing):** UT-1 → IT-1 → E2E-1

---

## Quick Wins (Can Ship Early)

| Task | Value | Effort |
|------|-------|--------|
| DB-6 (In-memory test DB) | Enables TDD | Low |
| LLM-5 (Keyword fallback) | Graceful degradation | Low |
| CE-4 (Chain unit tests) | Confidence in core logic | Medium |
| TTS-3 (Mock TTS adapter) | Testable TTS system | Low |
| VP-2 (Message variation) | Less robotic feel | Low |
| HS-2 (Streak counter) | Gamification | Low |

---

## Out of Scope (Per Spec)

- Password reset / account management
- Smart home integration
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Calendar write operations
- Two-way calendar sync
- Continuous location tracking
- Sound recording
- Sound trimming/editing
- Cloud sound library
