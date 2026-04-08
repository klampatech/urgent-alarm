# URGENT Alarm - Implementation Plan

## Analysis Summary

### Specification Files Analyzed
- `specs/urgent-voice-alarm-app-2026-04-08.md` - Product overview & user stories
- `specs/urgent-voice-alarm-app-2026-04-08.spec.md` - Full technical specification (14 sections, 1000+ lines)

### Current State: `src/test_server.py`
A **proof-of-concept Python test server** (~400 lines) that exposes core app logic via HTTP endpoints for scenario testing. This is NOT the mobile app - it's a test harness target.

**✅ Implemented (in test_server.py):**
- Basic database schema (partial - missing 10+ columns from spec)
- Escalation chain engine (`compute_escalation_chain`) - partial
- Chain validation (`validate_chain`) - partial
- Natural language parsing (`parse_reminder_natural`) - keyword fallback only
- Voice personality message templates (`VOICE_PERSONALITIES`) - partial (1 template per tier)
- Hit rate calculation (`calculate_hit_rate`)
- HTTP endpoints for all major operations

**❌ Gaps by Spec Section:**

| # | Section | Status | Critical Gaps |
|---|---------|--------|---------------|
| 2 | Escalation Chain Engine | Partial | Missing `get_next_unfired_anchor()`, incomplete validation |
| 3 | Reminder Parsing & Creation | Partial | No LLM adapter interface, no mock, no confirmation flow |
| 4 | Voice & TTS Generation | Missing | No ElevenLabs adapter, no TTS caching, no clip storage |
| 5 | Notification & Alarm Behavior | Missing | No DND/quiet hours, no tier escalation, no chain serialization |
| 6 | Background Scheduling | Missing | No Notifee, no BGTaskScheduler, no recovery scan |
| 7 | Calendar Integration | Missing | No EventKit/Google Calendar, no suggestion cards |
| 8 | Location Awareness | Missing | No CoreLocation/FusedLocationProvider |
| 9 | Snooze & Dismissal Flow | Missing | No snooze, no chain recompute, no feedback prompt |
| 10 | Voice Personality System | Partial | Only 1 template per tier (spec requires 3 min) |
| 11 | History, Stats & Feedback | Partial | Missing "common miss window", streak incomplete |
| 12 | Sound Library | Missing | No sound categories, no custom import |
| 13 | Data Persistence | Partial | Schema incomplete (missing 12+ columns from spec) |

---

## Implementation Tasks (Prioritized)

### Phase 1: Foundation (Blocks Everything)

#### 1.1 Complete Data Persistence Layer
**Priority:** P0
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

**Spec Reference:** Section 13 (Data Persistence)

**Current State:**
```sql
-- EXISTING (partial):
reminders: id, destination, arrival_time, drive_duration, reminder_type, 
           voice_personality, sound_category, selected_sound, status, created_at, updated_at

-- REQUIRED (missing):
reminders: origin_lat, origin_lng, origin_address, custom_sound_path, 
           calendar_event_id
anchors: tts_fallback, snoozed_to
history: actual_arrival, missed_reason
calendar_sync: NEW TABLE
custom_sounds: NEW TABLE
```

**Tasks:**
- [ ] Implement sequential migration system (v1 → v2 → v3...)
- [ ] Add all missing columns per spec schema
- [ ] Enable foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Add `Database.getInMemoryInstance()` for tests
- [ ] UUID v4 generation for all IDs
- [ ] Cascade delete for reminders → anchors

**Acceptance Tests:**
- Fresh DB starts at current schema version
- In-memory test DB works
- Cascade deletes work
- FK violations return errors

#### 1.2 Complete Escalation Chain Engine
**Priority:** P0
**Files:** `src/lib/chain_engine.py`

**Spec Reference:** Section 2 (Escalation Chain Engine)

**Current State:** `compute_escalation_chain()` exists but incomplete

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add compressed chain for 20-24 min buffer (currently only 10-24)
- [ ] Ensure determinism: same inputs = same outputs
- [ ] Complete validation: `arrival > departure + minimum_drive_time`
- [ ] Add `fire_count` retry logic

**Acceptance Tests (from spec):**
- TC-01: Full chain (≥25 min) → 8 anchors
- TC-02: Compressed chain (15-24 min) → 5 anchors
- TC-03: Minimum chain (≤5 min) → 3 anchors
- TC-04: Invalid chain rejection
- TC-05: Next unfired anchor recovery
- TC-06: Chain determinism

---

### Phase 2: Core Services

