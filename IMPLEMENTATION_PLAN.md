# Urgent Alarm - Implementation Plan

## Gap Analysis Summary

| Metric | Value |
|--------|-------|
| **Spec Sections** | 14 |
| **Spec Test Scenarios** | 40+ (TC-01 through TC-06 per section) |
| **Current Implementation** | ~25% complete |
| **Test Coverage** | 0 unit tests, 16 scenario files |
| **Harness Status** | **MISSING** - scenario_harness.py does not exist |

---

## Current State Assessment

### Implemented (in `src/test_server.py`)
- ✅ Basic escalation chain computation (with bugs)
- ✅ Keyword-based natural language parsing
- ✅ Voice message template generation (5 personalities)
- ✅ Basic SQLite database schema (incomplete)
- ✅ REST API endpoints (GET /chain, POST /reminders, POST /parse, POST /history, etc.)
- ✅ Basic hit rate calculation

### Missing / Incomplete

| Section | Feature | Status | Gap Details |
|---------|---------|--------|-------------|
| 2 | Chain Engine | ⚠️ Buggy | Compression logic doesn't match spec exactly |
| 2 | `get_next_unfired_anchor()` | ❌ Missing | Recovery after restart not implemented |
| 3 | LLM Adapter Interface | ❌ Missing | No `ILanguageModelAdapter` |
| 3 | LLM API Integration | ❌ Missing | No MiniMax/Anthropic integration |
| 4 | TTS Generation | ❌ Missing | Only text templates, no actual audio |
| 4 | TTS Caching | ❌ Missing | No file storage |
| 5 | Notification Behavior | ❌ Missing | No notification system |
| 6 | Background Scheduling | ❌ Missing | No Notifee integration |
| 7 | Calendar Integration | ❌ Missing | No Apple/Google Calendar |
| 8 | Location Awareness | ❌ Missing | No geolocation |
| 9 | Snooze Flow | ❌ Missing | No snooze implementation |
| 10 | Voice Personalities | ⚠️ Partial | Only 1 template per tier (needs 3+) |
| 10 | "Calm" Personality | ❌ Missing | Not in VOICE_PERSONALITIES dict |
| 11 | Streak Counter | ❌ Missing | Not implemented |
| 11 | Common Miss Window | ❌ Missing | Not implemented |
| 11 | Feedback Adjustment Cap | ⚠️ Buggy | Cap at +15 min not enforced |
| 12 | Sound Library | ❌ Missing | No sound system |
| 13 | Database Schema | ⚠️ Incomplete | Missing columns |
| 14 | Testing Infrastructure | ❌ Missing | No harness, no unit tests |

---

## Priority 1: Critical Blockers (Must Fix First)

### 1.1 Create Testing Harness Infrastructure ⚠️ CRITICAL
**Status:** `harness/scenario_harness.py` does not exist  
**Impact:** Cannot run scenario validation

| Task | Details | File |
|------|---------|------|
| Create `harness/scenario_harness.py` | Main test runner with YAML scenario loading | harness/scenario_harness.py |
| Implement scenario parser | Load and validate YAML scenarios | harness/scenario_harness.py |
| Implement HTTP assertion checker | Validate API responses | harness/scenario_harness.py |
| Implement DB assertion checker | Validate database state | harness/scenario_harness.py |
| Support `base_url` from env | Configurable test server URL | harness/scenario_harness.py |
| Support `OTTO_SCENARIO_DIR` env var | Custom scenario directory | harness/scenario_harness.py |

**Acceptance Criteria:**
- [ ] `python3 harness/scenario_harness.py --project urgent-alarm` runs without errors
- [ ] All 16 scenario files execute successfully
- [ ] Passes lint: `python3 -m py_compile harness/scenario_harness.py`

---

### 1.2 Fix Chain Engine Compression Logic ⚠️ HIGH PRIORITY
**Spec:** Section 2, TC-01 to TC-06  
**Status:** Current logic produces wrong anchor counts

**Current Implementation (BUGGY):**
```python
if buffer_minutes >= 25:      # 8 anchors ✅ CORRECT
elif buffer_minutes >= 20:    # 7 anchors - BUT spec TC-02 says 15min = 5 anchors
elif buffer_minutes >= 10:    # 5 anchors
elif buffer_minutes >= 5:     # 3 anchors
```

