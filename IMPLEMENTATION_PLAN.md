# URGENT Alarm — Implementation Plan

## Overview

This plan maps the specification (`specs/urgent-voice-alarm-app-2026-04-08.spec.md`) to actionable tasks, ordered by dependency. Last updated: 2026-04-08.

---

## Gap Analysis Summary

### ✅ Implemented (Partial)
| Component | Status | Notes |
|-----------|--------|-------|
| Chain engine | ⚠️ Buggy | Logic doesn't match spec TC-01/TC-02 |
| Keyword parser | ⚠️ Basic | Regex only, no LLM adapter |
| Voice message templates | ⚠️ Incomplete | 5 personalities, no variations, no custom prompt |
| Database schema | ⚠️ Incomplete | Missing 10+ fields, 3 tables |
| Hit rate calculation | ✅ Basic | Only hit rate, missing streaks, miss window |
| HTTP API endpoints | ✅ Complete | Ready for scenario harness |

### ❌ Not Implemented
| Component | Priority | Dependencies |
|-----------|----------|--------------|
| Scenario harness | Critical | None |
| LLM adapter interface | Critical | Chain engine, parser |
| TTS adapter + caching | Critical | Adapter interfaces |
| Background scheduler | Critical | Notifee integration |
| Notification behavior | Critical | DND, quiet hours, chain serialization |
| Snooze + dismissal | High | Chain engine |
| Feedback loop | Medium | History table |
| Calendar integration | Medium | Adapter interface |
| Location awareness | Medium | Adapter interface |
| Sound library | Low | Custom audio import |

---

## Phase 0: Foundation Fixes (Days 1-2)

### 0.1 Database Schema Completeness
**Priority:** Critical | **Spec:** Section 13

**Current Gap:** `init_db()` missing ~10 fields/tables per spec.

**Tasks:**
- [ ] Enhance `init_db()` with full schema:
  - `reminders`: add `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`
  - `anchors`: add `tts_fallback`, `snoozed_to`
  - `history`: add `actual_arrival`, `missed_reason`
  - `reminders`: rename `snoozed_to` (if needed)
- [ ] Add `schema_version` table for migration tracking
- [ ] Add `calendar_sync` table (apple/google sync state)
- [ ] Add `custom_sounds` table (imported audio files)
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] Add in-memory mode support (`?mode=memory`)

---

### 0.2 Chain Engine Fixes
**Priority:** Critical | **Spec:** Section 2.3

**Current Gap:** `compute_escalation_chain()` produces wrong anchor count for 15-min buffer.

**Spec anchor rules:**
| Buffer | Anchors | Start Tier | Timestamps |
|--------|---------|-----------|------------|
| ≥25 min | 8 | calm (T-30) | departure, T-25, T-20, T-15, T-10, T-5, T-1, T-0 |
| 20-24 min | 7 | casual (T-25) | T-25, T-20, T-15, T-10, T-5, T-1, T-0 |
| 15-19 min | 6 | pointed (T-20) | T-20, T-15, T-10, T-5, T-1, T-0 |
| 10-14 min | 5 | urgent (T-15) | T-15, T-10, T-5, T-1, T-0 |
| 5-9 min | 3 | firm (T-5) | T-5, T-1, T-0 |
| 1-4 min | 2 | critical (T-1) | T-1, T-0 |
| 0 min | 1 | alarm | T-0 |

**Tasks:**
- [ ] Rewrite `compute_escalation_chain()` to match spec table exactly
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Implement `shift_anchors(reminder_id, offset_minutes)` for snooze re-computation
- [ ] Add validation: reject if `departure_time <= now`
- [ ] Ensure deterministic output (same inputs = same anchors)

**Test Cases to Pass:**
- [ ] TC-01: 30 min buffer → 8 anchors (8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00)
- [ ] TC-02: 15 min buffer → 5 anchors (8:45, 8:50, 8:55, 8:59, 9:00)
- [ ] TC-03: 3 min buffer → 2 anchors (8:59, 9:00) per spec, not 3
- [ ] TC-04: drive_duration > time_to_arrival → 400 error
- [ ] TC-05: `get_next_unfired_anchor` returns earliest unfired
- [ ] TC-06: Chain determinism (identical inputs = identical outputs)

