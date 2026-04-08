# Urgent Alarm - Implementation Plan

## Project Overview

A mobile alarm app that speaks escalating urgency messages, adapting based on remaining time and context. The app creates departure reminder chains (e.g., "30 min drive to Parker Dr, arrive 9am") with progressive nudges from calm to urgent.

**Current State:** Basic test server with partial chain engine, keyword parser, voice templates, and SQLite storage. Missing modular architecture, LLM/TTS adapters, notification system, background scheduling, and 14 missing database columns/tables.

---

## Gap Analysis Summary

| Spec Section | Feature | Status | Verified Issues | Priority |
|-------------|---------|--------|-----------------|----------|
| 2 | Escalation Chain Engine | **Partial** | Bug: 3min produces 2 anchors (needs 3); missing `get_next_unfired_anchor()`; wrong tier mapping for 10-24min | **P0** |
| 3 | Reminder Parsing | **Partial** | Parser crashes on "in X min"; missing LLM adapter interface; no mock adapter | **P0** |
| 4 | Voice & TTS Generation | **Partial** | 40 templates exist (1/tier); needs 3/tier (120+ total); no TTS adapter interface | P1 |
| 5 | Notification & Alarm | **Missing** | Not implemented in test_server.py | P1 |
| 6 | Background Scheduling | **Missing** | Not implemented; no Notifee integration | P1 |
| 7 | Calendar Integration | **Missing** | Not implemented; no adapter interface | P2 |
| 8 | Location Awareness | **Missing** | Not implemented; no adapter interface | P2 |
| 9 | Snooze & Dismissal | **Missing** | Not implemented; no chain re-computation | P1 |
| 10 | Voice Personality System | **Partial** | 1 template per tier (40 total); needs 3+ variations each | P1 |
| 11 | History, Stats & Feedback | **Partial** | Hit rate works; missing common_miss_window, streak, missed_reason tracking | P2 |
| 12 | Sound Library | **Missing** | Not implemented; no adapter interface | P2 |
| 13 | Data Persistence | **Partial** | Missing 13 columns, 2 tables, no migration system | **P0** |

---

## Current Implementation Verified Issues

### Chain Engine Bugs (Section 2)

**Bug 1: 3 min buffer produces only 2 anchors (needs 3)**
- **Spec TC-03 requires:** 3 anchors: T-3 (firm), T-1 (critical), T-0 (alarm)
- **Current output:** 2 anchors: T-2 (firm), T-0 (alarm) — MISSING critical anchor
- **Root cause:** `buffer_minutes <= 4` branch creates `[('firm', buffer-1), ('alarm', 0)]` but `buffer-1 = 2`, missing the `critical` tier entirely

**Bug 2: 10-24 min buffer uses wrong tiers**
- **Spec says:** Skip calm/casual/pointed, start at urgent (T-5)
- **Current code:** Uses `buffer_minutes >= 10` but still includes pointed/urgent
- **Correct mapping:**
  - ≥25 min: full 8 anchors
  - 20-24 min: 7 anchors (skip calm only)
  - 15-19 min: 5 anchors (skip calm/casual)
  - 10-14 min: 5 anchors (urgent, pushing, firm, critical, alarm)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - ≤4 min: 2-3 anchors depending on duration

**Missing functions:**
- `get_next_unfired_anchor(reminder_id)` — returns earliest unfired anchor
- `get_unfired_anchors(reminder_id)` — returns all unfired anchors
- `validate_chain()` needs to reject `drive_duration > time_to_arrival`

### Parser Issues (Section 3)

**Bug 1: Crash on "in X min" format**
- Input: `"dryer in 3 min"`
- Error: `IndexError: no such group`
- Cause: Regex `r'in\s+(\d+)\s*(?:minute|min)'` only captures 1 group, but code expects 3 groups

**Bug 2: Unintelligible input returns 0.3 confidence instead of error**
- Spec TC-06: Should return user-facing error message
- Current behavior: Returns parsed object with `confidence: 0.3`