**Spec Requirements:**
| Buffer Size | Anchors | Tiers |
|-------------|---------|-------|
| ≥25 min | 8 | calm, casual, pointed, urgent, pushing, firm, critical, alarm |
| 15-24 min | 5 | urgent, pushing, firm, critical, alarm (skip calm/casual/pointed) |
| 10-14 min | 5 | urgent, pushing, firm, critical, alarm |
| 5-9 min | 3 | firm, critical, alarm |
| 1-4 min | 2-3 | firm, alarm (or just alarm) |

**Tasks:**
| Task | Details |
|------|---------|
| Fix 15-24 min range | Should produce 5 anchors starting at urgent |
| Fix 10-14 min range | Should produce anchors at drive_duration-5, drive_duration-10, etc. |
| Fix ≤5 min range | Minimum chain per spec TC-03: T-3, T-1, T-0 for 3 min buffer |
| Add unit tests | Test each buffer range produces correct anchor count |

**Files:** `src/test_server.py`

**Acceptance Criteria:**
- [ ] TC-01: 30 min buffer → 8 anchors (8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00)
- [ ] TC-02: 15 min buffer → 5 anchors (urgent, pushing, firm, critical, alarm)
- [ ] TC-03: 3 min buffer → 3 anchors (T-3 firm, T-1 critical, T-0 alarm)
- [ ] TC-04: 120 min buffer → 400 error "drive_duration exceeds time_to_arrival"
- [ ] TC-06: Identical inputs produce identical outputs (determinism)

---

### 1.3 Complete Database Schema ⚠️ HIGH PRIORITY
**Spec:** Section 13  
**Status:** Schema incomplete per spec

**Missing Columns:**
| Table | Column | Type | Notes |
|-------|--------|------|-------|
| reminders | origin_lat | REAL | Location awareness |
| reminders | origin_lng | REAL | Location awareness |
| reminders | origin_address | TEXT | Location awareness |
| reminders | calendar_event_id | TEXT | Calendar integration |
| reminders | custom_sound_path | TEXT | Sound library |
| anchors | tts_fallback | BOOLEAN | TTS failure tracking |
| anchors | snoozed_to | TEXT | Snooze tracking |
| history | missed_reason | TEXT | Missed anchor reasons |
| history | actual_arrival | TEXT | Nullable, resolved later |
| destination_adjustments | updated_at | TEXT | Audit trail |
| user_preferences | updated_at | TEXT | Audit trail |

**Missing Tables:**
| Table | Purpose |
|-------|---------|
| custom_sounds | Imported audio files |
| calendar_sync | Calendar sync state |
| schema_version | Migration tracking |

**Tasks:**
| Task | Details |
|------|---------|
| Add all missing columns | To existing tables |
| Add all missing tables | New tables |
| Enable PRAGMA foreign_keys | FK enforcement |
| Enable PRAGMA WAL mode | Performance |
| Add schema version tracking | Migration support |

**Files:** `src/test_server.py`

**Acceptance Criteria:**
- [ ] Fresh install creates all tables per schema in spec
- [ ] Cascade delete works: deleting reminder deletes anchors
- [ ] FK violation returns error without crash
- [ ] reminder.id is always valid UUID v4

---

## Priority 2: Core Engine Completion

### 2.1 Add `get_next_unfired_anchor()` Function
**Spec:** Section 2.3.6  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Implement function | Query earliest unfired anchor for reminder_id |
| Add endpoint | GET /anchors/next?reminder_id=X |
| Handle empty result | Return null if all anchors fired |
| Sort by timestamp | Always return earliest |

**Files:** `src/test_server.py`

**Acceptance Criteria:**
- [ ] TC-05: Given 5 anchors where first 2 fired, returns third anchor
- [ ] Returns null if all anchors fired

---

### 2.2 Add LLM Adapter Interface
**Spec:** Section 3  
**Status:** Keyword extraction only, no LLM integration

| Task | Details |
|------|---------|
| Define `ILanguageModelAdapter` | Abstract interface |
| Implement mock adapter | For testing without API |
| Implement MiniMax adapter | Environment-configurable |
| Implement Anthropic adapter | Alternative LLM |
| Add keyword fallback | On LLM failure |
| Add confidence scoring | Track parse quality |

**Files:** `src/parser/` (new module)

**Acceptance Criteria:**
- [ ] TC-07: Mock adapter returns fixture response without API call
- [ ] TC-04: On API failure, keyword extraction runs
- [ ] TC-06: Unintelligible input returns error

---

### 2.3 Complete Voice Personality System
**Spec:** Section 10  
**Status:** 1 template per tier, missing "Calm" personality

