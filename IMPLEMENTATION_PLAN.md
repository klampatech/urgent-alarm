# Urgent Alarm - Implementation Plan

## Gap Analysis Summary

| Metric | Value |
|--------|-------|
| **Spec Sections** | 14 (Overview, Chain Engine, Parser, TTS, Notifications, Scheduling, Calendar, Location, Snooze, Voice, History, Sounds, Data, Tests) |
| **Spec Test Scenarios** | 47 (TC-01 through TC-06+ per section) |
| **Scenario Files** | 16 (in `scenarios/` directory) |
| **Harness Status** | **MISSING** — `harness/scenario_harness.py` does not exist |
| **Current Implementation** | ~30% complete (basic chain engine, parser, voice templates in test_server.py) |

---

## Current State Assessment

### ✅ Implemented (in `src/test_server.py`)

| Feature | Status | Notes |
|---------|--------|-------|
| Escalation chain computation | ⚠️ Buggy | Wrong anchor counts for some buffer ranges |
| Natural language parsing | ⚠️ Partial | Keyword extraction works; no LLM adapter |
| Voice message templates | ⚠️ Partial | 1 template per tier, missing "Calm" personality |
| SQLite database | ⚠️ Incomplete | Missing columns per spec Section 13 |
| REST API endpoints | ⚠️ Partial | Missing some endpoints |
| Hit rate calculation | ⚠️ Buggy | Doesn't exclude pending correctly |

### ❌ Missing / Not Implemented

| Category | Missing | Impact |
|----------|---------|--------|
| **Testing Harness** | `harness/scenario_harness.py` | Cannot validate scenarios |
| **Chain Engine Fixes** | Compression logic, `get_next_unfired_anchor()` | Core functionality broken |
| **Database Schema** | 10+ missing columns, 3 missing tables | Data persistence incomplete |
| **LLM Adapter** | `ILanguageModelAdapter`, MiniMax, Anthropic | Parser won't use AI |
| **TTS System** | ElevenLabs adapter, caching, fallback | No real voice generation |
| **Notifications** | DND, quiet hours, chain overlap, T-0 alarm | No user alerts |
| **Background Scheduling** | Notifee, BGTaskScheduler, recovery scan | Reminders won't fire |
| **Calendar Integration** | EventKit, Google Calendar API | No calendar sync |
| **Location Awareness** | CoreLocation, geofence, escalation | No departure check |
| **Snooze Flow** | Tap snooze, custom snooze, re-compute | No snooze interaction |
| **Stats Completion** | Streak counter, common miss window, cap | Incomplete stats |
| **Sound Library** | Built-in sounds, custom import | No audio files |

---

## Priority 1: Critical Blockers (Must Fix First)

### 1.1 Create Testing Harness ⚠️ CRITICAL
**Status:** `harness/scenario_harness.py` does not exist  
**Impact:** Cannot run any of the 16 scenario files for validation

**Tasks:**
| Task | Details |
|------|---------|
| Create `harness/scenario_harness.py` | Main test runner with YAML loading |
| Implement scenario parser | Load and parse YAML scenarios |
| Implement HTTP assertion checker | Validate API responses against expected |
| Implement DB assertion checker | Validate database state |
| Support `base_url` env var | Configurable test server URL |
| Support `OTTO_SCENARIO_DIR` env var | Custom scenario directory |
| Handle `api_sequence` trigger type | Execute sequential API calls |
| Handle `llm_judge` assertion | AI-assisted validation |
| Handle `http_status` assertion | Status code validation |
| Handle `db_record` assertion | Database record validation |

**Scenario Files to Support:**
```
scenarios/chain-full-30min.yaml         # Section 2, TC-01
scenarios/chain-compressed-15min.yaml   # Section 2, TC-02
scenarios/chain-minimum-3min.yaml       # Section 2, TC-03
scenarios/chain-invalid-rejected.yaml   # Section 2, TC-04
scenarios/parse-natural-language.yaml   # Section 3, TC-01
scenarios/parse-simple-countdown.yaml   # Section 3, TC-02
scenarios/parse-tomorrow.yaml           # Section 3, TC-03
scenarios/voice-coach-personality.yaml  # Section 10, TC-01
scenarios/voice-no-nonsense.yaml        # Section 10, TC-02
scenarios/voice-all-personalities.yaml  # Section 10
scenarios/history-record-outcome.yaml   # Section 11
scenarios/history-record-miss-feedback.yaml # Section 11, TC-05
scenarios/stats-hit-rate.yaml           # Section 11, TC-01
scenarios/reminder-creation-crud.yaml   # Section 13
scenarios/reminder-creation-cascade-delete.yaml # Section 13, TC-03
```

