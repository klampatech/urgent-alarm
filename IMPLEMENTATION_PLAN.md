# URGENT Alarm — Implementation Plan

## Overview

This plan maps the specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to actionable tasks, ordered by dependency.

---

## Phase 0: Quick Wins (Days 1-2)

### 0.1 Database Schema Completeness
**Priority:** Critical | **Spec:** Section 13

Current `init_db()` in `test_server.py` is incomplete. Add missing schema elements:

```sql
-- reminders table additions:
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
custom_sound_path TEXT,
calendar_event_id TEXT,
reminder_type TEXT DEFAULT 'countdown_event'

-- anchors table additions:
tts_fallback INTEGER DEFAULT 0,
snoozed_to TEXT

-- history table additions:
actual_arrival TEXT,
missed_reason TEXT

-- New tables needed:
CREATE TABLE destination_adjustments (
  destination TEXT PRIMARY KEY,
  adjustment_minutes INTEGER DEFAULT 0,
  hit_count INTEGER DEFAULT 0,
  miss_count INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL
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

CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);
```

**Tasks:**
- [ ] Enhance `init_db()` with full schema
- [ ] Enable foreign keys (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Add in-memory mode support (`?mode=memory`)

---

### 0.2 Chain Engine Enhancements
**Priority:** Critical | **Spec:** Section 2.3

Current `compute_escalation_chain()` has bugs. Per TC-01 acceptance criteria:
> Chain for "30 min drive, arrive 9am" produces 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00

Current implementation calculates minutes incorrectly. Fix anchor generation:

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` — returns earliest unfired anchor
- [ ] Implement `shift_anchors(anchor_list, offset_minutes)` — shifts timestamps for snooze
- [ ] Fix chain generation to match TC-01/TC-02/TC-03 exactly
- [ ] Add validation: reject if `drive_duration > (arrival_time - now)`

**Expected behavior per spec:**
| Buffer | Anchors | Start Tier |
|--------|---------|------------|
| ≥25 min | 8 | calm (T-30) |
| 20-24 min | 7 | casual (T-25) |
| 15-19 min | 6 | pointed (T-20) |
| 10-14 min | 5 | urgent (T-15) |
| 5-9 min | 3 | firm (T-5), critical, alarm |
| 1-4 min | 2 | critical (T-1), alarm |
| 0 min | 1 | alarm |

---

## Phase 1: Test Infrastructure (Days 2-3)

### 1.1 Create Scenario Harness
**Priority:** Critical | **Location:** `harness/scenario_harness.py`

**Tasks:**
- [ ] Parse YAML scenario files from `/var/otto-scenarios/{project}/`
- [ ] Execute HTTP API sequences via `requests` library
- [ ] Support variable interpolation (`${variable}` syntax)
- [ ] Validate assertions:
  - `http_status` — verify HTTP response code
  - `db_record` — verify SQLite records exist
  - `llm_judge` — call LLM to evaluate output quality
- [ ] Report pass/fail per scenario
- [ ] Handle `sudo mkdir` for scenario directory creation

**Command:** `sudo python3 harness/scenario_harness.py --project otto-matic`

---

### 1.2 Unit Test Suite
**Priority:** High | **Location:** `tests/test_*.py`

**Tasks:**
- [ ] `tests/test_chain_engine.py` — all 6 test cases from Section 2.5
- [ ] `tests/test_parser.py` — all 7 test cases from Section 3.5
- [ ] `tests/test_voice_messages.py` — message template tests
- [ ] `tests/test_stats.py` — hit rate, streak calculations
- [ ] Use in-memory SQLite for isolation

---

## Phase 2: Core Parsing (Days 3-5)

### 2.1 LLM Adapter Architecture
**Priority:** Critical | **Spec:** Section 3

**Tasks:**
- [ ] Create `src/lib/adapters/ilanguage_model.py` interface:
```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
```

- [ ] Create `src/lib/adapters/mock_llm.py`:
  - Configurable fixture responses
  - Returns predefined `ParsedReminder` objects
  - No network calls

- [ ] Create `src/lib/adapters/keyword_parser.py`:
  - Regex patterns for time/duration extraction
  - Fallback when LLM unavailable
  - Returns `confidence_score < 1.0`

---

### 2.2 LLM Adapter Implementations
**Priority:** High

**Tasks:**
- [ ] Create `src/lib/adapters/minimax_adapter.py` (Anthropic-compatible)
- [ ] Create `src/lib/adapters/anthropic_adapter.py` (direct Claude)
- [ ] Implement orchestrator: try LLM → fallback to keyword → error on failure

**Parser test cases (Section 3.5):**
- [ ] TC-01: Full natural language parse
- [ ] TC-02: Simple countdown ("dryer in 3 min")
- [ ] TC-03: Tomorrow date resolution
- [ ] TC-04: LLM API failure fallback
- [ ] TC-05: Manual field correction (confirmation card)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

## Phase 3: Voice & TTS System (Days 5-8)

### 3.1 TTS Adapter Interface
**Priority:** Critical | **Spec:** Section 4

**Tasks:**
- [ ] Create `src/lib/adapters/itts_adapter.py`:
```python
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> str: ...  # returns file path
```

- [ ] Create `src/lib/adapters/mock_tts.py`:
  - Writes 1-second silent file to `/tmp/tts_cache/`
  - Returns file path

- [ ] Create `src/lib/adapters/elevenlabs_adapter.py`:
  - ElevenLabs API integration
  - Voice ID mapping per personality
  - Async generation with polling (30 sec timeout)
  - Audio caching in `/tts_cache/{reminder_id}/`

---

### 3.2 Voice Personality Enhancements
**Priority:** High | **Spec:** Section 10

**Tasks:**
- [ ] Expand each personality/tier to 3+ message templates (per TC-05)
- [ ] Add random/round-robin message rotation
- [ ] Support custom prompt (max 200 chars) from user_preferences
- [ ] Map personalities to ElevenLabs voice IDs:
  - Coach: `voice_coach_id`
  - Assistant: `voice_assistant_id`
  - Best Friend: `voice_best_friend_id`
  - No-nonsense: `voice_no_nonsense_id`
  - Calm: `voice_calm_id`

**Tests:**
- [ ] TC-01: Coach personality produces motivational messages
- [ ] TC-02: No-nonsense produces brief, direct messages
- [ ] TC-03: Custom prompt modifies tone
- [ ] TC-04: Existing reminders retain original personality
- [ ] TC-05: Message variation (3 distinct phrasings)

---

### 3.3 TTS Cache Manager
**Priority:** High

**Tasks:**
- [ ] Create `src/lib/services/tts_cache.py`:
  - `cache_clip(reminder_id, anchor_id, audio_data) -> file_path`
  - `get_clip(reminder_id, anchor_id) -> file_path`
  - `invalidate_cache(reminder_id)` — on reminder delete
- [ ] Implement fallback: if TTS fails, mark `tts_fallback = TRUE` and use notification text

---

## Phase 4: Scheduling & Notifications (Days 8-12)

### 4.1 Background Scheduler
**Priority:** Critical | **Spec:** Section 6

**Tasks:**
- [ ] Create `src/lib/adapters/ischeduler_adapter.py`:
```python
class ISchedulerAdapter(ABC):
    @abstractmethod
    def schedule_anchor(self, anchor_id: str, timestamp: datetime) -> None: ...
    
    @abstractmethod
    def cancel_anchor(self, anchor_id: str) -> None: ...
    
    @abstractmethod
    def re_register_all_pending(self) -> None: ...  # crash recovery
    
    @abstractmethod
    def run_recovery_scan(self) -> List[str]: ...  # returns fired anchor IDs
```

- [ ] Create `src/lib/adapters/mock_scheduler.py` — in-memory for tests
- [ ] Create `src/lib/adapters/notifee_scheduler.py` — real implementation
- [ ] Implement recovery scan: fire anchors within 15-min grace window
- [ ] Log/.drop anchors >15 min overdue with `missed_reason = "background_task_killed"`

---

### 4.2 Notification Behavior
**Priority:** Critical | **Spec:** Section 5

**Tasks:**
- [ ] Create `src/lib/adapters/inotification_adapter.py`:
```python
class INotificationAdapter(ABC):
    @abstractmethod
    def show(self, tier: UrgencyTier, content: NotificationContent) -> None: ...
    
    @abstractmethod
    def play_sound(self, tier: UrgencyTier) -> None: ...
    
    @abstractmethod
    def vibrate(self, pattern: VibrationPattern) -> None: ...
    
    @abstractmethod
    def is_dnd_enabled(self) -> bool: ...
```

- [ ] Map tiers to sounds:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm

- [ ] Implement DND handling:
  - Early anchors during DND → silent notification
  - Final 5 min during DND → visual override + vibration

- [ ] Implement quiet hours:
  - Default: 10pm–7am configurable
  - Suppress all anchors in window
  - Queue and fire after quiet hours end
  - Drop anchors >15 min overdue

- [ ] Implement chain overlap serialization:
  - Lock during chain escalation
  - Queue incoming anchors
  - Fire after current chain completes

---

### 4.3 T-0 Alarm Looping
**Priority:** Critical

**Tasks:**
- [ ] T-0 anchor loops alarm sound until user action
- [ ] No auto-dismiss — requires explicit dismiss/snooze
- [ ] Background continuation (notifee maintains wake lock)

---

## Phase 5: Snooze & Dismissal (Days 12-14)

### 5.1 Snooze Implementation
**Priority:** High | **Spec:** Section 9

**Tasks:**
- [ ] Tap snooze → 1 minute delay
- [ ] Tap-and-hold → custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement `recompute_chain_after_snooze(reminder_id, delay_minutes)`:
  - Shift all unfired anchor timestamps by `delay_minutes`
  - Update `snoozed_to` column
  - Re-register with scheduler

- [ ] TTS confirmation: "Okay, snoozed {X} minutes."

**Tests (Section 9.5):**
- [ ] TC-01: Tap snooze (1 min)
- [ ] TC-02: Custom snooze picker (5 min)
- [ ] TC-03: Chain re-computation shifts remaining anchors
- [ ] TC-06: Snooze persistence after restart

---

### 5.2 Dismissal & Feedback
**Priority:** High | **Spec:** Section 9.3

**Tasks:**
- [ ] Swipe-to-dismiss → show feedback prompt
- [ ] Feedback prompt: "You missed {destination} — was the timing right?"
  - Yes → store `outcome = 'hit'`
  - No → follow-up: "Left too early" / "Left too late" / "Other"
- [ ] Store feedback in history table
- [ ] "Left too late" → trigger drive_duration adjustment

---

## Phase 6: History & Feedback Loop (Days 14-17)

### 6.1 Stats Service
**Priority:** Medium | **Spec:** Section 11

**Tasks:**
- [ ] Hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` (trailing 7 days)
- [ ] Streak counter: increment on `outcome='hit'` for recurring reminders, reset on `'miss'`
- [ ] Common miss window: find most-frequently-missed urgency tier

**Tests (Section 11.5):**
- [ ] TC-01: Hit rate calculation (80% = 4 hits / 5 resolved)
- [ ] TC-04: Common miss window identification (T-5)
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table alone

---

### 6.2 Feedback Loop
**Priority:** Medium | **Spec:** Section 11.3

**Tasks:**
- [ ] Track adjustments in `destination_adjustments` table
- [ ] On "left_too_late" feedback: `adjustment_minutes += 2`
- [ ] Cap at +15 minutes maximum
- [ ] Apply adjustment when creating new reminder to same destination:
  - `suggested_drive_duration = user_specified + adjustment_minutes`

**Tests:**
- [ ] TC-02: 3 late feedbacks → +6 min on next reminder
- [ ] TC-03: 10 late feedbacks → +15 min cap

---

### 6.3 Data Retention
**Priority:** Low

**Tasks:**
- [ ] Archive history entries older than 90 days (still accessible)
- [ ] Run cleanup job on app launch

---

## Phase 7: Integrations (Days 17-22)

### 7.1 Calendar Integration
**Priority:** Medium | **Spec:** Section 7

**Tasks:**
- [ ] Create `src/lib/adapters/icalendar_adapter.py`:
```python
class ICalendarAdapter(ABC):
    @abstractmethod
    def sync_events(self) -> List[CalendarEvent]: ...
    
    @abstractmethod
    def is_connected(self) -> bool: ...
```

- [ ] Create `src/lib/adapters/apple_calendar_adapter.py` (EventKit)
- [ ] Create `src/lib/adapters/google_calendar_adapter.py` (Google Calendar API)
- [ ] Create `src/lib/adapters/mock_calendar_adapter.py` — for tests
- [ ] Sync on: app launch, every 15 min, background refresh
- [ ] Generate suggestion cards for events with locations
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully

**Tests (Section 7.5):**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

### 7.2 Location Awareness
**Priority:** Medium | **Spec:** Section 8

**Tasks:**
- [ ] Create `src/lib/adapters/ilocation_adapter.py`:
```python
class ILocationAdapter(ABC):
    @abstractmethod
    def check_at_origin(self, origin_lat: float, origin_lng: float) -> bool: ...
```

- [ ] Create `src/lib/adapters/core_location_adapter.py` (iOS)
- [ ] Create `src/lib/adapters/mock_location_adapter.py` — configurable `at_origin` flag
- [ ] Store origin at reminder creation (user-specified or current location)
- [ ] Single location check at departure anchor only
- [ ] 500m geofence radius
- [ ] If at origin: fire firm/critical tier immediately instead of calm departure
- [ ] Request permission at first location-aware reminder creation

**Tests (Section 8.5):**
- [ ] TC-01: User at origin → immediate escalation
- [ ] TC-02: User left → normal chain proceeds
- [ ] TC-03: Permission request at creation
- [ ] TC-04: Permission denied → reminder without location
- [ ] TC-05: Single location check only

---

### 7.3 Sound Library
**Priority:** Low | **Spec:** Section 12

**Tasks:**
- [ ] Bundle built-in sounds per category (5 sounds × 3 categories)
- [ ] Custom import: MP3, WAV, M4A, max 30 sec
- [ ] Sound picker UI per reminder
- [ ] Corrupted sound → fallback to category default
- [ ] Store custom sounds in `custom_sounds` table

**Tests (Section 12.5):**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Phase 8: Mobile App UI (Days 22-30)

### 8.1 Project Setup
**Priority:** High

**Tasks:**
- [ ] Initialize React Native project
- [ ] Set up navigation (React Navigation)
- [ ] Set up state management (Zustand or Redux)
- [ ] Integrate SQLite (react-native-sqlite-storage)
- [ ] Integrate HTTP client

---

### 8.2 Core Screens
**Priority:** High

- [ ] **Quick Add screen:** text/speech input → confirmation card → create
- [ ] **Home screen:** active reminders list, FAB for add
- [ ] **Reminder detail:** edit, snooze, dismiss, history
- [ ] **History screen:** hit rate, streaks, common miss window
- [ ] **Settings screen:** voice personality, quiet hours, calendar, sounds

---

## Adapter Interface Summary

| Interface | Location | Key Methods |
|-----------|----------|-------------|
| `ILanguageModelAdapter` | `src/lib/adapters/` | `parse(text) -> ParsedReminder` |
| `ITTSAdapter` | `src/lib/adapters/` | `generate(text, voice_id) -> path` |
| `ICalendarAdapter` | `src/lib/adapters/` | `sync_events() -> List[Event]` |
| `ILocationAdapter` | `src/lib/adapters/` | `check_at_origin(lat, lng) -> bool` |
| `INotificationAdapter` | `src/lib/adapters/` | `show(tier, content)`, `play_sound(tier)` |
| `ISchedulerAdapter` | `src/lib/adapters/` | `schedule_anchor()`, `re_register_all_pending()` |
| `IAudioPlayerAdapter` | `src/lib/adapters/` | `play(path)`, `loop(path)`, `stop()` |

---

## Dependency Graph

```
Phase 0: Schema + Chain Fixes
    │
    ├─► Phase 1: Test Infrastructure
    │       │
    │       └─► Phase 2: Core Parsing
    │               │
    │               ├─► Phase 3: Voice & TTS
    │               │
    │               ├─► Phase 4: Scheduling + Notifications
    │               │       │
    │               │       └─► Phase 5: Snooze + Dismissal
    │               │
    │               └─► Phase 7: Integrations (Calendar, Location)
    │
    └─► Phase 6: History + Feedback Loop
            │
            └─► Phase 8: Mobile App UI
```

---

## Acceptance Criteria Tracking

### Section 2 (Chain Engine)
- [ ] TC-01: 8 anchors for 30 min buffer
- [ ] TC-02: 5 anchors for 15 min buffer
- [ ] TC-03: 3 anchors for 3 min buffer
- [ ] TC-04: Invalid chain rejected (400 error)
- [ ] TC-05: `get_next_unfired_anchor` recovery
- [ ] TC-06: Chain determinism

### Section 3 (Parsing)
- [ ] TC-01 to TC-07: All parser test cases

### Section 4 (TTS)
- [ ] Clips generated at creation time
- [ ] Anchors fire from cache (no network)
- [ ] Fallback on API failure
- [ ] Cache cleanup on delete

### Section 5 (Notifications)
- [ ] DND early anchor suppressed
- [ ] DND final 5-min override
- [ ] Quiet hours suppression
- [ ] Overdue anchor drop (15 min)
- [ ] Chain overlap serialization
- [ ] T-0 loops until action

### Section 6 (Background)
- [ ] Anchors scheduled in Notifee
- [ ] Background fire with app closed
- [ ] Recovery scan on launch
- [ ] Pending anchors re-registered

### Section 9 (Snooze)
- [ ] Tap snooze (1 min)
- [ ] Custom snooze picker
- [ ] Chain re-computation
- [ ] Snooze persistence after restart
- [ ] Dismissal feedback
- [ ] TTS snooze confirmation

### Section 11 (Stats)
- [ ] Hit rate calculation
- [ ] Feedback loop adjustment
- [ ] Feedback loop cap
- [ ] Common miss window
- [ ] Streak increment/reset

---

## Out of Scope (v1)

- Password/auth (local-only data)
- Smart home integration
- Voice reply ("snooze 5 min")
- Multi-device sync
- Bluetooth audio routing
- Per-reminder personality override
- Voice recording import
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
