# Urgent Alarm - Implementation Plan

**Generated:** 2026-04-08 (Updated)
**Spec Version:** urgent-voice-alarm-app-2026-04-08.spec.md
**Spec Sections:** 14 (Sections 2-13 covering features, Section 1 overview, Section 14 definition of done)
**Test Scenarios:** 47 TC cases (6+ per section)
**Scenario Files:** 15 YAML files in `scenarios/`

---

## Gap Analysis Summary

| Component | Status | Gap |
|-----------|--------|-----|
| **Testing Harness** | ❌ **MISSING** | `harness/scenario_harness.py` does not exist — must be created |
| **Chain Engine** | ⚠️ Buggy | Compression logic produces duplicates (firm=0, alarm=0) and incorrect tier counts |
| **Database Schema** | ⚠️ Incomplete | Missing 6 columns, 3 tables per spec Section 13 |
| **LLM Parser** | ⚠️ Partial | Keyword extraction works; no LLM adapter interface |
| **Voice System** | ⚠️ Partial | 1 template/tier vs spec's 3+ variations required |
| **Stats System** | ⚠️ Buggy | No streak, no miss window, hit rate calculation needs review |
| **TTS System** | ❌ Not implemented | No ElevenLabs adapter, caching, or fallback |
| **Notifications** | ❌ Not implemented | No DND, quiet hours, tier escalation, chain overlap |
| **Background Scheduling** | ❌ Not implemented | No Notifee, BGTaskScheduler, recovery scan |
| **Calendar Integration** | ❌ Not implemented | No EventKit or Google Calendar API |
| **Location Awareness** | ❌ Not implemented | No CoreLocation, geofence, or origin check |
| **Snooze Flow** | ❌ Not implemented | No tap/hold snooze, chain re-computation |
| **Sound Library** | ❌ Not implemented | No built-in sounds or custom import |

**Current Implementation:** ~25% (basic engine present, harness missing entirely)

---

## Critical Path (Must Fix First)

These items block all other work:

### 1. Create Testing Harness ⚠️ **CRITICAL — HARNESS DOES NOT EXIST**

**Location:** `harness/scenario_harness.py` (file does not exist — must be created from scratch)

**Impact:** Cannot validate any of the 15 scenario files via `python3 -m pytest harness/` or `sudo python3 harness/scenario_harness.py --project urgent-alarm`

**Required Features:**
- YAML scenario parser
- HTTP assertion checker (status, body)
- DB assertion checker (record existence, field values)
- `llm_judge` assertion type support
- `api_sequence` trigger type (sequential API calls)
- `base_url` env var support
- `OTTO_SCENARIO_DIR` support (default: `/var/otto-scenarios/{project}`)
- Output to `/tmp/ralph-scenario-result.json`

**Scenario Files to Support:**
```
scenarios/chain-full-30min.yaml        # TC-01: 8 anchors for ≥25 min
scenarios/chain-compressed-15min.yaml  # TC-02: compressed for 15 min buffer
scenarios/chain-invalid-rejected.yaml # TC-04: 400 error on invalid
scenarios/chain-minimum-3min.yaml      # TC-03: minimum for ≤5 min
scenarios/parse-natural-language.yaml  # TC-01: full parse
scenarios/parse-simple-countdown.yaml # TC-02: simple countdown
scenarios/parse-tomorrow.yaml         # TC-03: tomorrow date resolution
scenarios/voice-coach-personality.yaml # TC-01: coach messages
scenarios/voice-no-nonsense.yaml      # TC-02: no-nonsense messages
scenarios/voice-all-personalities.yaml # All 5 personalities
scenarios/history-record-outcome.yaml # Record hit/miss
scenarios/history-record-miss-feedback.yaml # TC-05: feedback loop
scenarios/stats-hit-rate.yaml         # TC-01: 80% hit rate
scenarios/reminder-creation-crud.yaml # Full CRUD workflow
scenarios/reminder-creation-cascade-delete.yaml # TC-03: cascade delete
```

