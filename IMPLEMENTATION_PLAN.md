# Urgent Alarm - Implementation Plan

## Project Overview

A mobile alarm app that speaks escalating urgency messages, adapting based on remaining time and context. The app creates departure reminder chains (e.g., "30 min drive to Parker Dr, arrive 9am") with progressive nudges from calm to urgent.

**Current State:** Basic test server with minimal chain engine, keyword parser, and voice templates. No modular architecture, no LLM/TTS adapters, no notification system, no background scheduling, incomplete database schema.

---

## Gap Analysis Summary

| Spec Section | Feature | Status | Verified Issues | Priority |
|-------------|---------|--------|--------|----------|
| 2 | Escalation Chain Engine | **Partial** | 20-24min uses wrong tiers; 3min only 2 anchors (needs 3); missing `get_next_unfired_anchor()` | **P0** |
| 3 | Reminder Parsing | **Partial** | Parser crashes on "in X min"; missing LLM adapter interface | **P0** |
| 4 | Voice & TTS Generation | **Partial** | 40 templates exist (1/tier); needs 120+ (3/tier); no TTS adapter | P1 |
| 5 | Notification & Alarm | **Missing** | Not implemented | P1 |
| 6 | Background Scheduling | **Missing** | Not implemented | P1 |
| 7 | Calendar Integration | **Missing** | Not implemented | P2 |
| 8 | Location Awareness | **Missing** | Not implemented | P2 |
| 9 | Snooze & Dismissal | **Missing** | Not implemented | P1 |
| 10 | Voice Personality System | **Partial** | 1 template per tier, needs 3+ variations each | P1 |
| 11 | History, Stats & Feedback | **Partial** | Hit rate works; missing common_miss_window, streak logic | P2 |
| 12 | Sound Library | **Missing** | Not implemented | P2 |
| 13 | Data Persistence | **Partial** | Missing 13 columns/tables, no migration system | **P0** |

---

## Current Implementation Issues

### Chain Engine Bugs (Section 2)

**Spec requires:**
- ≥25 min buffer: 8 anchors (calm→casual→pointed→urgent→pushing→firm→critical→alarm)
- 10-24 min buffer: 5 anchors (urgent→pushing→firm→critical→alarm), skip calm/casual/pointed
- 5-9 min buffer: 3 anchors (firm→critical→alarm)
- ≤4 min buffer: 3 anchors (firm, critical, alarm)

**Verified bugs (confirmed by test run):**

```python
# BUG 1: 20 min buffer uses wrong tiers (starts at casual, not urgent)
# Code: buffer_minutes >= 20 → tiers = [casual, pointed, urgent, ...]
# Expected: buffer_minutes >= 10 → tiers = [urgent, pushing, firm, critical, alarm]
# Actual output for 20min: casual(15), pointed(10), urgent(5), pushing(0), alarm(0)

# BUG 2: 15 min buffer has duplicate/missing anchors
# Code: urgent(10), pushing(5), firm(0), critical(1), alarm(0)
# Problem: firm(0) and alarm(0) fire at same time; critical(1) fires after firm
# Expected: urgent(10), pushing(5), firm(0), critical(1), alarm(0)
# Issue: This should be correct for 15min per spec, but need to verify

# BUG 3: 3 min buffer produces only 2 anchors (firm, alarm)
# Code: buffer_minutes <= 4 → tiers = [firm(buffer-1), alarm(0)]
# Expected per spec TC-03: 3 anchors: firm(2), critical(1), alarm(0)
# Actual output: firm(2), alarm(0) — MISSING critical anchor
```

**Missing functions:**
- `get_next_unfired_anchor(reminder_id)` - recovery after restart
- `get_unfired_anchors(reminder_id)` - recovery after restart
- `validate_chain()` needs to check `drive_duration <= time_to_arrival`

### Parser Issues (Section 3)

**Confirmed bugs:**
1. **Crash on "in X min" format**: The parser crashes with `IndexError: no such group` when parsing "dryer in 3 min" because the regex pattern `r'in\s+(\d+)\s*(?:minute|min)'` only captures one group, but the code tries to access `match.group(2)` expecting three groups (hour, minute, ampm).
2. **Alternative format fails**: "Parker Dr 9am, 30 min drive" doesn't parse correctly - returns destination as the whole string and misses arrival_time.

**Missing:**
- LLM adapter interface (`ILanguageModelAdapter`)
- Mock adapter for testing
- Keyword extraction with confidence scoring (already has `confidence` field but fallback not triggered properly)
- Proper handling of "tomorrow" date resolution
- Unintelligible input rejection (currently returns 0.3 confidence instead of error)

### Voice Personality Issues (Section 10)

**Spec requires:** 3+ message variations per personality per tier (240+ total templates)
**Current state:** 1 template per tier per personality (40 templates total)

---

## Phase 1: Foundation (P0 — Critical)

### Task 1.1: Fix Escalation Chain Engine

**Files to modify:** `src/test_server.py` → extract to `src/lib/chain_engine.py`