**Missing:**
- `ILanguageModelAdapter` interface
- `MockLanguageModelAdapter` for testing
- Keyword extraction adapter as fallback

### Database Schema Issues (Section 13)

**Missing from `reminders` table (9 columns):**
- `origin_lat REAL`
- `origin_lng REAL`
- `origin_address TEXT`
- `calendar_event_id TEXT`
- `custom_voice_prompt TEXT`
- `custom_sound_path TEXT`
- `updated_at TEXT` (partial - exists but not in all paths)
- `tts_cache_dir TEXT` (for TTS clip storage)

**Missing from `anchors` table (2 columns):**
- `tts_fallback INTEGER DEFAULT 0`
- `snoozed_to TEXT`

**Missing from `history` table (3 columns):**
- `actual_arrival TEXT`
- `missed_reason TEXT`
- `updated_at TEXT`

**Missing tables (3 total):**
- `schema_version (version INTEGER PRIMARY KEY)`
- `calendar_sync (calendar_type, last_sync_at, sync_token, is_connected)`
- `custom_sounds (id, filename, original_name, category, file_path, duration_seconds, created_at)`

**Missing from `user_preferences`:**
- `updated_at TEXT`

**Missing `destination_adjustments` columns:**
- `updated_at TEXT`

---

## Phase 1: Foundation (P0 — Critical)

### Task 1.1: Complete Data Persistence Layer

**Objective:** Add missing schema elements and migration system

**Schema additions needed:**
```sql
-- reminders table additions:
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
calendar_event_id TEXT,
custom_voice_prompt TEXT,
custom_sound_path TEXT,
tts_cache_dir TEXT

-- anchors table additions:
tts_fallback INTEGER DEFAULT 0,
snoozed_to TEXT

-- history table additions:
actual_arrival TEXT,
missed_reason TEXT,
updated_at TEXT

-- user_preferences table addition:
updated_at TEXT

-- destination_adjustments table addition:
updated_at TEXT

-- New tables:
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE calendar_sync (
    calendar_type TEXT PRIMARY KEY,
    last_sync_at TEXT,
    sync_token TEXT,
    is_connected INTEGER DEFAULT 0
);

CREATE TABLE custom_sounds (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration_seconds REAL,
    created_at TEXT NOT NULL
);
```

**Operations to implement:**
- [ ] Migration system (sequential, versioned, never modify existing)
- [ ] Cascade delete for reminders → anchors
- [ ] UUID v4 generation for all IDs
- [ ] WAL mode and foreign keys enabled
- [ ] In-memory mode for tests

**Acceptance:** Fresh install creates all tables; test DB uses in-memory mode; cascade deletes work.

---

### Task 1.2: Create Modular Architecture

**Objective:** Extract core logic into testable modules with adapter interfaces

**Directory structure:**
```
src/
  lib/
    __init__.py
    chain_engine.py      # Escalation chain logic
    parser.py            # LLM adapter + keyword fallback
    tts_adapter.py       # ElevenLabs adapter interface
    llm_adapter.py       # Language model interface
    database.py          # SQLite operations + migrations
    models.py            # Data classes (Reminder, Anchor, etc.)
    voice_generator.py   # Message templates per personality
    notifier.py          # Notification/alarm behavior
    scheduler.py         # Background scheduling
    calendar_adapter.py  # Calendar integration interface
    location_adapter.py  # Location check interface
    stats.py             # Hit rate, streaks, adjustments
    sound_library.py     # Sound management
  test_server.py         # HTTP API layer (refactor after lib/)
```

