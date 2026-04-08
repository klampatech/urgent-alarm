# Urgent Voice Alarm - Implementation Plan

## Analysis Summary

**Spec Size:** 1024 lines covering 13 major subsystems  
**Current Codebase:** Single `src/test_server.py` file with ~650 lines  
**Gap:** ~75% of spec features not implemented; 25% partially implemented with bugs

### Verified Gaps

| Category | Spec Requirement | Current State | Status |
|----------|------------------|---------------|--------|
| **Chain Engine** | 8 anchors for 30min, 5 for 15min, 3 for 3min | 8 anchors correct, 5 for 15min has bugs (missing tiers), 3 for 3min only has 2 | BUGGY |
| **Chain Engine** | `get_next_unfired_anchor()` function | Not implemented | MISSING |
| **Chain Engine** | Critical tier at T-1 (e.g., 8:59 for 9am arrival) | Currently uses "1 minute before" which breaks for short buffers | BUGGY |
| **Parser** | Handle "in X minutes" pattern | IndexError bug when no time component | BUGGY |
| **Database** | Full schema per spec Section 13 | Missing columns: origin_lat/lng, origin_address, custom_sound_path, calendar_event_id, snoozed_to, missed_reason, actual_arrival, tts_fallback, adjustment_minutes, sync_token, is_connected, file_path, duration_seconds, etc. | INCOMPLETE |
| **Database** | Migration system with versioning | Not implemented | MISSING |
| **Adapter Interfaces** | ILanguageModelAdapter, ITTSAdapter, ICalendarAdapter, ILocationAdapter | Not implemented | MISSING |
| **Voice Personality** | Minimum 3 message variations per tier | Currently only 1 template per tier | INCOMPLETE |
| **Background Scheduling** | Notifee/BGTaskScheduler integration | Not implemented (API endpoint exists but no logic) | MISSING |
| **DND/Quiet Hours** | Notification suppression logic | Not implemented | MISSING |
| **Snooze Flow** | Chain re-computation after snooze | Not implemented | MISSING |
| **Dismissal Feedback** | Feedback prompt with adjustment logic | Partially in history endpoint, but not complete | PARTIAL |
| **Calendar Integration** | Apple/Google Calendar adapters | Not implemented | MISSING |
| **Location Awareness** | CoreLocation/FusedLocation check | Not implemented | MISSING |
| **Sound Library** | Categories, import, fallback | Not implemented | MISSING |
| **Stats** | Streak counter, common miss window | Not implemented | MISSING |

---

## Priority 1: Critical Bugs (Block Testing)

### 1.1 Fix Chain Engine

**File:** `src/test_server.py`

**Issues to fix:**
1. Critical tier timing: Should be at T-1 (e.g., 8:59 for 9am arrival with 30min drive), not "1 minute before"
2. 15-min buffer: Should produce 5 anchors (pointed T-10, urgent T-5, firm T-3, critical T-1, alarm T-0)
3. 3-min buffer: Should produce 3 anchors (firm T-3, critical T-1, alarm T-0)

**Spec reference:** Section 2.3, TC-01 through TC-06

```python
# Correct anchor calculation for 30-min buffer:
# departure: 8:30 (calm), T-25: 8:35, T-20: 8:40, T-15: 8:45, T-10: 8:50, T-5: 8:55, T-1: 8:59, T-0: 9:00

# Correct anchor calculation for 15-min buffer (compressed):
# T-10: 8:50 (urgent), T-5: 8:55 (pushing), T-3: 8:57 (firm), T-1: 8:59 (critical), T-0: 9:00 (alarm)
```

### 1.2 Fix Parser Bug

**File:** `src/test_server.py`

**Issue:** `IndexError` when matching "in X minutes" patterns due to regex group mismatch.

**Fix:** Update `time_patterns` to handle both absolute times (with hour:minute groups) and relative times ("in X minutes" with single group).

---

## Priority 2: Database Foundation

### 2.1 Full Schema Implementation

**File:** `src/lib/core/database.py` (new file)

Create complete schema per spec Section 13:

