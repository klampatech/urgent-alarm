# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Last Updated:** 2026-04-08  
**Analysis Mode:** Complete gap analysis between `specs/*.md` and current `src/` codebase  
**Codebase Coverage:** ~45% (core engine exists but has critical bugs)

---

## Executive Summary

The current codebase implements the core escalation chain engine, basic parsing, and voice message templates. However, **3 critical bugs block basic functionality**, the database schema is incomplete, and 60% of features from the specification are not implemented.

### Confirmed Test Results

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 30min chain | 8 anchors | 8 anchors | ✅ PASS |
| 3min chain | 3 anchors | 2 anchors | ❌ FAIL (missing T-1) |
| Parser "dryer in 3 min" | Parse success | Crash (IndexError) | ❌ FAIL |
| Parser "9am" without "at" | Extract time | No time extracted | ❌ FAIL |
| DELETE cascade | Delete reminders+anchors | Not implemented | ❌ MISSING |

---

## Priority 0 — Critical Bugs (Must Fix First)

### P0-1: Parser Crash on "in X minutes"

**Spec Reference:** Section 3.5, TC-02  
**File:** `src/test_server.py`, line ~266  
**Current Error:** `IndexError: no such group` when parsing "dryer in 3 min"

**Root Cause:**
```python
time_patterns = [
    r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # 3 groups
    r'in\s+(\d+)\s*(?:minute|min)',           # 1 group - code assumes 2!
]
# ...
minute = int(match.group(2)) if match.group(2) else 0  # BUG: group(2) doesn't exist
```

**Fix Required:** Separate relative time parsing from absolute time patterns:
```python
# Handle "in X minutes" FIRST as relative time
relative_pattern = r'in\s+(\d+)\s*(?:minute|min)'
# Then absolute time patterns in separate block
```

**Test:** `scenarios/parse-simple-countdown.yaml`

---

### P0-2: Parser Fails on Bare Time ("9am", "tomorrow 2pm")

**Spec Reference:** Section 3.5, TC-01, TC-03  
**File:** `src/test_server.py`, line ~180  
**Current Behavior:** "Parker Dr 9am" returns `arrival_time: None`

**Root Cause:** Regex requires "at" keyword:
```python
r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)'  # Requires "at"
```

**Fix Required:** Add bare time patterns:
```python
time_patterns = [
    r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',      # "at 9am"
    r'(\d{1,2}):?(\d{2})?\s*(am|pm)\b',          # "9am", "9:30am"
]
# Also handle "tomorrow Xam/pm"
```

**Test:** `scenarios/parse-tomorrow.yaml`

---

### P0-3: 3-Minute Chain Returns Wrong Anchor Count

**Spec Reference:** Section 2.5, TC-03  
**File:** `src/test_server.py`, `compute_escalation_chain()`  
**Current Output:** 2 anchors (firm, alarm)  
**Expected Output:** 3 anchors (firm at T-3, critical at T-1, alarm at T-0)

**Root Cause:**
```python
elif buffer_minutes <= 5:
    if buffer_minutes > 1:
        tiers = [
            ('firm', buffer_minutes - 1),  # T-2, not T-3!
            ('alarm', 0),
        ]
```

**Fix Required:**
```python
elif buffer_minutes <= 5:
    tiers = [
        ('firm', buffer_minutes),      # T-3 for 3min buffer
        ('critical', 1),               # T-1
        ('alarm', 0),                   # T-0
    ]
```

**Test:** `scenarios/chain-minimum-3min.yaml`

---

### P0-4: DELETE Endpoint Missing (Cascade Delete)

**Spec Reference:** Section 13, TC-03  
**File:** `src/test_server.py`  
**Current Behavior:** No DELETE endpoint exists

**Fix Required:** Add `do_DELETE` method:
```python
def do_DELETE(self):
    if self.path.startswith("/reminders/"):
        reminder_id = self.path.split("/")[-1]
        # Delete anchors first (or rely on ON DELETE CASCADE)
        # Delete reminder
```

**Requires:** Enable `PRAGMA foreign_keys = ON` in `init_db()`

**Test:** `scenarios/reminder-creation-cascade-delete.yaml`

