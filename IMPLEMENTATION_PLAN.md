# Urgent Voice Alarm - Implementation Plan

## Analysis Summary

**Specification:** 14 sections covering escalation chain engine, reminder parsing, TTS generation, notifications, background scheduling, calendar integration, location awareness, snooze/dismissal, voice personalities, history/stats, sound library, and data persistence.

**Current Implementation:** `src/test_server.py` provides a functional HTTP server with basic chain computation, keyword parsing, message templates, and simple database operations. Foundation exists but adapter interfaces, full schema, background services, and system integrations are missing.

---

## Priority 1: Foundation Layer (Must-Have)

### 1.1 Database Schema & Migrations
**Spec Section:** 13 (Data Persistence)

**Gap:** Schema is incomplete and missing migrations.
- Missing columns: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`
- Missing `tts_fallback`, `snoozed_to` columns in anchors
- Missing `missed_reason`, `actual_arrival` in history
- Missing `calendar_sync`, `custom_sounds` tables
- No migration system

**Tasks:**
- [ ] Create migration runner with version tracking
- [ ] Add migration_v1: Initial schema with all spec columns
- [ ] Implement UUID v4 generation helper
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Add cascade delete support
- [ ] Create `get_next_unfired_anchor(reminder_id)` function

**Acceptance Criteria (Spec 13.4):**
- Fresh install applies all migrations in order
- In-memory test database starts empty with migrations applied
- `reminders.id` is always UUID v4
- Deleting reminder cascades to delete anchors
- Foreign key violations return errors

---

### 1.2 Adapter Interfaces (Mock-able)
**Spec Sections:** 3, 4, 7

**Gap:** No adapter interfaces for mocking in tests.

**Tasks:**
- [ ] Create `ILanguageModelAdapter` interface for LLM parsing
- [ ] Implement `MockLanguageModelAdapter` for testing
- [ ] Create `ITTSAdapter` interface for TTS generation
- [ ] Implement `MockTTSAdapter` (writes silent file for tests)
- [ ] Create `ICalendarAdapter` interface
- [ ] Implement `MockCalendarAdapter` for testing

**Acceptance Criteria:**
- All adapters are mock-able via interface
- Mock adapters work without real API calls

---

### 1.3 Full Chain Engine
**Spec Section:** 2

**Gap:** `get_next_unfired_anchor()` missing, chain logic may differ from spec.

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` for scheduler recovery
- [ ] Verify compressed chain logic matches spec (TC-02: 10-24 min buffer → 5 anchors)
- [ ] Add chain determinism for unit testing
- [ ] Add validation: `arrival_time > departure_time + minimum_drive_time`

**Acceptance Criteria (Spec 2.4):**
- [ ] Chain for "30 min drive, arrive 9am" produces 8 anchors
- [ ] Chain for "10 min drive, arrive 9am" produces 4 anchors (T-10, T-5, T-1, T-0)
- [ ] Chain for "3 min drive, arrive 9am" produces 3 anchors (T-3, T-1, T-0)
- [ ] Invalid chain rejected with "drive_duration exceeds time_to_arrival"
- [ ] `get_next_unfired_anchor` returns earliest unfired anchor

---

### 1.4 Enhanced Parser
**Spec Section:** 3

**Gap:** Keyword extraction only, no LLM adapter, no "blah blah" rejection.

**Tasks:**
- [ ] Integrate `ILanguageModelAdapter` with MiniMax/Anthropic support
- [ ] Implement keyword extraction fallback on LLM failure
- [ ] Add confidence scoring for fallback results
- [ ] Add "unintelligible input" detection and user-facing error
- [ ] Handle tomorrow/date resolution correctly

**Acceptance Criteria (Spec 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] "dryer in 3 min" parses as simple_countdown
- [ ] "meeting tomorrow 2pm, 20 min drive" resolves to next day
- [ ] On API failure, keyword extraction produces best-effort result
- [ ] "asdfgh jkl" returns user-facing error

---

## Priority 2: Core Features

### 2.1 Voice Personality System
**Spec Section:** 10

**Gap:** Only 1 template per tier/personality (spec requires minimum 3).

**Tasks:**
- [ ] Expand each personality tier to 3+ message variations
- [ ] Add "custom" personality with user prompt (max 200 chars)
- [ ] Implement random/template selection
- [ ] Store selected personality in user_preferences

**Acceptance Criteria (Spec 10.4):**
- [ ] "Coach" at T-5: Motivational with exclamation
- [ ] "No-nonsense" at T-5: Brief, direct, no filler
- [ ] Custom prompt modifies tone
- [ ] Each personality has 3+ variations per tier

