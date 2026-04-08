# Urgent Alarm - Implementation Plan

## Current State Assessment

The project has a working **test server** (`src/test_server.py`) with partial core functionality. After thorough analysis, here are the **confirmed bugs and gaps**:

### Confirmed Bugs in Current Code

| Component | Bug | Severity |
|-----------|-----|----------|
| Chain Engine | Anchors not sorted by timestamp | **Critical** |
| Chain Engine | 3min buffer produces 2 anchors instead of 3 (missing critical) | **Critical** |
| Chain Engine | No validation for drive_duration > time_to_arrival | **Critical** |
| Parser | Regex bug: "dryer in 3 min" crashes (missing group) | **High** |
| Parser | "in X min" pattern doesn't set reminder_type correctly | **Medium** |

### Missing Schema (Per Spec Section 13)

| Table/Column | Status |
|--------------|--------|
| `reminders.custom_sound_path` | Missing |
| `reminders.origin_lat`, `origin_lng`, `origin_address` | Missing |
| `reminders.calendar_event_id` | Missing |
| `anchors.tts_fallback` | Missing |
| `anchors.snoozed_to` | Missing |
| `history.actual_arrival` | Missing |
| `history.missed_reason` | Missing |
| `user_preferences.updated_at` | Missing |
| `destination_adjustments.updated_at` | Missing |
| `custom_sounds` table | Missing |
| `calendar_sync` table | Missing |
| Schema versioning | Missing |

### Missing Functions/Features (Per Spec Sections)

| Feature | Spec Section | Status |
|---------|--------------|--------|
| `get_next_unfired_anchor()` | 2.3 | Missing |
| Chain determinism testing | 2.3 | Missing |
| LLM Adapter interface + mock | 3.3 | Missing |
| Keyword extraction as fallback | 3.3 | Partial (has bugs) |
| TTS Adapter interface + mock | 4.3 | Missing |
| TTS cache system | 4.3 | Missing |
| ElevenLabs adapter | 4.3 | Missing |
| Message variations (3 per tier) | 10.3 | Missing |
| Custom voice prompt support | 10.3 | Missing |
| Notification tier escalation | 5.3 | Missing |
| DND handling | 5.3 | Missing |
| Quiet hours | 5.3 | Missing |
| Chain overlap serialization | 5.3 | Missing |
| T-0 looping alarm | 5.3 | Missing |
| Background scheduling simulation | 6.3 | Missing |
| Recovery scan | 6.3 | Missing |
| Calendar adapters | 7.3 | Missing |
| Location awareness | 8.3 | Missing |
| Snooze chain re-computation | 9.3 | Missing |
| Feedback prompt | 9.3 | Missing |
| Feedback loop (adjust drive_duration) | 9.3 | Partial |
| Sound library | 12.3 | Missing |
| Common miss window | 11.3 | Missing |
| Streak counter | 11.3 | Missing |

---

## Priority 1: Critical Bug Fixes

### Task 1.1: Fix Chain Engine Bugs
**Priority:** Critical  
**Dependencies:** None

**Bugs to Fix:**
1. Sort anchors by timestamp before returning
2. Fix 3min buffer to produce 3 anchors: firm(T-2), critical(T-1), alarm(T-0)
3. Add validation: `drive_duration > (arrival_time - now)` → error "drive_duration exceeds time_to_arrival"

**Acceptance Criteria:**
- [ ] Anchors returned in sorted timestamp order
- [ ] 3min buffer → 3 anchors: 8:57 (firm), 8:59 (critical), 9:00 (alarm)
- [ ] 120min drive for 9am arrival → 400 error with "drive_duration exceeds time_to_arrival"

---

### Task 1.2: Fix Parser Bugs
**Priority:** High  
**Dependencies:** None

**Bugs to Fix:**
1. Fix regex for "in X min" pattern - remove minute group requirement
2. Set reminder_type to "simple_countdown" for "in X min" inputs
3. Set drive_duration to 0 for countdown-style inputs