---

### P0-5: Database Schema Incomplete

**Spec Reference:** Section 13, Schema  
**File:** `src/test_server.py`, `init_db()`

**Missing Columns in `reminders`:**
| Column | Type | Required For |
|--------|------|-------------|
| `origin_lat` | REAL | Location awareness |
| `origin_lng` | REAL | Location awareness |
| `origin_address` | TEXT | Location awareness |
| `custom_sound_path` | TEXT | Sound library |
| `calendar_event_id` | TEXT | Calendar integration |
| `tts_cache_dir` | TEXT | TTS cache management |

**Missing Columns in `anchors`:**
| Column | Type | Required For |
|--------|------|-------------|
| `tts_fallback` | BOOLEAN | TTS fallback tracking |
| `snoozed_to` | TEXT | Snooze functionality |
| `snoozed_at` | TEXT | Snooze persistence |

**Missing Columns in `history`:**
| Column | Type | Required For |
|--------|------|-------------|
| `actual_arrival` | TEXT | Feedback loop |
| `missed_reason` | TEXT | Miss reason tracking |
| `reminder_type` | TEXT | Type-based stats |

**Missing Tables:**
| Table | Purpose |
|-------|---------|
| `schema_version` | Migration tracking |
| `calendar_sync` | Calendar connection state |
| `custom_sounds` | Imported audio files |
| `quiet_hours` | Sleep mode settings |

**Required Pragmas:**
```python
cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute("PRAGMA journal_mode = WAL")
```

---

## Priority 1 — Core Features (High Value)

### P1-1: Next Unfired Anchor Endpoint

**Spec Reference:** Section 2.3, Req #6  
**Endpoint:** `GET /reminders/{id}/next-anchor`

**Purpose:** Scheduler recovery after app restart - returns earliest unfired anchor.

**Implementation:**
```python
def get_next_unfired_anchor(reminder_id: str) -> Optional[dict]:
    """Returns earliest unfired anchor for a reminder."""
    # SELECT * FROM anchors WHERE reminder_id=? AND fired=0 ORDER BY timestamp ASC LIMIT 1
```

---

### P1-2: Snooze & Chain Recomputation

**Spec Reference:** Section 9  
**Endpoint:** `POST /anchors/{id}/snooze`

**Features Required:**
1. Tap snooze: 1 minute default
2. Custom snooze: 1, 3, 5, 10, 15 minutes via `duration` param
3. Chain re-computation: shift remaining anchors by snooze duration
4. Re-registration with Notifee (mock in test server)
5. TTS confirmation message

**Chain Recomputation Logic:**
```
Given anchors at 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
User snoozes at 8:45 for 3 minutes
Remaining anchors shift to: 8:48, 8:53, 8:59, 9:00
```

---

### P1-3: Dismissal Feedback Flow

**Spec Reference:** Section 9.3, Req #5-7  
**Endpoint:** `POST /history` (already exists, needs expansion)

**Features Required:**
1. "Was timing right?" prompt on swipe-dismiss
2. "Left too early" / "Left too late" / "Other" sub-feedback
3. Store feedback in `history.feedback_type`
4. Update `destination_adjustments` table

**Feedback Loop Adjustment:**
```
adjustment_minutes = adjustment_minutes + 2 (capped at +15)
```

---

### P1-4: LLM Adapter Interface

**Spec Reference:** Section 3.3, Req #1-3  
**Files to Create:** `src/lib/adapters/llm_adapter.py`

**Interface Required:**
```python
class ILanguageModelAdapter(Protocol):
    async def parse(self, text: str) -> ParsedReminder
    def parse_sync(self, text: str) -> ParsedReminder

class MiniMaxAdapter(ILanguageModelAdapter):
    api_key: str
    endpoint: str  # Configurable via env var

class AnthropicAdapter(ILanguageModelAdapter):
    api_key: str

class MockLLMAdapter(ILanguageModelAdapter):
    """For testing - returns predefined fixture responses."""
    fixture: dict
```

**Mock Implementation:** Returns hardcoded parsed result without API calls.

---

### P1-5: TTS Adapter Interface

