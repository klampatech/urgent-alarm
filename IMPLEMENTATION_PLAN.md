# URGENT Alarm — Implementation Plan

## Project Overview

**Project:** URGENT — AI Escalating Voice Alarm
**Type:** Mobile app (React Native) with Python backend for core logic
**Goal:** Voice alarm app with escalating urgency messages based on arrival time and drive duration

---

## Current State

| Component | Status |
|-----------|--------|
| `src/test_server.py` | Basic HTTP server with chain engine, parser, voice messages, stats |
| `src/lib/` | Empty — no library modules |
| `harness/` | Empty — no test harness |
| `specs/` | Complete specs for all 14 feature areas |

**Key Gaps:**
- No mobile app (React Native codebase)
- No LLM adapter (mock only, no ElevenLabs integration)
- No TTS adapter (mock only)
- No calendar integration
- No location awareness
- No background scheduling
- No notification/alarm behavior
- No snooze/dismissal flow
- No sound library
- No complete test harness
- Missing database tables (calendar_sync, custom_sounds, schema versioning)
- Incomplete schema alignment with spec

---

## Phase 1: Foundation (Core Engine & Testing)

### 1.1 Expand Chain Engine ([Section 2](specs/urgent-voice-alarm-app-2026-04-08.spec.md#2-escalation-chain-engine))

**Priority:** P0 — Everything depends on this

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add anchor sorting by timestamp in database queries
- [ ] Add `snoozed_to` field handling in chain recomputation
- [ ] Implement full chain compression logic per spec (TC-02, TC-03)
- [ ] Add chain determinism verification (same inputs → same outputs)
- [ ] Add validation: reject `drive_duration > time_to_arrival`

**Acceptance Criteria:**
- Full chain (≥25 min buffer) → 8 anchors
- Compressed chain (10-24 min) → skips calm/casual
- Short chain (5-9 min) → starts at pushing
- Minimum chain (≤5 min) → firm, critical, alarm

---

### 1.2 Create Library Structure ([Section 13](specs/urgent-voice-alarm-app-2026-04-08.spec.md#13-data-persistence))

**Priority:** P0 — Foundation for all other components

**Tasks:**
- [ ] Create `src/lib/database.py` with SQLite wrapper
  - Schema versioning/migration system
  - WAL mode, foreign key enforcement
  - In-memory mode for tests
  - All tables from spec: reminders, anchors, history, user_preferences, destination_adjustments, calendar_sync, custom_sounds
- [ ] Create `src/lib/models.py` with data classes
- [ ] Create `src/lib/interfaces.py` with all adapter interfaces (ILanguageModelAdapter, ITTSAdapter, ICalendarAdapter, ILocationAdapter)
- [ ] Update `src/test_server.py` to use library

**Schema Alignment:**
```sql
-- Missing from current test_server.py:
- origin_lat, origin_lng, origin_address in reminders
- custom_sound_path in reminders
- calendar_event_id in reminders
- tts_fallback in anchors
- snoozed_to in anchors
- missed_reason in history
- schema_migrations table
- calendar_sync table
- custom_sounds table
```

---

### 1.3 Build Test Harness

**Priority:** P0 — Required for validation

**Tasks:**
- [ ] Create `harness/scenario_harness.py` (stub exists, needs completion)
- [ ] Create `harness/test_chain_engine.py` for chain computation tests
- [ ] Create `harness/test_parser.py` for LLM/keyword parsing tests
- [ ] Create `harness/test_voice.py` for voice personality tests
- [ ] Create `harness/test_stats.py` for hit rate and feedback loop tests
- [ ] Add integration tests: full reminder creation flow

**Test Coverage Required:**
- Unit: Chain determinism, parser fixtures, TTS adapter mock, LLM adapter mock
- Integration: parse → chain → persist, anchor firing, snooze recovery, feedback loop

---

## Phase 2: Core Features

### 2.1 LLM Adapter ([Section 3](specs/urgent-voice-alarm-app-2026-04-08.spec.md#3-reminder-parsing--creation))

**Priority:** P1

**Tasks:**
- [ ] Implement `src/lib/adapters/llm_adapter.py`
  - Support MiniMax API (Anthropic-compatible) and Anthropic API
  - Configurable via environment variable
  - System prompt for extraction schema
- [ ] Implement `src/lib/adapters/keyword_extractor.py` as fallback
  - Regex patterns for time and duration
  - Handle: "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
- [ ] Add mock adapter for testing
- [ ] Implement confirmation card response handling (user can edit fields)

**Acceptance Criteria:**
- "30 minute drive to Parker Dr, check-in at 9am" → parsed correctly
- "dryer in 3 min" → simple_countdown type
- "meeting tomorrow 2pm, 20 min drive" → tomorrow's date
- API failure → keyword extraction fallback
- Unintelligible input → error message

---

### 2.2 TTS Adapter ([Section 4](specs/urgent-voice-alarm-app-2026-04-08.spec.md#4-voice--tts-generation))

**Priority:** P1