**Acceptance Criteria:**
- [ ] `python3 -m py_compile harness/scenario_harness.py` passes
- [ ] `python3 harness/scenario_harness.py --project urgent-alarm` runs without error
- [ ] All 15 scenario files execute successfully
- [ ] `/tmp/ralph-scenario-result.json` is written after execution

**Dependencies:** None (pure Python, stdlib)

---

### 2. Fix Chain Engine Compression Logic ⚠️ HIGH PRIORITY

**Location:** `src/test_server.py` - `compute_escalation_chain()` function

**Current Bugs Identified:**

```
TC-02 (15 min buffer) - WRONG:
  urgent: 10 min before  ✓
  pushing: 5 min before  ✓
  firm: 0 min before     ✗ (should be 15 min before)
  critical: 1 min before ✗ (duplicate tier, wrong timing)
  alarm: 0 min before    ✗ (duplicate time)

TC-03 (3 min buffer) - WRONG:
  firm: 2 min before  ✓
  alarm: 0 min before ✗ (should have 3 anchors: firm, critical, alarm)
```

**Spec Requirements vs Current:**

| Buffer | Spec Requirement | Current | Bug |
|--------|------------------|---------|-----|
| ≥25 min | 8 anchors: calm→casual→pointed→urgent→pushing→firm→critical→alarm | 8 ✅ | None |
| 15-24 min | 5 anchors: urgent→pushing→firm→critical→alarm | 5 ❌ | Duplicates at T-0, wrong tiers |
| 10-14 min | 5 anchors (similar compression) | 5 ❌ | Same duplicates |
| 5-9 min | 3 anchors: firm→critical→alarm | 3 ❌ | Missing critical tier |
| 1-4 min | 2-3 anchors: firm+critical+alarm | 2 ❌ | Missing critical tier |

**Fix Needed for TC-02 (15 min buffer):**
Based on spec: anchors should be at T-10 (urgent), T-5 (pushing), T-15 (firm), T-1 (critical), T-0 (alarm)

Current code has wrong logic - `firm` and `alarm` both end up at 0 minutes before.

**Fix Needed for TC-03 (3 min buffer):**
Should be: T-2 (firm), T-1 (critical), T-0 (alarm) = 3 anchors

**Tasks:**
| Task | Description |
|------|-------------|
| Fix 15-24 min range | 5 anchors with correct tiers: urgent, pushing, firm, critical, alarm |
| Fix 10-14 min range | 5 anchors with adjusted T thresholds |
| Fix 5-9 min range | 3 anchors: firm, critical, alarm |
| Fix 1-4 min range | 3 anchors per TC-03 |
| Implement `get_next_unfired_anchor()` | Required for TC-05 |
| Add unit tests | Verify each buffer range |

**Acceptance Criteria:**
- [ ] TC-01: 30 min buffer → 8 anchors at 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] TC-02: 15 min buffer → 5 anchors at T-10, T-5, T-15, T-1, T-0 (urgent, pushing, firm, critical, alarm)
- [ ] TC-03: 3 min buffer → 3 anchors at T-2 (firm), T-1 (critical), T-0 (alarm)
- [ ] TC-04: 120 min buffer → 400 error "drive_duration exceeds time_to_arrival"
- [ ] TC-05: `get_next_unfired_anchor(reminder_id)` returns earliest unfired anchor
- [ ] TC-06: Identical inputs produce identical anchor lists

---

### 3. Complete Database Schema ⚠️ HIGH PRIORITY

**Location:** `src/test_server.py` - `init_db()` function

**Spec:** Section 13 - Full schema with 8 tables

**Current State (Partial):**

`reminders` table - Missing columns:
- `sound_category` (TEXT) - Sound library: commute/routine/errand/custom
- `selected_sound` (TEXT) - Per-reminder sound override
- `custom_sound_path` (TEXT) - Imported custom audio file path
- `origin_lat` (REAL) - Location awareness - origin latitude
- `origin_lng` (REAL) - Location awareness - origin longitude
- `origin_address` (TEXT) - Location awareness - origin address
- `calendar_event_id` (TEXT) - Calendar integration reference

