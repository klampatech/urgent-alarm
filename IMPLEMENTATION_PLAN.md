# URGENT Alarm - Implementation Plan

> **Generated:** 2026-04-08  
> **Updated:** 2026-04-08  
> **Spec Files:** `specs/urgent-voice-alarm-app-2026-04-08.md`, `specs/urgent-voice-alarm-app-2026-04-08.spec.md`

---

## Executive Summary

The codebase currently contains a minimal HTTP test server with basic chain engine, parser, and voice templates. **The harness is empty** (Otto cannot run), the database schema is incomplete, and ~70% of spec features are missing. This plan prioritizes the harness creation first (unblocking Otto), then completes the backend implementation.

---

## Quick Status

| Component | Status | Blocked By |
|-----------|--------|------------|
| `src/test_server.py` | ⚠️ ~40% | Missing adapters, incomplete schema |
| `harness/` | ❌ **EMPTY** | **CRITICAL — Otto cannot validate** |
| `src/lib/` | ❌ Missing | Must be created for adapters |
| `scenarios/` | ✅ 16 files | Need harness to execute |
| `specs/*.md` | ✅ Complete | Source of truth |

---

## Critical Blocker: Empty Harness

**The `harness/` directory is empty. Otto cannot run without `harness/scenario_harness.py`.**

### Why This Blocks Everything
1. Otto validates code by running scenarios from `/var/otto-scenarios/{project}/*.yaml`
2. No harness = no validation = cannot measure progress
3. Scenarios defined but not executable

### The Fix (Priority 0)

**File to create:** `harness/scenario_harness.py`

This is the ONLY thing blocking Otto. All other tasks are backend improvements that cannot be validated without this.

---

## Gaps by Spec Section

| § | Section | Severity | Status | Gap Details |
|---|---------|----------|--------|-------------|
| **—** | **Otto Harness** | 🔴 **CRITICAL** | ❌ Empty | `harness/` blocks all validation |
| 2 | Escalation Chain Engine | 🟡 Medium | ⚠️ Partial | Missing 20-24 min compression, `get_next_unfired_anchor()`, determinism |
| 3 | Reminder Parsing | 🔴 High | ⚠️ Keyword only | No LLM adapter interface, no mock, no confirmation flow |
| 4 | Voice & TTS Generation | 🔴 High | ❌ Missing | No ElevenLabs adapter, no TTS caching, no clip storage |
| 5 | Notification & Alarm | 🔴 High | ❌ Missing | No DND/quiet hours, no tier escalation sounds, no serialization |
| 6 | Background Scheduling | 🔴 High | ❌ Missing | No Notifee/BGTaskScheduler, no recovery scan, no 15-min rule |
| 7 | Calendar Integration | 🟡 Medium | ❌ Missing | No EventKit/Google Calendar adapters |
| 8 | Location Awareness | 🟡 Medium | ❌ Missing | No CoreLocation/FusedLocationProvider, no 500m geofence |
| 9 | Snooze & Dismissal | 🟡 Medium | ❌ Missing | No tap/tap-hold snooze, no chain recompute, no feedback |
| 10 | Voice Personality | 🟡 Medium | ⚠️ 1 template/tier | Spec requires 3 variations per tier (120 messages total) |
| 11 | History & Stats | 🟡 Medium | ⚠️ Basic | Missing common miss window, streak counter, adjustment cap |
| 12 | Sound Library | 🟡 Medium | ❌ Missing | No categories, no custom import, no fallback |
| 13 | Data Persistence | 🟡 Medium | ⚠️ Incomplete | Missing 10+ columns, no migration system, no in-memory for tests |
| 14 | Definition of Done | ⚪ Info | — | Requires passing tests for all acceptance criteria |

---

## Detailed Gap Analysis

### Section 2: Escalation Chain Engine

**Current:** `compute_escalation_chain()` in `test_server.py` handles basic cases

**Missing:**
- [ ] 20-24 min buffer compression (currently only 10-24 min and 5-9 min covered)
- [ ] `get_next_unfired_anchor(reminder_id)` function for recovery
- [ ] Chain determinism (same inputs → same outputs) for unit testing
- [ ] `fire_count` tracking in anchor records
- [ ] Validation: `arrival_time > departure_time + minimum_drive_time`

