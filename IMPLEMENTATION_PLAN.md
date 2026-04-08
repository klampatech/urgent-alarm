# Urgent Alarm - Implementation Plan

## Gap Analysis Summary

**Spec:** 14 sections covering all app features  
**Current State:** `test_server.py` implements ~25% of spec (basic chain engine, keyword parsing, message templates, simple DB schema)  
**Missing:** ~75% of features including TTS, notifications, background scheduling, calendar, location, snooze, stats, and testing infrastructure

---

## Phase 1: Foundation (Core Engine + Testing Infrastructure)

### 1.1 Complete Chain Engine (Priority: HIGH)
**Spec Section:** 2 (Escalation Chain Engine)  
**Status:** Partially implemented - logic needs refinement

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Fix chain compression logic | Current logic doesn't match spec exactly. Spec says: buffer ≥25 = 8 anchors, 10-24 = compressed, ≤5 = minimum | TC-01 to TC-06 pass |
| Add `get_next_unfired_anchor()` | Query next unfired anchor for a reminder | Returns earliest unfired after restart |
| Add validation: arrival > departure + minimum | Ensure valid time windows | TC-04: reject invalid chains |
| Add `snoozed_to` column tracking | Track snoozed anchors | Snooze persistence after restart |

**Files:** `src/test_server.py`

---

### 1.2 Complete Database Schema (Priority: HIGH)
**Spec Section:** 13 (Data Persistence)  
**Status:** Incomplete schema

| Task | Details |
|------|---------|
| Add missing columns to `anchors` | `tts_fallback`, `snoozed_to` |
| Add `origin_lat`, `origin_lng`, `origin_address` to reminders | Location awareness |
| Add `calendar_event_id` to reminders | Calendar integration |
| Add `custom_sound_path` to reminders | Sound library |
| Add `tts_cache` table | TTS file tracking |
| Add `custom_sounds` table | Imported audio files |
| Add `calendar_sync` table | Calendar sync state |
| Add `updated_at` to `destination_adjustments` | Audit trail |
| Enable WAL mode and foreign keys | PRAGMA settings |
| Add schema version table | Migration tracking |

**Files:** `src/test_server.py` (schema section)

---

### 1.3 Create Testing Infrastructure (Priority: HIGH)
**Spec Section:** 14 (Definition of Done) + AGENTS.md

| Task | Details |
|------|---------|
| Create `harness/scenario_harness.py` | Main test runner with scenario loading |
| Create `harness/test_chain_engine.py` | Unit tests for chain computation |
| Create `harness/test_parser.py` | Unit tests for LLM + keyword parsing |
| Create `harness/test_voice.py` | Unit tests for message generation |
| Create `harness/test_database.py` | Schema and migration tests |
| Implement in-memory DB mode | `?mode=memory` for tests |
| Add mock adapters | `ILanguageModelAdapter`, `ITTSAdapter` |

**Files:** `harness/*.py`

---

## Phase 2: Core Business Logic

### 2.1 Complete LLM Parser (Priority: HIGH)
**Spec Section:** 3 (Reminder Parsing & Creation)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Define `ILanguageModelAdapter` interface | Mock-able interface | Tests can inject mock responses |
| Implement keyword extraction | Regex patterns for all formats | TC-01 to TC-06 pass |
| Add confidence scoring | Track parse quality | Falls back gracefully |
| Add reminder type detection | countdown_event, simple_countdown, morning_routine, standing_recurring | Correct type assigned |
| Handle "tomorrow" date resolution | Proper datetime calculation | TC-03: correct tomorrow parsing |
| Add manual field correction | Allow user edits before confirm | TC-05: edits preserved |

**Files:** `src/parser/` module

---

### 2.2 Complete Voice & TTS System (Priority: MEDIUM)
**Spec Section:** 4 (Voice & TTS Generation)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Define `ITTSAdapter` interface | Mock-able for tests | TC-05: mock works without API |
| Implement ElevenLabs adapter | Environment-configurable | Real TTS generation |
| Add TTS caching to `/tts_cache/{reminder_id}/` | Local file storage | TC-01: files created |
| Implement TTS fallback | System sound + notification text | TC-03: fallback on 503 |
| Add voice personality → voice ID mapping | Five personalities + custom | Correct voice used |
| Implement cache invalidation on delete | Clean up TTS files | TC-04: cleanup works |

**Files:** `src/tts/` module

---

