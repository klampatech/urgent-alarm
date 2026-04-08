# URGENT — AI Escalating Voice Alarm: Implementation Plan

## Gap Analysis Summary

The specification defines a comprehensive voice alarm system with 13 major subsystems. The current codebase (`src/test_server.py`) provides only a **proof-of-concept HTTP API** with basic chain computation and keyword parsing — it represents ~15% of the required functionality.

---

## Priority 1: Foundation (Must Implement First)

These components are dependencies for all other features.

### 1.1 Database Schema & Migrations
**Status:** Partial (basic schema exists, missing key columns and migration system)
**Gap:** No migration versioning, missing columns per spec, no WAL mode, no foreign key enforcement

**Tasks:**
- [ ] Create `src/lib/database.py` with SQLite connection management
- [ ] Implement versioned migration system (`schema_v1` through `schema_vN`)
- [ ] Add missing columns per spec:
  - `reminders.origin_lat`, `reminders.origin_lng`, `reminders.origin_address`
  - `reminders.calendar_event_id`
  - `reminders.custom_sound_path`
  - `anchors.tts_clip_path`, `anchors.snoozed_to`
  - `history.actual_arrival`, `history.missed_reason`
  - `destination_adjustments.updated_at`
  - `calendar_sync` table
  - `custom_sounds` table
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Add in-memory database support for tests
- [ ] Write migration tests (TC-01 through TC-05 from spec)

### 1.2 Escalation Chain Engine (Refinement)
**Status:** Partial (basic chain computation exists)
**Gap:** Missing `get_next_unfired_anchor()`, no deterministic testing support, TTS clip path not in anchors

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add `tts_clip_path` and `tts_fallback` columns to anchor storage
- [ ] Add deterministic chain computation with seed support for unit testing
- [ ] Add `get_next_unfired_anchor` tests (TC-05 from spec)
- [ ] Add chain determinism test (TC-06 from spec)

### 1.3 Data Persistence Layer
**Status:** None
**Gap:** No repository pattern, no ORM-like abstraction

**Tasks:**
- [ ] Create `src/lib/repositories/reminder_repository.py`
- [ ] Create `src/lib/repositories/anchor_repository.py`
- [ ] Create `src/lib/repositories/history_repository.py`
- [ ] Create `src/lib/repositories/preferences_repository.py`
- [ ] Create `src/lib/repositories/adjustments_repository.py`
- [ ] Write integration tests for each repository

---

## Priority 2: Core Features (User-Facing)

### 2.1 LLM Adapter & Parsing Service
**Status:** Partial (keyword parsing exists, no LLM adapter)
**Gap:** No mock-able interface, no LLM integration, no confirmation UI

