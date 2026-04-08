# URGENT Alarm - Implementation Plan

> **Generated for Otto Loop Integration** — Focus on harness and critical gaps first.

## Analysis Summary

### Specification Files Analyzed
- `specs/urgent-voice-alarm-app-2026-04-08.md` — Product overview & user stories
- `specs/urgent-voice-alarm-app-2026-04-08.spec.md` — Full technical specification (14 sections)

### Current Codebase State

| Path | Status | Notes |
|------|--------|-------|
| `src/test_server.py` | ⚠️ Proof-of-concept | HTTP server with partial logic (~400 lines) |
| `harness/` | ❌ Empty | **Must be created** — Otto requires this |
| `src/lib/` | ❌ Missing | **Must be created** — structured library code |
| `specs/*.md` | ✅ Complete | Full spec with 14 sections |

### What's Implemented (in `test_server.py`)

✅ **Chain Engine** — `compute_escalation_chain()`: partial, handles ≥25 min and ≤5 min, missing 10-24 min compression
✅ **Parser** — `parse_reminder_natural()`: keyword fallback only, no LLM interface
✅ **Voice Messages** — `VOICE_PERSONALITIES`: 1 template per tier per personality (spec requires 3 min)
✅ **Hit Rate** — `calculate_hit_rate()`: basic SQL aggregation
✅ **HTTP Endpoints** — REST endpoints for testing

### Critical Gaps (by Spec Section)

| # | Section | Gap Severity | Gap Details |
|---|---------|--------------|-------------|
| 2 | Escalation Chain Engine | 🟡 Medium | Missing `get_next_unfired_anchor()`, 20-24 min buffer compression |
| 3 | Reminder Parsing | 🔴 High | No LLM adapter interface, no mock, no confirmation flow |
| 4 | Voice & TTS Generation | ❌ Missing | No ElevenLabs adapter, no TTS caching, no clip storage |
| 5 | Notification Behavior | ❌ Missing | No DND/quiet hours, no tier escalation sounds, no chain serialization |
| 6 | Background Scheduling | ❌ Missing | No Notifee/BGTaskScheduler, no recovery scan |
| 7 | Calendar Integration | ❌ Missing | No EventKit/Google Calendar |
| 8 | Location Awareness | ❌ Missing | No CoreLocation/FusedLocationProvider |
| 9 | Snooze & Dismissal | ❌ Missing | No snooze, no chain recompute, no feedback prompt |
| 10 | Voice Personality | 🟡 Medium | Only 1 template/tier (spec: 3 min variations) |
| 11 | History & Stats | 🟡 Medium | Missing common miss window, streak incomplete |
| 12 | Sound Library | ❌ Missing | No categories, no import |
| 13 | Data Persistence | 🟡 Medium | Schema incomplete (12+ columns missing) |
| **—** | **Otto Harness** | 🔴 **Critical** | **`harness/` is empty — Otto cannot run** |

---

## Otto Loop Priority

The Otto harness must exist and pass before anything else. This is the first priority.

### Otto Harness Structure (Must Create)

```
harness/
├── scenario_harness.py      # Main executable (sudo required)
├── conftest.py             # Pytest fixtures
├── test_chain_engine.py    # Unit tests
├── test_parser.py         # Unit tests
├── test_voice.py          # Voice message tests
├── test_database.py      # Schema tests
└── test_integration.py   # Full flow tests
```

---

## Implementation Tasks (Otto-First Priority)

### P0 — Otto Harness (Must Be Created First)

#### 1.1 Create Scenario Harness
**Priority:** P0 — **Otto cannot run without this**
**Files:** `harness/scenario_harness.py`

**Spec Reference:** Otto loop integration

**Tasks:**
- [ ] Create `harness/scenario_harness.py` executable
- [ ] Read scenarios from `/var/otto-scenarios/{project}/`
- [ ] Run pytest on `harness/` directory
- [ ] Write `{"pass": true}` or `{"pass": false}` to `/tmp/ralph-scenario-result.json`
- [ ] Support `--project` flag
- [ ] Support `--verbose` flag
- [ ] Log output for debugging

**Requirements:**
```bash
sudo python3 harness/scenario_harness.py --project otto-matic
```

**Acceptance Criteria:**
- [ ] Harness executes without sudo errors
- [ ] Harness runs pytest and captures results
- [ ] Results written to `/tmp/ralph-scenario-result.json`