#### 2.1 LLM Adapter Interface & Implementations
**Priority:** P1
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_minimax.py`, 
          `src/lib/adapters/llm_anthropic.py`, `src/lib/adapters/llm_mock.py`,
          `src/lib/adapters/llm_keyword_fallback.py`

**Spec Reference:** Section 3 (Reminder Parsing & Creation)

**Tasks:**
- [ ] Define `ILanguageModelAdapter` abstract interface
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter`
- [ ] Implement `MockLLMAdapter` for tests (returns fixtures)
- [ ] Implement `KeywordFallbackAdapter` (regex-based, confidence < 1.0)
- [ ] Connect parser confirmation flow

**Interface Requirements:**
```python
class ILanguageModelAdapter:
    async def parse(input_text: str) -> ParsedReminder
    def get_confidence() -> float
```

**Acceptance Tests:**
- TC-01: Full natural language parse
- TC-02: Simple countdown parse
- TC-03: Tomorrow date resolution
- TC-04: LLM API failure → keyword fallback
- TC-05: Manual field correction
- TC-06: Unintelligible input rejection
- TC-07: Mock adapter in tests

#### 2.2 TTS Adapter Interface & Implementations
**Priority:** P1
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_elevenlabs.py`,
          `src/lib/adapters/tts_mock.py`, `src/lib/tts_cache.py`

**Spec Reference:** Section 4 (Voice & TTS Generation)

**Tasks:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement `MockTTSAdapter` for tests
- [ ] Implement TTS cache (`/tts_cache/{reminder_id}/{anchor_id}.mp3`)
- [ ] Cache invalidation on reminder delete
- [ ] Fallback to system notification on TTS failure
- [ ] Voice ID mapping per personality (coach, assistant, best_friend, no_nonsense, calm)

**Acceptance Tests:**
- TC-01: TTS clip generation at creation (8 MP3s)
- TC-02: Anchor fires from cache (no network)
- TC-03: TTS fallback on API failure
- TC-04: TTS cache cleanup on delete
- TC-05: Mock TTS in tests

#### 2.3 Reminder Creation Workflow
**Priority:** P1
**Files:** `src/lib/reminder_service.py`, `src/lib/parser_service.py`

**Spec Reference:** Section 3.2 (User Journey)

**Tasks:**
- [ ] `create_reminder()` flow: parse → validate → compute chain → persist
- [ ] Confirmation card data structure
- [ ] Manual field correction handling
- [ ] Support all 4 reminder types:
  - countdown_event
  - simple_countdown
  - morning_routine
  - standing_recurring
- [ ] Destination adjustment from feedback loop

---

### Phase 3: Notifications & Scheduling

#### 3.1 Notification Behavior System
**Priority:** P1
**Files:** `src/lib/notification_service.py`

**Spec Reference:** Section 5 (Notification & Alarm Behavior)

**Tasks:**
- [ ] Urgency tier → notification sound mapping:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm
- [ ] DND detection and suppression logic
- [ ] Quiet hours configuration (default: 10pm-7am)
- [ ] Overdue anchor handling (15-min rule)
- [ ] Chain overlap serialization queue
- [ ] T-0 alarm looping until user action
- [ ] Display: destination, time remaining, voice personality icon

**Acceptance Tests:**
- TC-01: DND suppresses early anchors
- TC-02: DND final 5-min fires with vibration
- TC-03: Quiet hours suppression
- TC-04: Overdue anchor drop (15-min rule)
- TC-05: Chain overlap serialization
- TC-06: T-0 loops until action

#### 3.2 Background Scheduling
**Priority:** P1
**Files:** `src/lib/background_scheduler.py`

**Spec Reference:** Section 6 (Background Scheduling & Reliability)

**Tasks:**
- [ ] Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- [ ] Register each anchor as individual background task
- [ ] Recovery scan on app launch
- [ ] Re-register pending anchors on crash recovery
- [ ] Late fire warning (>60s delay)
- [ ] Grace window handling (15-min)

**Acceptance Tests:**
- TC-01: Anchor scheduling with Notifee
- TC-02: Background fire with app closed
- TC-03: Recovery scan on launch
- TC-04: Overdue anchor drop
- TC-05: Pending anchors re-registered on crash
- TC-06: Late fire warning

---

### Phase 4: Mobile Features

#### 4.1 Location Awareness
**Priority:** P2
**Files:** `src/lib/location_service.py`, `src/lib/geofence.py`

**Spec Reference:** Section 8 (Location Awareness)

**Tasks:**
- [ ] Single location check at departure anchor ONLY
- [ ] Origin resolution (user address OR device location at creation)
- [ ] 500m geofence radius comparison
- [ ] Immediate critical tier fire if at origin
- [ ] Permission request on first location-aware reminder
- [ ] NO location history retention

**Acceptance Tests:**
- TC-01: User still at origin → critical tier fires
- TC-02: User already left → normal chain proceeds
- TC-03: Location permission request timing
- TC-04: Location permission denied handling
- TC-05: Single location check only

#### 4.2 Calendar Integration
**Priority:** P2
**Files:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/calendar_eventkit.py`,
          `src/lib/adapters/calendar_google.py`, `src/lib/calendar_service.py`