`anchors` table - Missing columns:
- `tts_fallback` (BOOLEAN) - TTS failure → use system sound
- `snoozed_to` (TEXT) - Snooze redirect to new timestamp

`history` table - Missing columns:
- `actual_arrival` (TEXT) - Resolved after firing
- `missed_reason` (TEXT) - Log: background_task_killed, dnd_suppressed, user_dismissed

**Missing tables:**
| Table | Purpose |
|-------|---------|
| `user_preferences` | User settings (needs `updated_at` column) |
| `calendar_sync` | Calendar sync state per provider |
| `custom_sounds` | Sound library import tracking |
| `schema_version` | Migration tracking |

**Tasks:**
| Task | Description |
|------|-------------|
| Add missing `reminders` columns | ALTER TABLE ADD COLUMN |
| Add missing `anchors` columns | ALTER TABLE ADD COLUMN |
| Add missing `history` columns | ALTER TABLE ADD COLUMN |
| Create `user_preferences` table | With `updated_at` column |
| Create `calendar_sync` table | apple/google sync state |
| Create `custom_sounds` table | Import tracking |
| Create `schema_version` table | Migration support |
| Enable PRAGMA foreign_keys = ON | FK enforcement |
| Enable PRAGMA journal_mode = WAL | Performance |

**Acceptance Criteria:**
- [ ] Fresh install creates all 8 tables per spec schema
- [ ] Cascade delete works: DELETE reminder → DELETE anchors
- [ ] FK violation returns error without crash
- [ ] `reminders.id` is always valid UUID v4

---

## Core Engine Completion

### 4. Complete Voice Personality System

**Location:** `src/test_server.py` - `VOICE_PERSONALITIES` dict

**Spec:** Section 10

**Current State:**
- 5 personalities defined: coach, assistant, best_friend, no_nonsense, calm ✅
- 1 template per tier per personality
- Spec requires: minimum **3 variations** per tier per personality

**Tasks:**
| Task | Description |
|------|-------------|
| Add 3+ message variations | Per tier, per personality (9 tiers × 5 personalities = 135 messages) |
| Implement random selection | Choose from variations to avoid repetition |
| Support custom prompts | Max 200 chars appended to system prompt |
| Store custom prompt in reminder | For custom voice style |

**Message Template Inventory Needed:**
```
coach:        9 tiers × 3 variations = 27 messages
assistant:    9 tiers × 3 variations = 27 messages
best_friend:  9 tiers × 3 variations = 27 messages
no_nonsense:  9 tiers × 3 variations = 27 messages
calm:         9 tiers × 3 variations = 27 messages
custom:       User-defined (max 200 chars)
```

**Acceptance Criteria:**
- [ ] TC-01: "Coach" at T-5 → motivating message with exclamation
- [ ] TC-02: "No-nonsense" at T-5 → brief, direct, no filler words
- [ ] TC-03: Custom prompt "speak like a disappointed but caring parent" modifies tone
- [ ] TC-04: Existing reminders retain original personality when default changes
- [ ] TC-05: 3 calls produce 2+ distinct messages (randomization works)

---

### 5. Add LLM Adapter Interface

**Location:** `src/parser/llm_adapter.py` (new file)

**Spec:** Section 3

**Tasks:**
| Task | Description |
|------|-------------|
| Define `ILanguageModelAdapter` | Abstract interface with `parse()` method |
| Implement `MockLLMAdapter` | Returns predefined fixture responses for tests |
| Implement `MiniMaxAdapter` | Uses MiniMax API endpoint (configurable) |
| Implement `AnthropicAdapter` | Uses Anthropic API as alternative |
| Add keyword fallback | On LLM API failure, run keyword extraction |
| Track confidence score | 0.0-1.0 based on fields successfully extracted |