**Tasks:**
- [ ] Create `src/lib/adapters/llm_adapter.py` with `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible)
- [ ] Implement `AnthropicAdapter`
- [ ] Implement `MockLLMAdapter` for testing
- [ ] Implement `KeywordExtractionAdapter` as fallback
- [ ] Create `src/lib/services/parser_service.py` that orchestrates LLM → keyword fallback
- [ ] Add `parse_reminder_natural()` tests (TC-01 through TC-07 from spec)
- [ ] Add ISO 8601 datetime support
- [ ] Add "X-minute" (hyphenated) time format support

### 2.2 Voice & TTS Generation
**Status:** Partial (text message generation exists, no TTS)
**Gap:** No ElevenLabs integration, no file caching, no mock-able interface

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py` with `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping per personality
- [ ] Implement `MockTTSAdapter` for testing
- [ ] Create `src/lib/services/tts_cache_service.py`
  - Cache clips in `/tts_cache/{reminder_id}/`
  - Handle cache invalidation on reminder delete
  - Implement fallback to system sounds on TTS failure
- [ ] Add TTS generation at reminder creation time only
- [ ] Write TTS adapter tests (TC-01 through TC-05 from spec)

### 2.3 Voice Personality System
**Status:** Partial (templates exist, no variation rotation)
**Gap:** No ElevenLabs voice IDs, no variation rotation, no custom prompt support

**Tasks:**
- [ ] Add ElevenLabs voice IDs to personality definitions
- [ ] Add system prompt fragments for message generation
- [ ] Implement message variation rotation (min 3 per tier per personality)
- [ ] Add "Custom" personality mode with user prompt (max 200 chars)
- [ ] Store selected personality in user_preferences
- [ ] Add personality tests (TC-01 through TC-05 from spec)

### 2.4 Snooze & Dismissal Flow
**Status:** None
**Gap:** No snooze handling, no dismissal feedback, no chain re-computation

**Tasks:**
- [ ] Create `src/lib/services/snooze_service.py`
  - Implement 1-minute tap snooze
  - Implement custom snooze picker (1, 3, 5, 10, 15 min)
  - Implement chain re-computation after snooze
- [ ] Create `src/lib/services/dismissal_service.py`
  - Implement feedback prompt
  - Store feedback in history
- [ ] Add TTS confirmation for snooze: "Okay, snoozed [X] minutes"
- [ ] Persist snoozed timestamps for app restart recovery
- [ ] Write snooze/dismissal tests (TC-01 through TC-06 from spec)

---

## Priority 3: Background & System Integration

### 3.1 Background Scheduling
**Status:** None
**Gap:** No Notifee integration, no iOS BGTaskScheduler, no recovery scan

**Tasks:**
- [ ] Create `src/lib/services/scheduler_service.py`
- [ ] Implement Notifee adapter with iOS BGTaskScheduler integration
- [ ] Implement `BGAppRefreshTask` for near-accurate timing
- [ ] Implement `BGProcessingTask` for TTS clip pre-warming
- [ ] Implement recovery scan on app launch
  - Fire only anchors within 15-minute grace window
  - Drop and log anchors >15 min overdue
- [ ] Re-register pending anchors on crash recovery
- [ ] Add late firing warning log (>60 seconds)
- [ ] Write background scheduling tests (TC-01 through TC-06 from spec)

### 3.2 Notification & Alarm Behavior
**Status:** None
**Gap:** No notification handling, no DND awareness, no quiet hours, no chain serialization

**Tasks:**
- [ ] Create `src/lib/services/notification_service.py`
- [ ] Implement notification tier escalation sounds:
  - Gentle chime: calm/casual
  - Pointed beep: pointed/urgent
  - Urgent siren: pushing/firm
  - Looping alarm: critical/alarm
- [ ] Implement DND handling:
  - Silent notifications during DND for early anchors
  - Visual override + vibration for final 5 minutes
- [ ] Implement quiet hours (default 10pm-7am)
  - Queue suppressed anchors, fire after quiet hours end
  - Drop anchors >15 min overdue
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping until user action
- [ ] Write notification tests (TC-01 through TC-06 from spec)

### 3.3 Location Awareness
**Status:** None
**Gap:** No location handling, no geofence comparison

**Tasks:**
- [ ] Create `src/lib/adapters/location_adapter.py` with `ILocationAdapter` interface
- [ ] Implement `CoreLocationAdapter` (iOS)
- [ ] Implement `FusedLocationAdapter` (Android)
- [ ] Implement `MockLocationAdapter` for testing
- [ ] Create `src/lib/services/location_check_service.py`
  - Single location check at departure anchor only
  - 500m geofence radius comparison
  - Fire urgent tier if user still at origin
- [ ] Request location permission at first location-aware reminder
- [ ] Handle denied permission gracefully
- [ ] Write location tests (TC-01 through TC-05 from spec)

---

## Priority 4: Calendar & External Integration

### 4.1 Calendar Integration
**Status:** None
**Gap:** No calendar adapters, no sync service, no suggestion UI

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py` with `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement `MockCalendarAdapter` for testing
- [ ] Create `src/lib/services/calendar_sync_service.py`
  - Sync on app launch, every 15 minutes, background refresh
  - Filter events with non-empty location field
  - Generate suggestion cards for calendar events
- [ ] Implement recurring event handling
- [ ] Handle sync failure gracefully
- [ ] Handle permission denial with explanation banner
- [ ] Write calendar tests (TC-01 through TC-06 from spec)

### 4.2 Sound Library
**Status:** None
**Gap:** No sound library, no custom import, no playback

**Tasks:**
- [ ] Create `src/lib/services/sound_library_service.py`
- [ ] Bundle built-in sounds (5 per category: Commute, Routine, Errand)
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 seconds)
- [ ] Implement audio transcoding to normalized format
- [ ] Implement per-reminder sound selection
- [ ] Implement corrupted sound fallback to category default
- [ ] Write sound library tests (TC-01 through TC-05 from spec)

---

## Priority 5: Analytics & Learning

### 5.1 History & Stats Service
**Status:** Partial (basic hit rate calculation exists)
**Gap:** No common miss window, no streak counter, no 90-day retention

**Tasks:**
- [ ] Refine `src/lib/services/stats_service.py`
- [ ] Implement common miss window tracking (most frequently missed urgency tier)
- [ ] Implement streak counter for recurring reminders
- [ ] Add `actual_arrival` tracking
- [ ] Implement 90-day data retention policy
- [ ] Archive older data (but keep accessible)
- [ ] Write stats tests (TC-01 through TC-07 from spec)

### 5.2 Feedback Loop Service
**Status:** Partial (basic adjustment exists)
**Gap:** Incomplete adjustment logic, no cap enforcement

**Tasks:**
- [ ] Refine adjustment logic per spec:
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
  - Cap at +15 minutes maximum
- [ ] Write feedback loop tests (TC-02 and TC-03 from spec)

---

## Priority 6: UI Layer (Frontend)

### 6.1 Quick Add Interface
**Tasks:**
- [ ] Create reminder input screen (text/speech)
- [ ] Display parsed interpretation confirmation card
- [ ] Enable manual field correction before confirm
- [ ] Handle empty/unintelligible input with retry prompt

### 6.2 Reminder List & Detail Views
**Tasks:**
- [ ] Create reminder list view with status indicators
- [ ] Create reminder detail/edit view
- [ ] Visual distinction for calendar-sourced reminders

### 6.3 History & Stats Views
**Tasks:**
- [ ] Display weekly hit rate
- [ ] Display current streak counter
- [ ] Display common miss window insight
- [ ] Show recent history list

### 6.4 Settings View
**Tasks:**
- [ ] Voice personality selection (5 + custom)
- [ ] Quiet hours configuration
- [ ] Default drive duration setting
- [ ] Calendar connection management
- [ ] Sound library access

---

## Dependency Graph

```
Priority 1 (Foundation)
├── Database Schema & Migrations
├── Escalation Chain Engine
└── Data Persistence Layer
    │
    ▼