```sql
-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Core tables (complete columns)
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    destination TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    drive_duration INTEGER NOT NULL,
    reminder_type TEXT NOT NULL,
    voice_personality TEXT NOT NULL,
    sound_category TEXT,
    selected_sound TEXT,
    custom_sound_path TEXT,
    origin_lat REAL,
    origin_lng REAL,
    origin_address TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    calendar_event_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE anchors (
    id TEXT PRIMARY KEY,
    reminder_id TEXT NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL,
    urgency_tier TEXT NOT NULL,
    tts_clip_path TEXT,
    tts_fallback INTEGER DEFAULT 0,
    fired INTEGER DEFAULT 0,
    fire_count INTEGER DEFAULT 0,
    snoozed_to TEXT,
    UNIQUE(reminder_id, timestamp)
);

CREATE TABLE history (
    id TEXT PRIMARY KEY,
    reminder_id TEXT REFERENCES reminders(id),
    destination TEXT NOT NULL,
    scheduled_arrival TEXT NOT NULL,
    actual_arrival TEXT,
    outcome TEXT NOT NULL,
    feedback_type TEXT,
    missed_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE destination_adjustments (
    destination TEXT PRIMARY KEY,
    adjustment_minutes INTEGER DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
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
```

### 2.2 Migration System

**File:** `src/lib/core/database.py`

- Sequential migrations starting at schema_v1
- `get_schema_version()` and `apply_migrations()`
- In-memory mode for tests: `Database.get_in_memory_instance()`
- WAL mode enabled

---

## Priority 3: Chain Engine Enhancement

### 3.1 Add `get_next_unfired_anchor()` Function

**File:** `src/test_server.py` or `src/lib/core/chain_engine.py`

```python
def get_next_unfired_anchor(reminder_id: str) -> Optional[dict]:
    """Returns the earliest unfired anchor for a reminder."""
    # Query DB for earliest unfired anchor ordered by timestamp
    # Used for recovery after app restart
```

### 3.2 Chain Determinism Verification

**Add test:** Same inputs always produce same anchor timestamps (order-independent comparison).

---

## Priority 4: Adapter Interfaces

### 4.1 Create Adapter Base Interfaces

**File:** `src/lib/adapters/base.py`

```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...
    
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> bytes: ...
    
class ICalendarAdapter(ABC):
    @abstractmethod
    def get_events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...
    
class ILocationAdapter(ABC):
    @abstractmethod
    def get_current_location(self) -> tuple[float, float]: ...
```

### 4.2 Implement Mock Adapters

**Files:** `src/lib/adapters/mock_llm.py`, `src/lib/adapters/mock_tts.py`, etc.

---

## Priority 5: Core Features

### 5.1 Voice Personality Variations

**File:** `src/test_server.py` or `src/lib/services/voice_personality.py`

Add 3 message variations per tier per personality:

```python
VOICE_PERSONALITIES = {
    'coach': {
        'calm': [
            "Alright, time to head out for {dest}. {dur} minute drive, you've got this!",
            "Time to depart for {dest}. {dur} minutes to get there, no rush!",
            "Good morning! {dest} is your destination, {dur} minute drive ahead.",
        ],
        # ... 2 more variations for each tier
    },
}
```

### 5.2 Snooze & Dismissal Flow

**Add endpoints:**
- `POST /snooze` - Apply snooze, re-compute chain
- `POST /dismiss` - Dismiss with feedback

**Chain re-computation logic:**
```python
def recompute_chain_after_snooze(reminder_id: str, snooze_minutes: int) -> list[Anchor]:
    """Shift remaining unfired anchors by snooze duration."""
    # Get current time
    # For each unfired anchor: new_timestamp = anchor.timestamp + snooze_minutes
    # Re-register with Notifee
```

### 5.3 DND & Quiet Hours Logic

**Add configuration:**
- `quiet_hours_start`: default "22:00"
- `quiet_hours_end`: default "07:00"

**Add endpoint:** `GET /notification/check?anchor_time=X` → determines if anchor should fire or be queued.

### 5.4 History & Stats Completion

**Add calculations:**
- Streak counter per recurring reminder
- Common miss window (most frequently missed urgency tier)
- Feedback loop: adjust `destination_adjustments` table