**Spec Reference:** Section 7 (Calendar Integration)

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] Apple Calendar via EventKit (iOS)
- [ ] Google Calendar API integration
- [ ] Suggestion cards for events with locations
- [ ] Recurring event handling
- [ ] Permission denial handling with explanation banner
- [ ] Sync on launch + every 15 minutes

**Acceptance Tests:**
- TC-01: Apple Calendar event suggestion
- TC-02: Google Calendar event suggestion
- TC-03: Suggestion → reminder creation
- TC-04: Permission denial handling
- TC-05: Sync failure graceful degradation
- TC-06: Recurring event handling

#### 4.3 Snooze & Dismissal Flow
**Priority:** P2
**Files:** `src/lib/snooze_service.py`, `src/lib/dismissal_service.py`

**Spec Reference:** Section 9 (Snooze & Dismissal Flow)

**Tasks:**
- [ ] Tap snooze (1 min default)
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Re-registration with Notifee
- [ ] Swipe-to-dismiss feedback prompt
- [ ] Feedback types: timing_right, left_too_early, left_too_late, other
- [ ] TTS snooze confirmation

**Acceptance Tests:**
- TC-01: Tap snooze
- TC-02: Custom snooze
- TC-03: Chain re-computation after snooze
- TC-04: Dismissal feedback — timing correct
- TC-05: Dismissal feedback — timing off
- TC-06: Snooze persistence after restart

---

### Phase 5: User Experience

#### 5.1 Voice Personality System Enhancement
**Priority:** P2
**Files:** `src/lib/voice_personalities.py`, `src/lib/message_generator.py`

**Spec Reference:** Section 10 (Voice Personality System)

**Current State:** 1 template per tier per personality

**Tasks:**
- [ ] Add minimum 3 message variations per tier per personality (5 personalities × 8 tiers × 3 = 120 messages)
- [ ] Random selection or rotation
- [ ] Custom prompt support (max 200 chars)
- [ ] Per-reminder personality persistence
- [ ] Personality immutability for existing reminders

**Acceptance Tests:**
- TC-01: Coach personality messages
- TC-02: No-nonsense personality messages
- TC-03: Custom personality
- TC-04: Personality immutability for existing reminders
- TC-05: Message variation (≥3 variations produce distinct outputs)

#### 5.2 Sound Library
**Priority:** P3
**Files:** `src/lib/sound_library.py`, `src/lib/sound_importer.py`

**Spec Reference:** Section 12 (Sound Library)

**Tasks:**
- [ ] Built-in sounds (5 per category):
  - Commute: 5 sounds
  - Routine: 5 sounds
  - Errand: 5 sounds
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Sound transcoding/normalization
- [ ] Per-reminder sound selection
- [ ] Corrupted sound fallback

**Acceptance Tests:**
- TC-01: Built-in sound playback
- TC-02: Custom sound import
- TC-03: Custom sound playback
- TC-04: Corrupted sound fallback
- TC-05: Sound persistence on edit

---

### Phase 6: Stats & Feedback

#### 6.1 Complete History & Stats System
**Priority:** P2
**Files:** `src/lib/stats_service.py`, `src/lib/feedback_loop.py`

**Spec Reference:** Section 11 (History, Stats & Feedback Loop)

**Current State:** Basic `calculate_hit_rate()`

**Tasks:**
- [ ] Hit rate calculation: `count(hit) / count(outcome != 'pending') * 100`
- [ ] "Common miss window" identification
- [ ] Complete streak counter (increment on hit, reset on miss)
- [ ] Drive duration adjustment with cap (+15 min max)
- [ ] 90-day retention with archive

**Acceptance Tests:**
- TC-01: Hit rate calculation
- TC-02: Feedback loop — drive duration adjustment
- TC-03: Feedback loop cap (+15 min max)
- TC-04: Common miss window identification
- TC-05: Streak increment on hit
- TC-06: Streak reset on miss
- TC-07: Stats derived from history table

---

### Phase 7: Testing & Harness

#### 7.1 Scenario Harness
**Priority:** P1
**Files:** `harness/scenario_harness.py`, `harness/test_*.py`

**Spec Reference:** Otto loop integration

