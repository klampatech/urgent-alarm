# Urgent Alarm - Implementation Plan

## Project Overview

A mobile alarm app that speaks escalating urgency messages, adapting based on remaining time and context. The app creates departure reminder chains (e.g., "30 min drive to Parker Dr, arrive 9am") with progressive nudges from calm to urgent.

**Current State:** Basic test server with minimal chain engine and keyword parser exists. No modular architecture, no LLM/TTS adapters, no notification system, no background scheduling.

---

## Gap Analysis Summary

| Spec Section | Status | Priority |
|-------------|--------|----------|
| 2. Escalation Chain Engine | Partial | P0 |
| 3. Reminder Parsing | Minimal | P0 |
| 4. Voice & TTS Generation | Missing | P1 |
| 5. Notification & Alarm | Missing | P1 |
| 6. Background Scheduling | Missing | P1 |
| 7. Calendar Integration | Missing | P2 |
| 8. Location Awareness | Missing | P2 |
| 9. Snooze & Dismissal | Missing | P1 |
| 10. Voice Personality System | Partial | P1 |
| 11. History, Stats & Feedback | Partial | P2 |
| 12. Sound Library | Missing | P2 |
| 13. Data Persistence | Partial | P0 |

---

## Phase 1: Foundation (P0 — Critical)

### Task 1.1: Create Modular Project Structure
**Why:** Current `test_server.py` is a monolith. Need proper separation for testability.

**Files to create:**
```
src/
  lib/
    __init__.py
    chain_engine.py      # Escalation chain logic
    parser.py            # LLM adapter + keyword fallback
    tts_adapter.py       # ElevenLabs adapter interface
    llm_adapter.py       # Language model interface
    database.py          # SQLite operations
    models.py            # Data classes
    voice_generator.py   # Message templates per personality
    notifier.py          # Notification/alarm behavior
    scheduler.py         # Background scheduling
    calendar_adapter.py  # Calendar integration interface
    location_adapter.py  # Location check interface
    stats.py             # Hit rate, streaks, adjustments
    sound_library.py     # Sound management
```

**Acceptance:** `python3 -m py_compile src/lib/*.py` passes.

---

### Task 1.2: Fix Escalation Chain Engine
**Why:** Current implementation has incorrect anchor counts and tier assignments.

**Required changes:**
- `compute_escalation_chain()` must produce correct anchor counts per spec:
  - ≥25 min buffer: 8 anchors (departure, T-25, T-20, T-15, T-10, T-5, T-1, T-0)
  - 10-24 min buffer: 5 anchors (T-10, T-5, T-3, T-1, T-0)
  - 5-9 min buffer: 3 anchors (T-5, T-1, T-0)
  - ≤4 min buffer: 2 anchors (T-1, T-0) or 1 anchor (T-0)
- Add `get_next_unfired_anchor(reminder_id)` function
- Add `get_unfired_anchors(reminder_id)` function
- Add validation: `departure_time > now` and `arrival_time > now`
- Unit tests covering all TC scenarios from spec Section 2.5

**Test scenarios to pass:**
- TC-01: 30 min → 8 anchors at correct timestamps
- TC-02: 15 min → 5 anchors skipping calm/casual
- TC-03: 3 min → 3 anchors: T-3, T-1, T-0
- TC-04: Invalid chain rejection (120 min drive > arrival)
- TC-05: get_next_unfired_anchor recovery
- TC-06: Chain determinism (same inputs = same outputs)

---

### Task 1.3: Implement Adapter Interfaces (Mock-able)
**Why:** Spec requires all external services (LLM, TTS, Calendar, Location) to be mock-able for testing.

**Create interfaces:**
```python
# src/lib/llm_adapter.py
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse_reminder(self, text: str) -> ParsedReminder: ...

class MockLanguageModelAdapter(ILanguageModelAdapter):
    def __init__(self, fixture: dict): ...

class KeywordExtractionFallback:
    def parse(self, text: str) -> ParsedReminder: ...
```

