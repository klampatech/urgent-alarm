# URGENT Alarm - Implementation Plan

> **Generated:** 2026-04-08  
> **Purpose:** Bridge gaps between `specs/urgent-voice-alarm-app-2026-04-08.spec.md` and current codebase

---

## Analysis Summary

### Specification Files
- `specs/urgent-voice-alarm-app-2026-04-08.md` — Product overview (user stories, core experience, features)
- `specs/urgent-voice-alarm-app-2026-04-08.spec.md` — Full technical spec (14 sections, 1000+ lines)

### Current Codebase State

| Component | Status | Notes |
|-----------|--------|-------|
| `src/test_server.py` | ⚠️ Proof-of-concept | HTTP server with partial logic (~400 lines) |
| `harness/` | ❌ **EMPTY** | **CRITICAL** — Otto cannot run without this |
| `src/lib/` | ❌ Missing | Must be created for structured library |
| `src/lib/database.py` | ❌ Missing | Schema incomplete per spec Section 13 |
| `src/lib/chain_engine.py` | ❌ Missing | Core logic only in test_server.py |
| `src/lib/adapters/*.py` | ❌ Missing | LLM, TTS, Calendar interfaces missing |
| `src/lib/services/*.py` | ❌ Missing | Notification, snooze, location services missing |

### What's Implemented (in `test_server.py`)

| Feature | Implemented | Spec Section |
|---------|-------------|--------------|
| Chain engine (`compute_escalation_chain`) | ✅ Partial | §2 |
| Parser (`parse_reminder_natural`) | ⚠️ Keyword only | §3 |
| Voice personalities (`VOICE_PERSONALITIES`) | ⚠️ 1 template/tier | §10 |
| Hit rate calculation (`calculate_hit_rate`) | ✅ Basic | §11 |
| HTTP endpoints | ✅ Partial | N/A |
| Database schema | ⚠️ Incomplete | §13 |

### Gaps by Spec Section

| § | Section | Severity | Gap Details |
|---|---------|----------|-------------|
| — | **Otto Harness** | 🔴 Critical | `harness/` is empty — Otto cannot run |
| 2 | Escalation Chain Engine | 🟡 Medium | Missing 20-24 min compression, `get_next_unfired_anchor()` |
| 3 | Reminder Parsing | 🔴 High | No LLM adapter interface, no mock, no confirmation flow |
| 4 | Voice & TTS Generation | 🔴 High | No ElevenLabs adapter, no TTS caching, no clip storage |
| 5 | Notification Behavior | ❌ Missing | No DND/quiet hours, no tier escalation sounds, no serialization |
| 6 | Background Scheduling | ❌ Missing | No Notifee/BGTaskScheduler, no recovery scan |
| 7 | Calendar Integration | ❌ Missing | No EventKit/Google Calendar |
| 8 | Location Awareness | ❌ Missing | No CoreLocation/FusedLocationProvider |
| 9 | Snooze & Dismissal | ❌ Missing | No snooze, no chain recompute, no feedback prompt |
| 10 | Voice Personality | 🟡 Medium | 1 template/tier (spec: 3 min variations) |
| 11 | History & Stats | 🟡 Medium | Missing common miss window, streak incomplete |
| 12 | Sound Library | ❌ Missing | No categories, no import |
| 13 | Data Persistence | 🟡 Medium | Schema incomplete (12+ columns missing) |

---

## Implementation Tasks

### P0 — Otto Harness (Blocking)

> **Otto cannot run without this. Must be created first.**

#### 1.1 Create Scenario Harness
**Priority:** P0 — Blocking Otto loop  
**Files:** `harness/scenario_harness.py`, `harness/conftest.py`

**Tasks:**
- [ ] Create `harness/scenario_harness.py` as main executable
- [ ] Parse command-line args: `--project`, `--verbose`
- [ ] Read scenarios from `/var/otto-scenarios/{project}/*.yaml`
- [ ] Run pytest on `harness/` directory
- [ ] Write results to `/tmp/ralph-scenario-result.json`
- [ ] Handle sudo requirements gracefully

**Acceptance Criteria:**
```bash
sudo python3 harness/scenario_harness.py --project otto-matic
# Writes {"pass": true} or {"pass": false} to /tmp/ralph-scenario-result.json
```

---

### P1 — Foundation (Blocks Everything Else)

#### 1.2 Complete Data Persistence Layer
**Priority:** P1  
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