**Interface:**
```python
class ILanguageModelAdapter:
    def parse(self, text: str) -> dict:  # Returns parsed reminder
    def is_available(self) -> bool:        # API health check

class MockLLMAdapter(ILanguageModelAdapter):
    def __init__(self, fixture: dict): ...

class MiniMaxAdapter(ILanguageModelAdapter):
    def __init__(self, api_key: str, endpoint: str): ...

class AnthropicAdapter(ILanguageModelAdapter):
    def __init__(self, api_key: str): ...
```

**Acceptance Criteria:**
- [ ] TC-07: Mock adapter returns fixture without any API call
- [ ] TC-04: On API failure, keyword extraction runs as fallback
- [ ] TC-06: Unintelligible input "asdfgh jkl" returns error message
- [ ] Confidence score reflects parse quality (0.0-1.0)

---

### 6. Complete Stats System

**Location:** `src/stats/` (new module)

**Spec:** Section 11

**Missing Stats:**
| Stat | Description |
|------|-------------|
| Streak counter | Increment on hit, reset on miss for recurring |
| Common miss window | Most frequently missed urgency tier |
| Adjustment cap | Cap drive_duration adjustment at +15 min |
| `actual_arrival` tracking | Nullable, set on completion |

**Tasks:**
| Task | Description |
|------|-------------|
| Add `get_streak(reminder_id)` | Count consecutive hits for recurring reminders |
| Add `get_common_miss_window(destination)` | Return most-missed tier |
| Enforce adjustment cap | Cap at +15 minutes |
| Track `actual_arrival` | Set nullable when reminder completes |
| Track `missed_reason` | Log background_task_killed, dnd_suppressed, user_dismissed |

**Acceptance Criteria:**
- [ ] TC-01: 4 hits + 1 miss + 2 pending = 80% hit rate (4/5)
- [ ] TC-02: 3 "left too late" → +6 min adjustment for destination
- [ ] TC-03: 10 "left too late" → +15 min adjustment (capped)
- [ ] TC-04: "common miss window" returns T-5 when that's most missed
- [ ] TC-05: Streak increments on hit for recurring reminders
- [ ] TC-06: Streak resets to 0 on miss

---

## Feature Implementation

### 7. TTS System (Voice Generation)

**Location:** `src/tts/` (new module)

**Spec:** Section 4

**Tasks:**
| Task | Description |
|------|-------------|
| Define `ITTSAdapter` interface | Mock-able for testing |
| Implement `ElevenLabsAdapter` | Environment-configurable API key |
| Implement `MockTTSAdapter` | Writes silent file for tests |
| Implement TTS caching | Store MP3s in `/tts_cache/{reminder_id}/` |
| Implement cache invalidation | Delete on reminder deletion |
| Implement fallback | System sound + notification text |

**Acceptance Criteria:**
- [ ] TC-01: Reminder creation generates 8 MP3s in cache directory
- [ ] TC-02: Anchor fires from local cache (no network call at runtime)
- [ ] TC-03: On ElevenLabs API failure, fallback to system sound
- [ ] TC-04: Reminder deletion removes all cached TTS files
- [ ] TC-05: Mock adapter writes silent file without real API call

---

### 8. Snooze & Dismissal Flow

**Location:** `src/snooze/` (new module)

**Spec:** Section 9

**Tasks:**
| Task | Description |
|------|-------------|
| Implement tap snooze | 1 minute default, TTS "Okay, snoozed 1 minute" |
| Implement custom snooze | Picker: 1, 3, 5, 10, 15 min options |
| Re-compute chain | Shift remaining anchors by snooze duration |
| Re-register anchors | New timestamps with scheduler |
| Implement dismissal | Feedback prompt: "You missed [destination] - timing right?" |
| Process feedback | Store + adjust drive estimates (+2 min per "left too late") |
| TTS confirmation | "Okay, snoozed X minutes" |
| Persist snooze | Survive app restart with adjusted timestamps |