**Test Coverage Required (TC-01 through TC-06):**
```
TC-01: 30 min drive → 8 anchors (8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00)
TC-02: 15 min drive → 5 anchors (compressed, skip calm/casual)
TC-03: 3 min drive → 3 anchors (T-3 firm, T-1 critical, T-0 alarm)
TC-04: 120 min drive → validation error
TC-05: get_next_unfired_anchor() returns earliest unfired
TC-06: Chain determinism — same inputs = same outputs
```

### Section 3: Reminder Parsing & Creation

**Current:** `parse_reminder_natural()` with regex patterns

**Missing:**
- [ ] LLM adapter interface (`ILanguageModelAdapter`)
- [ ] Mock LLM adapter for testing (`MockLLMAdapter`)
- [ ] Keyword fallback adapter with confidence scoring
- [ ] Confirmation card flow (user edits parsed fields)
- [ ] Support for "tomorrow Xpm" date resolution
- [ ] Morning routine and standing_recurring type detection
- [ ] Empty/unintelligible input rejection with user-facing error

**Test Coverage Required:**
```
TC-01: "30 min drive to Parker Dr, check-in at 9am" → correct fields
TC-02: "dryer in 3 min" → simple_countdown, arrival=now+3min
TC-03: "meeting tomorrow 2pm" → next day's 2pm
TC-04: LLM API failure → keyword extraction fallback with confidence < 1.0
TC-05: User edits arrival to 9:15am → confirmed reminder uses 9:15
TC-06: "asdfgh" → error message
TC-07: Mock adapter returns fixture without API call
```

### Section 4: Voice & TTS Generation

**Current:** `VOICE_PERSONALITIES` dictionary with templates

**Missing:**
- [ ] ElevenLabs adapter interface (`ITTSAdapter`)
- [ ] Mock TTS adapter for testing
- [ ] TTS clip caching to filesystem (`/tts_cache/{reminder_id}/`)
- [ ] TTS fallback when ElevenLabs unavailable
- [ ] Custom voice prompt support (passed to ElevenLabs)
- [ ] TTS cache invalidation on reminder delete
- [ ] Voice ID mapping per personality

**Test Coverage Required:**
```
TC-01: 8 MP3 clips created in /tts_cache/{reminder_id}/
TC-02: Anchor fires from local cache (no network call)
TC-03: TTS fallback when ElevenLabs 503
TC-04: TTS cache cleanup on delete
TC-05: Mock TTS writes silent file without API call
```

### Section 5: Notification & Alarm Behavior

**Current:** None

**Missing:**
- [ ] Notification tier escalation (chime → beep → siren → alarm)
- [ ] DND awareness (early anchors silent, final 5 min override with vibration)
- [ ] Quiet hours (default 10pm–7am configurable)
- [ ] Overdue anchor queue (fired after DND/quiet hours end)
- [ ] 15-minute overdue drop rule
- [ ] Chain overlap serialization (queue new anchors until current completes)
- [ ] T-0 alarm looping until dismiss/snooze
- [ ] Notification display: destination, time remaining, voice icon

### Section 6: Background Scheduling

**Current:** None

**Missing:**
- [ ] Notifee integration (BGTaskScheduler + WorkManager)
- [ ] Individual anchor task registration
- [ ] Recovery scan on app launch
- [ ] Re-registration of pending anchors after crash
- [ ] Overdue anchor handling (15-min grace window)
- [ ] Missed anchor logging with `missed_reason`
- [ ] Late fire warning (>60s after scheduled time)

### Section 7: Calendar Integration

**Current:** None

**Missing:**
- [ ] `ICalendarAdapter` interface
- [ ] Apple Calendar adapter (EventKit)
- [ ] Google Calendar adapter (Google Calendar API)
- [ ] Calendar sync scheduler (every 15 min + on launch)
- [ ] Suggestion card generation for events with locations
- [ ] Recurring event handling
- [ ] Calendar permission denial handling
- [ ] Calendar sync failure graceful degradation

### Section 8: Location Awareness

**Current:** None