**Adapter interfaces to create:**
```python
# src/lib/llm_adapter.py
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse_reminder(self, text: str) -> ParsedReminder: ...

class MockLanguageModelAdapter(ILanguageModelAdapter):
    def __init__(self, fixture: dict): ...

class KeywordExtractionAdapter(ILanguageModelAdapter):
    def parse(self, text: str) -> ParsedReminder: ...

# src/lib/tts_adapter.py
class ITTSAdapter(ABC):
    @abstractmethod
    def generate_clip(self, text: str, voice_id: str) -> bytes: ...

class MockTTSAdapter(ITTSAdapter):
    def __init__(self, output_dir: str): ...

class ElevenLabsAdapter(ITTSAdapter):
    def __init__(self, api_key: str): ...

# src/lib/calendar_adapter.py
class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events_with_location(self, since: datetime) -> list[CalendarEvent]: ...

class AppleCalendarAdapter(ICalendarAdapter):
    def __init__(self): ...

class GoogleCalendarAdapter(ICalendarAdapter):
    def __init__(self, credentials: dict): ...

# src/lib/location_adapter.py
class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
    def is_at_origin(self, origin: tuple, radius_m: int = 500) -> bool: ...
```

**Acceptance:** `python3 -m py_compile src/lib/*.py` passes; all adapters have working mock implementations.

---

### Task 1.3: Fix Escalation Chain Engine

**Objective:** Correct anchor tier mapping and add missing functions

**Required fixes:**

1. **Correct anchor tier mapping per spec:**
```
buffer >= 25 min: calm(30), casual(25), pointed(20), urgent(15), pushing(10), firm(5), critical(1), alarm(0)
buffer 20-24 min: casual(25), pointed(20), urgent(15), pushing(10), firm(5), critical(1), alarm(0)
buffer 15-19 min: urgent(15), pushing(10), firm(5), critical(1), alarm(0)
buffer 10-14 min: urgent(15), pushing(10), firm(5), critical(1), alarm(0)
buffer 5-9 min: firm(5), critical(1), alarm(0)
buffer 3-4 min: firm(3), critical(1), alarm(0) ← WAS BROKEN
buffer 1-2 min: critical(1), alarm(0)
buffer < 1 min: alarm(0)
```

2. **Add missing functions:**
```python
def get_next_unfired_anchor(reminder_id: str) -> Optional[Anchor]:
    """Return earliest unfired anchor for recovery after restart."""
    
def get_unfired_anchors(reminder_id: str) -> List[Anchor]:
    """Return all unfired anchors for recovery scan."""

def validate_chain(arrival_time: datetime, drive_duration: int) -> ValidationResult:
    """Validate chain can be created. Reject if drive_duration > time_to_arrival."""
```

3. **Fix Bug: 3 min buffer produces 3 anchors**
   - Current: firm(2), alarm(0) — 2 anchors
   - Required: firm(3), critical(1), alarm(0) — 3 anchors

**Test scenarios to pass (Section 2.5):**
- [ ] TC-01: 30 min → 8 anchors
- [ ] TC-02: 15 min → 5 anchors (skip calm/casual)
- [ ] TC-03: 3 min → 3 anchors ← **Currently fails**
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: get_next_unfired_anchor recovery
- [ ] TC-06: Chain determinism

---

## Phase 2: Core Features (P1 — Important)

### Task 2.1: Implement LLM Parsing with Fallback

**Objective:** Full parsing pipeline with LLM + keyword fallback

**Requirements:**
- LLM adapter configurable via env var (`LLM_PROVIDER=minimax|anthropic`)
- Keyword extraction fallback with confidence scoring
- Parse reminder_type enum from context
- Handle "tomorrow" date resolution
- Reject unintelligible input with user-facing error

**Test scenarios to pass (Section 3.5):**
- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am"
- [ ] TC-02: "dryer in 3 min" (simple_countdown)
- [ ] TC-03: "meeting tomorrow 2pm, 20 min drive"
- [ ] TC-04: LLM API failure fallback
- [ ] TC-05: Manual field correction
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

### Task 2.2: Implement Voice Personality System

**Objective:** 3+ message variations per personality per tier