**Spec Reference:** Section 4.3, Req #1-2  
**Files to Create:** `src/lib/adapters/tts_adapter.py`

**Interface Required:**
```python
class ITTSAdapter(Protocol):
    async def generate(self, text: str, voice_id: str) -> bytes
    def generate_sync(self, text: str, voice_id: str) -> bytes

class ElevenLabsAdapter(ITTSAdapter):
    api_key: str
    voice_ids: dict[str, str]  # personality -> voice_id mapping

class MockTTSAdapter(ITTSAdapter):
    """Writes a silent 1-second file for testing."""
```

**Features:**
- Pre-generate clips at reminder creation
- Cache in `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- Fall back to system sound on API failure

---

### P1-6: Expand Voice Message Variations (3+ Per Tier)

**Spec Reference:** Section 10.3, Req #6  
**File:** `src/test_server.py`, `VOICE_PERSONALITIES`

**Current:** 1 template per tier per personality  
**Required:** 3+ variations per tier per personality

**Example for "Coach" urgency_tier="urgent":**
```python
'coach': {
    'urgent': [
        "Let's GO! {remaining} minutes to {dest}! Time to move!",
        "MOVE IT! {remaining} minutes - {dest}! Go go go!",
        "Come on! {remaining} minute{plural} to {dest} - get going!",
    ],
    # ... other tiers
}
```

**Selection:** Random or round-robin from variations.

---

### P1-7: Streak Counter

**Spec Reference:** Section 11.3, Req #4  
**New Table:** `recurring_streaks`

```sql
CREATE TABLE recurring_streaks (
    destination TEXT PRIMARY KEY,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    last_completed TEXT
);
```

**Logic:**
- On `outcome='hit'` for recurring reminder: `current_streak += 1`
- On `outcome='miss'` for recurring reminder: `current_streak = 0`

---

### P1-8: Common Miss Window

**Spec Reference:** Section 11.3, Req #3  
**Query Required:**
```sql
SELECT urgency_tier, COUNT(*) as miss_count
FROM history h
JOIN anchors a ON h.reminder_id = a.reminder_id
WHERE outcome = 'miss'
GROUP BY urgency_tier
ORDER BY miss_count DESC
LIMIT 1;
```

---

### P1-9: Schema Version Table + Migrations

**Spec Reference:** Section 13.3, Req #1-2

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

**Migration Pattern:**
```python
def get_schema_version():
    cursor.execute("SELECT MAX(version) FROM schema_version")
    return cursor.fetchone()[0] or 0

def apply_migrations():
    current = get_schema_version()
    for i in range(current + 1, LATEST_VERSION + 1):
        run_migration(i)
        cursor.execute("INSERT INTO schema_version VALUES (?, ?)", (i, datetime.now().isoformat()))
```

---

## Priority 2 — Integrations (Medium Value)

### P2-1: Calendar Adapter Interface

**Spec Reference:** Section 7  
**Files to Create:** `src/lib/adapters/calendar_adapter.py`

```python
class ICalendarAdapter(Protocol):
    async def sync(self) -> list[CalendarEvent]
    async def get_events(self, start: datetime, end: datetime) -> list[CalendarEvent]
    def is_connected(self) -> bool

class AppleCalendarAdapter(ICalendarAdapter):
    """Uses EventKit (iOS)."""
    calendars: list[str]  # Which calendars to monitor

class GoogleCalendarAdapter(ICalendarAdapter):
    """Uses Google Calendar API."""
    credentials_path: str
```

---

### P2-2: Calendar Sync Background Job

**Spec Reference:** Section 7.3, Req #3

**Schedule:**
- On app launch
- Every 15 minutes while app is open
- Via background refresh

**Event Filtering:**
- Only events with non-empty `location` field
- Only events in the future

---

### P2-3: Location Awareness

**Spec Reference:** Section 8  
**Files to Create:** `src/lib/location.py`

**Features:**
- Single location check at departure anchor
- Geofence radius: 500 meters
- If user still at origin → fire "LEAVE NOW" tier immediately
- Location permission requested at first location-aware reminder creation

```python
def check_departure_location(reminder_id: str) -> bool:
    """Returns True if user is still at origin (within 500m)."""
    origin = get_reminder_origin(reminder_id)
    current = get_current_location()  # One API call only
    return haversine_distance(origin, current) <= 500
