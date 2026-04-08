# URGENT — AI Escalating Voice Alarm: Implementation Plan

## Current State Analysis

### What Exists
- `src/test_server.py` — Proof-of-concept HTTP API (~750 lines) with:
  - Basic escalation chain computation (partial)
  - Keyword-based natural language parsing (partial)
  - Voice message template generation (partial)
  - Basic SQLite database schema (partial)
  - Hit rate calculation (partial)
- `scenarios/` — 16 YAML test scenario files (not yet executable)
- `harness/` — Empty directory (no scenario_harness.py exists)

### What Is Missing (Critical Gaps)
1. **No scenario_harness.py** — Test harness doesn't exist, scenarios cannot run
2. **No src/lib/ structure** — No modular architecture, all code in single file
3. **No mock-able interfaces** — Cannot test LLM/TTS adapters independently
4. **Incomplete database schema** — Missing columns per spec Section 13
5. **No migration system** — No versioned schema upgrades
6. **No background scheduling** — Notifee integration missing
7. **No notification service** — DND/quiet hours handling missing
8. **No snooze/dismissal flow** — Chain re-computation missing
9. **No location awareness** — Geofence comparison missing
10. **No calendar integration** — EventKit/Google Calendar missing
11. **No sound library** — Custom audio import missing
12. **No feedback loop** — Destination adjustment logic incomplete
13. **No UI layer** — Frontend screens missing

---

## Priority 1: Test Infrastructure (Critical Path Blocker)

### 1.1 Create scenario_harness.py
**Status:** Missing (blocker for all validation)
**Impact:** Cannot run any scenario tests without this

**Tasks:**
- [ ] Create `harness/scenario_harness.py` with:
  - YAML scenario loading from `/var/otto-scenarios/{project}/`
  - HTTP client for API calls
  - SQLite database inspection for `db_record` assertions
  - LLM judge integration for `llm_judge` assertions
  - Scenario runner with pass/fail reporting
  - CLI with `--project` argument
- [ ] Validate against existing scenario files
- [ ] Add README to harness/ explaining usage

### 1.2 Validate Existing Scenarios
**Status:** 16 scenarios defined but not validated
**Impact:** Unknown if current code passes existing tests

**Tasks:**
- [ ] Run all 16 scenarios against current test_server.py
- [ ] Document which scenarios pass/fail
- [ ] Identify code changes needed to make scenarios pass

---

## Priority 2: Database Foundation

### 2.1 Full Database Schema (per Spec Section 13)
**Status:** Partial — missing key tables and columns

**Tasks:**
- [ ] Create `src/lib/database.py` with:
  - `Database` class with connection management
  - WAL mode (`PRAGMA journal_mode = WAL`)
  - Foreign key enforcement (`PRAGMA foreign_keys = ON`)
  - In-memory mode for tests (`?mode=memory`)
- [ ] Implement versioned migration system:
  - `schema_v1` → `schema_vN` sequential migrations
  - Migration table tracking applied versions
- [ ] Add all tables per spec:
  - [ ] `reminders` with all spec columns (origin_lat/lng, custom_sound_path, calendar_event_id)
  - [ ] `anchors` with tts_clip_path, snoozed_to, tts_fallback
  - [ ] `history` with actual_arrival, missed_reason
  - [ ] `destination_adjustments` with updated_at
  - [ ] `calendar_sync` table
  - [ ] `custom_sounds` table
  - [ ] `user_preferences` table
- [ ] Write migration tests (TC-01 through TC-05)

---

## Priority 3: Core Library Architecture

### 3.1 Adapter Interfaces (Mock-able for Testing)
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/adapters/__init__.py`
- [ ] Create `src/lib/adapters/base.py` with abstract base classes:
  - `ILanguageModelAdapter` — LLM parsing
  - `ITTSAdapter` — Text-to-speech
  - `ICalendarAdapter` — Calendar integration
  - `ILocationAdapter` — Location services
- [ ] Implement concrete adapters:
  - [ ] `MiniMaxAdapter` — Anthropic-compatible API
  - [ ] `AnthropicAdapter` — Claude API
  - [ ] `ElevenLabsAdapter` — TTS generation
  - [ ] `AppleCalendarAdapter` — EventKit
  - [ ] `GoogleCalendarAdapter` — Google Calendar API
  - [ ] `CoreLocationAdapter` — iOS location
- [ ] Implement mock adapters:
  - [ ] `MockLLMAdapter` — Returns fixture responses
  - [ ] `MockTTSAdapter` — Writes silent audio file
  - [ ] `MockCalendarAdapter` — Returns fixture events
  - [ ] `MockLocationAdapter` — Returns fixture coordinates

### 3.2 Repository Layer
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/repositories/__init__.py`
- [ ] Create `src/lib/repositories/base.py` with:
  - Abstract base class for all repositories
  - Common CRUD operations