```python
# src/lib/tts_adapter.py
class ITTSAdapter(ABC):
    @abstractmethod
    def generate_clip(self, text: str, voice_id: str) -> bytes: ...

class MockTTSAdapter(ITTSAdapter):
    def __init__(self, output_dir: str): ...
```

```python
# src/lib/calendar_adapter.py
class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events_with_location(self, since: datetime) -> list[CalendarEvent]: ...

class AppleCalendarAdapter(ICalendarAdapter): ...
class GoogleCalendarAdapter(ICalendarAdapter): ...
```

```python
# src/lib/location_adapter.py
class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
    def is_at_origin(self, origin: tuple, radius_m: int = 500) -> bool: ...
```

**Acceptance:** All adapters have working mock implementations for tests.

---

### Task 1.4: Complete Data Persistence Layer
**Why:** Current schema is incomplete. Missing columns and tables.

**Schema additions:**
- Add to `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_voice_prompt`, `custom_sound_path`, `updated_at`
- Add to `anchors`: `tts_fallback`, `snoozed_to`
- Add to `history`: `actual_arrival`, `missed_reason`, `created_at`
- Add `calendar_sync` table (last_sync_at, sync_token, is_connected)
- Add `custom_sounds` table (filename, original_name, file_path, duration_seconds)

**Operations needed:**
- `destination_adjustments` CRUD with `adjustment_minutes` cap at +15
- Cascade delete for reminders → anchors
- Migration system (sequential, versioned)
- UUID v4 generation for all IDs
- WAL mode and foreign keys enabled

**Acceptance:** Fresh install creates all tables; test DB uses in-memory mode.

---

## Phase 2: Core Features (P1 — Important)

### Task 2.1: Implement LLM Parsing with Fallback
**Why:** Keyword parser exists but needs confidence scoring and better extraction.

**Requirements:**
- LLM adapter uses configurable API (MiniMax/Anthropic via env var)
- System prompt defines extraction schema
- Keyword extraction fallback with regex patterns:
  - Time: "at 9am", "in 3 minutes", "tomorrow 2pm"
  - Duration: "30 minute drive", "in X minutes"
  - Destination: "to Parker Dr", "for meeting"
- Parse reminder_type enum from context
- Return confidence score for fallback mode
- Reject unintelligible input ("asdfgh") with user-facing error

**Test scenarios to pass:**
- TC-01: Full natural language parse
- TC-02: Simple countdown parse
- TC-03: Tomorrow date resolution
- TC-04: LLM failure fallback to keyword extraction
- TC-05: Manual field correction
- TC-06: Unintelligible input rejection
- TC-07: Mock adapter in tests

---

### Task 2.2: Implement Voice Personality System
**Why:** Current has single templates per tier; need variations.

**Requirements:**
- 5 built-in personalities with 3+ message variations per tier each
- Custom prompt mode (max 200 chars) appended to generation prompt
- Personality stored in reminder at creation time (immutable after)
- Default personality stored in user_preferences

**Message templates needed (minimum 3 per personality per tier):**

| Personality | Tiers | Total Templates |
|------------|-------|-----------------|
| Coach | 8 | 24+ |
| Assistant | 8 | 24+ |
| Best Friend | 8 | 24+ |
| No-nonsense | 8 | 24+ |
| Calm | 8 | 24+ |
| Custom | 8 | varies |

**Acceptance:** "Coach" at T-5 generates motivational message; "No-nonsense" generates brief direct message.

---

### Task 2.3: Implement TTS Generation & Caching
**Why:** Spec requires pre-generated clips with zero runtime latency.

**Requirements:**
- ElevenLabs API adapter (mock-able)
- Generate clips at reminder creation for all anchors
- Cache at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- Update anchor record with `tts_clip_path`
- Fallback: if TTS fails, mark `tts_fallback = true`, use system sound
- Cleanup: delete cached files when reminder deleted
- Generation timeout: 30 seconds per reminder