---

## Phase 1: Test Infrastructure (Days 2-3)

### 1.1 Scenario Harness
**Priority:** Critical | **Location:** `harness/scenario_harness.py`

**Existing Resources:**
- 15 YAML scenarios in `scenarios/` directory
- Scenario format with `trigger`, `env`, `assertions`

**Tasks:**
- [ ] Parse YAML scenario files from `/var/otto-scenarios/{project}/`
- [ ] Support variable interpolation `${variable}` from `env` block
- [ ] Implement assertion types:
  - `http_status` — verify response code + body fields
  - `db_record` — verify SQLite records via direct query
  - `llm_judge` — call LLM to evaluate output quality
- [ ] Report pass/fail per scenario with diff on failure
- [ ] Exit with non-zero code on any failure

**Command:** `sudo python3 harness/scenario_harness.py --project urgent-alarm`

---

### 1.2 Unit Test Suite
**Priority:** High | **Location:** `tests/`

**Tasks:**
- [ ] `tests/test_chain_engine.py` — Section 2.5 TCs (TC-01 through TC-06)
- [ ] `tests/test_parser.py` — Section 3.5 TCs (TC-01 through TC-07)
- [ ] `tests/test_voice_messages.py` — all 5 personalities × 8 tiers
- [ ] `tests/test_stats.py` — hit rate, streak, miss window calculations
- [ ] Use in-memory SQLite for test isolation

---

## Phase 2: Core Parsing (Days 3-5)

### 2.1 LLM Adapter Architecture
**Priority:** Critical | **Spec:** Section 3

**Tasks:**
- [ ] Create `src/lib/adapters/ilanguage_model.py`:
```python
class ILanguageModelAdapter(ABC):
    @abstractmethod
    def parse(self, text: str) -> ParsedReminder: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
```

- [ ] Create `src/lib/adapters/mock_llm.py`:
  - Configurable fixture responses
  - No network calls

- [ ] Create `src/lib/adapters/keyword_parser.py`:
  - Current `parse_reminder_natural()` logic
  - Fallback when LLM unavailable
  - Returns `confidence_score < 1.0`

---

### 2.2 LLM Adapter Implementations
**Priority:** High

**Tasks:**
- [ ] Create `src/lib/adapters/minimax_adapter.py`
- [ ] Create `src/lib/adapters/anthropic_adapter.py`
- [ ] Implement orchestrator: try LLM → fallback to keyword → error on failure

**Parser TCs:**
- [ ] TC-01: Full NL parse → destination, arrival_time, drive_duration
- [ ] TC-02: Simple countdown ("dryer in 3 min")
- [ ] TC-03: Tomorrow date resolution
- [ ] TC-04: LLM API failure → keyword fallback
- [ ] TC-05: Manual field correction (confirmation card)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

## Phase 3: Voice & TTS System (Days 5-8)

### 3.1 TTS Adapter Interface
**Priority:** Critical | **Spec:** Section 4

**Tasks:**
- [ ] Create `src/lib/adapters/itts_adapter.py`:
```python
class ITTSAdapter(ABC):
    @abstractmethod
    def generate(self, text: str, voice_id: str) -> str: ...  # file path
```

- [ ] Create `src/lib/adapters/mock_tts.py` — writes silent file to `/tmp/tts_cache/`
- [ ] Create `src/lib/adapters/elevenlabs_adapter.py` — real API integration

---

### 3.2 Voice Personality Enhancements
**Priority:** High | **Spec:** Section 10

**Tasks:**
- [ ] Expand each personality/tier to 3+ message templates
- [ ] Add random/round-robin message rotation
- [ ] Support custom prompt (max 200 chars) from user preferences
- [ ] Map personalities to ElevenLabs voice IDs

**Tiers to test:**
- [ ] TC-01: Coach produces motivational messages with "!"
- [ ] TC-02: No-nonsense produces brief, direct messages
- [ ] TC-03: Custom prompt modifies tone
- [ ] TC-04: Existing reminders retain original personality
- [ ] TC-05: Message variation (3 distinct phrasings)

---

### 3.3 TTS Cache Manager
**Priority:** High

