# URGENT Alarm - Implementation Plan

## Analysis Summary

### Specification Files Analyzed
- `specs/urgent-voice-alarm-app-2026-04-08.md` - Product overview
- `specs/urgent-voice-alarm-app-2026-04-08.spec.md` - Full technical specification (14 sections)

### Current State: `src/test_server.py`
The current implementation is a **minimal proof-of-concept** that covers only the core validation needs:

**✅ Implemented:**
- Escalation Chain Engine (`compute_escalation_chain`, `validate_chain`)
- Reminder Parsing via keyword fallback (`parse_reminder_natural`)
- Voice Personality Message Templates (`VOICE_PERSONALITIES`, `generate_voice_message`)
- History & Stats (`calculate_hit_rate`, feedback loop with destination adjustments)
- Basic SQLite schema (partial - missing fields per spec)

**❌ Missing/Incomplete:**

| Section | Status | Gap |
|---------|--------|-----|
| 2. Escalation Chain Engine | Partial | Missing `get_next_unfired_anchor()`, incomplete validation |
| 3. Reminder Parsing & Creation | Partial | No LLM adapter, no mock interface, no confirmation flow |
| 4. Voice & TTS Generation | Missing | No ElevenLabs adapter, no TTS cache management |
| 5. Notification & Alarm Behavior | Missing | No notification tier escalation, DND/quiet hours, chain serialization |
| 6. Background Scheduling | Missing | No Notifee/BGTaskScheduler integration |
| 7. Calendar Integration | Missing | No EventKit/Google Calendar adapters |
| 8. Location Awareness | Missing | No CoreLocation/FusedLocationProvider integration |
| 9. Snooze & Dismissal Flow | Missing | No snooze/recompute logic |
| 10. Voice Personality System | Partial | Templates exist but no per-tier variations (min 3 required) |
| 11. History, Stats & Feedback Loop | Partial | Missing "common miss window", streak tracking incomplete |
| 12. Sound Library | Missing | No sound categories, no custom import |
| 13. Data Persistence | Partial | Schema incomplete per spec |

---

## Implementation Tasks (Prioritized)

### Phase 1: Core Infrastructure (Foundational)

#### 1.1 Complete Data Persistence Layer
**Priority:** P0 (blocks all other work)
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

**Tasks:**
- [ ] Implement full schema from spec Section 13 with all tables/columns:
  - `reminders`: origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id
  - `anchors`: tts_fallback, snoozed_to
  - `history`: missed_reason, actual_arrival
  - `calendar_sync`, `custom_sounds` tables
- [ ] Implement sequential migration system (schema_v1, v2, etc.)
- [ ] Enable foreign key enforcement, WAL mode
- [ ] Add `getInMemoryInstance()` for tests
- [ ] UUID v4 generation for all IDs

**Acceptance:** Fresh DB starts at schema version N, in-memory test DB works, cascade deletes work.

#### 1.2 Complete Escalation Chain Engine
**Priority:** P0 (blocks reminder creation)
**Files:** `src/lib/chain_engine.py`

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Ensure chain determinism (same inputs = same output)
- [ ] Complete validation: arrival > departure + minimum_drive_time
- [ ] Add compressed chain logic for 20-24 min buffer (currently only 10-24)

**Acceptance:** TC-01 through TC-06 from spec pass.

---

### Phase 2: Reminder Creation & Parsing

#### 2.1 LLM Adapter Interface & Implementation
**Priority:** P1 (differentiating feature)
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_minimax.py`, `src/lib/adapters/llm_anthropic.py`, `src/lib/adapters/llm_mock.py`

**Tasks:**
- [ ] Define `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter`
- [ ] Implement `MockLLMAdapter` for tests
- [ ] Implement keyword extraction fallback
- [ ] Connect to confirmation flow

**Acceptance:** Parser accepts MiniMax or Anthropic, fallback works on API failure, mock used in tests.

#### 2.2 Reminder Creation Workflow
**Priority:** P1
**Files:** `src/lib/reminder_service.py`

**Tasks:**
- [ ] `create_reminder()` flow: parse → validate → compute chain → persist
- [ ] Confirmation card data structure
- [ ] Manual field correction handling
- [ ] Support all 4 reminder types

**Acceptance:** TC-01 through TC-07 from spec pass.

---

### Phase 3: Voice & TTS

#### 3.1 TTS Adapter Interface & Implementation
**Priority:** P1 (critical UX feature)
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_elevenlabs.py`, `src/lib/adapters/tts_mock.py`