**Spec Reference:** Section 13

**Schema Gaps (per spec):**

```sql
-- MISSING from reminders:
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
custom_sound_path TEXT,
calendar_event_id TEXT

-- MISSING from anchors:
tts_fallback BOOLEAN DEFAULT FALSE,
snoozed_to TEXT

-- MISSING from history:
actual_arrival TEXT,
missed_reason TEXT

-- NEW TABLES needed:
calendar_sync (...)
custom_sounds (...)
destination_adjustments (...)  -- Already partially exists
```

**Tasks:**
- [ ] Implement sequential migration system (`migrations.py`)
- [ ] Add all missing columns per spec schema
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] Add `Database.getInMemoryInstance()` for tests
- [ ] UUID v4 generation for all IDs
- [ ] Cascade delete for reminders → anchors

**Acceptance Tests:**
- [ ] Fresh DB starts at current schema version
- [ ] In-memory test DB works
- [ ] Cascade deletes work (reminder → anchors)
- [ ] FK violations return errors without crash

---

#### 1.3 Complete Escalation Chain Engine
**Priority:** P1  
**Files:** `src/lib/chain_engine.py`

**Spec Reference:** Section 2

**Current Gaps:**
- Missing 20-24 min buffer compression
- Missing `get_next_unfired_anchor(reminder_id)`
- Missing `fire_count` tracking
- Missing validation: `arrival > departure + minimum_drive_time`

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` for recovery
- [ ] Add compressed chain for **20-24 min buffer** (currently only 10-24 covered)
- [ ] Ensure determinism: same inputs = same outputs
- [ ] Complete validation per spec
- [ ] Track `fire_count` for retry logic

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Full chain (≥25 min) | 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00 |
| TC-02 | Compressed chain (10-24 min) | 4-5 anchors, skip calm/casual |
| TC-03 | Minimum chain (≤5 min) | 3 anchors: T-3, T-1, T-0 |
| TC-04 | Invalid chain rejection | Error: "drive_duration exceeds time_to_arrival" |
| TC-05 | Next unfired anchor recovery | Returns earliest unfired anchor |
| TC-06 | Chain determinism | Same inputs = same outputs |

---

### P2 — Core Services

#### 2.1 LLM Adapter Interface
**Priority:** P2  
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_mock.py`, `src/lib/adapters/keyword_fallback.py`

**Spec Reference:** Section 3

**Tasks:**
- [ ] Define `ILanguageModelAdapter` abstract interface
- [ ] Implement `MockLLMAdapter` for tests (returns predefined fixtures)
- [ ] Implement `KeywordFallbackAdapter` (regex-based, confidence < 1.0)
- [ ] Support formats: "X min drive", "in X minutes", "arrive at X"
- [ ] Parse all 4 reminder types: countdown_event, simple_countdown, morning_routine, standing_recurring

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Full NLP parse | destination, arrival_time, drive_duration extracted |
| TC-02 | Simple countdown | reminder_type = "simple_countdown" |
| TC-03 | Tomorrow date | arrival_time = next day's specified time |
| TC-04 | LLM failure fallback | keyword extraction with confidence < 1.0 |
| TC-05 | Manual correction | Edited values used for chain creation |
| TC-06 | Unintelligible input | User-facing error message |
| TC-07 | Mock adapter | No real API calls in test mode |

---