**Message templates needed (120+ total):**
| Personality | Tiers | Variations | Total |
|------------|-------|------------|-------|
| Coach | 8 | 3 each | 24 |
| Assistant | 8 | 3 each | 24 |
| Best Friend | 8 | 3 each | 24 |
| No-nonsense | 8 | 3 each | 24 |
| Calm | 8 | 3 each | 24 |

**Test scenarios to pass (Section 10.5):**
- [ ] TC-01: Coach personality messages (motivational, exclamations)
- [ ] TC-02: No-nonsense personality messages (brief, direct)
- [ ] TC-03: Custom personality prompt
- [ ] TC-04: Personality immutability for existing reminders
- [ ] TC-05: Message variation (distinct phrasings)

---

### Task 2.3: Implement TTS Generation & Caching

**Objective:** Pre-generate TTS clips at reminder creation

**Requirements:**
- ElevenLabs API adapter (mock-able)
- Generate clips at reminder creation for all anchors
- Cache at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- Fallback: if TTS fails, mark `tts_fallback = true` and use notification sound
- Cleanup: delete cached files when reminder deleted

**Test scenarios to pass (Section 4.5):**
- [ ] TC-01: TTS clip generation at creation
- [ ] TC-02: Anchor fires from cache (no network call)
- [ ] TC-03: TTS fallback on API failure
- [ ] TC-04: TTS cache cleanup on delete
- [ ] TC-05: Mock TTS in tests

---

### Task 2.4: Implement Snooze & Dismissal Flow

**Objective:** Full snooze chain re-computation and feedback system

**Requirements:**
- Tap snooze: 1 minute delay, TTS confirmation "Okay, snoozed 1 minute"
- Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation: shift remaining anchors by snooze duration
- Swipe dismiss: feedback prompt with Yes/No options
- Feedback updates `destination_adjustments` (+2 min per 'left_too_late', cap +15)
- Snooze persistence survives app restart

**Test scenarios to pass (Section 9.5):**
- [ ] TC-01: Tap snooze
- [ ] TC-02: Custom snooze picker
- [ ] TC-03: Chain re-computation after snooze
- [ ] TC-04: Dismissal feedback — timing correct
- [ ] TC-05: Dismissal feedback — timing off (left too late)
- [ ] TC-06: Snooze persistence after restart

---

### Task 2.5: Implement Notification & Alarm Behavior

**Objective:** Escalating notifications respecting DND and quiet hours

**Requirements:**
- Notification sound tiers:
  - Calm/Casual: gentle chime
  - Pointed/Urgent: pointed beep
  - Pushing/Firm: urgent siren
  - Critical/Alarm: looping alarm
- DND handling with visual+vibration override for final 5 min
- Quiet hours (default 10pm-7am), configurable
- Overdue anchors (15-min rule): drop silently
- Chain overlap serialization
- T-0 alarm loops until user acts

**Test scenarios to pass (Section 5.5):**
- [ ] TC-01: DND — early anchor suppressed
- [ ] TC-02: DND — final 5-minute override
- [ ] TC-03: Quiet hours suppression
- [ ] TC-04: Overdue anchor drop (15 min rule)
- [ ] TC-05: Chain overlap serialization
- [ ] TC-06: T-0 alarm loops until action

---

### Task 2.6: Implement Background Scheduling

**Objective:** Reliable background execution with recovery

**Requirements:**
- Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- Recovery scan on app launch:
  - Fire anchors within 15-minute grace window
  - Drop and log anchors >15 min overdue with `missed_reason = "background_task_killed"`
- Re-register pending anchors on crash recovery
- Late fire warning (>60s after scheduled time)

**Test scenarios to pass (Section 6.5):**
- [ ] TC-01: Anchor scheduling with Notifee
- [ ] TC-02: Background fire with app closed
- [ ] TC-03: Recovery scan on launch
- [ ] TC-04: Overdue anchor drop
- [ ] TC-05: Pending anchors re-registered on crash recovery
- [ ] TC-06: Late fire warning

---

## Phase 3: Advanced Features (P2 — Nice to Have)