**Acceptance Criteria:**
- [ ] "dryer in 3 min" parses without crash
- [ ] "dryer in 3 min" → reminder_type="simple_countdown", drive_duration=0, arrival_time=now+3min

---

## Priority 2: Database Schema Alignment

### Task 2.1: Complete Schema per Spec
**Priority:** Critical  
**Dependencies:** Task 1.1, Task 1.2

**Add Missing Columns:**
```sql
-- reminders table additions
ALTER TABLE reminders ADD COLUMN custom_sound_path TEXT;
ALTER TABLE reminders ADD COLUMN origin_lat REAL;
ALTER TABLE reminders ADD COLUMN origin_lng REAL;
ALTER TABLE reminders ADD COLUMN origin_address TEXT;
ALTER TABLE reminders ADD COLUMN calendar_event_id TEXT;

-- anchors table additions
ALTER TABLE anchors ADD COLUMN tts_fallback INTEGER DEFAULT 0;
ALTER TABLE anchors ADD COLUMN snoozed_to TEXT;

-- history table additions
ALTER TABLE history ADD COLUMN actual_arrival TEXT;
ALTER TABLE history ADD COLUMN missed_reason TEXT;

-- user_preferences table addition
ALTER TABLE user_preferences ADD COLUMN updated_at TEXT;

-- destination_adjustments table addition
ALTER TABLE destination_adjustments ADD COLUMN updated_at TEXT;
```

**Add Missing Tables:**
```sql
CREATE TABLE custom_sounds (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  category TEXT NOT NULL,
  file_path TEXT NOT NULL,
  duration_seconds REAL,
  created_at TEXT NOT NULL
);

CREATE TABLE calendar_sync (
  calendar_type TEXT PRIMARY KEY,
  last_sync_at TEXT,
  sync_token TEXT,
  is_connected INTEGER DEFAULT 0
);

CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY
);
```

**Acceptance Criteria:**
- [ ] All spec columns exist
- [ ] All spec tables exist
- [ ] Schema version tracked
- [ ] Foreign key cascade works

---

## Priority 3: Core Interfaces (Mock-able)

### Task 3.1: Add `get_next_unfired_anchor()` Function
**Priority:** High  
**Dependencies:** Task 2.1

**Spec Requirement (Section 2.3):**
"Expose a `get_next_unfired_anchor(reminder_id)` function for scheduler recovery after app restart."

**Implementation:**
```python
def get_next_unfired_anchor(reminder_id: str) -> dict | None:
    """Return the earliest unfired anchor for a reminder, or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, reminder_id, timestamp, urgency_tier, fired, snoozed_to
        FROM anchors
        WHERE reminder_id = ? AND fired = 0
        ORDER BY timestamp ASC
        LIMIT 1
    """, (reminder_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'reminder_id': row[1], 'timestamp': row[2],
                'urgency_tier': row[3], 'fired': row[4], 'snoozed_to': row[5]}
    return None
```

**Acceptance Criteria:**
- [ ] Function returns earliest unfired anchor
- [ ] Returns None if all anchors fired
- [ ] Works after app restart

---

### Task 3.2: LLM Adapter Interface
**Priority:** High  
**Dependencies:** Task 2.1

**Spec Requirement (Section 3.3):**
"ILanguageModelAdapter interface — a test implementation returns predefined fixture responses."

**Implementation:**
```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> dict:
        pass

class MockLanguageModelAdapter(ILanguageModelAdapter):
    def __init__(self, fixture: dict):
        self.fixture = fixture
    
    def parse(self, text: str) -> dict:
        return self.fixture.copy()

class KeywordExtractionAdapter(ILanguageModelAdapter):
    def parse(self, text: str) -> dict:
        # Use existing parse_reminder_natural logic
        pass

class MiniMaxAdapter(ILanguageModelAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def parse(self, text: str) -> dict:
        # Call MiniMax API
        pass
```

**Acceptance Criteria:**
- [ ] Interface defined
- [ ] Mock adapter returns fixture without API call
- [ ] Keyword extraction as fallback works

---

