# URGENT — AI Escalating Voice Alarm: Implementation Plan

## Project Overview

**Current State:** A minimal HTTP API server (`src/test_server.py`) exposing core functionality via HTTP endpoints. This is a **demo/prototype**, not the full production app.

**Target State:** Full mobile app (React Native/Flutter) with all features from the specification.

---

## Gap Analysis Summary

| Component | Spec Section | Current Status | Gap Severity | Notes |
|-----------|-------------|----------------|--------------|-------|
| Test Server | - | **IMPLEMENTED** | - | HTTP API with chain, parser, voice, stats |
| Scenario Harness | - | **MISSING** | CRITICAL | `harness/scenario_harness.py` doesn't exist |
| src/lib/ structure | - | **MISSING** | HIGH | No adapters, repositories, or services |
| Chain Engine | 2 | **PARTIAL** | MEDIUM | Compression logic needs fixes per test scenarios |
| Parser | 3 | **PARTIAL** | MEDIUM | Works for basic cases, needs confidence scoring |
| Voice Personality | 4, 10 | **PARTIAL** | MEDIUM | Single template per tier, needs variations |
| TTS Generation | 4 | **MISSING** | HIGH | No ElevenLabs adapter, no TTS caching |
| Notifications | 5 | **MISSING** | HIGH | No notification service |
| Background Scheduling | 6 | **MISSING** | HIGH | No Notifee integration |
| Calendar Integration | 7 | **MISSING** | HIGH | No EventKit/Google Calendar adapters |
| Location Awareness | 8 | **MISSING** | HIGH | No geofence check |
| Snooze/Dismissal | 9 | **MISSING** | HIGH | No chain re-computation |
| Feedback Loop | 11 | **PARTIAL** | MEDIUM | Basic adjustment, no cap |
| History/Stats | 11 | **PARTIAL** | MEDIUM | Basic hit rate only |
| Sound Library | 12 | **MISSING** | MEDIUM | No per-reminder sounds |
| Database Schema | 13 | **PARTIAL** | HIGH | Missing columns/tables |
| Migrations | 13 | **MISSING** | HIGH | No versioned migration system |

---

## Priority 1: CRITICAL - Test Infrastructure

### 1.1 Create scenario_harness.py
**Status:** MISSING (blocks all validation)
**File:** `harness/scenario_harness.py`
**Spec Reference:** Definition of Done (Section 14)

**Description:** CLI tool that runs YAML scenario files against the HTTP API server.

**Required Features:**
- Load YAML scenarios from `/var/otto-scenarios/{project}/`
- HTTP client for API calls (POST /reminders, /parse, /voice/message, /history, /anchors/fire, etc.)
- SQLite database inspection for `db_record` assertions
- LLM judge integration for `llm_judge` assertions (call LLM API)
- Scenario runner with pass/fail reporting
- CLI with `--project` argument

**Acceptance Criteria:**
- [ ] Loads scenarios from `/var/otto-scenarios/{project}/`
- [ ] Executes `api_sequence` trigger steps
- [ ] Validates `http_status` assertions
- [ ] Validates `db_record` assertions (query SQLite at `/tmp/urgent-alarm.db`)
- [ ] Validates `llm_judge` assertions (call LLM API with prompt)
- [ ] Reports PASS/FAIL per scenario with summary

**Test Scenarios:** All 15 YAML files in `scenarios/`

---

## Priority 2: Core Logic Refinements

### 2.1 Chain Engine Fixes
**Status:** PARTIAL - needs verification and fixes
**File:** `src/test_server.py` (lines 60-120)
**Spec Reference:** Section 2

**Current Implementation Issues:**
The chain engine has logic for different buffer sizes but test scenarios may reveal bugs:

```python
# Current logic (needs verification against spec):
if buffer_minutes >= 25:  # Full 8 anchors
elif buffer_minutes >= 20:  # 7 anchors
elif buffer_minutes >= 10:  # 5 anchors  
elif buffer_minutes >= 5:  # 3 anchors
else:  # Minimum 2 anchors
```