### Task 3.1: Calendar Integration

**Objective:** Apple Calendar + Google Calendar integration

**Requirements:**
- Apple Calendar adapter (EventKit)
- Google Calendar adapter (Google Calendar API)
- Sync on launch + every 15 minutes
- Suggestion cards for events with locations
- Calendar-sourced reminders visually distinguished

**Test scenarios to pass (Section 7.5):**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

### Task 3.2: Location Awareness

**Objective:** Single location check at departure time

**Requirements:**
- Single location check at departure anchor only (never continuously)
- Origin: user-specified address or current device location at creation
- Geofence radius: 500 meters
- If at origin: fire firm/critical immediately
- Request permission at first location-aware reminder
- No location history retained

**Test scenarios to pass (Section 8.5):**
- [ ] TC-01: User still at origin at departure
- [ ] TC-02: User already left at departure
- [ ] TC-03: Location permission request
- [ ] TC-04: Location permission denied
- [ ] TC-05: Single location check only

---

### Task 3.3: History, Stats & Feedback Loop

**Objective:** Complete stats system with feedback learning

**Requirements:**
- Hit rate: `hits / (total - pending) * 100` for trailing 7 days
- Common miss window: most frequently missed urgency tier
- Streak counter: increment on hit, reset on miss
- Feedback loop: +2 min per 'left_too_late', cap at +15 min
- 90-day retention with archiving

**Test scenarios to pass (Section 11.5):**
- [ ] TC-01: Hit rate calculation
- [ ] TC-02: Feedback loop — drive duration adjustment
- [ ] TC-03: Feedback loop cap
- [ ] TC-04: Common miss window identification
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table

---

### Task 3.4: Sound Library

**Objective:** Per-reminder sound selection with custom import

**Requirements:**
- 5 built-in sounds per category (Commute, Routine, Errand)
- Custom audio import (MP3, WAV, M4A, max 30 sec)
- Corrupted file fallback to category default
- Sound selection per reminder, not global

**Test scenarios to pass (Section 12.5):**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Phase 4: Testing & Validation (P1)

### Task 4.1: Create Comprehensive Test Suite

**Test files to create:**
```
tests/
  __init__.py
  test_chain_engine.py      # TC-01 through TC-06
  test_parser.py            # TC-01 through TC-07
  test_tts_adapter.py       # TC-01 through TC-05
  test_notifier.py          # TC-01 through TC-06
  test_scheduler.py         # TC-01 through TC-06
  test_calendar_adapter.py  # TC-01 through TC-06
  test_location_adapter.py  # TC-01 through TC-05
  test_snooze.py            # TC-01 through TC-06
  test_voice_personalities.py # TC-01 through TC-05
  test_stats.py             # TC-01 through TC-07
  test_sound_library.py      # TC-01 through TC-05
  test_database.py          # TC-01 through TC-05
  conftest.py               # Shared fixtures
```

**Acceptance:** All spec test scenarios pass.

---

### Task 4.2: Additional API Endpoints

**Endpoints to add:**
- `GET /anchors/{reminder_id}` — List all anchors for reminder
- `GET /anchors/{reminder_id}/next` — Get next unfired anchor
- `POST /anchors/{anchor_id}/fire` — Mark anchor as fired
- `POST /snooze` — Apply snooze to anchor
- `DELETE /reminders/{id}` — Cancel reminder
- `GET /stats/hit-rate` — Weekly hit rate
- `GET /stats/common-miss-window` — Most missed urgency tier
- `GET /stats/streak/{destination}` — Current streak
- `GET /adjustments/{destination}` — Drive duration adjustments
- `POST /calendar/sync` — Trigger calendar sync
- `GET /calendar/suggestions` — Pending calendar suggestions
- `POST /calendar/suggestions/{id}/accept` — Accept suggestion

---

## Implementation Order