| Task | Details |
|------|---------|
| Add "Calm" personality | Gentle-only messages |
| Add 3+ variations per tier | Avoid repetition |
| Implement random selection | Choose from variations |
| Support custom prompts | Max 200 chars |
| Store personality per reminder | Immute after creation |

**Files:** `src/test_server.py`

**Acceptance Criteria:**
- [ ] TC-01: "Coach" at T-5 produces motivating message
- [ ] TC-02: "No-nonsense" at T-5 produces brief direct message
- [ ] TC-03: Custom prompt modifies tone
- [ ] TC-04: Existing reminders retain original personality
- [ ] TC-05: 3 calls produce 2+ distinct messages

---

## Priority 3: Feature Implementation

### 3.1 TTS System (Voice Generation)
**Spec:** Section 4  
**Status:** Text templates only, no audio generation

| Task | Details |
|------|---------|
| Define `ITTSAdapter` interface | Mock-able |
| Implement ElevenLabs adapter | Environment-configurable |
| Implement TTS caching | `/tts_cache/{reminder_id}/` |
| Implement cache invalidation | On reminder delete |
| Implement fallback | System sound + notification text |

**Files:** `src/tts/` (new module)

**Acceptance Criteria:**
- [ ] TC-01: New reminder generates MP3 files in cache
- [ ] TC-02: Anchor fires from local cache (no network)
- [ ] TC-03: On API failure, fallback to system sound
- [ ] TC-04: Reminder deletion removes cached files

---

### 3.2 Snooze & Dismissal Flow
**Spec:** Section 9  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Implement tap snooze | 1 minute default |
| Implement custom snooze | 1, 3, 5, 10, 15 min options |
| Re-compute chain after snooze | Shift remaining anchors |
| Re-register with scheduler | New timestamps |
| Implement dismissal feedback | "Timing right?" Yes/No |
| Process feedback adjustments | +2 min per "left too late" |
| TTS snooze confirmation | "Okay, snoozed X minutes" |

**Files:** `src/snooze/` (new module)

**Acceptance Criteria:**
- [ ] TC-01: Tap snooze → 1 min delay + TTS confirmation
- [ ] TC-02: Custom snooze → picker + TTS confirmation
- [ ] TC-03: Chain re-computation shifts remaining anchors
- [ ] TC-04: Feedback stored on dismissal
- [ ] TC-05: "Left too late" → +2 min drive estimate
- [ ] TC-06: Snooze persistence after restart

---

### 3.3 Stats & Feedback Loop
**Spec:** Section 11  
**Status:** Basic hit rate only

| Task | Details |
|------|---------|
| Fix hit rate calculation | 7-day trailing, exclude pending |
| Add streak counter | Increment on hit, reset on miss |
| Add common miss window | Most-missed urgency tier |
| Add adjustment cap | Cap +15 min |
| Add `actual_arrival` tracking | Nullable |
| Add `missed_reason` tracking | Log reasons |

**Files:** `src/stats/` (new module)

**Acceptance Criteria:**
- [ ] TC-01: 4 hits, 1 miss → 80% hit rate
- [ ] TC-02: 3 late feedback → +6 min adjustment
- [ ] TC-03: 10 late feedback → +15 min (capped)
- [ ] TC-04: Returns most-missed urgency tier
- [ ] TC-05: Streak increments on hit
- [ ] TC-06: Streak resets on miss

---

### 3.4 Notification & Alarm Behavior
**Spec:** Section 5  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Implement tier escalation | gentle → beep → siren → alarm |
| Handle DND awareness | Silent early, visual+ vibrate final 5 min |
| Implement quiet hours | Default 10pm-7am |
| Queue overdue anchors | ≤15 min after restriction |
| Drop >15 min overdue | TC-04: 15-min rule |
| Serialize chain execution | Queue during active chain |
| Implement T-0 looping | Until user acts |

**Files:** `src/notifications/` (new module)

**Acceptance Criteria:**
- [ ] TC-01: DND early anchor → silent notification
- [ ] TC-02: DND final 5 min → visual + vibration
- [ ] TC-03: Quiet hours → suppress + queue
- [ ] TC-04: >15 min overdue → drop + log
- [ ] TC-05: Chain overlap → serialize
- [ ] TC-06: T-0 alarm loops until action

---

### 3.5 Background Scheduling
**Spec:** Section 6  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Register anchors with Notifee | Individual background tasks |
| iOS BGTaskScheduler | BGAppRefreshTask + BGProcessingTask |
| Recovery scan on launch | Fire ≤15 min overdue |
| Drop >15 min overdue | Log with missed_reason |
| Re-register on crash | Pending anchors |
| Late fire warning | Log if >60s late |