**Tasks:**
- [ ] Create `src/lib/services/tts_cache.py`:
  - `cache_clip(reminder_id, anchor_id, audio_data) -> file_path`
  - `get_clip(reminder_id, anchor_id) -> file_path`
  - `invalidate_cache(reminder_id)` — on reminder delete
- [ ] Implement fallback: if TTS fails, mark `tts_fallback = TRUE`

---

## Phase 4: Scheduling & Notifications (Days 8-12)

### 4.1 Background Scheduler
**Priority:** Critical | **Spec:** Section 6

**Tasks:**
- [ ] Create `src/lib/adapters/ischeduler_adapter.py`:
```python
class ISchedulerAdapter(ABC):
    def schedule_anchor(self, anchor_id: str, timestamp: datetime) -> None: ...
    def cancel_anchor(self, anchor_id: str) -> None: ...
    def re_register_all_pending(self) -> None: ...
    def run_recovery_scan(self) -> List[str]: ...
```

- [ ] Create `src/lib/adapters/mock_scheduler.py` — in-memory for tests
- [ ] Create `src/lib/adapters/notifee_scheduler.py` — real implementation
- [ ] Implement recovery scan: fire anchors within 15-min grace window
- [ ] Drop anchors >15 min overdue with `missed_reason = "background_task_killed"`

**Background TCs:**
- [ ] Anchors scheduled in Notifee
- [ ] Background fire with app closed
- [ ] Recovery scan on launch
- [ ] Pending anchors re-registered

---

### 4.2 Notification Behavior
**Priority:** Critical | **Spec:** Section 5

**Tasks:**
- [ ] Create `src/lib/adapters/inotification_adapter.py`:
```python
class INotificationAdapter(ABC):
    def show(self, tier: UrgencyTier, content: NotificationContent) -> None: ...
    def play_sound(self, tier: UrgencyTier) -> None: ...
    def is_dnd_enabled(self) -> bool: ...
```

- [ ] Map tiers to sounds:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm

- [ ] Implement DND handling:
  - Early anchors during DND → silent notification
  - Final 5 min during DND → visual override + vibration

- [ ] Implement quiet hours:
  - Default: 10pm–7am (configurable)
  - Queue anchors during quiet hours
  - Drop anchors >15 min overdue

- [ ] Implement chain overlap serialization:
  - Lock during chain escalation
  - Queue incoming anchors

- [ ] T-0 alarm loops until user action (no auto-dismiss)

**Notification TCs:**
- [ ] DND — early anchor suppressed
- [ ] DND — final 5-min override
- [ ] Quiet hours suppression
- [ ] Overdue anchor drop (15 min)
- [ ] Chain overlap serialization
- [ ] T-0 loops until action

---

## Phase 5: Snooze & Dismissal (Days 12-14)

### 5.1 Snooze Implementation
**Priority:** High | **Spec:** Section 9

**Tasks:**
- [ ] Tap snooze → 1 minute delay
- [ ] Tap-and-hold → custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement `recompute_chain_after_snooze(reminder_id, delay_minutes)`:
  - Shift all unfired anchor timestamps by `delay_minutes`
  - Update `snoozed_to` column
  - Re-register with scheduler

- [ ] TTS confirmation: "Okay, snoozed {X} minutes."

**Snooze TCs:**
- [ ] TC-01: Tap snooze (1 min)
- [ ] TC-02: Custom snooze picker (5 min)
- [ ] TC-03: Chain re-computation shifts remaining anchors
- [ ] TC-06: Snooze persistence after restart

---

### 5.2 Dismissal & Feedback
**Priority:** High | **Spec:** Section 9.3

**Tasks:**
- [ ] Swipe-to-dismiss → feedback prompt
- [ ] Feedback prompt: "You missed {destination} — was the timing right?"
  - Yes → store `outcome = 'hit'`
  - No → follow-up: "Left too early" / "Left too late" / "Other"
- [ ] Store feedback in history table

---

## Phase 6: History & Feedback Loop (Days 14-17)

### 6.1 Stats Service
**Priority:** Medium | **Spec:** Section 11