**Tasks:**
- [ ] Implement `scenario_harness.py` executable
- [ ] Run hidden scenario tests from `/var/otto-scenarios/`
- [ ] Write `{"pass": true}` or `{"pass": false}` to `/tmp/ralph-scenario-result.json`
- [ ] Unit tests for all components
- [ ] Integration tests for full flows

**Test Coverage Required:**
- All TC-* scenarios from spec sections 2-13
- Unit tests: chain engine, parser, TTS, LLM, schema
- Integration tests: parse → chain → TTS → persist, anchor firing, snooze recovery
- E2E tests: Quick Add, reminder confirmation, anchor firing, snooze, dismissal

#### 7.2 Test Suite for Core Components
**Priority:** P1
**Files:** `harness/test_chain_engine.py`, `harness/test_parser.py`, 
          `harness/test_voice.py`, `harness/test_database.py`

**Tasks:**
- [ ] Chain engine determinism tests
- [ ] Parser fixture tests (all spec TCs)
- [ ] TTS adapter mock tests
- [ ] LLM adapter mock tests
- [ ] Keyword extraction tests
- [ ] Schema validation tests
- [ ] Database operation tests

---

## Dependencies Map

```
┌─────────────────────────────────────────────────────────────┐
│ Database Schema (1.1) ─── P0                                  │
│    └─────────────────────────────────────────────────────────┤
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ Chain Engine    │     │ Stats Service   │               │
│  │   (1.2) ─ P0    │     │   (6.1)         │               │
│  └────────┬────────┘     └────────┬────────┘               │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌─────────────────────────────────────────────────┐        │
│  │         Reminder Service (2.3)                  │        │
│  │    ┌────────────────┐  ┌────────────────┐       │        │
│  │    │ LLM Adapter   │  │ TTS Adapter    │       │        │
│  │    │   (2.1)       │  │   (2.2)        │       │        │
│  │    └────────────────┘  └────────────────┘       │        │
│  └─────────────────────────────────────────────────┘        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ Notification    │  │ Background      │  │ Snooze     │ │
│  │   (3.1)         │  │   Scheduler     │  │   (4.3)    │ │
│  └────────┬────────┘  │   (3.2)         │  └─────┬──────┘ │
│           │           └────────┬────────┘        │        │
│           │                    │                 │        │
│           ▼                    ▼                 ▼        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 Location (4.1) + Calendar (4.2)        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Task Summary by Priority

### P0 (Critical Path - Must Implement First)
1. **1.1 Complete Data Persistence Layer** - Schema incomplete, blocks all work
2. **1.2 Complete Escalation Chain Engine** - Core logic incomplete

### P1 (Core Features - MVP Required)
3. **2.1 LLM Adapter Interface** - Parser required for reminder creation
4. **2.2 TTS Adapter Interface** - Voice is differentiating feature
5. **2.3 Reminder Creation Workflow** - User-facing flow
6. **3.1 Notification Behavior System** - How users receive nudges
7. **3.2 Background Scheduling** - Reminders must fire reliably
8. **7.1 Scenario Harness** - Otto loop integration

### P2 (Important Features)
9. **4.1 Location Awareness** - Key differentiator (departure detection)
10. **4.2 Calendar Integration** - Auto-suggestions
11. **4.3 Snooze & Dismissal Flow** - User interaction
12. **5.1 Voice Personality Enhancement** - Message variations (120+ messages)
13. **6.1 Complete Stats & Feedback** - Learning system

### P3 (Nice to Have)
14. **5.2 Sound Library** - Custom audio import

### P4 (Continuous)
15. **7.2 Test Suite** - All TC-* scenarios from spec

---

## Estimated Effort

| Phase | Tasks | Complexity | Notes |
|-------|-------|------------|-------|
| Phase 1 | 2 | High | Foundation - blocks everything |
| Phase 2 | 3 | High | Parser + adapters |
| Phase 3 | 2 | Medium | Notifications + scheduling |
| Phase 4 | 3 | High | Mobile-specific |
| Phase 5 | 2 | Medium | UX enhancements |
| Phase 6 | 1 | Low | Stats system |
| Phase 7 | 2 | Medium | Testing |
| **Total** | **15** | - | - |

---

## Quick Wins (First Iteration)

For Otto loop's first few iterations, implement these quick wins:

1. **Add missing columns to database schema** - Low risk, high value
2. **Add `get_next_unfired_anchor()`** - Simple function, unlocks recovery
3. **Expand voice message templates to 3 variations each** - 120 messages needed
4. **Add "common miss window" to stats** - Simple SQL aggregation

---

## Out of Scope (Per Spec)

- Password reset / account management (v1: local-only)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Database encryption
- Full-text search on destinations

---

*Generated: 2026-04-08*
*Last Updated: 2026-04-08*
