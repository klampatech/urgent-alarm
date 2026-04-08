# URGENT Alarm — Implementation Plan

## Gap Analysis Summary

The `src/test_server.py` implements a minimal proof-of-concept with basic chain computation, keyword parsing, and message templates. The full specification requires 14 major subsystems.

**Completeness by Section:**
| Section | Status | Notes |
|---------|--------|-------|
| 2. Escalation Chain Engine | Partial | Core logic exists, missing validation edge cases |
| 3. Reminder Parsing | Partial | Keyword parser exists, no LLM adapter interface |
| 4. Voice & TTS Generation | Missing | No adapter interface, no file caching |
| 5. Notification & Alarm | Missing | No notification system implementation |
| 6. Background Scheduling | Missing | No Notifee/scheduler integration |
| 7. Calendar Integration | Missing | No adapters for Apple/Google Calendar |
| 8. Location Awareness | Missing | No location check implementation |
| 9. Snooze & Dismissal | Partial | Basic snooze, no chain recompute |
| 10. Voice Personality | Partial | 4 of 5 personalities, 1 template per tier |
| 11. History & Stats | Partial | Hit rate only, no streaks/miss window |
| 12. Sound Library | Missing | No sound management |
| 13. Data Persistence | Partial | Schema incomplete (missing 10+ columns) |
| 14. Testing | Missing | No test files exist |

---

## Priority 1: Foundation (Must Complete First)

### 1.1 Complete Data Persistence Schema
**Files:** `src/db/schema.py`, `src/db/migrations.py`

Add missing columns and tables per spec Section 13:

```sql
-- reminders table additions:
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
calendar_event_id TEXT,
custom_sound_path TEXT,

-- anchors table additions:
tts_fallback BOOLEAN DEFAULT FALSE,
snoozed_to TEXT,

-- history table additions:
actual_arrival TEXT,
missed_reason TEXT,

-- New tables needed:
destination_adjustments (
  destination TEXT PRIMARY KEY,
  adjustment_minutes INTEGER DEFAULT 0,
  hit_count INTEGER DEFAULT 0,
  miss_count INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL
)

calendar_sync (
  calendar_type TEXT PRIMARY KEY,
  last_sync_at TEXT,
  sync_token TEXT,
  is_connected BOOLEAN DEFAULT FALSE
)

custom_sounds (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  category TEXT NOT NULL,
  file_path TEXT NOT NULL,
  duration_seconds REAL,
  created_at TEXT NOT NULL
)

schema_version (key, value)
```

**Acceptance Criteria:**
- All tables created with proper constraints
- Foreign key cascade deletes work
- In-memory mode available for tests

---

### 1.2 Adapter Interfaces (LLM + TTS)
**Files:** `src/adapters/base.py`, `src/adapters/llm.py`, `src/adapters/tts.py`

Define mock-able interfaces per spec Sections 3.3 and 4.3:

```python
# src/adapters/base.py
from abc import ABC, abstractmethod

class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...
    
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> bytes: ...

class ICalendarAdapter(ABC):
    @abstractmethod
    def sync_events(self) -> list[CalendarEvent]: ...
    
class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
```

**Implementations:**
- `MockLanguageModelAdapter` — returns fixture responses (for tests)
- `KeywordExtractionAdapter` — regex-based fallback (already exists as `parse_reminder_natural`)
- `MockTTSAdapter` — writes silent 1-second file
- Future: `MiniMaxAdapter`, `ElevenLabsAdapter`, `AppleCalendarAdapter`, `GoogleCalendarAdapter`

---

### 1.3 Complete Voice Personality System
**Files:** `src/voice/personalities.py`

**Missing:**
- "Calm" personality (5th built-in)
- 3 message variations per tier per personality (currently 1)

**Template Structure:**
```python
VOICE_TEMPLATES = {
    'coach': {
        'calm': [
            "Alright, time to head out for {dest}. {dur} minute drive, you've got this!",
            "Time to go! {dest} awaits in {dur} minutes.",
            "Let's hit the road for {dest} — {dur} minutes to get there.",
        ],
        # ... 3 variations each for all 8 tiers
    },
    # Same for: assistant, best_friend, no_nonsense, calm
}
```

Random selection from available variations on generation.

---

## Priority 2: Core Business Logic

### 2.1 Complete Chain Engine
**Files:** `src/chain/engine.py`, `src/chain/validation.py`

**Gaps:**
- Missing `get_next_unfired_anchor(reminder_id)` function
- Missing validation: `arrival_time > departure_time + minimum_drive_time`
- Missing chain determinism guarantee (testable)

**Implementation:**
```python
def get_next_unfired_anchor(reminder_id: str) -> Anchor | None:
    """Return earliest unfired anchor for recovery after restart."""
    
def validate_reminder(arrival_time, drive_duration) -> ValidationResult:
    """Full validation per TC-04 in spec Section 2."""
```

---

### 2.2 TTS Generation & Caching Service
**Files:** `src/voice/generator.py`, `src/voice/cache.py`

**Flow:**
1. User confirms reminder
2. For each anchor, generate TTS clip via adapter
3. Save to `/tts_cache/{reminder_id}/{anchor_id}.mp3`
4. Update anchor with `tts_clip_path`
5. On fire: play from local cache (zero network latency)

**Graceful Degradation:**
- If TTS fails: set `tts_fallback = True`, play notification sound + text

---

### 2.3 Snooze & Chain Recompute
**Files:** `src/chain/snooze.py`

**Requirements (Section 9):**
- Tap snooze: 1 minute
- Tap-and-hold: custom picker (1, 3, 5, 10, 15 min)
- Recompute remaining anchors: `new_time = now + original_time_remaining`
- TTS confirmation: "Okay, snoozed {X} minutes"
- Persist snooze across app restart