```

---

### P2-4: Notification Tiers & DND Awareness

**Spec Reference:** Section 5  
**Files to Create:** `src/lib/notifications.py`

**Notification Sound Tiers:**
| Tier | Sound | Behavior |
|------|-------|----------|
| calm/casual | Gentle chime | Normal notification |
| pointed/urgent | Pointed beep | Louder notification |
| pushing/firm | Urgent siren | Vibration |
| critical/alarm | Looping alarm | Full alarm, no auto-dismiss |

**DND Handling:**
- Early anchors during DND: Silent notification only
- Final 5 minutes during DND: Visual + vibration override
- Post-DND catch-up for suppressed anchors (within 15 min)

---

### P2-5: Quiet Hours / Sleep Mode

**Spec Reference:** Section 5.3, Req #3

**New Table:**
```sql
CREATE TABLE quiet_hours (
    id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    start_time TEXT DEFAULT '22:00',  -- 10 PM
    end_time TEXT DEFAULT '07:00',    -- 7 AM
    timezone TEXT DEFAULT 'local'
);
```

**Logic:**
- Suppress all anchors between start_time and end_time
- Queue suppressed anchors
- Fire at end_time + grace period (15 min), or drop if more than 15 min overdue

---

### P2-6: Background Scheduling (Notifee Mock)

**Spec Reference:** Section 6  
**Files to Create:** `src/lib/scheduler.py`

**For Test Server:** Mock implementation that tracks scheduled tasks in memory.

```python
class MockScheduler:
    """Mock Notifee for testing."""
    scheduled_tasks: dict[str, datetime]
    
    def schedule_anchor(self, anchor_id: str, timestamp: datetime):
        self.scheduled_tasks[anchor_id] = timestamp
    
    def cancel_anchor(self, anchor_id: str):
        del self.scheduled_tasks[anchor_id]
    
    def get_pending(self) -> list[str]:
        return list(self.scheduled_tasks.keys())
```

---

### P2-7: Sound Library

**Spec Reference:** Section 12  
**Files to Create:** `src/lib/sound_library.py`

**Built-in Sounds (bundled):**
- Commute: 5 sounds
- Routine: 5 sounds
- Errand: 5 sounds

**Custom Import:**
- Formats: MP3, WAV, M4A
- Max duration: 30 seconds
- Stored in app sandbox

**Playback:** Play selected sound under TTS at anchor fire.

---

## Priority 3 — Polish (Lower Value)

### P3-1: Custom Voice Prompt Mode

**Spec Reference:** Section 10.3, Req #3

**Database Change:**
```sql
ALTER TABLE user_preferences ADD COLUMN custom_voice_prompt TEXT;
```

**Implementation:** Append user prompt to message generation system prompt.

---

### P3-2: Chain Overlap Queue

**Spec Reference:** Section 5.3, Req #6

**Logic:**
- Track active chain in progress
- If new anchor fires while chain is active, queue it
- Fire queued anchors after current chain completes

---

### P3-3: 90-Day Data Retention

**Spec Reference:** Section 11.3, Req #7

```python
def archive_old_history(days: int = 90):
    cutoff = datetime.now() - timedelta(days=days)
    cursor.execute("""
        INSERT OR IGNORE INTO history_archive 
        SELECT * FROM history WHERE created_at < ?
    """, (cutoff.isoformat(),))
    cursor.execute("DELETE FROM history WHERE created_at < ?", (cutoff.isoformat(),))
```

---

### P3-4: TTS Cache Cleanup

**Spec Reference:** Section 4.3, Req #8

**On reminder deletion:**
```python
def cleanup_tts_cache(reminder_id: str):
    cache_dir = f"/tts_cache/{reminder_id}"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
```

---

## File Structure

### Current
```
src/
  test_server.py  ( monolithic, 600+ lines)