**Required fixes:**
1. Correct anchor tier mapping per spec:
   - ≥25 min: calm, casual, pointed, urgent, pushing, firm, critical, alarm
   - 20-24 min: urgent, pushing, firm, critical, alarm (skip calm/casual)
   - 15-19 min: urgent, pushing, firm, critical, alarm
   - 10-14 min: urgent, pushing, firm, critical, alarm
   - 5-9 min: firm, critical, alarm
   - ≤4 min: critical, alarm (or alarm only if ≤1 min)

2. Add functions:
   ```python
   def get_next_unfired_anchor(reminder_id: str) -> Optional[Anchor]
   def get_unfired_anchors(reminder_id: str) -> List[Anchor]
   def validate_chain(arrival_time: datetime, drive_duration: int) -> ValidationResult
   ```

3. Add unit tests for all TC scenarios

**Acceptance:** All Section 2 test scenarios pass:
- TC-01: 30 min → 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
- TC-02: 15 min → 5 anchors (urgent, pushing, firm, critical, alarm)
- TC-03: 3 min → 3 anchors (firm, critical, alarm) ← **Currently fails (only 2 anchors)**
- TC-04: Invalid chain rejection
- TC-05: get_next_unfired_anchor recovery
- TC-06: Chain determinism

---

### Task 1.2: Complete Data Persistence Layer

**Schema additions needed:**
```sql
-- Add to reminders table (9 columns missing):
, origin_lat REAL
, origin_lng REAL
, origin_address TEXT
, calendar_event_id TEXT
, custom_voice_prompt TEXT
, custom_sound_path TEXT

-- Add to anchors table (2 columns missing):
, tts_fallback INTEGER DEFAULT 0
, snoozed_to TEXT

-- Add to history table (2 columns missing):
, actual_arrival TEXT
, missed_reason TEXT

-- New tables needed (3 tables missing):
calendar_sync (
    calendar_type TEXT PRIMARY KEY
    , last_sync_at TEXT
    , sync_token TEXT
    , is_connected INTEGER DEFAULT 0
)

custom_sounds (
    id TEXT PRIMARY KEY
    , filename TEXT NOT NULL
    , original_name TEXT NOT NULL
    , category TEXT NOT NULL
    , file_path TEXT NOT NULL
    , duration_seconds REAL
    , created_at TEXT NOT NULL
)

schema_version (
    version INTEGER PRIMARY KEY
)
```

**Operations needed:**
- Cascade delete for reminders → anchors
- Migration system (sequential, versioned)
- UUID v4 for all IDs
- WAL mode and foreign keys enabled

**Acceptance:** Fresh install creates all tables; test DB uses in-memory mode.

---

### Task 1.3: Create Modular Architecture

**Directory structure:**
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

# src/lib/calendar_adapter.py
class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events_with_location(self, since: datetime) -> list[CalendarEvent]: ...

# src/lib/location_adapter.py
class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
    def is_at_origin(self, origin: tuple, radius_m: int = 500) -> bool: ...