---

### 2.2 TTS Cache System
**Spec Section:** 4

**Gap:** No actual TTS generation or file caching.

**Tasks:**
- [ ] Create `/tts_cache/{reminder_id}/` directory structure
- [ ] Implement `ElevenLabsTTSAdapter` (or mock)
- [ ] Add pre-generation at reminder creation
- [ ] Implement `ITTSAdapter.play(anchor_id)` from cache
- [ ] Add cache invalidation on reminder delete
- [ ] Fallback to system notification on TTS failure

**Acceptance Criteria (Spec 4.4):**
- [ ] New reminder generates clips in `/tts_cache/{reminder_id}/`
- [ ] Anchor plays from local cache (no network call)
- [ ] TTS failure falls back to system sound + notification text
- [ ] Reminder deletion removes cached files

---

### 2.3 Snooze & Dismissal System
**Spec Section:** 9

**Gap:** No snooze or dismissal handling.

**Tasks:**
- [ ] Implement tap snooze (1 min) endpoint
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze
- [ ] Implement swipe-to-dismiss feedback prompt
- [ ] Add TTS snooze confirmation: "Okay, snoozed X minutes"
- [ ] Persist snooze state for app restart recovery

**Acceptance Criteria (Spec 9.4):**
- [ ] Tap snooze pauses and re-fires after 1 min
- [ ] Custom snooze shifts remaining anchors
- [ ] Feedback prompt appears on dismiss
- [ ] "Left too late" feedback increases drive_duration by 2 min
- [ ] TTS confirms snooze duration

---

### 2.4 History & Feedback Loop
**Spec Section:** 11

**Gap:** Only basic hit rate, missing feedback adjustments, streak, common miss window.

**Tasks:**
- [ ] Implement destination adjustment tracking
- [ ] Add feedback loop: `adjusted_drive_duration = stored + (late_count * 2)`, cap at +15 min
- [ ] Implement "common miss window" identification
- [ ] Implement streak counter for recurring reminders
- [ ] Add 90-day data retention logic

**Acceptance Criteria (Spec 11.4):**
- [ ] Hit rate calculated correctly (4 hits / 5 non-pending = 80%)
- [ ] After 3 "Left too late", drive_duration +6 min for destination
- [ ] "Common miss window" identifies most missed tier
- [ ] Streak increments on hit, resets on miss

---

## Priority 3: System Integrations

### 3.1 Background Scheduling
**Spec Section:** 6

**Gap:** No Notifee integration, no recovery scan.

**Tasks:**
- [ ] Create `BackgroundScheduler` interface
- [ ] Implement `NotifeeSchedulerAdapter` (for mobile future)
- [ ] Add `register_anchors(reminder_id)` to schedule all anchors
- [ ] Implement recovery scan on app launch
- [ ] Add 15-minute grace window for overdue anchors
- [ ] Log late firing (>60s) with warning

**Acceptance Criteria (Spec 6.4):**
- [ ] Anchors registered correctly
- [ ] Recovery scan fires only anchors within 15-min grace
- [ ] Overdue anchors (>15 min) dropped and logged

---

### 3.2 Calendar Integration
**Spec Section:** 7

**Gap:** No calendar adapters.

**Tasks:**
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Add calendar sync on launch + 15-min interval
- [ ] Create suggestion cards for events with locations
- [ ] Handle permission denial with explanation banner

**Acceptance Criteria (Spec 7.4):**
- [ ] Apple Calendar events with locations appear as suggestions
- [ ] Google Calendar events with locations appear as suggestions
- [ ] Permission denial shows explanation + "Open Settings"
- [ ] Calendar sync failure doesn't block manual reminders

---

### 3.3 Location Awareness
**Spec Section:** 8

**Gap:** No location check system.

**Tasks:**
- [ ] Create `LocationAdapter` interface
- [ ] Implement `CoreLocationAdapter` for iOS
- [ ] Single location check at departure anchor only
- [ ] Implement 500m geofence comparison
- [ ] Trigger "LEAVE NOW" escalation if user still at origin
- [ ] Handle denied location permission gracefully

**Acceptance Criteria (Spec 8.4):**
- [ ] Departure anchor performs single location check
- [ ] User within 500m triggers urgent escalation
- [ ] User >500m proceeds with normal chain
- [ ] Denied permission creates reminder without location escalation

---

### 3.4 Notification System
**Spec Section:** 5

**Gap:** No DND awareness, quiet hours, or chain serialization.