**Acceptance Criteria:**
- [ ] TC-01: Tap snooze → 1 min delay + TTS confirmation
- [ ] TC-02: Tap-hold → custom snooze picker → TTS confirmation
- [ ] TC-03: Chain re-computation shifts remaining anchors by snooze duration
- [ ] TC-04: Swipe-dismiss → feedback prompt with destination
- [ ] TC-05: "No - left too late" → +2 min adjustment for future reminders
- [ ] TC-06: App killed after snooze → remaining anchors fire at adjusted times

---

### 9. Notification & Alarm Behavior

**Location:** `src/notifications/` (new module)

**Spec:** Section 5

**Tasks:**
| Task | Description |
|------|-------------|
| Implement tier escalation | gentle chime → pointed beep → urgent siren → looping alarm |
| Handle DND early | Silent notification for calm/casual/pointed |
| Handle DND final 5 min | Visual + vibration override |
| Implement quiet hours | Default 10pm-7am suppression (user-configurable) |
| Queue overdue anchors | ≤15 min after restriction ends |
| Drop >15 min overdue | Log with `missed_reason` |
| Serialize chain execution | Queue new anchors during active chain |
| Implement T-0 looping | Loop until user dismisses or snoozes |

**Acceptance Criteria:**
- [ ] TC-01: DND early anchor → silent notification only
- [ ] TC-02: DND final 5 min → visual + vibration override
- [ ] TC-03: Quiet hours → suppress + queue for later
- [ ] TC-04: >15 min overdue → drop silently + log
- [ ] TC-05: Chain overlap → serialize (queue new until current completes)
- [ ] TC-06: T-0 alarm loops until user action

---

### 10. Background Scheduling

**Location:** `src/scheduler/` (new module)

**Spec:** Section 6

**Tasks:**
| Task | Description |
|------|-------------|
| Register anchors with Notifee | Individual background tasks per anchor |
| iOS: BGTaskScheduler | BGAppRefreshTask + BGProcessingTask |
| Android: WorkManager | Background task scheduling |
| Recovery scan on launch | Fire any ≤15 min overdue anchors |
| Drop >15 min overdue | Log `missed_reason = "background_task_killed"` |
| Re-register on crash | Re-register all pending (unfired) anchors |
| Late fire warning | Log warning if >60 seconds after scheduled time |

**Acceptance Criteria:**
- [ ] TC-01: All anchors registered with correct trigger timestamps
- [ ] TC-02: Anchors fire with app closed (simulated via test)
- [ ] TC-03: Recovery scan fires grace window anchors on launch
- [ ] TC-04: >15 min overdue → drop + log
- [ ] TC-05: Crash → re-register pending anchors
- [ ] TC-06: >60s late → warning log entry

---

## Integration Implementation

### 11. Calendar Integration

**Location:** `src/calendar/` (new module)

**Spec:** Section 7

**Tasks:**
| Task | Description |
|------|-------------|
| Define `ICalendarAdapter` | Common interface for all providers |
| Implement `AppleCalendarAdapter` | EventKit integration (iOS) |
| Implement `GoogleCalendarAdapter` | Google Calendar API |
| Sync on launch + every 15 min | Background refresh support |
| Surface suggestion cards | "Add departure reminder?" for events with locations |
| Handle permission denial | Explanation + "Open Settings" link |
| Handle sync failure | Graceful degradation, error banner |
| Handle recurring events | Generate reminder for each occurrence |

**Acceptance Criteria:**
- [ ] TC-01: Apple Calendar events with locations → suggestion cards
- [ ] TC-02: Google Calendar events with locations → suggestion cards
- [ ] TC-03: Confirm suggestion → countdown_event reminder created
- [ ] TC-04: Permission denial → explanation banner with settings link
- [ ] TC-05: Sync failure → manual reminders still work, error banner
- [ ] TC-06: Recurring daily event → reminder for each occurrence

---

### 12. Location Awareness

**Location:** `src/location/` (new module)

**Spec:** Section 8