---

## Priority 6: Integration Stubs

### 6.1 Calendar Adapter Stubs

**File:** `src/lib/adapters/calendar_adapter.py`

```python
class AppleCalendarAdapter(ICalendarAdapter):
    """EventKit integration - stub for now."""
    pass

class GoogleCalendarAdapter(ICalendarAdapter):
    """Google Calendar API - stub for now."""
    pass
```

### 6.2 Location Adapter Stub

**File:** `src/lib/adapters/location_adapter.py`

```python
class CoreLocationAdapter(ILocationAdapter):
    """iOS CoreLocation - stub for now."""
    def get_current_location(self) -> tuple[float, float]:
        # Return mock coordinates for testing
        return (37.7749, -122.4194)
```

### 6.3 TTS Adapter Stub

**File:** `src/lib/adapters/tts_adapter.py`

```python
class ElevenLabsAdapter(ITTSAdapter):
    """ElevenLabs API - stub for now."""
    def generate(self, text: str, voice_id: str) -> bytes:
        # Return placeholder bytes for testing
        return b'MOCK_AUDIO_DATA'
```

---

## Task List (Prioritized)

### Phase 1: Fix Critical Bugs (Day 1)
- [ ] **P1.1** Fix chain engine critical tier timing (T-1, not "1 min before")
- [ ] **P1.2** Fix chain engine 15-min buffer (add missing tiers)
- [ ] **P1.3** Fix chain engine 3-min buffer (add missing anchor)
- [ ] **P1.4** Fix parser IndexError bug for "in X minutes" pattern

### Phase 2: Database Foundation (Day 2)
- [ ] **P2.1** Create `src/lib/` directory structure
- [ ] **P2.2** Implement full database schema
- [ ] **P2.3** Implement migration system
- [ ] **P2.4** Add in-memory mode for tests
- [ ] **P2.5** Add `get_next_unfired_anchor()` function

### Phase 3: Adapter Interfaces (Day 3)
- [ ] **P3.1** Create adapter base interfaces (`ILanguageModelAdapter`, `ITTSAdapter`, `ICalendarAdapter`, `ILocationAdapter`)
- [ ] **P3.2** Implement mock adapters for testing
- [ ] **P3.3** Add mock LLM adapter to parser endpoint

### Phase 4: Feature Completion (Day 4-5)
- [ ] **P4.1** Add 3 message variations per personality tier
- [ ] **P4.2** Implement snooze endpoint and chain re-computation
- [ ] **P4.3** Implement dismiss endpoint with feedback
- [ ] **P4.4** Add DND/quiet hours suppression logic
- [ ] **P4.5** Complete stats: streak counter, common miss window

### Phase 5: Integration Stubs (Day 6)
- [ ] **P5.1** Create calendar adapter stubs
- [ ] **P5.2** Create location adapter stub
- [ ] **P5.3** Create TTS adapter stub with clip caching
- [ ] **P5.4** Implement TTS cache cleanup on reminder delete

### Phase 6: Testing (Day 7)
- [ ] **P6.1** Create `harness/scenario_harness.py`
- [ ] **P6.2** Add unit tests for chain engine
- [ ] **P6.3** Add unit tests for parser
- [ ] **P6.4** Verify all existing scenarios pass

---

## Implementation Order

```
Week 1: Foundation & Bug Fixes
  Day 1: Fix critical chain engine and parser bugs
  Day 2: Database schema and migrations
  Day 3: Adapter interfaces
  
Week 2: Feature Completion
  Day 4: Voice personality variations
  Day 5: Snooze/dismissal flow, DND/quiet hours
  Day 6: Stats completion
  
Week 3: Integrations & Testing
  Day 7: Integration stubs
  Day 8: Test harness
  Day 9: Scenario validation
  Day 10: Polish and documentation
```

---

## Notes

- The current `test_server.py` serves as both the API and the implementation - no separate app yet
- All adapter interfaces should be mock-able for testing without real API calls
- Chain engine must be deterministic for reproducible tests
- Database must support in-memory mode for fast test execution
- Mobile app implementation (React Native/Flutter) is out of scope for this phase