- [ ] Implement repositories:
  - [ ] `ReminderRepository` — CRUD for reminders
  - [ ] `AnchorRepository` — CRUD for anchors, `get_next_unfired_anchor()`
  - [ ] `HistoryRepository` — CRUD for history records
  - [ ] `PreferencesRepository` — Key-value settings
  - [ ] `AdjustmentsRepository` — Destination feedback adjustments
  - [ ] `CalendarSyncRepository` — Sync state tracking
  - [ ] `CustomSoundsRepository` — Sound library

### 3.3 Service Layer
**Status:** Partial (chain engine in test_server.py)

**Tasks:**
- [ ] Create `src/lib/services/__init__.py`
- [ ] Create `src/lib/services/chain_engine.py`:
  - Refactored from test_server.py
  - Add `get_next_unfired_anchor(reminder_id)`
  - Add deterministic chain computation (seed support)
  - Validate all test cases (TC-01 through TC-06)
- [ ] Create `src/lib/services/parser_service.py`:
  - LLM adapter orchestration
  - Keyword extraction fallback
  - ISO 8601 datetime parsing
  - "tomorrow" date resolution
  - Validate TC-01 through TC-07
- [ ] Create `src/lib/services/tts_cache_service.py`:
  - Cache clips in `/tts_cache/{reminder_id}/`
  - Handle cache invalidation on delete
  - Fallback to system sounds on TTS failure
- [ ] Create `src/lib/services/voice_personality_service.py`:
  - ElevenLabs voice ID mapping
  - Message variation rotation (min 3 per tier)
  - Custom prompt support (max 200 chars)
  - Validate TC-01 through TC-05

---

## Priority 4: User Interactions

### 4.1 Snooze Service
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/snooze_service.py`:
  - 1-minute tap snooze
  - Custom snooze picker (1, 3, 5, 10, 15 min)
  - Chain re-computation after snooze
  - Snoozed timestamp persistence for restart recovery
  - TTS confirmation: "Okay, snoozed [X] minutes"
- [ ] Write tests (TC-01 through TC-06)

### 4.2 Dismissal & Feedback Service
**Status:** Partial (basic history recording exists)

**Tasks:**
- [ ] Create `src/lib/services/dismissal_service.py`:
  - Feedback prompt presentation
  - Feedback type storage (timing_right, left_too_early, left_too_late, other)
  - Integration with feedback loop
- [ ] Write tests (TC-04 through TC-06)

### 4.3 Feedback Loop Service
**Status:** Partial (basic adjustment exists)

**Tasks:**
- [ ] Create `src/lib/services/feedback_loop_service.py`:
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2)`
  - Cap at +15 minutes maximum
  - Destination-specific tracking
- [ ] Write tests (TC-02, TC-03)

---

## Priority 5: Background & System Integration

### 5.1 Background Scheduler
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/scheduler_service.py`:
  - Notifee adapter integration
  - iOS BGTaskScheduler (`BGAppRefreshTask`, `BGProcessingTask`)
  - Individual anchor registration
  - Recovery scan on app launch
    - Fire only anchors within 15-minute grace window
    - Drop and log >15 min overdue
  - Re-register pending anchors on crash recovery
  - Late firing warning (>60 seconds)
- [ ] Write tests (TC-01 through TC-06)

### 5.2 Notification Service
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/notification_service.py`:
  - Notification tier escalation sounds:
    - Gentle chime: calm/casual
    - Pointed beep: pointed/urgent
    - Urgent siren: pushing/firm
    - Looping alarm: critical/alarm
  - DND handling:
    - Silent notifications during DND (early anchors)
    - Visual override + vibration (final 5 min)
  - Quiet hours (default 10pm-7am)
    - Queue suppressed anchors
    - Fire after quiet hours end
    - Drop >15 min overdue
  - Chain overlap serialization
  - T-0 alarm looping until user action