### Task 3.3: TTS Adapter Interface
**Priority:** High  
**Dependencies:** Task 2.1

**Spec Requirement (Section 4.3):**
"ITTSAdapter interface — a test implementation writes a 1-second silent file."

**Implementation:**
```python
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str, output_path: str) -> str:
        pass

class MockTTSAdapter(ITTSAdapter):
    def generate(self, text: str, voice_id: str, output_path: str) -> str:
        # Write silent audio file
        with open(output_path, 'wb') as f:
            f.write(b'\x00' * 1000)  # 1 sec silent
        return output_path

class ElevenLabsAdapter(ITTSAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def generate(self, text: str, voice_id: str, output_path: str) -> str:
        # Call ElevenLabs API
        pass
```

**Acceptance Criteria:**
- [ ] Interface defined
- [ ] Mock creates local audio file
- [ ] Cache directory structure: `/tts_cache/{reminder_id}/{anchor_id}.mp3`

---

## Priority 4: Voice Personality System Upgrade

### Task 4.1: Add Message Variations
**Priority:** Medium  
**Dependencies:** Task 3.3

**Spec Requirement (Section 10.3):**
"Each personality tier SHALL produce distinct message variations (minimum 3 per tier per personality) to avoid robotic repetition."

**Implementation:**
- Convert each personality template from single string to list of 3+ strings
- Rotate through variations on each call
- Add "Calm" personality (gentle-only for non-aggressive users)

**Acceptance Criteria:**
- [ ] Each tier has 3+ message variations
- [ ] Messages cycle through variations
- [ ] "Calm" personality available

---

### Task 4.2: Custom Voice Prompt Support
**Priority:** Medium  
**Dependencies:** Task 4.1

**Spec Requirement (Section 10.3):**
"'Custom' mode SHALL accept a user-written prompt (max 200 characters) that is appended to the message generation system prompt."

**Implementation:**
- Store custom prompt in user_preferences
- Append to system prompt for message generation

**Acceptance Criteria:**
- [ ] Custom prompt up to 200 chars
- [ ] Prompt modifies message tone

---

## Priority 5: User Interaction

### Task 5.1: Notification & Alarm Behavior
**Priority:** High  
**Dependencies:** Task 3.3

**Missing Features (Section 5.3):**
- Sound tier escalation: gentle chime → pointed beep → urgent siren → looping alarm
- DND handling: silent for early, visual+vibration for final 5 min
- Quiet hours: suppress nudges 10pm-7am (configurable)
- Chain overlap serialization: queue new anchors, fire after current
- T-0 looping alarm

**Acceptance Criteria:**
- [ ] Sound matches urgency tier
- [ ] DND suppressed early, visual+vibration for final 5 min
- [ ] Quiet hours skip and queue
- [ ] 15+ min overdue anchors dropped
- [ ] Chain serialization prevents overlap

---

### Task 5.2: Snooze & Dismissal Flow
**Priority:** High  
**Dependencies:** Task 5.1

**Missing Features (Section 9.3):**
- Tap snooze: 1 min
- Custom snooze picker: 1, 3, 5, 10, 15 min
- Chain re-computation after snooze
- Feedback prompt on dismiss
- Feedback data storage and adjustment

**Implementation:**
```python
def recompute_chain_after_snooze(reminder_id: str, snooze_minutes: int):
    """Shift all unfired anchors by snooze duration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get unfired anchors
    cursor.execute("""
        SELECT id, timestamp FROM anchors
        WHERE reminder_id = ? AND fired = 0
        ORDER BY timestamp ASC
    """, (reminder_id,))
    unfired = cursor.fetchall()
    
    now = datetime.now()
    for anchor_id, original_ts in unfired:
        original = datetime.fromisoformat(original_ts)
        new_ts = original + timedelta(minutes=snooze_minutes)
        cursor.execute("""
            UPDATE anchors SET snoozed_to = ? WHERE id = ?
        """, (new_ts.isoformat(), anchor_id))
    
    conn.commit()
    conn.close()
```