**Tasks:**
- [ ] Define `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement `MockTTSAdapter` for tests
- [ ] TTS cache management (`/tts_cache/{reminder_id}/`)
- [ ] TTS cache invalidation on reminder delete
- [ ] Fallback to system notification on TTS failure

**Acceptance:** TC-01 through TC-05 from spec pass.

#### 3.2 Voice Personality System Enhancement
**Priority:** P2
**Files:** `src/lib/voice_personalities.py`

**Tasks:**
- [ ] Add minimum 3 message variations per tier per personality
- [ ] Custom prompt support (max 200 chars)
- [ ] Per-reminder personality persistence

**Acceptance:** TC-01 through TC-05 from spec pass (message variation requirement).

---

### Phase 4: Notifications & Alarms

#### 4.1 Notification Behavior System
**Priority:** P1
**Files:** `src/lib/notification_service.py`

**Tasks:**
- [ ] Implement urgency tier → notification sound mapping
- [ ] DND detection and suppression logic
- [ ] Quiet hours configuration and enforcement
- [ ] Overdue anchor handling (15-min rule)
- [ ] Chain overlap serialization queue
- [ ] T-0 alarm looping until user action

**Acceptance:** TC-01 through TC-06 from spec pass.

---

### Phase 5: Background & Mobile Features

#### 5.1 Background Scheduling
**Priority:** P1
**Files:** `src/lib/background_scheduler.py`

**Tasks:**
- [ ] Notifee integration (iOS BGTaskScheduler + Android WorkManager)
- [ ] Anchor registration as individual background tasks
- [ ] Recovery scan on app launch
- [ ] Re-registration of pending anchors on crash recovery
- [ ] Late fire warning (>60s delay)

**Acceptance:** TC-01 through TC-06 from spec pass.

#### 5.2 Location Awareness
**Priority:** P2
**Files:** `src/lib/location_service.py`

**Tasks:**
- [ ] Single location check at departure anchor only
- [ ] Origin resolution (address or device location)
- [ ] 500m geofence comparison
- [ ] Immediate critical tier fire if still at origin
- [ ] Permission request on first location-aware reminder
- [ ] No location history retention

**Acceptance:** TC-01 through TC-05 from spec pass.

#### 5.3 Calendar Integration
**Priority:** P2
**Files:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/calendar_eventkit.py`, `src/lib/adapters/calendar_google.py`

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] Apple Calendar via EventKit
- [ ] Google Calendar API integration
- [ ] Suggestion cards for events with locations
- [ ] Recurring event handling
- [ ] Permission denial handling

**Acceptance:** TC-01 through TC-06 from spec pass.

---

### Phase 6: User Interaction

#### 6.1 Snooze & Dismissal Flow
**Priority:** P2
**Files:** `src/lib/snooze_service.py`, `src/lib/dismissal_service.py`

**Tasks:**
- [ ] Tap snooze (1 min default)
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Re-registration with Notifee
- [ ] Swipe-to-dismiss feedback prompt
- [ ] Feedback type storage and processing

**Acceptance:** TC-01 through TC-06 from spec pass.

#### 6.2 Sound Library
**Priority:** P3
**Files:** `src/lib/sound_library.py`

**Tasks:**
- [ ] Built-in sounds (5 per category: commute, routine, errand)
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Sound transcoding/normalization
- [ ] Per-reminder sound selection
- [ ] Corrupted sound fallback

**Acceptance:** TC-01 through TC-05 from spec pass.

---

### Phase 7: Stats & Feedback

#### 7.1 Complete History & Stats System
**Priority:** P2
**Files:** `src/lib/stats_service.py`, `src/lib/feedback_loop.py`

**Tasks:**
- [ ] Implement "common miss window" identification
- [ ] Complete streak counter (increment on hit, reset on miss)
- [ ] Drive duration adjustment with cap (+15 min max)
- [ ] 90-day retention with archive

**Acceptance:** TC-01 through TC-07 from spec pass.

---

### Phase 8: Testing & Validation

#### 8.1 Test Suite
**Priority:** P1 (ongoing throughout)
**Files:** `harness/test_*.py` or `tests/`

**Tasks:**
- [ ] Unit tests for chain engine determinism
- [ ] Parser fixture tests
- [ ] TTS adapter mock tests
- [ ] LLM adapter mock tests
- [ ] Keyword extraction tests
- [ ] Schema validation tests
- [ ] Integration tests (full flows)
- [ ] E2E test setup

**Acceptance:** All TC-* scenarios from spec pass, CI blocks merge on failure.

---

## Task Summary by Priority

### P0 (Critical Path - Implement First)
1. Complete database schema and migrations
2. Complete escalation chain engine

### P1 (Core Features)
3. LLM adapter interface + implementations
4. TTS adapter interface + implementations
5. Reminder creation workflow
6. Notification behavior system
7. Background scheduling

### P2 (Important Features)
8. Voice personality enhancements (variations)
9. Snooze & dismissal flow
10. Location awareness
11. Calendar integration
12. Complete stats & feedback loop

### P3 (Nice to Have)
13. Sound library with custom import

### P4 (Continuous)
14. Test suite completion

---

## Dependencies Map

```
┌─────────────────────────────────────────────────────────────┐
│ Database Schema (1.1)                                        │
│    └─────────────────────────────────────────────────────────┤
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ Chain Engine    │     │ Stats Service   │               │
│  │   (1.2)         │     │   (7.1)         │               │
│  └────────┬────────┘     └────────┬────────┘               │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌─────────────────────────────────────────────────┐        │
│  │         Reminder Creation (2.2)                 │        │
│  │    ┌────────────────┐  ┌────────────────┐       │        │
│  │    │ LLM Adapter    │  │ TTS Adapter    │       │        │
│  │    │   (2.1)        │  │   (3.1)        │       │        │
│  │    └────────────────┘  └────────────────┘       │        │
│  └─────────────────────────────────────────────────┘        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ Notification    │  │ Background      │  │ Snooze     │ │
│  │   (4.1)         │  │   Scheduler     │  │   (6.1)    │ │
│  └────────┬────────┘  │   (5.1)         │  └─────┬──────┘ │
│           │           └────────┬────────┘        │        │
│           │                    │                 │        │
│           ▼                    ▼                 ▼        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 Location (5.2) + Calendar (5.3)         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Estimated Effort

| Phase | Tasks | Notes |
|-------|-------|-------|
| Phase 1 | 2 | Foundation - blocks everything |
| Phase 2 | 2 | Parser + creation flow |
| Phase 3 | 2 | TTS + voice system |
| Phase 4 | 1 | Notifications |
| Phase 5 | 3 | Background, location, calendar |
| Phase 6 | 2 | Snooze/dismissal, sound library |
| Phase 7 | 1 | Stats + feedback loop |
| Phase 8 | 1 | Testing (continuous) |
| **Total** | **14** | |

---

*Generated: 2026-04-08*
