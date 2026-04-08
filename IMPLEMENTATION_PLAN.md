# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Current State:** Python test server with basic chain engine, keyword parser, and partial SQLite schema. No mobile app infrastructure, no LLM/TTS adapters, no background scheduling, no calendar/location integration.

**Spec Coverage:** ~15% — basic escalation chain logic and message templates exist.

---

## Phase 1: Foundation (Core Engine + Infrastructure)

### 1.1 [CRITICAL] Database Schema Alignment
**Why:** All other components depend on the data schema.

Align `src/lib/database.py` with the full spec schema in Section 13:
- [ ] Add `origin_lat`, `origin_lng`, `origin_address` to `reminders`
- [ ] Add `tts_fallback`, `snoozed_to` to `anchors`
- [ ] Add `actual_arrival`, `missed_reason` to `history`
- [ ] Add `updated_at` to `destination_adjustments`
- [ ] Add `calendar_sync` table (apple/google sync state)
- [ ] Add `custom_sounds` table
- [ ] Add migration system with versioned sequential migrations
- [ ] Enable foreign keys (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)

**Files:** `src/lib/database.py`, `src/migrations/`

---

### 1.2 [CRITICAL] LLM Adapter Interface + Mock Implementation
**Why:** Reminder parsing depends on this; must be mockable for testing.