**Acceptance Criteria:**
- [ ] `python3 -m py_compile harness/scenario_harness.py` passes
- [ ] `python3 harness/scenario_harness.py --project urgent-alarm` runs without error
- [ ] All 16 scenario files parse and execute

---

### 1.2 Fix Chain Engine Compression Logic ⚠️ HIGH PRIORITY
**Spec:** Section 2.3, TC-01 to TC-06  
**File:** `src/test_server.py`

**Spec Requirements vs Current Implementation:**

| Buffer | Spec | Current | Status |
|--------|------|---------|--------|
| ≥25 min | 8 anchors: calm→alarm | 8 anchors ✅ | OK |
| 15-24 min | 5 anchors: urgent→alarm (skip calm/casual/pointed) | Wrong | ❌ |
| 10-14 min | 5 anchors: urgent→alarm | Wrong | ❌ |
| 5-9 min | 3 anchors: firm→critical→alarm | Wrong | ❌ |
| 1-4 min | 2-3 anchors: firm/alarm | Wrong | ❌ |

**Current BUGGY Logic:**
```python
if buffer_minutes >= 25:      # 8 anchors ✅
elif buffer_minutes >= 20:    # 7 anchors ❌ (should be 5)
elif buffer_minutes >= 10:    # 5 anchors ❌ (should skip pointed)
elif buffer_minutes >= 5:    # 3 anchors ❌
```

**Correct Logic per Spec TC-02:**
- 15 min buffer → anchors at T-5 (urgent), T-10 (pushing), T-15 (firm), T-19 (critical), T-0 (alarm)
- Wait, TC-02 says 15 min buffer should have 5 anchors skipping calm, casual, pointed

**Spec TC-02 Clarification:**
> "Given a reminder with arrival_time = 9:00 AM and drive_duration = 15 minutes"
> "Then 5 anchors are created skipping calm and casual tiers, starting at T-10 (urgent)"

This means: T-10 (urgent), T-5 (pushing), T-4 (firm), T-1 (critical), T-0 (alarm)

**Tasks:**
| Task | Details |
|------|---------|
| Fix 15-24 min range | 5 anchors starting at urgent tier |
| Fix 10-14 min range | 5 anchors, adjust thresholds |
| Fix 5-9 min range | 3 anchors: firm, critical, alarm |
| Fix 1-4 min range | 2-3 anchors per TC-03 |
| Add unit tests | Verify each buffer range |
| Add `get_next_unfired_anchor()` | Required for TC-05 |

**Acceptance Criteria:**
- [ ] TC-01: 30 min buffer → 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] TC-02: 15 min buffer → 5 anchors: T-10 (urgent), T-5 (pushing), T-4 (firm), T-1 (critical), T-0 (alarm)
- [ ] TC-03: 3 min buffer → 3 anchors: T-3 (firm), T-1 (critical), T-0 (alarm)
- [ ] TC-04: 120 min buffer → 400 error "drive_duration exceeds time_to_arrival"
- [ ] TC-05: `get_next_unfired_anchor` returns earliest unfired anchor
- [ ] TC-06: Identical inputs produce identical outputs (determinism)

---

### 1.3 Complete Database Schema ⚠️ HIGH PRIORITY
**Spec:** Section 13, Table Schema  
**File:** `src/test_server.py`

**Missing Columns in `reminders` table:**
| Column | Type | Purpose |
|--------|------|---------|
| `origin_lat` | REAL | Location awareness - origin latitude |
| `origin_lng` | REAL | Location awareness - origin longitude |
| `origin_address` | TEXT | Location awareness - origin address |
| `calendar_event_id` | TEXT | Calendar integration reference |
| `custom_sound_path` | TEXT | Sound library - custom audio path |

**Missing Columns in `anchors` table:**
| Column | Type | Purpose |
|--------|------|---------|
| `tts_fallback` | BOOLEAN | TTS failure tracking |
| `snoozed_to` | TEXT | Snooze timestamp redirect |

**Missing Columns in `history` table:**
| Column | Type | Purpose |
|--------|------|---------|
| `actual_arrival` | TEXT | Nullable, resolved after firing |
| `missed_reason` | TEXT | Log missed anchor reasons |