### 2.3 Complete Voice Personality System (Priority: MEDIUM)
**Spec Section:** 10 (Voice Personality System)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Add 3+ message variations per tier | Avoid repetition | TC-05: variation exists |
| Implement "Calm" personality | Gentle-only for non-aggressive users | Distinct from others |
| Add custom prompt handling | User-written style prompts | Max 200 chars |
| Add personality storage | User preferences | Default per user |

**Files:** `src/voice_personalities/` module

---

## Phase 3: Features

### 3.1 Notification & Alarm Behavior (Priority: MEDIUM)
**Spec Section:** 5 (Notification & Alarm Behavior)

| Task | Details |
|------|---------|
| Implement notification tier escalation | Gentle → pointed → urgent → alarm |
| Handle DND awareness | Silent early, visual+ vibrating final 5 min |
| Implement quiet hours | Suppress nudges 10pm-7am default |
| Queue overdue anchors (≤15 min) | Fire after restriction ends |
| Drop overdue anchors (>15 min) | TC-04: 15-min rule |
| Serialize chain execution | Queue new anchors during active chain |
| Implement T-0 looping alarm | Until user dismisses/snoozes |

**Files:** `src/notifications/` module

---

### 3.2 Snooze & Dismissal Flow (Priority: MEDIUM)
**Spec Section:** 9 (Snooze & Dismissal Flow)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Implement tap snooze (1 min default) | Pause and re-fire | TC-01: 1-min snooze |
| Implement tap-and-hold custom snooze | Picker: 1, 3, 5, 10, 15 min | TC-02: custom works |
| Re-compute chain after snooze | Shift remaining anchors | TC-03: re-computation correct |
| Re-register with Notifee | New timestamps | TC-06: persistence after restart |
| Implement dismissal feedback | "Timing right?" Yes/No | TC-04: feedback stored |
| Process "left too late" feedback | +2 min drive estimate | TC-05: adjustment applied |
| TTS snooze confirmation | "Okay, snoozed X minutes" | TC-01: spoken confirmation |

**Files:** `src/snooze/` module

---

### 3.3 History, Stats & Feedback Loop (Priority: MEDIUM)
**Spec Section:** 11 (History, Stats & Feedback Loop)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Calculate weekly hit rate | 7-day trailing | TC-01: 80% calculation correct |
| Implement feedback adjustment | +2 min per "left too late", cap +15 | TC-02, TC-03: cap enforced |
| Identify common miss window | Most-missed urgency tier | TC-04: correct identification |
| Implement streak counter | Increment on hit, reset on miss | TC-05, TC-06: counter works |
| Add `actual_arrival` tracking | Nullable, resolved later | History entry completion |
| Add `missed_reason` tracking | Log missed anchor reasons | Background task kills |

**Files:** `src/stats/` module

---

### 3.4 Sound Library (Priority: LOW)
**Spec Section:** 12 (Sound Library)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Add built-in sounds | 5 per category (commute, routine, errand) | No network required |
| Implement custom audio import | MP3, WAV, M4A, max 30 sec | TC-02: import works |
| Add sound selection per reminder | Override category default | TC-05: persistence on edit |
| Implement corrupted file fallback | Use category default + error | TC-04: graceful degradation |

**Files:** `src/sounds/` module

---

## Phase 4: Integrations

### 4.1 Calendar Integration (Priority: MEDIUM)
**Spec Section:** 7 (Calendar Integration)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Define `ICalendarAdapter` interface | Common interface for Apple + Google | |
| Implement Apple Calendar adapter | EventKit integration | TC-01: events appear |
| Implement Google Calendar adapter | Google Calendar API | TC-02: events appear |
| Sync on launch + every 15 min | Background refresh | |
| Surface suggestion cards | "Add departure reminder?" | TC-03: creates reminder |
| Handle permission denial | Explanation + settings link | TC-04: denial handling |
| Graceful sync failure | Continue with local reminders | TC-05: degradation works |
| Handle recurring events | Generate for each occurrence | TC-06: recurring works |

**Files:** `src/calendar/` module

---

### 4.2 Location Awareness (Priority: MEDIUM)
**Spec Section:** 8 (Location Awareness)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Single location check at departure | CoreLocation (iOS) / FusedLocationProvider (Android) | TC-05: only one API call |
| Geofence radius 500m | "At origin" if within 500m | TC-01, TC-02: behavior correct |
| Escalate if still at origin | Fire firm/critical tier immediately | TC-01: escalation works |
| Lazy permission request | Only on first location-aware reminder | TC-03: request timing correct |
| Denied permission handling | Create reminder without location | TC-04: graceful handling |
| No location history | Single comparison, then discard | |