- [ ] Write tests (TC-01 through TC-06)

### 5.3 Location Awareness
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/location_check_service.py`:
  - Single location check at departure anchor only
  - 500m geofence radius comparison
  - Fire urgent tier if user still at origin
- [ ] Permission handling:
  - Request at first location-aware reminder
  - Graceful handling of denied permission
- [ ] No location history retention
- [ ] Write tests (TC-01 through TC-05)

---

## Priority 6: External Integrations

### 6.1 Calendar Integration
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/calendar_sync_service.py`:
  - Sync on app launch, every 15 minutes, background refresh
  - Filter events with non-empty location
  - Generate suggestion cards
  - Recurring event handling
  - Sync failure graceful degradation
  - Permission denial handling with explanation
- [ ] Write tests (TC-01 through TC-06)

### 6.2 Sound Library
**Status:** Missing

**Tasks:**
- [ ] Create `src/lib/services/sound_library_service.py`:
  - Bundle built-in sounds (5 per category: Commute, Routine, Errand)
  - Custom audio import (MP3, WAV, M4A, max 30 sec)
  - Audio transcoding to normalized format
  - Per-reminder sound selection
  - Corrupted sound fallback to category default
- [ ] Write tests (TC-01 through TC-05)

---

## Priority 7: Analytics

### 7.1 Stats Service
**Status:** Partial (basic hit rate exists)

**Tasks:**
- [ ] Enhance `src/lib/services/stats_service.py`:
  - Hit rate calculation (trailing 7 days)
  - Common miss window tracking
  - Streak counter for recurring reminders
  - actual_arrival tracking
  - 90-day data retention
  - Archive older data (accessible)
- [ ] Write tests (TC-01 through TC-07)

---

## Priority 8: UI Layer (Frontend)

### 8.1 Core Screens
**Tasks:**
- [ ] Create `src/ui/__init__.py`
- [ ] Create `src/ui/screens/__init__.py`
- [ ] `quick_add_screen.py`:
  - Text/speech input
  - Parsed interpretation confirmation card
  - Manual field correction
  - Error handling for unintelligible input
- [ ] `reminder_list_screen.py`:
  - Reminder list with status indicators
  - Calendar-sourced visual distinction
- [ ] `reminder_detail_screen.py`:
  - Edit reminder
  - Delete reminder
- [ ] `history_screen.py`:
  - Weekly hit rate display
  - Streak counter
  - Common miss window
  - Recent history list
- [ ] `settings_screen.py`:
  - Voice personality selection (5 + custom)
  - Quiet hours configuration
  - Default drive duration
  - Calendar connection management
  - Sound library access

### 8.2 Core Components
**Tasks:**
- [ ] Create `src/ui/components/__init__.py`
- [ ] `reminder_card.py`:
  - Destination, time, status display
  - Calendar icon for calendar-sourced
- [ ] `confirmation_card.py`:
  - Parsed fields display
  - Edit capability
- [ ] `stats_display.py`:
  - Hit rate, streak, miss window

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│ Priority 1: Test Infrastructure                             │
│ └── scenario_harness.py (CRITICAL BLOCKER)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Priority 2: Database Foundation                              │
│ ├── database.py (connection, migrations, WAL, FK)           │
│ └── Full schema per spec Section 13                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Priority 3: Core Library Architecture                       │
│ ├── adapters/ (LLM, TTS, Calendar, Location interfaces)    │
│ ├── repositories/ (Reminder, Anchor, History, etc.)        │
│ └── services/ (chain_engine, parser, TTS cache, voice)      │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Priority 4:     │ │ Priority 5:     │ │ Priority 6:      │
│ User Interact.  │ │ Background &    │ │ External         │
│ - Snooze        │ │ System           │ │ Integrations     │
│ - Dismissal     │ │ - Scheduler     │ │ - Calendar       │
│ - Feedback Loop │ │ - Notification  │ │ - Sound Library │
│                 │ │ - Location      │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Priority 7: Analytics                                        │
│ └── stats_service.py (hit rate, streaks, retention)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Priority 8: UI Layer                                        │
│ ├── screens/ (Quick Add, List, Detail, History, Settings)   │
│ └── components/ (cards, displays)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Test Coverage Map