**Test scenarios to pass:**
- TC-01: 8 MP3 files created at reminder creation
- TC-02: Anchor plays from local cache (no network)
- TC-03: TTS fallback on API failure
- TC-04: TTS cache cleanup on delete
- TC-05: Mock TTS in tests

---

### Task 2.4: Implement Snooze & Dismissal Flow
**Why:** User interaction is core to the app.

**Requirements:**
- Tap snooze: 1 minute delay, TTS confirmation "Okay, snoozed 1 minute"
- Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation: shift remaining anchors by snooze duration
- Re-register snoozed anchors with scheduler
- Swipe dismiss: feedback prompt "You missed {dest} — timing right?"
  - Yes → store as 'hit'
  - No → follow-up: "Left too early" / "Left too late" / "Other"
- Feedback updates `destination_adjustments` (+2 min per 'left_too_late', cap +15)
- Snooze persistence survives app restart

**Test scenarios to pass:**
- TC-01: Tap snooze pauses 1 minute
- TC-02: Custom snooze picker works
- TC-03: Chain re-computation after snooze
- TC-04: Dismissal feedback (timing correct)
- TC-05: Dismissal feedback (left too late → adjustment)
- TC-06: Snooze persistence after restart

---

### Task 2.5: Implement Notification & Alarm Behavior
**Why:** Core UX — how nudges feel to users.

**Requirements:**
- Notification sound tiers:
  - Calm/Casual: gentle chime
  - Pointed/Urgent: pointed beep
  - Pushing/Firm: urgent siren
  - Critical/Alarm: looping alarm
- DND handling:
  - Pre-5-min during DND: silent notification only
  - Final 5 min during DND: visual + vibration override
- Quiet hours: configurable (default 10pm-7am), suppress all nudges
- Overdue anchors (15-min rule): silently drop
- Chain overlap: queue new anchors, fire after current chain
- T-0 alarm: loop until user acts
- Notification display: destination, time remaining, voice icon

**Test scenarios to pass:**
- TC-01: DND early anchor suppressed
- TC-02: DND final 5-min override
- TC-03: Quiet hours suppression
- TC-04: Overdue anchor drop (15 min rule)
- TC-05: Chain overlap serialization
- TC-06: T-0 alarm loops until action

---

### Task 2.6: Implement Background Scheduling
**Why:** Reminders must fire even when app is closed.

**Requirements:**
- Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- Each anchor registered as individual background task
- Recovery scan on app launch:
  - Find all unfired anchors
  - Fire those within 15-minute grace window
  - Drop and log those >15 min overdue
- Re-register pending anchors on crash recovery
- Late fire warning (>60s after scheduled time)
- Anchor state persisted to SQLite

**Test scenarios to pass:**
- TC-01: Anchor scheduling with Notifee
- TC-02: Background fire with app closed
- TC-03: Recovery scan on launch
- TC-04: Overdue anchor drop
- TC-05: Pending anchors re-registered on crash recovery
- TC-06: Late fire warning

---

## Phase 3: Advanced Features (P2 — Nice to Have)

### Task 3.1: Calendar Integration
**Why:** Automatic departure reminders from calendar events.

**Requirements:**
- Apple Calendar adapter (EventKit)
- Google Calendar adapter (API)
- Sync on launch + every 15 minutes
- Suggestion cards for events with locations
- Recurring event support
- Permission denial handling with explanation
- Calendar icon distinction for calendar-sourced reminders

**Test scenarios to pass:**
- TC-01 to TC-06 from spec Section 7.5

---

### Task 3.2: Location Awareness
**Why:** Escalate harder if user still at origin at departure time.

**Requirements:**
- Single location check at departure anchor only
- Geofence radius: 500 meters
- If at origin: fire T-5 (firm) immediately instead of calm departure
- If left: proceed with normal chain
- Request permission only at first location-aware reminder
- No location history stored

**Test scenarios to pass:**
- TC-01 to TC-05 from spec Section 8.5

---