---

### 2.4 Stats & Feedback Loop
**Files:** `src/stats/engine.py`

**Implement per Section 11:**

```python
def calculate_hit_rate(days: int = 7) -> float:
    """TC-01: hit / (hit + miss) * 100 for trailing N days."""

def get_drive_adjustment(destination: str) -> int:
    """TC-02/03: adjustment_minutes capped at +15."""

def get_common_miss_window(destination: str) -> str | None:
    """TC-04: Return most frequently missed urgency tier."""

def update_streak(reminder_id: str, outcome: str) -> int:
    """TC-05/06: Increment on hit, reset on miss."""
```

---

## Priority 3: System Integration

### 3.1 Notification & Alarm Behavior
**Files:** `src/notifications/manager.py`

**Per Section 5:**
- Notification tier escalation (gentle → beep → siren → looping alarm)
- DND awareness (suppress early, override for final 5 min)
- Quiet hours (10pm–7am configurable)
- Chain overlap serialization (queue new anchors)
- T-0 alarm loops until user action

---

### 3.2 Background Scheduling
**Files:** `src/scheduler/manager.py`

**Per Section 6:**
- Register each anchor as individual Notifee task
- Recovery scan on app launch (within 15-min grace window)
- Re-register pending anchors after crash
- Log: late fires (>60s), missed anchors with reason

---

### 3.3 Calendar Integration (Stub)
**Files:** `src/adapters/calendar_apple.py`, `src/adapters/calendar_google.py`

**Per Section 7:**
- Interface for EventKit (iOS) and Google Calendar API
- Sync on launch + every 15 min
- Surface suggestion cards for events with locations
- Create countdown_event on user confirm

**Note:** Full implementation requires platform-specific code; stub for server-side validation.

---

### 3.4 Location Awareness (Stub)
**Files:** `src/adapters/location.py`

**Per Section 8:**
- Single location check at departure anchor
- Compare against origin (500m geofence)
- If still at origin: fire firm/critical tier immediately
- No continuous tracking

**Note:** Full implementation requires platform-specific code; stub for server-side validation.

---

### 3.5 Sound Library
**Files:** `src/sound/library.py`

**Per Section 12:**
- Built-in sounds per category (commute, routine, errand)
- Custom audio import (MP3, WAV, M4A, max 30 sec)
- Per-reminder sound selection
- Fallback to category default if file missing

---

## Priority 4: Testing Infrastructure

### 4.1 Test Suite Structure
**Files:** `harness/test_chain.py`, `harness/test_parser.py`, `harness/test_voice.py`, etc.

**Per Section 14 and AGENTS.md:**

```bash
# Run tests
python3 -m pytest harness/
```

**Test Categories:**

**Unit Tests:**
- Chain engine determinism (TC-06 Section 2)
- Parser fixtures (TC-01-07 Section 3)
- Keyword extraction fallback
- Schema validation
- Stats calculations

**Integration Tests:**
- Parse → Chain → Persist flow
- Anchor scheduling → Fire → Mark fired
- Snooze → Recompute → Re-register
- Dismiss → Feedback → Adjustment

**Scenario Tests:**
- Via `harness/scenario_harness.py --project otto-matic`
- YAML scenarios in `/var/otto-scenarios/otto-matic/`

---

### 4.2 Scenario Harness
**Files:** `harness/scenario_harness.py`

**Per AGENTS.md:**
```bash
sudo python3 harness/scenario_harness.py --project otto-matic
```

Implement scenario runner that:
- Loads YAML scenarios from `/var/otto-scenarios/`
- Makes HTTP requests to test server
- Validates responses against expected outcomes
- Reports pass/fail

---

## Priority 5: Polish & Edge Cases

### 5.1 Error Handling & Graceful Degradation
- LLM failure → keyword extraction fallback
- TTS failure → notification sound + text
- Calendar sync failure → manual reminders still work
- Location permission denied → reminder without location escalation
- Database errors → return meaningful HTTP errors

### 5.2 Validation Edge Cases
- Departure time in the past
- Drive duration exceeds arrival time
- Invalid UUIDs
- Duplicate anchor timestamps

### 5.3 Data Retention
- 90-day history retention
- Archive old data (don't delete)
- Stats computable from history table

---

## Implementation Order (Dependency Graph)

```
[1.1 Schema] ─────┬──→ [2.1 Chain Engine]
                  │
[1.2 Adapters] ──┼──→ [2.2 TTS Caching]
                  │              │
[1.3 Personalities] → [2.4 Stats] ←┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
          [3.1 Notifications] [3.2 Scheduler] [3.3 Calendar]
              │             │             │
              └─────────────┼─────────────┘
                            │
                    [4.1-4.2 Tests]
                            │
                       [5.1-5.3 Polish]
```

---

## Quick Wins (1-2 hours each)

1. **Add "Calm" personality** — Add to templates dict
2. **Add message variations** — Expand each tier to 3 strings
3. **Complete schema** — Add missing columns to SQLite
4. **Add get_next_unfired_anchor** — Query unfired anchors ordered by timestamp
5. **Chain determinism test** — Verify same inputs → same outputs

---

## Estimated Total Effort

| Priority | Components | Estimated |
|----------|------------|-----------|
| P1: Foundation | Schema, Adapters, Personalities | 8-12 hours |
| P2: Core Logic | Chain, TTS, Snooze, Stats | 10-15 hours |
| P3: Integration | Notifications, Scheduler, Calendar, Location, Sound | 15-20 hours |
| P4: Testing | Test suite, Harness | 8-10 hours |
| P5: Polish | Error handling, edge cases, validation | 4-6 hours |
| **Total** | | **45-63 hours** |