**Tasks:**
- [ ] Implement `src/lib/adapters/tts_adapter.py`
  - ElevenLabs API integration
  - Voice personality to voice ID mapping
  - Custom prompt support
- [ ] Implement TTS cache management
  - Store in `/tts_cache/{reminder_id}/`
  - Invalidate on reminder deletion
- [ ] Implement fallback: system notification sound + text
- [ ] Add mock TTS adapter for testing
- [ ] Add async generation with 30-second timeout handling

**Acceptance Criteria:**
- 8 MP3 clips generated per reminder
- Cached clips played with no network call
- Fallback fires on API failure
- Reminder deletion removes cached files

---

### 2.3 Voice Personality System ([Section 10](specs/urgent-voice-alarm-app-2026-04-08.spec.md#10-voice-personality-system))

**Priority:** P1

**Tasks:**
- [ ] Implement `src/lib/voice_personalities.py`
  - 5 built-in personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
  - Custom prompt mode (max 200 chars)
  - Tier-specific message templates (min 3 variations per tier per personality)
- [ ] Update message generation to use templates
- [ ] Store selected personality in user_preferences
- [ ] Ensure existing reminders retain personality at creation time

**Acceptance Criteria:**
- Each personality produces distinct tone
- 3+ message variations per tier
- Custom prompt modifies tone appropriately
- Personality immutability for existing reminders

---

### 2.4 Snooze & Dismissal Flow ([Section 9](specs/urgent-voice-alarm-app-2026-04-08.spec.md#9-snooze--dismissal-flow))

**Priority:** P1

**Tasks:**
- [ ] Implement snooze handlers
  - Tap snooze: 1 minute default
  - Tap-and-hold: custom duration picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain recomputation on snooze
  - Shift remaining anchors by snooze duration
  - Re-register with Notifee
- [ ] Implement dismissal flow
  - Feedback prompt: "Was the timing right?"
  - "No" → follow-up: "What was wrong?"
  - Store feedback in history table
- [ ] TTS snooze confirmation: "Okay, snoozed X minutes"

**Acceptance Criteria:**
- Tap snooze pauses 1 minute
- Custom snooze picker works
- Chain recomputation shifts all remaining anchors
- Feedback prompt appears on dismiss
- "Left too late" feedback adjusts future estimates by +2 min

---

## Phase 3: Background & Notifications

### 3.1 Background Scheduling ([Section 6](specs/urgent-voice-alarm-app-2026-04-08.spec.md#6-background-scheduling--reliability))

**Priority:** P2

**Tasks:**
- [ ] Implement `src/lib/scheduler.py`
  - Notifee integration for background tasks
  - iOS: BGAppRefreshTask + BGProcessingTask
  - Android: WorkManager
- [ ] Implement recovery scan on app launch
  - Fire overdue unfired anchors within 15-minute grace window
  - Drop anchors >15 minutes overdue
  - Log missed_reason = "background_task_killed"
- [ ] Implement late fire warning (>60 seconds after scheduled)
- [ ] Persist anchor state to SQLite

**Acceptance Criteria:**
- Anchors fire with app closed
- Recovery scan fires grace-window anchors
- Overdue anchors dropped and logged
- Pending anchors re-registered on crash recovery

---

### 3.2 Notification & Alarm Behavior ([Section 5](specs/urgent-voice-alarm-app-2026-04-08.spec.md#5-notification--alarm-behavior))

**Priority:** P2

**Tasks:**
- [ ] Implement notification tier escalation
  - Gentle chime: calm/casual
  - Pointed beep: pointed/urgent
  - Urgent siren: pushing/firm
  - Looping alarm: critical/alarm
- [ ] Implement DND awareness
  - Early anchors: silent notification
  - Final 5 minutes: visual override + vibration
- [ ] Implement quiet hours (default 10pm–7am)
  - Queue suppressed anchors
  - Drop if >15 minutes overdue
- [ ] Implement chain overlap serialization
  - Queue new anchors until current chain completes
- [ ] T-0 alarm loops until user action

**Acceptance Criteria:**
- DND suppresses early anchors silently
- DND triggers override for final 5 minutes
- Quiet hours suppress and queue anchors
- Overdue anchors dropped after 15 min
- Chain overlap serialized

---

### 3.3 Location Awareness ([Section 8](specs/urgent-voice-alarm-app-2026-04-08.spec.md#8-location-awareness))

**Priority:** P2

**Tasks:**
- [ ] Implement `src/lib/adapters/location_adapter.py`
  - Single location check at departure anchor
  - CoreLocation (iOS) / FusedLocationProvider (Android)
  - 500m geofence radius
- [ ] Implement origin resolution
  - User-specified address
  - Current device location at creation time
- [ ] Implement escalation on "still at origin"
  - Fire firm/critical anchor immediately instead of departure nudge
- [ ] Request permission at first location-aware reminder creation

**Acceptance Criteria:**
- Single location check at departure time
- Within 500m → immediate escalation
- Already left → normal chain proceeds
- No location history stored

---

## Phase 4: Integrations