**Missing Tables:**
| Table | Purpose |
|-------|---------|
| `user_preferences` | User settings (needs `updated_at`) |
| `calendar_sync` | Calendar sync state |
| `schema_version` | Migration tracking |

**Tasks:**
| Task | Details |
|------|---------|
| Add all missing columns | ALTER TABLE statements |
| Add all missing tables | CREATE TABLE statements |
| Enable `PRAGMA foreign_keys = ON` | FK enforcement |
| Enable `PRAGMA journal_mode = WAL` | Performance |
| Add schema version table | Migration support |

**Acceptance Criteria:**
- [ ] Fresh install creates all tables per spec schema
- [ ] Cascade delete works: DELETE reminder → DELETE anchors
- [ ] FK violation returns error without crash
- [ ] `reminders.id` is always valid UUID v4

---

## Priority 2: Core Engine Completion

### 2.1 Complete Voice Personality System
**Spec:** Section 10  
**File:** `src/test_server.py`

**Current State:**
- 5 personalities defined: coach, assistant, best_friend, no_nonsense, calm
- Wait - `calm` IS in VOICE_PERSONALITIES dict ✅
- 1 template per tier per personality
- Spec requires: minimum 3 variations per tier per personality

**Tasks:**
| Task | Details |
|------|---------|
| Add 3+ message variations | Per tier, per personality |
| Implement random selection | Choose from variations |
| Support custom prompts | Max 200 chars appended to system prompt |
| Add `custom_prompt` field | For custom voice style |
| Randomize message selection | Avoid robotic repetition |

**Acceptance Criteria:**
- [ ] TC-01: "Coach" at T-5 → motivating message with exclamation
- [ ] TC-02: "No-nonsense" at T-5 → brief, direct, no filler
- [ ] TC-03: Custom prompt modifies message tone
- [ ] TC-04: Existing reminders retain original personality
- [ ] TC-05: 3 calls produce 2+ distinct messages

---

### 2.2 Add LLM Adapter Interface
**Spec:** Section 3  
**File:** `src/parser/llm_adapter.py` (new)

**Tasks:**
| Task | Details |
|------|---------|
| Define `ILanguageModelAdapter` | Abstract interface with `parse()` method |
| Implement mock adapter | Returns predefined fixture responses |
| Implement MiniMax adapter | Configurable via environment variable |
| Implement Anthropic adapter | Alternative LLM provider |
| Add keyword fallback | On LLM API failure |
| Track confidence score | 0.0-1.0 based on parse quality |

**Interface:**
```python
class ILanguageModelAdapter:
    def parse(self, text: str) -> ParsedReminder
    def is_available(self) -> bool

class MockLLMAdapter(ILanguageModelAdapter):
    def __init__(self, fixture: dict)

class MiniMaxAdapter(ILanguageModelAdapter):
    # Uses MiniMax API endpoint

class AnthropicAdapter(ILanguageModelAdapter):
    # Uses Anthropic API
```

**Acceptance Criteria:**
- [ ] TC-07: Mock adapter returns fixture without API call
- [ ] TC-04: On API failure, keyword extraction runs
- [ ] TC-06: Unintelligible input returns error
- [ ] Confidence score reflects parse quality

---

### 2.3 Complete Stats System
**Spec:** Section 11  
**File:** `src/stats/` (new module)

**Current Issues:**
- Hit rate calculation doesn't exclude pending correctly
- No streak counter
- No common miss window
- Adjustment cap (+15 min) not enforced

**Tasks:**
| Task | Details |
|------|---------|
| Fix hit rate calculation | Exclude pending from denominator |
| Add streak counter | Increment on hit, reset on miss |
| Add common miss window | Return most-missed urgency tier |
| Enforce adjustment cap | Cap at +15 minutes |
| Track `actual_arrival` | Nullable, set on completion |
| Track `missed_reason` | Log for analytics |

**Acceptance Criteria:**
- [ ] TC-01: 4 hits, 1 miss, 2 pending → 80% (4/5)
- [ ] TC-02: 3 "left too late" → +6 min adjustment
- [ ] TC-03: 10 "left too late" → +15 min (capped)
- [ ] TC-04: Returns most-missed urgency tier
- [ ] TC-05: Streak increments on hit
- [ ] TC-06: Streak resets on miss