**Tasks:**
| Task | Description |
|------|-------------|
| Single location check | At departure anchor only (T-drive_duration) |
| 500m geofence radius | "At origin" if within 500m |
| Escalate if at origin | Fire firm/critical immediately instead of calm |
| Lazy permission request | On first location-aware reminder creation |
| No location history | Single comparison only, data discarded |

**Acceptance Criteria:**
- [ ] TC-01: User at origin (≤500m) → firm/critical fires immediately
- [ ] TC-02: User left (>500m) → normal departure nudge fires
- [ ] TC-03: Permission requested at first location-aware reminder
- [ ] TC-04: Denied → reminder created without location escalation
- [ ] TC-05: Only one location API call per reminder (at departure anchor)

---

### 13. Sound Library

**Location:** `src/sounds/` (new module)

**Spec:** Section 12

**Tasks:**
| Task | Description |
|------|-------------|
| Bundle built-in sounds | 5 sounds per category: Commute, Routine, Errand |
| Custom import | MP3, WAV, M4A support, max 30 seconds |
| Transcode to normalized format | Store in app sandbox |
| Per-reminder selection | Override category default |
| Corrupted file fallback | Use category default + log error |

**Acceptance Criteria:**
- [ ] TC-01: Built-in sounds play without network access
- [ ] TC-02: Custom MP3 import appears in sound picker
- [ ] TC-03: Custom sound plays at anchor fire
- [ ] TC-04: Corrupted custom sound → default + error
- [ ] TC-05: Sound selection persists on reminder edit

---

## Files to Create/Modify

### New Module Structure
```
src/
├── parser/
│   ├── __init__.py
│   ├── llm_adapter.py      # ILanguageModelAdapter + implementations
│   └── keyword_extractor.py  # Fallback parser
├── tts/
│   ├── __init__.py
│   ├── elevenlabs_adapter.py
│   └── cache_manager.py
├── stats/
│   ├── __init__.py        # Hit rate, streak, miss window
│   └── destination_stats.py
├── snooze/
│   └── __init__.py        # Snooze logic + chain re-computation
├── notifications/
│   └── __init__.py        # Tier escalation, DND, quiet hours
├── scheduler/
│   └── __init__.py        # Notifee, BGTaskScheduler, recovery
├── calendar/
│   └── __init__.py        # EventKit, Google Calendar adapters
├── location/
│   └── __init__.py        # CoreLocation, geofence check
└── sounds/
    └── __init__.py        # Built-in sounds, custom import
```

### Modify
| File | Changes |
|------|---------|
| `src/test_server.py` | Fix chain logic bugs, complete schema, add missing endpoints |
| `harness/scenario_harness.py` | Create from scratch |

---

## Implementation Phases

```
Phase 1: Critical Blockers (Day 1-2)
├── 1. Create testing harness (harness/scenario_harness.py)
├── 2. Fix chain engine compression logic
└── 3. Complete database schema

Phase 2: Core Engine (Day 3-5)
├── 4. Complete voice personality system (3+ variations)
├── 5. Add LLM adapter interface
└── 6. Complete stats system (hit rate, streak, miss window)

Phase 3: Feature Implementation (Day 6-14)
├── 7. TTS system (ElevenLabs + caching)
├── 8. Snooze & dismissal flow
├── 9. Notification & alarm behavior
└── 10. Background scheduling

Phase 4: Integrations (Day 15-21)
├── 11. Calendar integration
├── 12. Location awareness
└── 13. Sound library

Phase 5: Polish (Day 22-28)
├── E2E testing
├── Scenario validation
└── Documentation
```

---

## Validation Commands

```bash
# Start test server (required for scenarios)
python3 src/test_server.py &

# Lint
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Run harness (after creation)
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Custom scenario directory
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project urgent-alarm

# Test server health
curl http://localhost:8090/health
```

---

## Spec Reference

| Document | Location |
|----------|----------|
| Full specification | `specs/urgent-voice-alarm-app-2026-04-08.spec.md` |
| Product requirements | `specs/urgent-voice-alarm-app-2026-04-08.md` |
| Scenario files | `scenarios/*.yaml` (15 files) |