### Task 3.3: History, Stats & Feedback Loop
**Why:** Users need to see their performance and system learns.

**Requirements:**
- Hit rate: `hits / (total - pending) * 100` for trailing 7 days
- Common miss window: most frequently missed urgency tier
- Streak counter: increment on hit, reset on miss for recurring
- Feedback loop: +2 min per late, cap at +15 min
- History retention: 90 days

**Test scenarios to pass:**
- TC-01 to TC-07 from spec Section 11.5

---

### Task 3.4: Sound Library
**Why:** Customization for different reminder types.

**Requirements:**
- 5 built-in sounds per category (Commute, Routine, Errand)
- Import custom audio (MP3, WAV, M4A, max 30 sec)
- Transcode to normalized format
- Corrupted file fallback to category default
- Per-reminder sound selection

**Test scenarios to pass:**
- TC-01 to TC-05 from spec Section 12.5

---

## Phase 4: Testing & Validation (P1)

### Task 4.1: Create Comprehensive Test Suite
**Why:** Spec requires "Every acceptance criterion maps to at least one test."

**Test files to create:**
```
tests/
  __init__.py
  test_chain_engine.py      # All Section 2 scenarios
  test_parser.py            # All Section 3 scenarios
  test_tts_adapter.py       # All Section 4 scenarios
  test_notifier.py          # All Section 5 scenarios
  test_scheduler.py        # All Section 6 scenarios
  test_calendar_adapter.py  # All Section 7 scenarios
  test_location_adapter.py  # All Section 8 scenarios
  test_snooze.py            # All Section 9 scenarios
  test_voice_personalities.py # All Section 10 scenarios
  test_stats.py             # All Section 11 scenarios
  test_sound_library.py     # All Section 12 scenarios
  test_database.py          # All Section 13 scenarios
  conftest.py               # Shared fixtures
```

**Acceptance:** `python3 -m pytest tests/` passes all scenarios.

---

### Task 4.2: Integration with Test Server
**Why:** Harness validates against HTTP endpoints.

**Endpoint additions:**
- `GET /anchors/{reminder_id}` — List anchors for reminder
- `POST /anchors/{anchor_id}/fire` — Mark anchor fired (already exists)
- `GET /stats/common-miss-window` — Most missed tier
- `GET /stats/streak/{destination}` — Current streak
- `GET /adjustments/{destination}` — Drive duration adjustments
- `POST /snooze` — Apply snooze to chain
- `DELETE /reminders/{id}` — Cancel reminder

**Acceptance:** All endpoints return correct data per spec.

---

## Implementation Order

```
Phase 1 (Foundation):
  1.1 → 1.2 → 1.3 → 1.4

Phase 2 (Core Features):
  2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6

Phase 3 (Advanced):
  3.1 → 3.2 → 3.3 → 3.4

Phase 4 (Testing):
  4.1 → 4.2
```

**Parallelizable:** Tasks within a phase that don't depend on each other.

**Key dependencies:**
- 2.3 (TTS) depends on 1.3 (TTS adapter interface)
- 2.4 (Snooze) depends on 1.2 (Chain engine) and 2.6 (Scheduler)
- 2.5 (Notifier) depends on 2.3 (TTS) and 2.6 (Scheduler)
- 3.1 (Calendar) depends on 1.3 (Calendar adapter interface)
- 4.1 (Tests) depends on all Phase 1-3 tasks

---

## Quick Wins (Can ship early)

1. **Better keyword parser** — Improve regex patterns for common phrases
2. **More voice message variations** — Add template variations per personality
3. **Hit rate calculation** — Compute from existing history table
4. **Simple snooze** — 1-minute tap snooze without full chain re-computation

---

## Out of Scope (v1)

- Password/auth system
- Smart home integration (Hue lights)
- Voice reply snooze
- Multi-device sync
- Bluetooth audio routing
- Per-reminder personality override
- Sound recording
- Sound trimming
- Database encryption
- Full-text search on destinations