**Required Test Scenarios:**
- [ ] TC-01: 30 min buffer → 8 anchors at 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] TC-02: 15 min buffer → compressed chain (verify anchor count and timestamps)
- [ ] TC-03: 3 min buffer → 3 anchors at T-3, T-1, T-0
- [ ] TC-04: Invalid chain (drive > arrival) → rejected
- [ ] TC-05: `get_next_unfired_anchor()` returns earliest unfired
- [ ] TC-06: Chain determinism (same inputs = same output)

### 2.2 Parser Improvements
**Status:** PARTIAL - basic keyword extraction works
**File:** `src/test_server.py` (lines 130-210)
**Spec Reference:** Section 3

**Current Capabilities:**
- Extracts destination via regex patterns
- Extracts drive duration ("30 minute drive", "in X minutes")
- Extracts arrival time ("at 9am", "tomorrow 2pm")
- Returns confidence score (0.0-1.0)

**Required Test Scenarios:**
- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am" → correct fields
- [ ] TC-02: "dryer in 3 min" → simple_countdown type
- [ ] TC-03: "meeting tomorrow 2pm, 20 min drive" → tomorrow resolution
- [ ] TC-04: API failure → keyword extraction fallback with confidence < 1.0
- [ ] TC-05: Manual field correction (user edits parsed result)
- [ ] TC-06: Unintelligible input → error message

### 2.3 Voice Personality - Add Message Variations
**Status:** PARTIAL - 1 template per tier
**File:** `src/test_server.py` (lines 230-320)
**Spec Reference:** Section 10

**Current:** Each personality has exactly 1 template per urgency tier.
**Required:** Minimum 3 variations per tier per personality.

**Tasks:**
- [ ] Add 2 more templates per tier per personality (Coach, Assistant, Best Friend, No-nonsense, Calm)
- [ ] Implement rotation logic (round-robin or random selection)
- [ ] Support custom prompt modifier (append to system prompt)

**Required Test Scenarios:**
- [ ] TC-01: "Coach" at T-5 → motivational message
- [ ] TC-02: "No-nonsense" at T-5 → brief, direct
- [ ] TC-03: Custom prompt modifies tone
- [ ] TC-04: Existing reminders keep original personality
- [ ] TC-05: 3 distinct message variations generated

---

## Priority 3: Database Schema Updates

### 3.1 Missing Columns
**Spec Reference:** Section 13

**Current Tables (src/test_server.py, init_db):**
- reminders: id, destination, arrival_time, drive_duration, reminder_type, voice_personality, sound_category, selected_sound, status, created_at, updated_at
- anchors: id, reminder_id, timestamp, urgency_tier, tts_clip_path, fired, fire_count
- history: id, reminder_id, destination, scheduled_arrival, outcome, feedback_type, created_at
- destination_adjustments: destination, adjustment_minutes, hit_count, miss_count
- user_preferences: key, value

**Missing Columns:**
| Table | Missing |
|-------|---------|
| reminders | origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id |
| anchors | tts_fallback, snoozed_to |
| history | actual_arrival, missed_reason |
| destination_adjustments | updated_at |

**Missing Tables:**
- calendar_sync: calendar_type, last_sync_at, sync_token, is_connected
- custom_sounds: id, filename, original_name, category, file_path, duration_seconds, created_at

### 3.2 Migration System
**Status:** MISSING
**Tasks:**
- [ ] Create `schema_migrations` table (version, applied_at)
- [ ] Implement sequential migration runner
- [ ] Apply PRAGMA: WAL mode, foreign_keys ON
- [ ] Support in-memory mode for tests

---

## Priority 4: Adapter Interfaces

### 4.1 Abstract Base Interfaces
**Files:** `src/lib/adapters/base.py`