```

### Target Structure
```
src/
  test_server.py                    # HTTP endpoints + test utilities
  lib/
    __init__.py
    adapters/
      __init__.py
      llm_adapter.py               # ILanguageModelAdapter
      tts_adapter.py               # ITTSAdapter
      calendar_adapter.py          # ICalendarAdapter
    chain_engine.py                # compute_escalation_chain()
    parser.py                      # parse_reminder_natural()
    voice.py                       # generate_voice_message()
    database.py                    # init_db(), migrations
    snooze.py                      # chain_recomputation()
    feedback.py                    # feedback_loop()
    notifications.py               # Notification tiers
    scheduler.py                   # Background scheduling mock
    location.py                    # Single location check
    sound_library.py              # Built-in + custom sounds
    stats.py                       # Hit rate, streaks, miss window
```

---

## Scenario Coverage Map

| Scenario | Status | Blocking On |
|----------|--------|-------------|
| `chain-full-30min.yaml` | ✅ PASS | - |
| `chain-compressed-15min.yaml` | ⚠️ Needs review | - |
| `chain-minimum-3min.yaml` | ❌ FAIL | P0-3 |
| `chain-invalid-rejected.yaml` | ⚠️ Needs review | - |
| `parse-simple-countdown.yaml` | ❌ FAIL | P0-1 |
| `parse-tomorrow.yaml` | ❌ FAIL | P0-2 |
| `parse-natural-language.yaml` | ⚠️ Partial | P0-1, P0-2 |
| `voice-coach-personality.yaml` | ✅ PASS | - |
| `voice-no-nonsense.yaml` | ✅ PASS | - |
| `voice-all-personalities.yaml` | ⚠️ Needs 3+ variations | P1-6 |
| `history-record-outcome.yaml` | ✅ PASS | - |
| `history-record-miss-feedback.yaml` | ⚠️ Partial | P1-3 |
| `stats-hit-rate.yaml` | ✅ PASS | - |
| `reminder-creation-cascade-delete.yaml` | ❌ FAIL | P0-4 |
| `reminder-creation-crud.yaml` | ⚠️ Partial | P0-4 |

---

## Validation Commands

```bash
# Syntax check
python3 -m py_compile src/test_server.py

# Start server
pkill -f "python3 src/test_server.py" 2>/dev/null
python3 src/test_server.py &
sleep 2

# Test P0-1: Simple countdown (should not crash)
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"dryer in 3 min"}' | jq

# Test P0-2: Tomorrow parsing
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"meeting tomorrow 2pm, 20 min drive"}' | jq '.arrival_time'

# Test P0-3: 3min chain (should return 3 anchors)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Quick","arrival_time":"2026-04-10T09:00:00","drive_duration":3}' | jq '.anchors_created'

# Test P0-4: Cascade delete
ID=$(curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Cascade","arrival_time":"2026-04-10T15:00:00","drive_duration":30}' | jq -r '.id')
curl -s -X DELETE http://localhost:8090/reminders/$ID

# Run harness tests
python3 -m pytest harness/ 2>/dev/null || echo "Harness tests not yet implemented"
```

---

## Definition of Done

### Phase 1: Critical Bugs (P0)
- [ ] P0-1: Parser crash on "in X minutes" fixed
- [ ] P0-2: Parser extracts bare time ("9am", "tomorrow 2pm")
- [ ] P0-3: 3min chain returns 3 anchors
- [ ] P0-4: DELETE endpoint with cascade implemented
- [ ] P0-5: Database schema complete

### Phase 2: Core Features (P1)
- [ ] P1-1: Next unfired anchor endpoint
- [ ] P1-2: Snooze + chain recomputation
- [ ] P1-3: Dismissal feedback flow
- [ ] P1-4: LLM adapter interface
- [ ] P1-5: TTS adapter interface
- [ ] P1-6: 3+ voice message variations per tier
- [ ] P1-7: Streak counter
- [ ] P1-8: Common miss window
- [ ] P1-9: Schema migrations

### Phase 3: Integrations (P2)
- [ ] P2-1: Calendar adapter interface
- [ ] P2-2: Calendar sync
- [ ] P2-3: Location awareness
- [ ] P2-4: Notification tiers + DND
- [ ] P2-5: Quiet hours
- [ ] P2-6: Background scheduling
- [ ] P2-7: Sound library

---

*Last updated: 2026-04-08*