**Acceptance Criteria:**
- [ ] Tap snooze pauses 1 min
- [ ] Custom snooze picker works
- [ ] Chain re-computation shifts correctly
- [ ] Feedback prompt on dismiss
- [ ] "Left too late" adds 2 min (cap +15)

---

### Task 5.3: Sound Library
**Priority:** Medium  
**Dependencies:** Task 5.1

**Missing Features (Section 12.3):**
- Built-in sounds: 5 per category (Commute, Routine, Errand)
- Custom audio import: MP3, WAV, M4A (max 30 sec)
- Per-reminder sound selection
- Corrupted file fallback

**Acceptance Criteria:**
- [ ] Built-in sounds play without network
- [ ] Custom import works
- [ ] Corrupted file fallback uses category default

---

## Priority 6: Background & Reliability

### Task 6.1: Background Scheduling Simulation
**Priority:** High  
**Dependencies:** Task 3.1

**Missing Features (Section 6.3):**
- Anchor scheduling simulation
- Recovery scan on startup
- Late fire warning logging

**Implementation:**
```python
class Scheduler:
    def __init__(self):
        self.pending = {}  # reminder_id -> list of anchor_ids
    
    def schedule_anchors(self, reminder_id: str, anchors: list):
        for anchor in anchors:
            self.pending[reminder_id].append(anchor['id'])
    
    def recovery_scan(self):
        """Fire overdue anchors within 15 min grace window."""
        now = datetime.now()
        for reminder_id, anchor_ids in self.pending.items():
            next_anchor = get_next_unfired_anchor(reminder_id)
            if next_anchor:
                scheduled = datetime.fromisoformat(next_anchor['snoozed_to'] or next_anchor['timestamp'])
                overdue_minutes = (now - scheduled).total_seconds() / 60
                if 0 < overdue_minutes <= 15:
                    fire_anchor(next_anchor['id'])
                elif overdue_minutes > 15:
                    log_missed(next_anchor['id'], 'background_task_killed')
```

**Acceptance Criteria:**
- [ ] Anchors scheduled with timestamps
- [ ] Recovery scan fires overdue within 15 min
- [ ] 15+ min overdue dropped and logged

---

### Task 6.2: Location Awareness
**Priority:** Medium  
**Dependencies:** Task 6.1

**Missing Features (Section 8.3):**
- Origin storage at creation
- Single location check at departure
- 500m geofence comparison
- Immediate escalation if at origin

**Implementation:**
```python
class LocationAdapter:
    def check_if_at_origin(self, origin_lat: float, origin_lng: float) -> bool:
        current = get_current_location()  # Single CoreLocation call
        distance = haversine(origin_lat, origin_lng, current.lat, current.lng)
        return distance <= 500  # meters

def fire_departure_anchor(reminder_id: str):
    reminder = get_reminder(reminder_id)
    if reminder.origin_lat and reminder.origin_lng:
        if is_at_origin(reminder.origin_lat, reminder.origin_lng):
            # Fire firm/critical immediately instead of calm departure
            fire_anchor_type(reminder_id, 'firm')
            return
    fire_anchor_type(reminder_id, 'calm')
```

**Acceptance Criteria:**
- [ ] Origin stored at creation
- [ ] Single location check at departure
- [ ] At-origin triggers immediate escalation

---

## Priority 7: External Integrations

### Task 7.1: Calendar Integration
**Priority:** Medium  
**Dependencies:** Task 2.1

**Missing Features (Section 7.3):**
- Apple Calendar adapter (EventKit mock)
- Google Calendar adapter (API mock)
- ICalendarAdapter interface
- Sync scheduling (every 15 min)
- Suggestion cards for events with locations

**Implementation:**
```python
class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events_with_locations(self, start: datetime, end: datetime) -> list:
        pass

class AppleCalendarAdapter(ICalendarAdapter):
    def get_events_with_locations(self, start, end):
        # Mock EventKit
        pass

class GoogleCalendarAdapter(ICalendarAdapter):
    def __init__(self, credentials: dict):
        self.credentials = credentials
    
    def get_events_with_locations(self, start, end):
        # Mock Google Calendar API
        pass
```