```

**Acceptance:** `python3 -m py_compile src/lib/*.py` passes; all adapters have working mock implementations.

---

## Phase 2: Core Features (P1 — Important)

### Task 2.1: Implement LLM Parsing with Fallback

**Requirements:**
- LLM adapter configurable via env var (MiniMax/Anthropic)
- Keyword extraction fallback with regex patterns
- Parse reminder_type enum from context
- Return confidence score for fallback mode
- Reject unintelligible input with user-facing error

**Test scenarios to pass:** TC-01 through TC-07 from Section 3.5

---

### Task 2.2: Implement Voice Personality System

**Requirements:**
- 5 built-in personalities with 3+ message variations per tier each
- Custom prompt mode (max 200 chars)
- Personality stored in reminder at creation time

**Message templates needed:**
| Personality | Tiers | Variations | Total |
|------------|-------|------------|-------|
| Coach | 8 | 3 each | 24 |
| Assistant | 8 | 3 each | 24 |
| Best Friend | 8 | 3 each | 24 |
| No-nonsense | 8 | 3 each | 24 |
| Calm | 8 | 3 each | 24 |
| **Total** | | | **120+** |

**Acceptance:** Each personality generates distinct message styles.

---

### Task 2.3: Implement TTS Generation & Caching

**Requirements:**
- ElevenLabs API adapter (mock-able)
- Generate clips at reminder creation for all anchors
- Cache at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- Fallback: if TTS fails, mark `tts_fallback = true`
- Cleanup: delete cached files when reminder deleted

**Test scenarios to pass:** TC-01 through TC-05 from Section 4.5

---

### Task 2.4: Implement Snooze & Dismissal Flow

**Requirements:**
- Tap snooze: 1 minute delay, TTS confirmation
- Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation: shift remaining anchors by snooze duration
- Swipe dismiss: feedback prompt with Yes/No options
- Feedback updates `destination_adjustments` (+2 min per 'left_too_late', cap +15)
- Snooze persistence survives app restart

**Test scenarios to pass:** TC-01 through TC-06 from Section 9.5

---

### Task 2.5: Implement Notification & Alarm Behavior

**Requirements:**
- Notification sound tiers:
  - Calm/Casual: gentle chime
  - Pointed/Urgent: pointed beep
  - Pushing/Firm: urgent siren
  - Critical/Alarm: looping alarm
- DND handling with visual+vibration override for final 5 min
- Quiet hours (default 10pm-7am)
- Overdue anchors (15-min rule): drop silently
- Chain overlap serialization
- T-0 alarm loops until user acts

**Test scenarios to pass:** TC-01 through TC-06 from Section 5.5

---

### Task 2.6: Implement Background Scheduling

**Requirements:**
- Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- Recovery scan on app launch:
  - Fire anchors within 15-minute grace window
  - Drop and log anchors >15 min overdue
- Re-register pending anchors on crash recovery
- Late fire warning (>60s after scheduled time)

**Test scenarios to pass:** TC-01 through TC-06 from Section 6.5

---

## Phase 3: Advanced Features (P2 — Nice to Have)

### Task 3.1: Calendar Integration

**Requirements:**
- Apple Calendar adapter (EventKit)
- Google Calendar adapter (API)
- Sync on launch + every 15 minutes
- Suggestion cards for events with locations

**Test scenarios:** TC-01 through TC-06 from Section 7.5

---

### Task 3.2: Location Awareness

**Requirements:**
- Single location check at departure anchor only
- Geofence radius: 500 meters
- If at origin: fire firm/critical immediately
- Request permission at first location-aware reminder

**Test scenarios:** TC-01 through TC-05 from Section 8.5

---

### Task 3.3: History, Stats & Feedback Loop

**Requirements:**
- Hit rate: `hits / (total - pending) * 100` for trailing 7 days
- Common miss window: most frequently missed urgency tier
- Streak counter: increment on hit, reset on miss
- Feedback loop: +2 min per late, cap at +15 min

**Test scenarios:** TC-01 through TC-07 from Section 11.5

---

### Task 3.4: Sound Library

**Requirements:**
- 5 built-in sounds per category (Commute, Routine, Errand)
- Import custom audio (MP3, WAV, M4A, max 30 sec)
- Corrupted file fallback to category default

**Test scenarios:** TC-01 through TC-05 from Section 12.5

---

## Phase 4: Testing & Validation (P1)

### Task 4.1: Create Comprehensive Test Suite

**Test files to create:**
```
tests/
  __init__.py
  test_chain_engine.py
  test_parser.py
  test_tts_adapter.py
  test_notifier.py
  test_scheduler.py
  test_calendar_adapter.py
  test_location_adapter.py
  test_snooze.py
  test_voice_personalities.py
  test_stats.py
  test_sound_library.py
  test_database.py
  conftest.py
```

**Acceptance:** All spec test scenarios pass.

---

### Task 4.2: Additional API Endpoints

**Endpoints to add:**
- `GET /anchors/{reminder_id}` — List anchors
- `GET /stats/common-miss-window` — Most missed tier
- `GET /stats/streak/{destination}` — Current streak
- `GET /adjustments/{destination}` — Drive duration adjustments
- `POST /snooze` — Apply snooze
- `DELETE /reminders/{id}` — Cancel reminder

---

## Scenario Coverage

| Spec Section | Scenario Files | Status |
|-------------|----------------|--------|
| 2 | chain-full-30min, chain-compressed-15min, chain-minimum-3min, chain-invalid-rejected | Partial (bugs) |
| 3 | parse-natural-language, parse-simple-countdown, parse-tomorrow | Partial |
| 10 | voice-coach, voice-no-nonsense, voice-all-personalities | Partial (1 template) |
| 11 | history-record-outcome, history-record-miss-feedback, stats-hit-rate | Partial |
| 13 | reminder-creation-crud, reminder-creation-cascade-delete | Partial |

**Missing scenarios:**
- Section 4: TTS generation tests
- Section 5: Notification/alarm behavior
- Section 6: Background scheduling
- Section 7: Calendar integration
- Section 8: Location awareness
- Section 9: Snooze/dismissal flow
- Section 12: Sound library

---

## Implementation Order

```
Phase 1 (Foundation):
  1.3 → 1.2 → 1.1    (architecture → schema → fix chain engine)

Phase 2 (Core Features):
  2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6

Phase 3 (Advanced):
  3.1 → 3.2 → 3.3 → 3.4

Phase 4 (Testing):
  4.1 → 4.2
```

**Key dependencies:**
- 2.3 (TTS) depends on 1.3 (TTS adapter interface)
- 2.4 (Snooze) depends on 1.1 (Chain engine) and 2.6 (Scheduler)
- 2.5 (Notifier) depends on 2.3 (TTS) and 2.6 (Scheduler)
- 3.1 (Calendar) depends on 1.3 (Calendar adapter interface)
- 4.1 (Tests) depends on all Phase 1-3 tasks

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