Priority 2 (Core Features)
├── LLM Adapter & Parsing Service
├── Voice & TTS Generation
├── Voice Personality System
└── Snooze & Dismissal Flow
    │
    ▼
Priority 3 (Background & System)
├── Background Scheduling
├── Notification & Alarm Behavior
└── Location Awareness
    │
    ▼
Priority 4 (External Integration)
├── Calendar Integration
└── Sound Library
    │
    ▼
Priority 5 (Analytics)
├── History & Stats Service
└── Feedback Loop Service
    │
    ▼
Priority 6 (UI Layer)
├── Quick Add Interface
├── Reminder Views
├── History & Stats Views
└── Settings View
```

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

## Test Coverage Requirements

Per Section 14 (Definition of Done), all acceptance criteria must have corresponding passing tests. The following test suites are required:

| Section | Test Count | Status |
|---------|------------|--------|
| 2. Escalation Chain Engine | 6 | Partial |
| 3. Reminder Parsing | 7 | Partial |
| 4. Voice & TTS | 5 | None |
| 5. Notification & Alarm | 6 | None |
| 6. Background Scheduling | 6 | None |
| 7. Calendar Integration | 6 | None |
| 8. Location Awareness | 5 | None |
| 9. Snooze & Dismissal | 6 | None |
| 10. Voice Personality | 5 | None |
| 11. History & Stats | 7 | Partial |
| 12. Sound Library | 5 | None |
| 13. Data Persistence | 5 | None |

**Total:** 69 test scenarios required

---

## Files to Create

```
src/
├── lib/
│   ├── __init__.py
│   ├── database.py                 # Connection management, migrations
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── llm_adapter.py          # ILanguageModelAdapter interface
│   │   ├── tts_adapter.py          # ITTSAdapter interface
│   │   ├── calendar_adapter.py     # ICalendarAdapter interface
│   │   └── location_adapter.py     # ILocationAdapter interface
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── reminder_repository.py
│   │   ├── anchor_repository.py
│   │   ├── history_repository.py
│   │   ├── preferences_repository.py
│   │   └── adjustments_repository.py
│   └── services/
│       ├── __init__.py
│       ├── chain_engine.py         # Enhanced escalation chain
│       ├── parser_service.py       # LLM + keyword fallback
│       ├── tts_cache_service.py    # TTS caching
│       ├── scheduler_service.py    # Notifee integration
│       ├── notification_service.py # Notification handling
│       ├── snooze_service.py       # Snooze logic
│       ├── dismissal_service.py    # Feedback collection
│       ├── location_check_service.py
│       ├── calendar_sync_service.py
│       ├── sound_library_service.py
│       ├── stats_service.py         # Hit rate, streaks, etc.
│       └── feedback_loop_service.py
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
└── app.py                          # Main app entry point
```

---

## Implementation Order (Recommended)

1. **Database & Chain Engine** — Foundation for everything
2. **Repositories** — Data access layer
3. **LLM Adapter & Parser Service** — User input handling
4. **TTS Adapter & Cache** — Voice generation
5. **Voice Personality** — Message templates
6. **Background Scheduler** — Reliability
7. **Notification Service** — User alerts
8. **Snooze & Dismissal** — User interactions
9. **Location Service** — Location awareness
10. **Calendar Integration** — External data
11. **Sound Library** — Audio playback
12. **Stats & Feedback Loop** — Learning
13. **UI Layer** — User interface
14. **Integration Tests** — End-to-end validation