**Files:** `src/location/` module

---

### 4.3 Background Scheduling (Priority: HIGH)
**Spec Section:** 6 (Background Scheduling & Reliability)

| Task | Details | Acceptance Criteria |
|------|---------|---------------------|
| Register anchors with Notifee | Individual background tasks | TC-01: all anchors scheduled |
| iOS BGTaskScheduler | BGAppRefreshTask + BGProcessingTask | TC-02: fires with app closed |
| Recovery scan on launch | Fire overdue anchors (≤15 min) | TC-03: recovery works |
| Drop >15 min overdue anchors | Log with `missed_reason` | TC-04: drop + log |
| Re-register on crash | Pending anchors re-registered | TC-05: crash recovery |
| Late fire warning | Log if >60s late | TC-06: warning logged |

**Files:** `src/scheduler/` module

---

## Phase 5: Polish & E2E

### 5.1 E2E Testing (Priority: MEDIUM)
**Spec Section:** 14 (Definition of Done)

| Task | Details |
|------|---------|
| Quick Add flow E2E | Text/speech → parse → confirm → reminder created |
| Reminder confirmation E2E | Review parsed data, edit, confirm |
| Anchor firing sequence E2E | Chain fires in order |
| Snooze interaction E2E | Tap → snooze → re-fire |
| Dismissal feedback E2E | Dismiss → feedback → adjustment |
| Settings navigation E2E | Change voice, quiet hours, etc. |
| Sound library browsing E2E | Browse, import, select |

**Files:** `harness/e2e/` module

---

## Implementation Order (Dependency Graph)

```
Phase 1: Foundation
├── 1.1 Chain Engine (all other features depend on correct anchor computation)
├── 1.2 Complete DB Schema (all features persist data)
└── 1.3 Testing Infrastructure (validate everything else)

Phase 2: Core Business Logic
├── 2.1 LLM Parser (reminder creation flow)
├── 2.2 TTS System (voice output)
└── 2.3 Voice Personalities (messaging)

Phase 3: Features
├── 3.1 Notifications (user-facing output)
├── 3.2 Snooze/Dismissal (user interactions)
├── 3.3 Stats/History (feedback loop)
└── 3.4 Sound Library (audio customization)

Phase 4: Integrations
├── 4.1 Calendar (Apple + Google)
├── 4.2 Location (single-point check)
└── 4.3 Background Scheduling (reliability)

Phase 5: Polish
└── 5.1 E2E Testing (full coverage)
```

---

## Quick Wins (1-2 days each)

1. **Fix chain engine compression** - 1 day, high impact
2. **Complete database schema** - 0.5 day, unblocks everything
3. **Create testing infrastructure** - 1 day, enables validation
4. **Add message variations (3 per tier)** - 0.5 day, quality improvement
5. **Implement hit rate calculation** - 0.5 day, visible stats

---

## Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `src/test_server.py` | Modify - complete schema + endpoints | 1 |
| `harness/scenario_harness.py` | Create | 1 |
| `harness/test_chain_engine.py` | Create | 1 |
| `harness/test_parser.py` | Create | 1 |
| `harness/test_voice.py` | Create | 1 |
| `harness/test_database.py` | Create | 1 |
| `src/parser/__init__.py` | Create | 2 |
| `src/parser/llm_adapter.py` | Create | 2 |
| `src/parser/keyword_extractor.py` | Create | 2 |
| `src/tts/__init__.py` | Create | 2 |
| `src/tts/elevenlabs_adapter.py` | Create | 2 |
| `src/tts/cache_manager.py` | Create | 2 |
| `src/voice_personalities/__init__.py` | Create | 2 |
| `src/notifications/__init__.py` | Create | 3 |
| `src/snooze/__init__.py` | Create | 3 |
| `src/stats/__init__.py` | Create | 3 |
| `src/sounds/__init__.py` | Create | 3 |
| `src/calendar/__init__.py` | Create | 4 |
| `src/calendar/apple_adapter.py` | Create | 4 |
| `src/calendar/google_adapter.py` | Create | 4 |
| `src/location/__init__.py` | Create | 4 |
| `src/scheduler/__init__.py` | Create | 4 |
| `src/scheduler/notifee_adapter.py` | Create | 4 |
| `harness/e2e/` | Create | 5 |