### 4.1 Calendar Integration ([Section 7](specs/urgent-voice-alarm-app-2026-04-08.spec.md#7-calendar-integration))

**Priority:** P3

**Tasks:**
- [ ] Implement `src/lib/adapters/calendar_adapter.py`
  - Apple Calendar via EventKit
  - Google Calendar via Google Calendar API
  - Common ICalendarAdapter interface
- [ ] Implement sync scheduler
  - On launch, every 15 minutes, background refresh
- [ ] Implement suggestion cards
  - Surface events with locations
  - "Add departure reminder?" flow
- [ ] Handle recurring events
- [ ] Implement permission denial handling

**Acceptance Criteria:**
- Apple/Google Calendar events with locations appear as suggestions
- Confirming creates countdown_event reminder
- Permission denial shows explanation banner
- Recurring events generate reminders for each occurrence

---

### 4.2 Sound Library ([Section 12](specs/urgent-voice-alarm-app-2026-04-08.spec.md#12-sound-library))

**Priority:** P3

**Tasks:**
- [ ] Implement `src/lib/sound_library.py`
  - Built-in sounds per category (Commute, Routine, Errand, Custom)
  - 5 sounds per category, bundled with app
- [ ] Implement custom audio import
  - MP3, WAV, M4A support
  - Max 30 seconds duration
  - Store in app sandbox
- [ ] Implement corrupted file fallback

**Acceptance Criteria:**
- Built-in sounds play without network
- Custom import appears in picker
- Corrupted file falls back to category default

---

## Phase 5: Stats & History

### 5.1 History & Feedback Loop ([Section 11](specs/urgent-voice-alarm-app-2026-04-08.spec.md#11-history-stats--feedback-loop))

**Priority:** P2

**Tasks:**
- [ ] Implement hit rate calculation
  - `count(outcome = 'hit') / count(outcome != 'pending') * 100`
  - Trailing 7 days
- [ ] Implement feedback loop adjustments
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
  - Cap at +15 minutes
- [ ] Implement common miss window detection
  - Most frequently missed urgency tier
- [ ] Implement streak counter
  - Increment on hit, reset on miss
  - For standing/recurring reminders

**Acceptance Criteria:**
- Hit rate displays correctly
- Late feedback adjusts future estimates
- Cap at +15 minutes
- Streak increments/resets correctly
- Stats computable from history table alone

---

## Phase 6: Mobile App

### 6.1 React Native App Structure

**Priority:** P3 (lower priority as backend enables testing)

**Tasks:**
- [ ] Initialize React Native project
- [ ] Set up navigation (Home, Add Reminder, History, Settings)
- [ ] Implement Quick Add UI
  - Text/speech input
  - Confirmation card display
  - Manual field correction
- [ ] Implement reminder list view
- [ ] Implement history/stats view
- [ ] Implement settings
  - Voice personality selection
  - Quiet hours configuration
  - Calendar connection
  - Sound library

---

## Dependencies Graph

```
Phase 1 (Foundation)
├── 1.1 Chain Engine
│   └── Required by: Everything
├── 1.2 Library Structure
│   ├── Database → Required by: All data operations
│   ├── Models → Required by: All business logic
│   └── Interfaces → Required by: All adapters
└── 1.3 Test Harness
    └── Required by: All validation

Phase 2 (Core Features) [depend on Phase 1]
├── 2.1 LLM Adapter [depends on 1.2]
├── 2.2 TTS Adapter [depends on 1.2]
├── 2.3 Voice Personalities [depends on 2.1]
└── 2.4 Snooze/Dismissal [depends on 1.1, 2.2]

Phase 3 (Background & Notifications) [depend on Phase 2]
├── 3.1 Background Scheduling [depends on 1.2]
├── 3.2 Notifications [depends on 3.1, 2.2]
└── 3.3 Location [depends on 1.2]

Phase 4 (Integrations) [parallel with Phase 3]
├── 4.1 Calendar [depends on 1.2]
└── 4.2 Sound Library [depends on 1.2]

Phase 5 (Stats) [depends on Phase 1]
└── 5.1 History & Feedback [depends on 1.2]

Phase 6 (Mobile App) [depends on Phases 1-5]
└── 6.1 React Native [depends on all backend]
```

---

## Quick Wins (Immediate Value)

1. **Expand chain compression logic** in `test_server.py` — validates core differentiator
2. **Add missing schema tables** — enables full feature set
3. **Create keyword extractor** — fallback when LLM unavailable
4. **Add message variations** — each personality needs 3+ templates per tier
5. **Implement stats functions** — hit rate, feedback loop, streak counter

---

## Out of Scope (Per Spec)

- Password reset / account management (local-only v1)
- Smart home integration (Hue lights)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Sound recording within app
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Automatic calendar adjustment from feedback

---

## Next Steps

1. **Start with Phase 1.2** — Create library structure in `src/lib/`
2. **Then Phase 1.1** — Expand chain engine with missing functions
3. **Then Phase 1.3** — Build test harness for validation
4. **Continue through phases** based on priority and dependencies