```
Phase 1 (Foundation):
  1.1 → 1.2 → 1.3
  
  1.1 (Schema) must come before 1.2 (Architecture) because adapters depend on models
  1.3 (Chain Engine) depends on 1.2 for the module structure

Phase 2 (Core Features):
  2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6
  
  2.1 (Parsing) is standalone
  2.2 (Voice) depends on 2.1 for message generation
  2.3 (TTS) depends on 2.2 for voice templates
  2.4 (Snooze) depends on 1.3 (Chain) and 2.6 (Scheduler)
  2.5 (Notifier) depends on 2.3 (TTS) and 2.6 (Scheduler)
  2.6 (Scheduler) is standalone but orchestrates everything

Phase 3 (Advanced):
  3.1 → 3.2 → 3.3 → 3.4
  
  All independent of each other

Phase 4 (Testing):
  4.1 → 4.2
  
  4.1 (Tests) must complete before 4.2 (Endpoints)
```

**Key dependencies:**
```
1.1 Schema ─────┐
                ├──► 1.2 Architecture ──► 1.3 Chain ──► 2.4 Snooze ─┐
1.1 Schema ─────┘                                          │
                                                          ├──► 2.5 Notifier
2.1 Parsing ──► 2.2 Voice ──► 2.3 TTS ────────────────────►│
                                                          │
2.6 Scheduler ─────────────────────────────────────────────┘
```

---

## Out of Scope (v1)

- Password/auth system
- Smart home integration (Hue lights)
- Voice reply snooze ("snooze 5 min" spoken)
- Multi-device sync
- Bluetooth audio routing preference
- Per-reminder personality override (all anchors use same personality)
- Voice recording import (custom audio files)
- Sound recording within app
- Sound trimming/editing
- Database encryption
- Full-text search on destinations
- Calendar write operations
- Two-way calendar sync
- Event RSVP status filtering
- Continuous location tracking
- Origin address autocomplete
- ETA-based dynamic drive duration

---

## Scenario Coverage Map

| Spec Section | Scenario Files | Status |
|-------------|----------------|--------|
| 2 | chain-full-30min, chain-compressed-15min, chain-minimum-3min, chain-invalid-rejected | **Partial (bugs)** |
| 3 | parse-natural-language, parse-simple-countdown, parse-tomorrow, parse-llm-fallback | **Partial** |
| 4 | tts-generation, tts-fallback, tts-cache-cleanup | **Missing** |
| 5 | dnd-early-suppress, dnd-5min-override, quiet-hours, overdue-drop, chain-serialize, alarm-loop | **Missing** |
| 6 | notifee-schedule, background-fire, recovery-scan, overdue-drop, re-register, late-warning | **Missing** |
| 7 | apple-calendar-suggestion, google-calendar-suggestion, suggestion-accept, permission-denial, sync-failure, recurring | **Missing** |
| 8 | location-still-at-origin, location-already-left, permission-request, permission-denied, single-check | **Missing** |
| 9 | tap-snooze, custom-snooze, chain-recompute, dismiss-timing-right, dismiss-timing-off, snooze-persist | **Missing** |
| 10 | voice-coach, voice-no-nonsense, voice-custom, voice-immutable, voice-variation | **Partial (1 template)** |
| 11 | hit-rate, feedback-adjust, feedback-cap, common-miss, streak-increment, streak-reset, stats-derived | **Partial** |
| 12 | built-in-sound, custom-import, custom-playback, corrupted-fallback, sound-persist | **Missing** |
| 13 | migration-sequence, in-memory-db, cascade-delete, fk-enforcement, uuid-generation | **Partial** |

**Total:** 50 test scenarios defined in spec
**Currently testable:** ~15 (30%)
**Missing coverage:** ~35 scenarios (70%)

---

## Definition of Done

All 50 spec test scenarios have corresponding passing tests.

Every criterion in Sections 2–13 maps to at least one test scenario (Given/When/Then).

**Current test coverage:** 15/50 scenarios (30%)
**Target test coverage:** 50/50 scenarios (100%)