**Missing:**
- [ ] Origin storage (lat/lng or address)
- [ ] Single CoreLocation/FusedLocationProvider call at departure
- [ ] 500m geofence check
- [ ] Immediate escalation if still at origin
- [ ] Location permission request (only at first location-aware reminder)
- [ ] No location history retention
- [ ] Fallback if permission denied

### Section 9: Snooze & Dismissal Flow

**Current:** None

**Missing:**
- [ ] Tap snooze (1 minute)
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain recomputation after snooze
- [ ] Snoozed anchor re-registration with Notifee
- [ ] Swipe-to-dismiss feedback prompt
- [ ] Feedback processing (left_too_early, left_too_late, other)
- [ ] TTS snooze confirmation
- [ ] Snooze persistence after app restart

### Section 10: Voice Personality System

**Current:** 1 template per tier per personality (5 personalities × 8 tiers = 40)

**Missing:**
- [ ] 3 message variations per tier per personality (5 × 8 × 3 = 120 total)
- [ ] Custom prompt support (max 200 chars)
- [ ] Message selection randomization
- [ ] Per-destination personality storage

### Section 11: History, Stats & Feedback

**Current:** Basic `calculate_hit_rate()`

**Missing:**
- [ ] "Common miss window" identification
- [ ] Streak counter (increment on hit, reset on miss)
- [ ] Drive duration adjustment: `+2 min` per late feedback, capped at +15 min
- [ ] 90-day retention with archive
- [ ] Stats computed from history table (no separate stats store)
- [ ] `GET /stats/common-miss-window`
- [ ] `GET /stats/streaks`

### Section 12: Sound Library

**Current:** None

**Missing:**
- [ ] Built-in sounds per category (Commute, Routine, Errand, Custom)
- [ ] Custom audio import (MP3, WAV, M4A, max 30 sec)
- [ ] Sound normalization/transcoding
- [ ] Per-reminder sound selection
- [ ] Corrupted sound fallback
- [ ] `custom_sounds` table in schema

### Section 13: Data Persistence

**Current:** Basic schema in `init_db()`

**Missing:**
- [ ] Sequential migration system (schema_v1, schema_v2, etc.)
- [ ] In-memory SQLite for tests (`Database.getInMemoryInstance()`)
- [ ] UUID v4 generation enforcement
- [ ] WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Missing columns:
  - `reminders`: origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id, updated_at
  - `anchors`: tts_fallback, snoozed_to
  - `history`: actual_arrival, missed_reason
- [ ] New tables: `calendar_sync`, `custom_sounds`
- [ ] Cascade delete: reminders → anchors

---

## Implementation Tasks (Prioritized)

### P0 — Otto Harness (BLOCKING ALL VALIDATION)

#### Task 0.1: Create Scenario Harness
**File:** `harness/scenario_harness.py`

```bash
# Acceptance:
# 1. Copy scenarios (requires sudo)
sudo mkdir -p /var/otto-scenarios/urgent-alarm
sudo cp scenarios/*.yaml /var/otto-scenarios/urgent-alarm/

# 2. Run harness
sudo python3 harness/scenario_harness.py --project urgent-alarm

# 3. Verify output
cat /tmp/ralph-scenario-result.json
# Should contain {"pass": true} or {"pass": false}
```

**Dependencies:** None

**Responsible:** This is the ONLY task blocking all validation.

---

### P1 — Database Schema Completion

#### Task 1.1: Complete Schema (Spec §13)
**File:** `src/test_server.py` (update `init_db()`)

**Changes:**
```sql
-- reminders table: add
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
custom_sound_path TEXT,
calendar_event_id TEXT,
updated_at TEXT NOT NULL,

-- anchors table: add
tts_fallback INTEGER DEFAULT 0,
snoozed_to TEXT,

-- history table: add
actual_arrival TEXT,
missed_reason TEXT,

-- Add new tables:
calendar_sync (
    calendar_type TEXT PRIMARY KEY,
    last_sync_at TEXT,
    sync_token TEXT,
    is_connected INTEGER DEFAULT 0
),

custom_sounds (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration_seconds REAL,
    created_at TEXT NOT NULL
),

-- Enable PRAGMAs
PRAGMA foreign_keys = ON,
PRAGMA journal_mode = WAL
```