#### 2.2 TTS Adapter Interface
**Priority:** P2  
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_mock.py`, `src/lib/tts_cache.py`

**Spec Reference:** Section 4

**Tasks:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement `MockTTSAdapter` (writes 1-second silent file)
- [ ] Implement TTS cache (`/tts_cache/{reminder_id}/{anchor_id}.mp3`)
- [ ] Cache invalidation on reminder delete
- [ ] Fallback to system notification on TTS failure

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | TTS clip generation at creation | 8 MP3 files in cache |
| TC-02 | Anchor fires from cache | No network call |
| TC-03 | TTS fallback on API failure | tts_fallback = true |
| TC-04 | TTS cache cleanup on delete | All files removed |
| TC-05 | Mock TTS in tests | Local file written, no API call |

---

#### 2.3 Voice Personality Enhancement
**Priority:** P2  
**Files:** `src/lib/voice_personalities.py`, `src/lib/message_generator.py`

**Spec Reference:** Section 10

**Current State:** 1 template per tier per personality

**Tasks:**
- [ ] Add minimum **3 message variations** per tier per personality (5 × 8 × 3 = 120 messages)
- [ ] Random selection or rotation
- [ ] Custom prompt support (max 200 chars)
- [ ] Personality immutability for existing reminders

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Coach personality at T-5 | Motivational language with "!" |
| TC-02 | No-nonsense at T-5 | Brief, direct, no filler |
| TC-03 | Custom personality | Tone reflects custom prompt |
| TC-04 | Personality immutability | Existing reminders keep original |
| TC-05 | Message variation | 3 calls → at least 2 distinct outputs |

---

### P3 — Notifications & Scheduling

#### 3.1 Notification Behavior System
**Priority:** P2  
**Files:** `src/lib/notification_service.py`

**Spec Reference:** Section 5

**Tasks:**
- [ ] Urgency tier → notification sound mapping
- [ ] DND detection and suppression logic
- [ ] Quiet hours (default: 10pm-7am, configurable)
- [ ] Overdue anchor handling (15-min grace window)
- [ ] Chain overlap serialization queue
- [ ] T-0 alarm looping until user action

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | DND early anchor suppressed | Silent notification, no TTS |
| TC-02 | DND final 5-minute override | Visual + vibration, TTS plays |
| TC-03 | Quiet hours suppression | Anchor suppressed, queued |
| TC-04 | Overdue anchor drop (15 min rule) | Anchor dropped, chain continues |
| TC-05 | Chain overlap serialization | New anchor queued |
| TC-06 | T-0 alarm loops | Loops until user action |

---

#### 3.2 Background Scheduling
**Priority:** P3  
**Files:** `src/lib/background_scheduler.py`

**Spec Reference:** Section 6

**Tasks:**
- [ ] Notifee integration (placeholder for mobile)
- [ ] Recovery scan on app launch
- [ ] Re-register pending anchors on crash recovery
- [ ] Late fire warning (>60s delay)

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Anchor scheduling | 8 Notifee tasks registered |
| TC-02 | Background fire with app closed | Anchor fires via notification |
| TC-03 | Recovery scan on launch | Overdue anchors fire within grace window |
| TC-04 | Overdue anchor drop | >15 min overdue → dropped, logged |
| TC-05 | Pending anchors re-registered | After crash, anchors re-registered |
| TC-06 | Late fire warning | >60s delay → warning log entry |

---

### P4 — Mobile Features

#### 4.1 Location Awareness
**Priority:** P3  
**Files:** `src/lib/location_service.py`

**Spec Reference:** Section 8

**Tasks:**
- [ ] Single location check at departure anchor only
- [ ] 500m geofence comparison
- [ ] Immediate critical tier if at origin
- [ ] Location permission request on first use

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | User still at origin | Critical tier fires immediately |
| TC-02 | User already left | Normal chain proceeds |
| TC-03 | Location permission request | Requested at first location-aware reminder |
| TC-04 | Location permission denied | Reminder created without escalation, note shown |
| TC-05 | Single location check only | Only 1 API call per reminder |

---

#### 4.2 Calendar Integration
**Priority:** P3  
**Files:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/eventkit_adapter.py`, `src/lib/adapters/google_calendar_adapter.py`

**Spec Reference:** Section 7

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] Apple Calendar adapter placeholder (EventKit)
- [ ] Google Calendar adapter placeholder
- [ ] Suggestion card generation
- [ ] Recurring event handling

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Apple Calendar event suggestion | Suggestion card appears |
| TC-02 | Google Calendar event suggestion | Suggestion card appears |
| TC-03 | Suggestion → reminder creation | countdown_event reminder created |
| TC-04 | Permission denial handling | Explanation banner with settings link |
| TC-05 | Sync failure graceful degradation | Manual reminders still work |
| TC-06 | Recurring event handling | Reminder for each occurrence |

---

#### 4.3 Snooze & Dismissal
**Priority:** P3  
**Files:** `src/lib/snooze_service.py`, `src/lib/dismissal_service.py`

**Spec Reference:** Section 9

**Tasks:**
- [ ] Tap snooze (1 min default)
- [ ] Custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Swipe-to-dismiss feedback prompt
- [ ] TTS snooze confirmation
- [ ] Snooze persistence across app restarts

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Tap snooze | Current anchor snoozed 1 min, TTS confirms |
| TC-02 | Custom snooze | Picker appears, anchors shifted |
| TC-03 | Chain re-computation after snooze | Anchors re-centered around now |
| TC-04 | Dismissal feedback — timing correct | No adjustment made |
| TC-05 | Dismissal feedback — left too late | drive_duration +2 min |
| TC-06 | Snooze persistence after restart | Snooze offset retained |