---

## Priority 3: Feature Implementation

### 3.1 TTS System (Voice Generation)
**Spec:** Section 4  
**Files:** `src/tts/__init__.py`, `src/tts/elevenlabs_adapter.py`, `src/tts/cache_manager.py`

**Tasks:**
| Task | Details |
|------|---------|
| Define `ITTSAdapter` interface | Mock-able for testing |
| Implement ElevenLabs adapter | Environment-configurable API key |
| Implement TTS caching | Store MP3s in `/tts_cache/{reminder_id}/` |
| Implement cache invalidation | Delete on reminder deletion |
| Implement fallback | System sound + notification text |

**Acceptance Criteria:**
- [ ] TC-01: Reminder creation generates MP3s in cache directory
- [ ] TC-02: Anchor fires from local cache (no network call)
- [ ] TC-03: On API failure, fallback to system sound
- [ ] TC-04: Reminder deletion removes cached files
- [ ] TC-05: Mock adapter writes silent file in tests

---

### 3.2 Snooze & Dismissal Flow
**Spec:** Section 9  
**Files:** `src/snooze/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Implement tap snooze | 1 minute default |
| Implement custom snooze | Picker: 1, 3, 5, 10, 15 min |
| Re-compute chain | Shift remaining anchors by snooze duration |
| Re-register anchors | New timestamps with scheduler |
| Implement dismissal | Feedback prompt: "Timing right?" |
| Process feedback | Store + adjust drive estimates |
| TTS confirmation | "Okay, snoozed X minutes" |

**Acceptance Criteria:**
- [ ] TC-01: Tap snooze → 1 min delay + TTS
- [ ] TC-02: Custom snooze → picker + TTS
- [ ] TC-03: Chain re-computation shifts remaining anchors
- [ ] TC-04: Feedback prompt on swipe-dismiss
- [ ] TC-05: "Left too late" → +2 min estimate
- [ ] TC-06: Snooze persists after app restart

---

### 3.3 Notification & Alarm Behavior
**Spec:** Section 5  
**Files:** `src/notifications/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Implement tier escalation | gentle chime → beep → siren → alarm |
| Handle DND early | Silent notification for calm/casual/pointed |
| Handle DND final 5 min | Visual + vibration override |
| Implement quiet hours | Default 10pm-7am suppression |
| Queue overdue anchors | ≤15 min after restriction ends |
| Drop >15 min overdue | Log with missed_reason |
| Serialize chain execution | Queue during active chain |
| Implement T-0 looping | Loop until user acts |

**Acceptance Criteria:**
- [ ] TC-01: DND early anchor → silent notification
- [ ] TC-02: DND final 5 min → visual + vibration
- [ ] TC-03: Quiet hours → suppress + queue
- [ ] TC-04: >15 min overdue → drop + log
- [ ] TC-05: Chain overlap → serialize
- [ ] TC-06: T-0 loops until action

---

### 3.4 Background Scheduling
**Spec:** Section 6  
**Files:** `src/scheduler/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Register anchors with Notifee | Individual background tasks |
| iOS: BGTaskScheduler | BGAppRefreshTask + BGProcessingTask |
| Recovery scan on launch | Fire ≤15 min overdue |
| Drop >15 min overdue | Log missed_reason |
| Re-register on crash | Pending anchors |
| Late fire warning | Log if >60s late |

**Acceptance Criteria:**
- [ ] TC-01: All anchors registered with correct timestamps
- [ ] TC-02: Anchors fire with app closed
- [ ] TC-03: Recovery scan fires grace window anchors
- [ ] TC-04: >15 min overdue → drop + log
- [ ] TC-05: Crash → re-register pending anchors
- [ ] TC-06: >60s late → warning log

---

## Priority 4: Integrations

### 4.1 Calendar Integration
**Spec:** Section 7  
**Files:** `src/calendar/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Define `ICalendarAdapter` | Common interface |
| Implement Apple Calendar | EventKit integration |
| Implement Google Calendar | Google Calendar API |
| Sync on launch + 15 min | Background refresh |
| Surface suggestion cards | "Add departure reminder?" |
| Handle permission denial | Explanation + settings link |
| Handle recurring events | Generate for each occurrence |