#### Task 1.2: Add Migration System
**File:** `src/lib/db_migrations.py`

```python
MIGRATIONS = [
    ("schema_v1", create_base_tables),
    ("schema_v2", add_missing_columns),
    ("schema_v3", add_new_tables),
]
```

#### Task 1.3: Add In-Memory Database for Tests
**File:** `src/lib/database.py`

```python
def get_inmemory_instance():
    """Returns fresh in-memory SQLite connection with migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn
```

---

### P1 — Chain Engine Enhancement

#### Task 1.4: Complete Chain Engine (Spec §2)
**File:** `src/test_server.py`

**Changes:**
1. Fix 20-24 min buffer compression
2. Add `get_next_unfired_anchor(reminder_id)` function
3. Add `fire_count` tracking
4. Add determinism (use sorted tuple output)

**Acceptance:** All 6 test scenarios pass (TC-01 through TC-06)

---

### P2 — Adapter Interfaces

#### Task 2.1: LLM Adapter (Spec §3)
**Files:** `src/lib/adapters/__init__.py`, `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_mock.py`

```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...
    
    @abstractmethod
    def is_mock(self) -> bool: ...

class MockLLMAdapter(ILanguageModelAdapter):
    fixtures: dict[str, ParsedReminder]

class KeywordFallbackAdapter(ILanguageModelAdapter):
    # Regex-based, returns confidence < 1.0

class ProductionLLMAdapter(ILanguageModelAdapter):
    # MiniMax or Anthropic API
```

#### Task 2.2: TTS Adapter (Spec §4)
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_mock.py`

```python
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> bytes: ...
    
    @abstractmethod
    def cache_clip(self, reminder_id: str, anchor_id: str, audio: bytes) -> str: ...

class MockTTSAdapter(ITTSAdapter):
    # Writes 1-second silent file

class ElevenLabsAdapter(ITTSAdapter):
    # Production ElevenLabs API
```

---

### P3 — Voice Personalities

#### Task 3.1: Expand Message Templates (Spec §10)
**File:** `src/test_server.py` (update `VOICE_PERSONALITIES`)

**Change:** 1 template → 3 templates per tier per personality

```python
VOICE_PERSONALITIES = {
    'coach': {
        'urgent': [
            "Let's GO! You've got {remaining} minutes to {dest}!",
            "Time to move! {dest} in {remaining} minutes!",
            "Chop chop! {remaining} minutes — {dest}!",
        ],
        # ... other tiers
    },
    # ... other personalities
}
```

**Acceptance:** 120 unique message templates (5 personalities × 8 tiers × 3 variations)

---

### P3 — History & Stats

#### Task 3.2: Complete Stats (Spec §11)
**File:** `src/test_server.py`

**Changes:**
1. Add `calculate_common_miss_window()` function
2. Add `calculate_streak(reminder_id)` function
3. Cap adjustment at +15 minutes
4. Add 90-day retention logic

**New endpoints:**
```
GET  /stats/common-miss-window
GET  /stats/streak/{reminder_id}
```

---

### P4 — Notifications & Scheduling

#### Task 4.1: Notification Behavior (Spec §5)
**File:** `src/lib/notifications.py`

**Components:**
- `NotificationTier` enum (gentle_chime, pointed_beep, urgent_siren, looping_alarm)
- `DNDChecker` class
- `QuietHoursChecker` class
- `ChainSerializer` class
- `NotificationManager` class

#### Task 4.2: Background Scheduling (Spec §6)
**File:** `src/lib/scheduler.py`

**Components:**
- `NotifeeAdapter` class (mock-able)
- `RecoveryScanner` class
- `AnchorRegistry` class

---

### P5 — Calendar & Location

#### Task 5.1: Calendar Integration (Spec §7)
**File:** `src/lib/adapters/calendar_adapter.py`

**Components:**
- `ICalendarAdapter` interface
- `AppleCalendarAdapter` (EventKit)
- `GoogleCalendarAdapter` (Google Calendar API)
- `CalendarSyncScheduler` class

#### Task 5.2: Location Awareness (Spec §8)
**File:** `src/lib/location.py`

**Components:**
- `LocationChecker` class
- `GeofenceManager` class (500m radius)

---

### P6 — Snooze & Dismissal

#### Task 6.1: Snooze & Dismissal (Spec §9)
**File:** `src/lib/snooze.py`

**Components:**
- `SnoozeHandler` class (tap, tap-hold, custom duration)
- `ChainRecomputer` class
- `FeedbackCollector` class

---

## Scenario → Task Mapping

| Scenario File | Test Case | Requires |
|--------------|-----------|----------|
| `chain-full-30min.yaml` | TC-01 (§2) | Task 1.4 |
| `chain-compressed-15min.yaml` | TC-02 (§2) | Task 1.4 |
| `chain-minimum-3min.yaml` | TC-03 (§2) | Task 1.4 |
| `chain-invalid-rejected.yaml` | TC-04 (§2) | Task 1.4 |
| `parse-natural-language.yaml` | TC-01 (§3) | Tasks 2.1, 3.1 |
| `parse-simple-countdown.yaml` | TC-02 (§3) | Task 2.1 |
| `parse-tomorrow.yaml` | TC-03 (§3) | Task 2.1 |
| `voice-coach-personality.yaml` | TC-01 (§10) | Task 3.1 |
| `voice-no-nonsense.yaml` | TC-02 (§10) | Task 3.1 |
| `voice-all-personalities.yaml` | §10 all | Task 3.1 |
| `history-record-outcome.yaml` | TC-04 (§11) | Task 3.2 |
| `history-record-miss-feedback.yaml` | TC-05 (§11) | Task 3.2 |
| `stats-hit-rate.yaml` | TC-01 (§11) | Task 3.2 |
| `reminder-creation-crud.yaml` | §13 CRUD | Task 1.1 |
| `reminder-creation-cascade-delete.yaml` | TC-03 (§13) | Task 1.1 |

---

## Validation Commands

```bash
# 1. Start test server
python3 src/test_server.py &
sleep 2