| Section | Test Count | Current Status | Priority |
|---------|------------|----------------|----------|
| 2. Chain Engine | 6 | Partial | P3 |
| 3. Parsing | 7 | Partial | P3 |
| 4. TTS | 5 | None | P3 |
| 5. Notification | 6 | None | P5 |
| 6. Background | 6 | None | P5 |
| 7. Calendar | 6 | None | P6 |
| 8. Location | 5 | None | P5 |
| 9. Snooze | 6 | None | P4 |
| 10. Voice Personality | 5 | Partial | P3 |
| 11. History/Stats | 7 | Partial | P7 |
| 12. Sound Library | 5 | None | P6 |
| 13. Data Persistence | 5 | Partial | P2 |
| **Total** | **69** | **~20%** | |

---

## Files to Create

```
src/
├── lib/
│   ├── __init__.py
│   ├── database.py                 # Connection, migrations, WAL, FK
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract interfaces
│   │   ├── llm_adapter.py         # MiniMax, Anthropic, Mock
│   │   ├── tts_adapter.py         # ElevenLabs, Mock
│   │   ├── calendar_adapter.py    # Apple, Google, Mock
│   │   └── location_adapter.py    # CoreLocation, Mock
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── reminder_repository.py
│   │   ├── anchor_repository.py
│   │   ├── history_repository.py
│   │   ├── preferences_repository.py
│   │   ├── adjustments_repository.py
│   │   ├── calendar_sync_repository.py
│   │   └── custom_sounds_repository.py
│   └── services/
│       ├── __init__.py
│       ├── chain_engine.py
│       ├── parser_service.py
│       ├── tts_cache_service.py
│       ├── voice_personality_service.py
│       ├── snooze_service.py
│       ├── dismissal_service.py
│       ├── feedback_loop_service.py
│       ├── scheduler_service.py
│       ├── notification_service.py
│       ├── location_check_service.py
│       ├── calendar_sync_service.py
│       ├── sound_library_service.py
│       └── stats_service.py
├── ui/
│   ├── __init__.py
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── quick_add_screen.py
│   │   ├── reminder_list_screen.py
│   │   ├── reminder_detail_screen.py
│   │   ├── history_screen.py
│   │   └── settings_screen.py
│   └── components/
│       ├── __init__.py
│       ├── reminder_card.py
│       ├── confirmation_card.py
│       └── stats_display.py
└── app.py                          # Main entry point

harness/
├── __init__.py
└── scenario_harness.py             # Test runner
```

---

## Implementation Order (Recommended)

### Phase 1: Infrastructure (Week 1)
1. Create `harness/scenario_harness.py`
2. Run existing scenarios, document failures
3. Create `src/lib/database.py` with migrations
4. Validate database scenarios pass

### Phase 2: Core Library (Week 2)
5. Create adapter interfaces and mock adapters
6. Create repository layer
7. Create service layer (chain_engine, parser, TTS)
8. Validate chain/parsing/voice scenarios pass

### Phase 3: User Interactions (Week 3)
9. Implement snooze service
10. Implement dismissal & feedback
11. Implement feedback loop
12. Validate snooze/feedback scenarios pass

### Phase 4: Background & System (Week 4)
13. Implement scheduler service (Notifee)
14. Implement notification service
15. Implement location service
16. Validate background/notification/location scenarios pass

### Phase 5: External Integrations (Week 5)
17. Implement calendar sync service
18. Implement sound library service
19. Validate calendar/sound scenarios pass

### Phase 6: Analytics & UI (Week 6)
20. Enhance stats service
21. Build UI screens
22. Build UI components
23. End-to-end integration testing

---

## Out of Scope (Per Specification)

These features are explicitly deferred to future iterations:

- Password reset / account management (local-only v1)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing preference
- Calendar write operations
- Two-way calendar sync
- Voice recording import
- Prosody control (speed/pitch)
- Per-reminder personality override
- Export/history sharing
- Database encryption
- Full-text search on destinations

---

## Validation Commands

After implementing, run these to validate:

```bash
# Start test server
python3 src/test_server.py &

# Run all scenarios
sudo python3 harness/scenario_harness.py --project otto-matic

# Validate syntax
python3 -m py_compile harness/scenario_harness.py src/test_server.py
```