**Tasks:**
- [ ] Hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` (trailing 7 days)
- [ ] Streak counter: increment on `outcome='hit'` for recurring, reset on `'miss'`
- [ ] Common miss window: most-frequently-missed urgency tier

**Stats TCs:**
- [ ] TC-01: Hit rate calculation (80% = 4/5)
- [ ] TC-04: Common miss window identification
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table alone

---

### 6.2 Feedback Loop
**Priority:** Medium | **Spec:** Section 11.3

**Tasks:**
- [ ] Track adjustments in `destination_adjustments` table
- [ ] On "left_too_late" feedback: `adjustment_minutes += 2`
- [ ] Cap at +15 minutes maximum
- [ ] Apply adjustment when creating reminder to same destination

**Feedback TCs:**
- [ ] TC-02: 3 late feedbacks → +6 min on next reminder
- [ ] TC-03: 10 late feedbacks → +15 min cap

---

## Phase 7: Integrations (Days 17-22)

### 7.1 Calendar Integration
**Priority:** Medium | **Spec:** Section 7

**Tasks:**
- [ ] Create `src/lib/adapters/icalendar_adapter.py`
- [ ] Create `src/lib/adapters/apple_calendar_adapter.py` (EventKit)
- [ ] Create `src/lib/adapters/google_calendar_adapter.py`
- [ ] Create `src/lib/adapters/mock_calendar_adapter.py`
- [ ] Sync on: app launch, every 15 min, background refresh
- [ ] Generate suggestion cards for events with locations
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully

**Calendar TCs:**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

### 7.2 Location Awareness
**Priority:** Medium | **Spec:** Section 8

**Tasks:**
- [ ] Create `src/lib/adapters/ilocation_adapter.py`
- [ ] Create `src/lib/adapters/core_location_adapter.py` (iOS)
- [ ] Create `src/lib/adapters/mock_location_adapter.py`
- [ ] Store origin at reminder creation
- [ ] Single location check at departure anchor only
- [ ] 500m geofence radius
- [ ] If at origin: fire firm/critical tier immediately

**Location TCs:**
- [ ] TC-01: User at origin → immediate escalation
- [ ] TC-02: User left → normal chain proceeds
- [ ] TC-03: Permission request at creation
- [ ] TC-04: Permission denied → reminder without location
- [ ] TC-05: Single location check only

---

### 7.3 Sound Library
**Priority:** Low | **Spec:** Section 12

**Tasks:**
- [ ] Bundle built-in sounds per category (5 sounds × 3 categories)
- [ ] Custom import: MP3, WAV, M4A, max 30 sec
- [ ] Corrupted sound → fallback to category default
- [ ] Store custom sounds in `custom_sounds` table

**Sound TCs:**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Dependency Graph

```
Phase 0: Schema + Chain Fixes
    │
    ├─► Phase 1: Test Infrastructure
    │       │
    │       └─► Phase 2: Core Parsing
    │               │
    │               ├─► Phase 3: Voice & TTS
    │               │
    │               ├─► Phase 4: Scheduling + Notifications
    │               │       │
    │               │       └─► Phase 5: Snooze + Dismissal
    │               │
    │               └─► Phase 7: Integrations (Calendar, Location)
    │
    └─► Phase 6: History + Feedback Loop
```

---

## Adapter Interface Summary

| Interface | Location | Key Methods |
|-----------|----------|-------------|
| `ILanguageModelAdapter` | `src/lib/adapters/` | `parse(text) -> ParsedReminder` |
| `ITTSAdapter` | `src/lib/adapters/` | `generate(text, voice_id) -> path` |
| `ICalendarAdapter` | `src/lib/adapters/` | `sync_events() -> List[Event]` |
| `ILocationAdapter` | `src/lib/adapters/` | `check_at_origin(lat, lng) -> bool` |
| `INotificationAdapter` | `src/lib/adapters/` | `show(tier, content)`, `play_sound(tier)` |
| `ISchedulerAdapter` | `src/lib/adapters/` | `schedule_anchor()`, `re_register_all_pending()` |
| `IAudioPlayerAdapter` | `src/lib/adapters/` | `play(path)`, `loop(path)`, `stop()` |

---

## Out of Scope (v1)

- Password/auth (local-only data)
- Smart home integration
- Voice reply ("snooze 5 min")
- Multi-device sync
- Bluetooth audio routing
- Per-reminder personality override
- Voice recording import
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