**Acceptance Criteria:**
- [ ] TC-01: Apple Calendar events with locations → suggestion cards
- [ ] TC-02: Google Calendar events → suggestion cards
- [ ] TC-03: Confirm suggestion → countdown_event reminder
- [ ] TC-04: Permission denial → explanation banner
- [ ] TC-05: Sync failure → graceful degradation
- [ ] TC-06: Recurring events → each occurrence

---

### 4.2 Location Awareness
**Spec:** Section 8  
**Files:** `src/location/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Single location check | At departure anchor only |
| 500m geofence radius | "At origin" determination |
| Escalate if at origin | Fire firm/critical immediately |
| Lazy permission request | On first location-aware reminder |
| No location history | Single comparison only |

**Acceptance Criteria:**
- [ ] TC-01: User still at origin → firm/critical fires immediately
- [ ] TC-02: User left → normal departure nudge
- [ ] TC-03: Permission request at first use
- [ ] TC-04: Denied → reminder without escalation
- [ ] TC-05: Single location API call

---

### 4.3 Sound Library
**Spec:** Section 12  
**Files:** `src/sounds/` (new module)

**Tasks:**
| Task | Details |
|------|---------|
| Bundle built-in sounds | 5 per category: Commute, Routine, Errand |
| Custom import | MP3, WAV, M4A, max 30 sec |
| Per-reminder selection | Override category default |
| Corrupted file fallback | Use default + error |

**Acceptance Criteria:**
- [ ] TC-01: Built-in sounds play without network
- [ ] TC-02: Custom MP3 import appears in picker
- [ ] TC-03: Custom sound plays at anchor fire
- [ ] TC-04: Corrupted sound → default + error
- [ ] TC-05: Sound persists on edit

---

## Files to Create/Modify

### Create (New Modules)
| File | Purpose | Priority |
|------|---------|----------|
| `harness/scenario_harness.py` | Test runner | P1 |
| `src/parser/__init__.py` | Parser module | P2 |
| `src/parser/llm_adapter.py` | LLM adapter interface | P2 |
| `src/parser/keyword_extractor.py` | Keyword fallback parser | P2 |
| `src/tts/__init__.py` | TTS module | P3 |
| `src/tts/elevenlabs_adapter.py` | ElevenLabs integration | P3 |
| `src/tts/cache_manager.py` | TTS file caching | P3 |
| `src/snooze/__init__.py` | Snooze module | P3 |
| `src/stats/__init__.py` | Stats module | P2 |
| `src/notifications/__init__.py` | Notification module | P3 |
| `src/scheduler/__init__.py` | Scheduler module | P3 |
| `src/calendar/__init__.py` | Calendar module | P4 |
| `src/location/__init__.py` | Location module | P4 |
| `src/sounds/__init__.py` | Sound module | P4 |

### Modify
| File | Changes | Priority |
|------|---------|----------|
| `src/test_server.py` | Fix chain logic, complete schema, add endpoints | P1-P2 |

---

## Quick Wins (1-2 days each)

1. **Fix chain engine compression** — 1 day, high impact, unblocks scenarios
2. **Complete database schema** — 0.5 day, enables all data persistence
3. **Create testing harness** — 1 day, enables validation
4. **Add 3 variations per personality tier** — 0.5 day, quality improvement
5. **Fix hit rate + add streak** — 0.5 day, visible stats

---

## Implementation Phases

```
Phase 1: Critical Blockers (Week 1)
├── 1.1 Create testing harness
├── 1.2 Fix chain engine compression
└── 1.3 Complete database schema

Phase 2: Core Engine (Week 2)
├── 2.1 Complete voice personality system
├── 2.2 Add LLM adapter interface
└── 2.3 Complete stats system

Phase 3: Features (Week 3-4)
├── 3.1 TTS system
├── 3.2 Snooze & dismissal
├── 3.3 Notification & alarm behavior
└── 3.4 Background scheduling

Phase 4: Integrations (Week 5-6)
├── 4.1 Calendar integration
├── 4.2 Location awareness
└── 4.3 Sound library

Phase 5: Polish (Week 7)
└── E2E testing + documentation
```

---

## Validation Commands

```bash
# Start test server
python3 src/test_server.py &

# Lint
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Run tests (after harness created)
python3 -m pytest harness/

# Run scenarios
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Custom scenario directory
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project urgent-alarm
```

---

## Spec Reference

- **Full spec:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md`
- **Product doc:** `specs/urgent-voice-alarm-app-2026-04-08.md`
- **Scenario files:** `scenarios/*.yaml` (16 files)