---

### P1 — Foundation (Blocks Tests)

#### 1.2 Complete Data Persistence Layer
**Priority:** P1
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

**Spec Reference:** Section 13 (Data Persistence)

**Schema Gaps (vs. spec):**

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
destination_adjustments (...)
```

**Tasks:**
- [ ] Implement sequential migration system (v1 → v2 → ... → current)
- [ ] Add all missing columns per spec schema
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] Add `Database.getInMemoryInstance()` for tests
- [ ] UUID v4 generation for all IDs
- [ ] Cascade delete for reminders → anchors

**Acceptance Tests:**
- [ ] Fresh DB starts at current schema version
- [ ] In-memory test DB works
- [ ] Cascade deletes work
- [ ] FK violations return errors

#### 1.3 Complete Escalation Chain Engine
**Priority:** P1
**Files:** `src/lib/chain_engine.py`

**Spec Reference:** Section 2 (Escalation Chain Engine)

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add compressed chain for **20-24 min buffer** (currently missing)
- [ ] Ensure determinism: same inputs = same outputs (set comparison)
- [ ] Complete validation: `arrival > departure + minimum_drive_time`
- [ ] Add `fire_count` tracking for retry logic

**Acceptance Tests (from spec):**
- [ ] TC-01: Full chain (≥25 min) → 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] TC-02: Compressed chain (10-24 min) → 4-5 anchors
- [ ] TC-03: Minimum chain (≤5 min) → 3 anchors
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism (set comparison)

---

### P2 — Core Services

#### 2.1 LLM Adapter Interface
**Priority:** P2
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_mock.py`

**Spec Reference:** Section 3 (Reminder Parsing & Creation)

**Tasks:**
- [ ] Define `ILanguageModelAdapter` abstract interface
- [ ] Implement `MockLLMAdapter` for tests (returns fixtures)
- [ ] Implement `KeywordFallbackAdapter` (regex-based, confidence < 1.0)
- [ ] Support formats: "X min drive", "in X minutes", "arrive at X"
- [ ] Parse all 4 reminder types

**Acceptance Tests:**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" → correct fields
- [ ] "dryer in 3 min" → simple_countdown type
- [ ] "meeting tomorrow 2pm" → tomorrow date resolved
- [ ] Failed parsing → keyword fallback with confidence < 1.0
- [ ] Unintelligible input → user-facing error