**Files:** `src/scheduler/` (new module)

**Acceptance Criteria:**
- [ ] TC-01: All anchors registered correctly
- [ ] TC-02: Anchors fire with app closed
- [ ] TC-03: Recovery scan fires grace window anchors
- [ ] TC-04: >15 min overdue → drop + log
- [ ] TC-05: Crash → re-register pending anchors
- [ ] TC-06: >60s late → warning log

---

## Priority 4: Integrations

### 4.1 Calendar Integration
**Spec:** Section 7  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Define `ICalendarAdapter` | Common interface |
| Implement Apple Calendar | EventKit |
| Implement Google Calendar | Google Calendar API |
| Sync on launch + 15 min | Background refresh |
| Surface suggestion cards | "Add departure reminder?" |
| Handle permission denial | Explanation + settings |
| Handle recurring events | Generate for each occurrence |

**Files:** `src/calendar/` (new module)

---

### 4.2 Location Awareness
**Spec:** Section 8  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Single location check | At departure anchor only |
| Geofence radius 500m | "At origin" check |
| Escalate if still at origin | Fire firm/critical immediately |
| Lazy permission request | On first location-aware reminder |
| No location history | Single comparison only |

**Files:** `src/location/` (new module)

---

### 4.3 Sound Library
**Spec:** Section 12  
**Status:** Not implemented

| Task | Details |
|------|---------|
| Bundle built-in sounds | 5 per category |
| Implement custom import | MP3, WAV, M4A, max 30 sec |
| Per-reminder selection | Override category default |
| Corrupted file fallback | Use category default + error |

**Files:** `src/sounds/` (new module)

---

## Implementation Order

```
Phase 1: Critical Blockers (Week 1)
├── 1.1 Create testing harness (scenario_harness.py)
├── 1.2 Fix chain engine compression logic
└── 1.3 Complete database schema

Phase 2: Core Engine (Week 2)
├── 2.1 Add get_next_unfired_anchor()
├── 2.2 Add LLM adapter interface + mock
└── 2.3 Complete voice personality system

Phase 3: Features (Week 3-4)
├── 3.1 TTS system
├── 3.2 Snooze & dismissal
├── 3.3 Stats & feedback loop
└── 3.4 Notification & alarm behavior

Phase 4: Integrations (Week 5-6)
├── 4.1 Calendar integration
├── 4.2 Location awareness
└── 4.3 Sound library

Phase 5: Polish (Week 7)
└── E2E testing + documentation
```

---

## Files to Create/Modify

### Create (New Modules)
| File | Purpose | Phase |
|------|---------|-------|
| `harness/scenario_harness.py` | Test runner | 1 |
| `src/parser/__init__.py` | Parser module | 2 |
| `src/parser/llm_adapter.py` | LLM adapter interface | 2 |
| `src/parser/keyword_extractor.py` | Fallback parser | 2 |
| `src/tts/__init__.py` | TTS module | 3 |
| `src/tts/elevenlabs_adapter.py` | ElevenLabs integration | 3 |
| `src/tts/cache_manager.py` | TTS file caching | 3 |
| `src/snooze/__init__.py` | Snooze module | 3 |
| `src/stats/__init__.py` | Stats module | 3 |
| `src/notifications/__init__.py` | Notification module | 3 |
| `src/scheduler/__init__.py` | Scheduler module | 4 |
| `src/calendar/__init__.py` | Calendar module | 4 |
| `src/location/__init__.py` | Location module | 4 |
| `src/sounds/__init__.py` | Sound module | 4 |

### Modify
| File | Changes | Phase |
|------|---------|-------|
| `src/test_server.py` | Fix chain logic, add columns, add endpoints | 1-2 |

---

## Quick Wins (1-2 days each)

1. **Fix chain engine compression** - 1 day, high impact, unblocks scenarios
2. **Complete database schema** - 0.5 day, enables all data persistence
3. **Create testing harness** - 1 day, enables validation
4. **Add "Calm" personality + 3 variations** - 0.5 day, quality improvement
5. **Fix hit rate calculation + add streak** - 0.5 day, visible stats

---

## Validation Commands

```bash
# Start test server
python3 src/test_server.py &

# Run linting
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Run scenarios (after harness is created)
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Custom scenario directory
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project urgent-alarm
```