---

### P5 — Stats & Feedback

#### 5.1 Complete History & Stats
**Priority:** P3  
**Files:** `src/lib/stats_service.py`, `src/lib/feedback_loop.py`

**Spec Reference:** Section 11

**Tasks:**
- [ ] Hit rate calculation (trailing 7 days)
- [ ] "Common miss window" identification
- [ ] Streak counter (increment on hit, reset on miss)
- [ ] Drive duration adjustment (cap: +15 min)
- [ ] 90-day retention with archive

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Hit rate calculation | 4 hits, 1 miss = 80% |
| TC-02 | Feedback loop — drive duration | +2 min per late feedback |
| TC-03 | Feedback loop cap | Max +15 min |
| TC-04 | Common miss window | Returns most missed tier |
| TC-05 | Streak increment on hit | Streak +1 |
| TC-06 | Streak reset on miss | Streak = 0 |

---

### P6 — Sound Library

#### 6.1 Sound Library
**Priority:** P4  
**Files:** `src/lib/sound_library.py`, `src/lib/sound_importer.py`

**Spec Reference:** Section 12

**Tasks:**
- [ ] Built-in sounds (5 per category: Commute, Routine, Errand)
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Per-reminder sound selection
- [ ] Corrupted sound fallback

**Test Scenarios (from spec):**
| ID | Scenario | Expected |
|----|----------|----------|
| TC-01 | Built-in sound playback | No network access required |
| TC-02 | Custom sound import | File appears in picker |
| TC-03 | Custom sound playback | Custom sound plays under TTS |
| TC-04 | Corrupted sound fallback | Category default plays, error logged |
| TC-05 | Sound persistence on edit | Sound selection retained |

---

## Otto Harness Tests (P0)

Per spec Section 14, the test suite must cover:

### Unit Tests
- [ ] Chain engine determinism (TC-06)
- [ ] Parser fixtures (TC-01 to TC-07 from §3)
- [ ] TTS adapter mock (TC-05 from §4)
- [ ] LLM adapter mock (TC-07 from §3)
- [ ] Keyword extraction (TC-04 from §3)
- [ ] Schema validation (TC-01 to TC-05 from §13)
- [ ] Database operations (cascade, FK enforcement)

### Integration Tests
- [ ] Parse → chain → TTS → persist
- [ ] Anchor firing (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment applied)

### E2E Tests (future - Detox)
- [ ] Quick Add flow
- [ ] Reminder confirmation
- [ ] Anchor firing sequence
- [ ] Snooze interaction
- [ ] Dismissal feedback
- [ ] Settings navigation
- [ ] Sound library browsing

---

## Dependencies Map

```
harness/scenario_harness.py (P0) ───────────────────────┐
                                                        │
src/lib/database.py (P1) ──────────────────────────────┤
    │                                                  │
    ▼                                                  │
src/lib/chain_engine.py (P1)                          │
    │                                                  │
    ├──────────────────────────────────────────┐       │
    ▼                                          ▼       │
src/lib/adapters/llm_adapter.py (P2)    src/lib/voice_personalities.py (P2)
    │                                          │       │
    ├─────────────────────┐                    │       │
    ▼                     ▼                    │       │
src/lib/adapters/tts_adapter.py (P2)            │       │
    │                                          │       │
    ▼                                          ▼       │
src/lib/notification_service.py (P3)  src/lib/stats_service.py (P3)
    │                                          │       │
    └─────────────────────┬───────────────────┘       │
                          ▼                           ▼
                  All tests pass ◄─────────────────────┘
```

---

## Quick Wins (First Iteration)

For Otto's first few iterations:

1. **Create `harness/scenario_harness.py`** — Otto cannot run without this
2. **Complete database schema** — Low risk, enables proper tests
3. **Add `get_next_unfired_anchor()`** — Simple function, unlocks recovery
4. **Expand voice message templates** — 3 variations each (120 messages)
5. **Add "common miss window" to stats** — Simple SQL aggregation

---

## Out of Scope (Per Spec)

- Password reset / account management (v1: local-only)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min")
- Multi-device sync (future consideration)
- Bluetooth audio routing preference
- Database encryption (future consideration)
- Full-text search on destinations

---

*Last Updated: 2026-04-08*