From spec Section 3.3:
- [ ] Create `src/lib/adapters/llm_adapter.py` with `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` class (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter` class
- [ ] Implement `MockLLMAdapter` class for testing
- [ ] Add fallback to keyword extraction on API failure
- [ ] Environment variable for adapter selection (`LLM_ADAPTER=minimax|anthropic|mock`)

**Files:** `src/lib/adapters/llm_adapter.py`, `tests/adapters/test_llm_adapter.py`

---

### 1.3 [CRITICAL] TTS Adapter Interface + Mock Implementation
**Why:** Voice generation depends on this; must be mockable for testing.

From spec Section 4.3:
- [ ] Create `src/lib/adapters/tts_adapter.py` with `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` class with voice ID mapping
- [ ] Implement `MockTTSAdapter` class for testing (writes silent audio file)
- [ ] Implement `TTSCacheManager` for file storage under `/tts_cache/{reminder_id}/`
- [ ] Implement cache invalidation on reminder deletion
- [ ] Environment variable for adapter selection (`TTS_ADAPTER=elevenlabs|mock`)
- [ ] Fallback behavior: skip clip, mark `tts_fallback = true`

**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/tts_cache.py`, `tests/adapters/test_tts_adapter.py`

---

## Phase 2: Core Features (Chain Engine + Parser)

### 2.1 [HIGH] Chain Engine Enhancement
**Why:** Core value proposition; must match spec exactly.

From spec Section 2.3:
- [ ] `compute_escalation_chain()`: Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Validate `arrival_time > departure_time + minimum_drive_time` (reject if not)
- [ ] Verify chain determinism (same inputs → same anchors)
- [ ] Add anchor state persistence (`fired`, `fire_count`, `snoozed_to`)
- [ ] Implement snooze chain recomputation (shift remaining anchors)

**Files:** `src/lib/chain_engine.py`, `tests/test_chain_engine.py`

---

### 2.2 [HIGH] Natural Language Parser Enhancement
**Why:** Core user interaction; must handle all spec test cases.

From spec Section 3.4-3.5:
- [ ] Integrate LLM adapter into parser flow
- [ ] Support all test case formats:
  - "30 minute drive to Parker Dr, check-in at 9am"
  - "dryer in 3 min" (simple_countdown)
  - "meeting tomorrow 2pm, 20 min drive" (tomorrow date resolution)
- [ ] Display confirmation card (returned parsed object)
- [ ] Allow manual field correction before confirm
- [ ] Handle empty/unintelligible input with retry prompt
- [ ] Extract `reminder_type` enum: countdown_event, simple_countdown, morning_routine, standing_recurring

**Files:** `src/lib/parser.py`, `tests/test_parser.py`

---

### 2.3 [HIGH] Voice Personality System
**Why:** Differentiates app experience.

From spec Section 10.3:
- [ ] Map 5 personalities to ElevenLabs voice IDs in TTS adapter
- [ ] Store selected personality in `user_preferences` (SQLite)
- [ ] Implement custom personality prompt (max 200 chars)
- [ ] Generate message variations (minimum 3 per tier per personality)
- [ ] Ensure existing reminders retain original personality on user preference change

**Files:** `src/lib/voice_personalities.py`, `src/lib/user_preferences.py`, `tests/test_voice.py`

---

## Phase 3: User Interaction (Notifications + Snooze)

### 3.1 [HIGH] Notification & Alarm Behavior
**Why:** Core UX; must handle DND, quiet hours, chain serialization.

From spec Section 5.3:
- [ ] Implement 4-tier notification sounds: gentle chime, pointed beep, urgent siren, looping alarm
- [ ] Respect system DND — silent for early anchors, visual override for final 5 min
- [ ] Implement quiet hours suppression (configurable start/end, default 10pm–7am)
- [ ] Queue overdue anchors; drop if >15 minutes overdue
- [ ] Implement chain overlap serialization (queue new anchors until current chain completes)
- [ ] T-0 alarm loops until user dismisses/snoozes
- [ ] Notification display: destination, time remaining, voice icon

**Files:** `src/lib/notifications.py`, `src/lib/quiet_hours.py`, `tests/test_notifications.py`

---

### 3.2 [HIGH] Snooze & Dismissal Flow
**Why:** Core interaction pattern.

From spec Section 9.3:
- [ ] Implement tap snooze (1 minute default)
- [ ] Implement tap-and-hold custom snooze (1, 3, 5, 10, 15 min options)
- [ ] Implement chain re-computation after snooze (shift remaining anchors)
- [ ] Re-register snoozed anchors with new timestamps
- [ ] Implement dismissal feedback prompt: "You missed [destination] — was timing right?"
- [ ] Implement feedback routing: Yes → store, No → secondary prompt
- [ ] TTS confirmation: "Okay, snoozed [X] minutes"
- [ ] Persist snoozed timestamps across app restart

**Files:** `src/lib/snooze.py`, `src/lib/dismissal.py`, `tests/test_snooze.py`

---

## Phase 4: Background & System Integration

### 4.1 [HIGH] Background Scheduling
**Why:** Reminders must fire even when app is closed.

From spec Section 6.3:
- [ ] Integrate Notifee for iOS/Android background scheduling
- [ ] Register each anchor as individual background task
- [ ] Implement recovery scan on app launch:
  - Fire overdue unfired anchors within 15-minute grace window
  - Drop anchors >15 minutes overdue, log with `missed_reason`
- [ ] Re-register pending anchors after crash/termination
- [ ] Log warning for late firing (>60 seconds after scheduled)
- [ ] iOS: Use `BGAppRefreshTask` + `BGProcessingTask` for TTS pre-warming

**Note:** This requires React Native plugin integration (not pure Python).

**Files:** `src/lib/scheduler.py`, `src/notifee_integration.js`

---

### 4.2 [MEDIUM] Location Awareness
**Why:** "Still at origin?" check at departure time.

From spec Section 8.3:
- [ ] Implement single location check at departure anchor only
- [ ] Accept origin: user-specified address OR current location at creation time
- [ ] Use CoreLocation (iOS) / FusedLocationProvider (Android) — single API call
- [ ] Implement geofence comparison: within 500m = "at origin"
- [ ] If at origin: fire firm/critical tier immediately instead of calm departure
- [ ] Request permission at first location-aware reminder (not at launch)
- [ ] If denied: create reminder without location escalation, show note
- [ ] No location history stored

**Files:** `src/lib/location.py`, `src/core_location_integration.js`

---

## Phase 5: Integrations (Calendar + Sound Library)

### 5.1 [MEDIUM] Calendar Integration
**Why:** Auto-suggest departure reminders for calendar events.

From spec Section 7.3:
- [ ] Implement `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Sync on: app launch, every 15 minutes, background refresh
- [ ] Filter events with non-empty `location` field
- [ ] Surface suggestion cards: "Add departure reminder?"
- [ ] Support recurring events (one reminder per occurrence)
- [ ] Calendar-sourced reminders: visual distinction (calendar icon)
- [ ] Handle permission denial with explanation banner
- [ ] Handle sync failures gracefully (manual reminders still work)

**Files:** `src/lib/adapters/calendar_adapter.py`, `src/lib/calendar_sync.py`, `tests/test_calendar.py`

---

### 5.2 [MEDIUM] Sound Library
**Why:** Per-reminder sound customization.

From spec Section 12.3:
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom audio import: MP3, WAV, M4A (max 30 seconds)
- [ ] Transcode imported sounds to normalized format
- [ ] Implement `custom_sounds` table and picker UI
- [ ] Per-reminder sound selection overrides category default
- [ ] If custom sound corrupted: fallback to category default + error log
- [ ] Sound selection persists on reminder edit

**Files:** `src/lib/sound_library.py`, `src/lib/audio_transcoder.py`, `tests/test_sound_library.py`

---

## Phase 6: Analytics (History + Feedback Loop)

### 6.1 [MEDIUM] History & Stats System
**Why:** User-facing analytics + feedback learning.

From spec Section 11.3:
- [ ] Implement `calculate_hit_rate()`: hits / (total - pending) * 100 for trailing 7 days
- [ ] Implement "common miss window" identification (most frequently missed tier)
- [ ] Implement streak counter: increment on hit, reset on miss for recurring reminders
- [ ] Implement 90-day retention with archive
- [ ] Stats computable from history table alone (no separate stats table)

**Files:** `src/lib/history.py`, `src/lib/stats.py`, `tests/test_stats.py`

---

### 6.2 [MEDIUM] Feedback Loop
**Why:** Learns from missed reminders to improve future estimates.

From spec Section 11.3:
- [ ] On "left too late" feedback: `adjustment_minutes += 2` for destination
- [ ] Cap adjustment at +15 minutes
- [ ] On reminder creation: apply destination adjustments to drive_duration estimate
- [ ] Store feedback in `history` table with `feedback_type`

**Files:** `src/lib/feedback_loop.py`, `tests/test_feedback.py`

---

## Phase 7: Mobile App UI (React Native/Flutter)

**Note:** The current Python test server serves as the backend logic layer. The actual mobile UI must be implemented separately as a React Native or Flutter app.

### 7.1 [LOW] Quick Add Interface
- Text/speech input for reminders
- Parsed interpretation confirmation card
- Manual field editing

### 7.2 [LOW] Reminder List & Management
- List active reminders with countdown
- Edit/delete reminders
- Calendar suggestion cards

### 7.3 [LOW] Settings Screen
- Voice personality selection
- Quiet hours configuration
- Sound library access
- Calendar permissions

### 7.4 [LOW] History/Stats Screen
- Weekly hit rate display
- Streak counter
- Common miss window

---

## Task Prioritization Summary

| Priority | Task | Dependencies | Est. Effort |
|----------|------|--------------|-------------|
| P0 | Database schema alignment | None | Medium |
| P0 | LLM adapter interface | None | Medium |
| P0 | TTS adapter interface | None | Medium |
| P1 | Chain engine enhancement | None | Low |
| P1 | Natural language parser | LLM adapter | Medium |
| P1 | Voice personality system | TTS adapter | Medium |
| P1 | Notification behavior | None | Medium |
| P1 | Snooze & dismissal | Chain engine | Medium |
| P2 | Background scheduling | Database | High |
| P2 | Location awareness | Database | Medium |
| P2 | Calendar integration | Database | High |
| P2 | Sound library | Database | Medium |
| P2 | History & stats | Database | Medium |
| P2 | Feedback loop | History, stats | Low |
| P3 | Mobile UI (React Native) | All above | Very High |

---

## Definition of Done

Every task must have:
1. Implementation matching acceptance criteria in spec
2. Unit tests covering all test scenarios (Given/When/Then)
3. No regressions in existing tests

Tests should be runnable via:
```bash
python3 -m pytest tests/
```