# 2. Run manual tests
curl http://localhost:8090/health

# 3. Run harness (requires sudo)
sudo python3 harness/scenario_harness.py --project urgent-alarm

# 4. Lint
python3 -m py_compile src/test_server.py harness/scenario_harness.py
```

---

## Dependencies Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Otto Harness (P0)                            │
│                  harness/scenario_harness.py                        │
│                     MUST BE FIRST                                   │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Database Layer (P1)                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐    │
│  │ Schema v1..N   │  │ Migrations    │  │ In-memory for tests │    │
│  └────────────────┘  └────────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Core Logic (P1-P3)                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐      │
│  │ Chain Engine   │  │ LLM Adapter    │  │ TTS Adapter        │      │
│  │ §2             │  │ §3             │  │ §4                  │      │
│  └────────────────┘  └────────────────┘  └────────────────────┘      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐      │
│  │ Voice Messages │  │ History/Stats │  │ Notifications      │      │
│  │ §10            │  │ §11           │  │ §5                  │      │
│  └────────────────┘  └────────────────┘  └────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 External Integrations (P4-P6)                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐      │
│  │ Scheduler      │  │ Calendar       │  │ Location           │      │
│  │ §6             │  │ §7             │  │ §8                  │      │
│  └────────────────┘  └────────────────┘  └────────────────────┘      │
│  ┌────────────────┐  ┌────────────────┐                              │
│  │ Snooze/Dismiss │  │ Sound Library │                              │
│  │ §9             │  │ §12            │                              │
│  └────────────────┘  └────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Out of Scope (Per Spec)

- Password reset / account management (v1: local-only)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min")
- Multi-device sync
- Bluetooth audio routing preference
- Database encryption
- Full-text search on destinations
- Continuous location tracking (single check only)
- Smart home integration
- Automatic calendar adjustment based on feedback

---

## File Corrections

| AGENTS.md says | Actual file |
|----------------|-------------|
| `src/web.py` | `src/test_server.py` |
| `python3 src/web.py &` | `python3 src/test_server.py &` |

---

*Last Updated: 2026-04-08*