```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...

class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> str: ...  # returns file path

class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events(self, since: datetime) -> list[CalendarEvent]: ...

class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
```

### 4.2 Concrete Implementations Needed
**Files:** `src/lib/adapters/*.py`

| Adapter | Production | Test/Mock |
|---------|------------|-----------|
| LLM | MiniMaxAdapter, AnthropicAdapter | MockLLMAdapter |
| TTS | ElevenLabsAdapter | MockTTSAdapter |
| Calendar | AppleCalendarAdapter, GoogleCalendarAdapter | MockCalendarAdapter |
| Location | CoreLocationAdapter, FusedLocationAdapter | MockLocationAdapter |

---

## Priority 5: New Services (Not Yet Implemented)

### 5.1 TTS Cache Service
**File:** `src/lib/services/tts_cache_service.py`
**Spec:** Section 4

**Required Features:**
- Generate TTS clips at reminder creation (batch)
- Cache in `/tts_cache/{reminder_id}/`
- Map clip paths to anchor records
- Fallback to system notification sound on failure
- Invalidate cache on reminder deletion

### 5.2 Notification Service
**File:** `src/lib/services/notification_service.py`
**Spec:** Section 5

**Required Features:**
- Sound tier escalation: gentle chime → pointed beep → urgent siren → looping alarm
- DND awareness: silent (early), visual+vibration (final 5 min)
- Quiet hours: 10pm-7am default, queue for post-quiet-hours
- Chain overlap serialization
- T-0 alarm loops until user action

### 5.3 Background Scheduler
**File:** `src/lib/services/scheduler_service.py`
**Spec:** Section 6

**Required Features:**
- Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- Recovery scan on app launch (15-min grace window)
- Re-register pending anchors on crash recovery
- Late firing warning (>60s after scheduled)

### 5.4 Location Check Service
**File:** `src/lib/services/location_check_service.py`
**Spec:** Section 8

**Required Features:**
- Single location check at departure anchor
- 500m geofence radius
- At origin → fire firm tier immediately
- No location history retained

### 5.5 Snooze Service
**File:** `src/lib/services/snooze_service.py`
**Spec:** Section 9

**Required Features:**
- Tap → 1-min snooze
- Tap-and-hold → custom picker (1, 3, 5, 10, 15 min)
- Chain re-computation (shift remaining anchors)
- Re-register with scheduler
- TTS confirmation: "Okay, snoozed [X] minutes"

### 5.6 Dismissal & Feedback Service
**File:** `src/lib/services/dismissal_service.py`
**Spec:** Section 9

**Required Features:**
- Swipe-to-dismiss → feedback prompt
- "Yes — timing was right" → store, no adjustment
- "No — timing was off" → select "Left too early", "Left too late", "Other"
- "Left too late" → +2 min adjustment (cap +15 min)

### 5.7 Calendar Sync Service
**File:** `src/lib/services/calendar_sync_service.py`
**Spec:** Section 7

**Required Features:**
- EventKit (Apple Calendar) adapter
- Google Calendar API adapter
- Sync on launch + every 15 min
- Suggestion cards for events with location
- Recurring event handling
- Permission denial handling

### 5.8 Sound Library Service
**File:** `src/lib/services/sound_library_service.py`
**Spec:** Section 12

**Required Features:**
- 5 built-in sounds per category (Commute, Routine, Errand)
- Custom audio import (MP3, WAV, M4A, max 30 sec)
- Per-reminder sound selection
- Corrupted sound fallback

### 5.9 Stats Service
**File:** `src/lib/services/stats_service.py`
**Spec:** Section 11

**Required Features:**
- Hit rate: hits / (total - pending) * 100 (trailing 7 days)
- Common miss window: most frequently missed tier
- Streak counter: increment on hit, reset on miss
- 90-day retention with archive

---

## Implementation Order