**Tasks:**
- [ ] Implement notification tier escalation (gentle → pointed → siren → alarm)
- [ ] Add DND detection and handling
- [ ] Implement quiet hours suppression (configurable start/end)
- [ ] Queue anchors suppressed by DND/quiet hours
- [ ] Implement chain overlap serialization
- [ ] T-0 alarm loops until user action

**Acceptance Criteria (Spec 5.5):**
- [ ] DND early anchor fires as silent notification
- [ ] DND final 5 min fires with vibration override
- [ ] Quiet hours anchors queued until end
- [ ] >15 min overdue anchors dropped
- [ ] Chain overlap queues new anchors
- [ ] T-0 alarm loops until dismiss/snooze

---

## Priority 4: Sound Library

### 4.1 Sound System
**Spec Section:** 12

**Gap:** No sound library implementation.

**Tasks:**
- [ ] Bundle built-in sounds per category (commute, routine, errand, custom)
- [ ] Implement custom sound import (MP3, WAV, M4A, max 30 sec)
- [ ] Store custom sounds in app sandbox
- [ ] Associate sound with reminder
- [ ] Implement corrupted sound fallback to category default

**Acceptance Criteria (Spec 12.4):**
- [ ] Built-in sounds play without network
- [ ] Custom MP3 import appears in picker
- [ ] Corrupted custom sound falls back to default

---

## Priority 5: Tests & Validation

### 5.1 Test Coverage
**Spec Section:** 14

**Gap:** Missing test infrastructure.

**Tasks:**
- [ ] Create unit tests for chain engine (determinism, all buffer sizes)
- [ ] Create unit tests for parser (fixtures from TC-01 to TC-07)
- [ ] Create unit tests for TTS adapter mock
- [ ] Create unit tests for LLM adapter mock
- [ ] Create integration tests: parse → chain → TTS → persist
- [ ] Create integration tests: schedule → fire → mark fired
- [ ] Create integration tests: snooze → recompute → re-register
- [ ] Create integration tests: dismiss → feedback → adjustment

**Acceptance Criteria (Spec 14):**
- All acceptance criteria have corresponding passing tests

---

## Dependencies Map

```
Priority 1 (Foundation)
├── 1.1 Database Schema & Migrations
│   └── Required by all data operations
├── 1.2 Adapter Interfaces
│   └── Required by parser, TTS, calendar
└── 1.3 Full Chain Engine
│   └── Required by reminder creation
└── 1.4 Enhanced Parser
    └── Required by Quick Add flow

Priority 2 (Core Features) - depends on Priority 1
├── 2.1 Voice Personality System
│   └── Depends on 1.2
├── 2.2 TTS Cache System
│   └── Depends on 1.1, 1.2
├── 2.3 Snooze & Dismissal
│   └── Depends on 1.3
└── 2.4 History & Feedback Loop
    └── Depends on 1.1

Priority 3 (System Integrations) - depends on Priority 2
├── 3.1 Background Scheduling
│   └── Depends on 1.3
├── 3.2 Calendar Integration
│   └── Depends on 1.2
├── 3.3 Location Awareness
│   └── Depends on 1.1
└── 3.4 Notification System
    └── Depends on 2.2, 3.1

Priority 4 - depends on Priority 3
└── 4.1 Sound System

Priority 5 - depends on all
└── 5.1 Test Coverage
```

---

## Implementation Order

1. **Database Layer** - Schema + migrations + UUID helpers
2. **Chain Engine** - Full implementation + `get_next_unfired_anchor`
3. **Adapter Interfaces** - Create mock-able adapters
4. **Parser** - LLM adapter + keyword fallback + validation
5. **Voice System** - Templates + variations + custom prompts
6. **TTS Cache** - File management + fallback
7. **Snooze/Dismissal** - Tap/hold handlers + chain recompute
8. **History/Stats** - Feedback loop + adjustments
9. **Background Scheduling** - Recovery scan + grace window
10. **Calendar Adapter** - Apple/Google integration
11. **Location Adapter** - Single-check + geofence
12. **Notification System** - DND + quiet hours + serialization
13. **Sound Library** - Built-in + import + fallback
14. **Test Coverage** - Full suite

---

## Notes

- Mobile-specific features (Notifee, CoreLocation, EventKit) will need platform-specific implementations or mocks for the HTTP test server
- Consider splitting `test_server.py` into modular components (db/, adapters/, services/)
- The HTTP API surface should be extended to cover all spec endpoints (snooze, dismiss, calendar sync, location check)