#### 2.2 TTS Adapter Interface
**Priority:** P2
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_mock.py`, `src/lib/tts_cache.py`

**Spec Reference:** Section 4 (Voice & TTS Generation)

**Tasks:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement `MockTTSAdapter` (writes silent file for tests)
- [ ] Implement TTS cache (`/tts_cache/{reminder_id}/{anchor_id}.mp3`)
- [ ] Cache invalidation on reminder delete
- [ ] Fallback to system notification on TTS failure

**Acceptance Tests:**
- [ ] Mock TTS writes file and returns path
- [ ] Reminder delete removes cached TTS files
- [ ] TTS fallback flag set on API failure

#### 2.3 Voice Personality Enhancement
**Priority:** P2
**Files:** `src/lib/voice_personalities.py`, `src/lib/message_generator.py`

**Spec Reference:** Section 10 (Voice Personality System)

**Current State:** 1 template per tier per personality

**Tasks:**
- [ ] Add minimum **3 message variations** per tier per personality (5 × 8 × 3 = 120 messages)
- [ ] Random selection or rotation
- [ ] Custom prompt support (max 200 chars)
- [ ] Personality immutability for existing reminders

**Acceptance Tests:**
- [ ] 3 distinct outputs for same personality + tier
- [ ] Custom prompt modifies tone

---

### P3 — Notifications & Scheduling

#### 3.1 Notification Behavior System
**Priority:** P2
**Files:** `src/lib/notification_service.py`

**Spec Reference:** Section 5 (Notification & Alarm Behavior)

**Tasks:**
- [ ] Urgency tier → notification sound mapping (gentle chime → alarm)
- [ ] DND detection and suppression logic
- [ ] Quiet hours (default: 10pm-7am)
- [ ] Overdue anchor handling (15-min rule)
- [ ] Chain overlap serialization queue
- [ ] T-0 alarm looping until user action

#### 3.2 Background Scheduling
**Priority:** P3
**Files:** `src/lib/background_scheduler.py`

**Spec Reference:** Section 6 (Background Scheduling & Reliability)

**Tasks:**
- [ ] Notifee integration placeholder (for future mobile)
- [ ] Recovery scan on app launch
- [ ] Re-register pending anchors on crash recovery
- [ ] Late fire warning (>60s delay)

---

### P4 — Mobile Features

#### 4.1 Location Awareness
**Priority:** P3
**Files:** `src/lib/location_service.py`

**Spec Reference:** Section 8 (Location Awareness)

**Tasks:**
- [ ] Single location check at departure anchor only
- [ ] 500m geofence comparison
- [ ] Immediate critical tier if at origin

#### 4.2 Calendar Integration
**Priority:** P3
**Files:** `src/lib/adapters/calendar_adapter.py`

**Spec Reference:** Section 7 (Calendar Integration)

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] Apple Calendar adapter placeholder
- [ ] Google Calendar adapter placeholder
- [ ] Suggestion card generation

#### 4.3 Snooze & Dismissal
**Priority:** P3
**Files:** `src/lib/snooze_service.py`, `src/lib/dismissal_service.py`

**Spec Reference:** Section 9 (Snooze & Dismissal Flow)

**Tasks:**
- [ ] Tap snooze (1 min default)
- [ ] Custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Swipe-to-dismiss feedback prompt
- [ ] TTS snooze confirmation

---

### P5 — Stats & Feedback

#### 5.1 Complete History & Stats
**Priority:** P3
**Files:** `src/lib/stats_service.py`, `src/lib/feedback_loop.py`

**Spec Reference:** Section 11 (History, Stats & Feedback Loop)

**Tasks:**
- [ ] Hit rate calculation
- [ ] "Common miss window" identification
- [ ] Streak counter (increment on hit, reset on miss)
- [ ] Drive duration adjustment (cap: +15 min)
- [ ] 90-day retention with archive

---

### P6 — Sound Library

#### 6.1 Sound Library
**Priority:** P4
**Files:** `src/lib/sound_library.py`, `src/lib/sound_importer.py`

**Spec Reference:** Section 12 (Sound Library)

**Tasks:**
- [ ] Built-in sounds (5 per category: Commute, Routine, Errand)
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Corrupted sound fallback

---

## Otto Harness Test Requirements

Per spec Section 14 (Definition of Done), the test suite must cover:

### Unit Tests
- [ ] Chain engine determinism
- [ ] Parser fixtures (all TC-* from Section 3)
- [ ] TTS adapter mock
- [ ] LLM adapter mock
- [ ] Keyword extraction
- [ ] Schema validation
- [ ] Database operations

### Integration Tests
- [ ] Parse → chain → TTS → persist
- [ ] Anchor firing (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment applied)

---

## Dependencies Map

```
harness/scenario_harness.py (P0) ─────────────────┐
                                                  │
src/lib/database.py (P1) ─────────────────────────┤
    │                                            │
    ▼                                            │
src/lib/chain_engine.py (P1)                     │
    │                                            │
    ├─────────────────────┐                      │
    ▼                     ▼                      │
src/lib/parser_service.py (P2)                   │
    │                     │                      │
    ▼                     ▼                      │
src/lib/adapters/llm_adapter.py (P2)              │
src/lib/adapters/tts_adapter.py (P2)             │
src/lib/notification_service.py (P3)             │
src/lib/stats_service.py (P3)                    │
    │                                            │
    └─────────────────────┐                     │
                          ▼                     ▼
                  All tests pass ←──────────────┘
```

---

## Quick Wins (First Iteration)

For Otto's first few iterations:

1. **Create `harness/scenario_harness.py`** — Otto cannot run without this
2. **Add missing schema columns** — Low risk, enables proper tests
3. **Add `get_next_unfired_anchor()`** — Simple function, unlocks recovery
4. **Expand voice message templates** — 3 variations each (120 messages)
5. **Add "common miss window" to stats** — Simple SQL aggregation

---

## Out of Scope (Per Spec)

- Password reset / account management (v1: local-only)
- Smart home integration
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Database encryption
- Full-text search on destinations

---

*Generated: 2026-04-08*
*Last Updated: 2026-04-08*