### Phase 1: Critical Infrastructure
1. ✅ **scenario_harness.py** — Unblock all validation (create first)
2. **src/lib/database.py** — Full schema + migrations
3. **src/lib/adapters/base.py** — Abstract interfaces

### Phase 2: Core Logic
4. **Chain engine** — Fix compression logic per test scenarios
5. **Parser** — Improve confidence scoring, error handling
6. **Voice personality** — Add message variations

### Phase 3: External Services (Full Mobile App)
7. **TTS cache service** — ElevenLabs + caching
8. **Notification service** — DND, tier escalation
9. **Background scheduler** — Notifee integration
10. **Location check** — Geofence at departure
11. **Snooze service** — Tap, custom, chain re-compute
12. **Dismissal + feedback** — Feedback flow
13. **Calendar sync** — EventKit + Google Calendar
14. **Sound library** — Built-in + custom import
15. **Stats** — Hit rate, streaks, retention

---

## File Structure to Create

```
src/
├── test_server.py          # Existing - HTTP API
├── lib/
│   ├── __init__.py
│   ├── database.py                 # Connection, migrations, WAL, FK
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract interfaces
│   │   ├── llm_adapter.py          # MiniMax, Anthropic, Mock
│   │   ├── tts_adapter.py          # ElevenLabs, Mock
│   │   ├── calendar_adapter.py      # Apple, Google, Mock
│   │   └── location_adapter.py      # CoreLocation, Mock
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
│       ├── voice_personality_service.py
│       ├── tts_cache_service.py
│       ├── notification_service.py
│       ├── scheduler_service.py
│       ├── location_check_service.py
│       ├── snooze_service.py
│       ├── dismissal_service.py
│       ├── feedback_loop_service.py
│       ├── calendar_sync_service.py
│       ├── sound_library_service.py
│       └── stats_service.py

harness/
├── __init__.py
└── scenario_harness.py              # NEW - critical missing file

scenarios/
└── *.yaml                           # 15 existing test scenarios
```

---

## Validation Commands

```bash
# Start test server
python3 src/test_server.py &

# Syntax check
python3 -m py_compile src/test_server.py

# Run harness (after creating scenario_harness.py)
sudo python3 harness/scenario_harness.py --project otto-matic
```

---

## Out of Scope (Per Spec)

- Password reset / account management (local-only v1)
- Smart home integration (Hue lights)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing preference
- Calendar write operations
- Two-way calendar sync
- Voice recording import
- Prosody control beyond ElevenLabs voice settings
- Per-reminder personality override
- Export/history sharing
- Database encryption
- Full-text search on destinations

---

## Scenario Coverage Map

| Scenario File | Component | Spec Section |
|---------------|-----------|-------------|
| chain-full-30min.yaml | Chain Engine | 2 |
| chain-compressed-15min.yaml | Chain Engine | 2 |
| chain-minimum-3min.yaml | Chain Engine | 2 |
| chain-invalid-rejected.yaml | Chain Engine | 2 |
| parse-natural-language.yaml | Parser | 3 |
| parse-simple-countdown.yaml | Parser | 3 |
| parse-tomorrow.yaml | Parser | 3 |
| voice-coach-personality.yaml | Voice | 10 |
| voice-no-nonsense.yaml | Voice | 10 |
| voice-all-personalities.yaml | Voice | 10 |
| reminder-creation-crud.yaml | Reminders | - |
| reminder-creation-cascade-delete.yaml | Database | 13 |
| history-record-outcome.yaml | History | 11 |
| history-record-miss-feedback.yaml | Feedback | 11 |
| stats-hit-rate.yaml | Stats | 11 |

---

## Dependencies

- Python 3.10+
- SQLite3 (built-in)
- PyYAML (for scenario files)
- requests (for harness HTTP calls)
- anthropic or openai (for LLM judge)
- Notifee, EventKit, CoreLocation (mobile - future)
- ElevenLabs SDK (TTS - future)