**Acceptance Criteria:**
- [ ] Interface defined with mock
- [ ] Events with locations surface as suggestions
- [ ] Permission denial shows explanation

---

## Priority 8: Stats & History

### Task 8.1: Complete History & Stats
**Priority:** Medium  
**Dependencies:** Task 2.1, Task 5.2

**Missing Features (Section 11.3):**
- Common miss window calculation
- Streak counter for recurring
- 90-day archive
- Adjustment cap (+15 min)

**Implementation:**
```python
def get_common_miss_window(destination: str) -> str | None:
    """Return the urgency tier most frequently missed for a destination."""
    # Query history for missed anchors at each tier
    # Return most common tier

def calculate_streak(reminder_id: str) -> int:
    """Calculate streak for recurring reminder."""
    # Increment on hit, reset on miss

def get_adjusted_drive_duration(destination: str, base_duration: int) -> int:
    """Get drive duration with feedback adjustments, capped at +15."""
    adjustment = get_adjustment(destination)
    return min(base_duration + adjustment, base_duration + 15)
```

**Acceptance Criteria:**
- [ ] Common miss window identifies most-missed tier
- [ ] Streak increments on hit, resets on miss
- [ ] Adjustment capped at +15 minutes
- [ ] Stats computable from history table

---

## Implementation Order

```
Phase 1: Critical Bug Fixes
├── 1.1 Fix Chain Engine (sorting, 3min anchors, validation)
└── 1.2 Fix Parser Bugs

Phase 2: Schema
└── 2.1 Complete Schema per Spec

Phase 3: Core Functions
├── 3.1 get_next_unfired_anchor()
├── 3.2 LLM Adapter Interface
└── 3.3 TTS Adapter Interface

Phase 4: Voice System
├── 4.1 Message Variations
└── 4.2 Custom Voice Prompt

Phase 5: User Interaction
├── 5.1 Notification & Alarm Behavior
├── 5.2 Snooze & Dismissal Flow
└── 5.3 Sound Library

Phase 6: Background & Reliability
├── 6.1 Background Scheduling
└── 6.2 Location Awareness

Phase 7: External Integrations
└── 7.1 Calendar Integration

Phase 8: Stats & History
└── 8.1 Complete History & Stats
```

---

## Testing Strategy

Per spec section 14, all acceptance criteria require corresponding tests:

### Unit Tests Needed
- [x] Chain engine determinism (verify)
- [ ] Parser fixtures (mock adapter)
- [ ] TTS adapter mock
- [ ] Keyword extraction
- [ ] Schema validation
- [ ] Message generation variations

### Integration Tests Needed
- [x] Full reminder creation flow (verify)
- [ ] Anchor firing (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment applied)

### Scenario Tests (via Otto Harness)
The following scenarios are defined and should pass:
- [ ] `chain-full-30min.yaml` - TC-01
- [ ] `chain-compressed-15min.yaml` - TC-02
- [ ] `chain-minimum-3min.yaml` - TC-03
- [ ] `chain-invalid-rejected.yaml` - TC-04
- [ ] `parse-natural-language.yaml` - TC-01
- [ ] `parse-simple-countdown.yaml` - TC-02
- [ ] `parse-tomorrow.yaml` - TC-03
- [ ] `voice-coach-personality.yaml` - TC-01
- [ ] `voice-no-nonsense.yaml` - TC-02
- [ ] `voice-all-personalities.yaml`
- [ ] `history-record-outcome.yaml`
- [ ] `history-record-miss-feedback.yaml` - TC-05
- [ ] `stats-hit-rate.yaml` - TC-01
- [ ] `reminder-creation-cascade-delete.yaml`
- [ ] `reminder-creation-crud.yaml`

---

## Notes

- The Python test server is a **harness for validation**, not the actual mobile app
- Real TTS (ElevenLabs) and LLM (MiniMax) adapters are configurable via environment variable
- All external dependencies should fail gracefully with sensible fallbacks
- The project uses NLSpec format for specifications
