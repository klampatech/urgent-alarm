# URGENT Voice Alarm - Implementation Plan

## Project Overview

This is a mobile app for AI-powered escalating voice alarms. The current codebase (`src/test_server.py`) provides a Python test harness implementing core logic. The full mobile app needs to be built according to `specs/urgent-voice-alarm-app-2026-04-08.spec.md`.

---

## Current Implementation Status (as of 2026-04-08)

### Implemented in `test_server.py`
| Component | Status | Details |
|-----------|--------|---------|
| Chain Engine - Core logic | ✅ Complete | `compute_escalation_chain()` with 8-tier system |
| Chain Engine - Validation | ✅ Complete | `validate_chain()` checks |
| Parser - Keyword extraction | ✅ Complete | `parse_reminder_natural()` with regex patterns |
| Voice - All 5 personalities | ✅ Complete | `generate_voice_message()` with templates |
| Voice - Message templates | ✅ Complete | 8 tiers per personality |
| Database - Core tables | ✅ Complete | reminders, anchors, history, destination_adjustments, user_preferences |
| HTTP API - Core endpoints | ✅ Complete | /health, /chain, /reminders, /parse, /voice/message, /history, /anchors/fire |
| Stats - Hit rate | ✅ Complete | `calculate_hit_rate()` |
| Feedback - Adjustment tracking | ✅ Partial | Basic +2 min per miss, no cap enforcement |

### Missing / Incomplete
| Component | Priority | Gap |
|-----------|----------|-----|
| LLM Adapter (interface + MiniMax/Anthropic/Mock) | HIGH | Spec Section 3 |
| TTS Adapter (interface + ElevenLabs/Mock) | HIGH | Spec Section 4 |
| Snooze & Dismissal Flow | HIGH | Spec Section 9 |
| Feedback Loop - Adjustment cap, streak, miss window | HIGH | Spec Section 11 |
| Chain Engine - get_next_unfired_anchor, determinism tests | HIGH | Spec Section 2 |
| Background Scheduling (Notifee) | MEDIUM | Spec Section 6 |
| Notification & Alarm Behavior (DND, quiet hours) | MEDIUM | Spec Section 5 |
| Location Awareness | MEDIUM | Spec Section 8 |
| Calendar Integration | MEDIUM | Spec Section 7 |
| Sound Library | MEDIUM | Spec Section 12 |
| Database - Migration system | MEDIUM | Spec Section 13 |
| Database - Missing columns | MEDIUM | origin_*, calendar_event_id, custom_sound_path, etc. |

---

## Phase 1: Core API Completion (HIGH Priority)

### 1.1 Chain Engine Completeness
**Spec:** Section 2.3 (FR #6, #7), TC-05, TC-06

**Current Status:** Basic chain computation works, missing recovery functions.

**Tasks:**
- [ ] `get_next_unfired_anchor(reminder_id)` - Returns earliest unfired anchor
- [ ] Anchor sorting by timestamp ascending (verify)
- [ ] Chain determinism verification (same inputs → same outputs)
- [ ] Unit tests for chain determinism

**Endpoints to add:**
```
GET  /anchors/next?reminder_id={id}  # get next unfired anchor
```

**Scenarios to create:**
- [ ] `chain-next-unfired-anchor.yaml`
- [ ] `chain-determinism.yaml`

---

### 1.2 LLM Adapter for Parsing
**Spec:** Section 3.3 (FR #1-8), TC-01 to TC-07

**Current Status:** Only keyword extraction exists, no LLM integration.

**Tasks:**
- [ ] Create `ILanguageModelAdapter` interface (abstract base class)
- [ ] Implement `MinimaxAdapter` (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter` for direct API
- [ ] Implement `MockLanguageModelAdapter` for testing with fixture responses
- [ ] Wire adapter into `/parse` endpoint with keyword fallback
- [ ] Handle "unintelligible input" error case (return confidence < 0.5)

**Configuration:**
```bash
LLM_PROVIDER=minimax|anthropic|mock
MINIMAX_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
LLM_MOCK_FIXTURE={"destination": "...", "arrival_time": "...", "drive_duration": 30}
```

**Scenarios to create:**
- [ ] `parse-llm-success.yaml`
- [ ] `parse-llm-fallback-keyword.yaml`
- [ ] `parse-unintelligible-rejection.yaml`
- [ ] `parse-mock-adapter-test.yaml`

---

### 1.3 TTS Adapter & Clip Caching
**Spec:** Section 4.3 (FR #1-9), TC-01 to TC-05

**Current Status:** Voice messages are text-only, no actual TTS.

**Tasks:**
- [ ] Create `ITTSAdapter` interface (abstract base class)
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement `MockTTSAdapter` for testing (writes silent audio file)
- [ ] TTS generation at reminder creation (async with 30s timeout)
- [ ] Clip caching at `{TTS_CACHE_DIR}/{reminder_id}/{anchor_id}.mp3`
- [ ] Cache invalidation on reminder deletion
- [ ] Fallback behavior on API failure (`tts_fallback=true`)

**Configuration:**
```bash
ELEVENLABS_API_KEY=xxx
TTS_CACHE_DIR=/tts_cache
VOICE_IDS={"coach": "voice_id_1", "assistant": "voice_id_2", ...}
```

**Endpoints to add:**
```
POST /tts/generate        # Pre-generate clips for reminder
GET  /tts/clips/{reminder_id}  # List cached clips
DELETE /tts/cache/{reminder_id}   # Clear cache for reminder
```

**Scenarios to create:**
- [ ] `tts-clip-generation-at-creation.yaml`
- [ ] `tts-anchor-fires-from-cache.yaml`
- [ ] `tts-fallback-on-api-failure.yaml`
- [ ] `tts-cache-cleanup-on-delete.yaml`

---

### 1.4 Snooze & Dismissal Flow
**Spec:** Section 9.3 (FR #1-9), TC-01 to TC-06

**Current Status:** Not implemented.

**Tasks:**
- [ ] Tap snooze (1 min default) - `POST /reminders/{id}/snooze`
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain recomputation after snooze (shift remaining anchors)
- [ ] Re-registration of snoozed anchors with new timestamps
- [ ] Feedback prompt on dismiss - `POST /reminders/{id}/dismiss`
- [ ] TTS snooze confirmation: "Okay, snoozed {X} minutes"
- [ ] Snooze persistence after restart (store `snoozed_to` in anchors table)

**Endpoints:**
```
POST /reminders/{id}/snooze   # body: {duration: 1|3|5|10|15}
POST /reminders/{id}/dismiss  # body: {feedback_type: "timing_right"|"left_too_early"|"left_too_late"|"other"}
GET  /reminders/{id}/chain    # Get chain status with snooze info
```

**Scenarios to create:**
- [ ] `snooze-tap-1min.yaml`
- [ ] `snooze-custom-duration.yaml`
- [ ] `snooze-chain-recompute.yaml`
- [ ] `dismissal-feedback-timing-correct.yaml`
- [ ] `dismissal-feedback-left-too-late.yaml`
- [ ] `snooze-persistence-after-restart.yaml`

---

### 1.5 Feedback Loop & Destination Adjustments
**Spec:** Section 11.3 (FR #1-7), TC-02 to TC-06

**Current Status:** Basic +2 min per miss, missing cap and advanced features.

**Tasks:**
- [ ] Adjustment cap enforcement: `adjusted = min(original + (late_count * 2), original + 15)`
- [ ] Apply adjustments when creating new reminder for same destination
- [ ] Common miss window tracking (most frequently missed urgency tier)
- [ ] Streak counter for recurring reminders (increment on hit, reset on miss)
- [ ] `GET /stats/destination/{destination}` - adjustment info
- [ ] `GET /stats/streak` - streak counter
- [ ] 90-day data retention (archive old history)

**Endpoints:**
```
GET  /stats/destination/{destination}
GET  /stats/streak
GET  /stats/common-miss-window
```

**Scenarios to create:**
- [ ] `destination-adjustment-calculation.yaml`
- [ ] `destination-adjustment-cap.yaml` (verify 15-min cap)
- [ ] `common-miss-window.yaml`
- [ ] `streak-increment.yaml`
- [ ] `streak-reset.yaml`

---

## Phase 2: System Integration (MEDIUM Priority)

### 2.1 Background Scheduling & Reliability
**Spec:** Section 6.3 (FR #1-8), TC-01 to TC-06

**Tasks:**
- [ ] Notifee integration (or mock for Python harness)
- [ ] Register anchors with scheduler at reminder creation
- [ ] Recovery scan on app/session start
- [ ] Re-registration after crash (load unfired anchors, reschedule)
- [ ] Late-fire warning logging (>60s after scheduled time)
- [ ] 15-minute grace window for overdue anchors

**Endpoints:**
```
POST /anchors/{id}/schedule     # Register with scheduler
POST /scheduler/recovery-scan   # Run recovery scan
GET  /anchors/pending           # List pending anchors
GET  /anchors/overdue           # List overdue anchors (for logging)
```

**Scenarios to create:**
- [ ] `background-anchor-scheduling.yaml`
- [ ] `background-recovery-scan.yaml`
- [ ] `background-pending-reregister.yaml`
- [ ] `background-late-fire-warning.yaml`

---

### 2.2 Notification & Alarm Behavior
**Spec:** Section 5.3 (FR #1-8), TC-01 to TC-06

**Tasks:**
- [ ] DND detection and handling
- [ ] Quiet hours suppression (configurable, default 10pm-7am)
- [ ] Post-DND/quiet-hours catch-up queue
- [ ] 15-minute overdue anchor drop (silent)
- [ ] Chain overlap serialization (queue new anchors)
- [ ] T-0 alarm looping until user action

**Endpoints:**
```
GET  /system/dnd-status
GET  /system/quiet-hours
PUT  /system/quiet-hours        # body: {start: "22:00", end: "07:00"}
GET  /queue/status              # Queue status for overlap handling
```

**Scenarios to create:**
- [ ] `dnd-early-anchor-suppressed.yaml`
- [ ] `dnd-final-5min-override.yaml`
- [ ] `quiet-hours-suppression.yaml`
- [ ] `overdue-anchor-drop-15min.yaml`
- [ ] `chain-overlap-serialization.yaml`
- [ ] `t0-alarm-loops.yaml`

---

### 2.3 Location Awareness
**Spec:** Section 8.3 (FR #1-8), TC-01 to TC-05

**Tasks:**
- [ ] Single-point location check at departure anchor only
- [ ] Origin resolution (user-specified address or device location at creation)
- [ ] 500m geofence comparison
- [ ] "Still at origin" escalation (fire firm/critical tier immediately)
- [ ] Location permission request timing (at first location-aware reminder)
- [ ] No location history storage (single comparison, discard)

**Endpoints:**
```
POST /reminders/{id}/set-origin    # body: {address: "...", lat: xx, lng: xx}
GET  /reminders/{id}/origin
POST /location/check               # body: {reminder_id: "..."} - single check
```

**Scenarios to create:**
- [ ] `location-still-at-origin.yaml`
- [ ] `location-already-left.yaml`
- [ ] `location-permission-request.yaml`
- [ ] `location-permission-denied.yaml`
- [ ] `location-single-check-only.yaml`

---

### 2.4 Calendar Integration
**Spec:** Section 7.3 (FR #1-9), TC-01 to TC-06

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] `AppleCalendarAdapter` (EventKit)
- [ ] `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Calendar sync on launch + every 15 min
- [ ] Suggestion card generation for events with locations
- [ ] Recurring event handling (generate reminder for each occurrence)
- [ ] Permission denial handling with explanation
- [ ] Sync failure graceful degradation

**Endpoints:**
```
GET  /calendar/events              # List events with locations
GET  /calendar/suggestions         # List suggestion cards
POST /calendar/suggestions/{id}    # Create reminder from suggestion
GET  /calendar/sync-status
POST /calendar/sync               # Trigger manual sync
```

**Scenarios to create:**
- [ ] `calendar-apple-event-suggestion.yaml`
- [ ] `calendar-google-event-suggestion.yaml`
- [ ] `calendar-suggestion-to-reminder.yaml`
- [ ] `calendar-permission-denial.yaml`
- [ ] `calendar-sync-failure-degradation.yaml`
- [ ] `calendar-recurring-event.yaml`

---

## Phase 3: Polish & Extensions (LOWER Priority)

### 3.1 Voice Personality System Enhancements
**Spec:** Section 10.3 (FR #1-6), TC-01 to TC-05

**Tasks:**
- [ ] Custom voice prompt support (max 200 characters)
- [ ] Message template variations (minimum 3 per tier per personality)
- [ ] Personality immutability for existing reminders
- [ ] Voice preview functionality

**Endpoints:**
```
POST /voice/personality     # body: {personality: "custom", custom_prompt: "..."}
GET  /voice/preview         # body: {personality, tier, destination, duration}
GET  /voice/personalities    # List available personalities
```

---

### 3.2 Sound Library
**Spec:** Section 12.3 (FR #1-8), TC-01 to TC-05

**Tasks:**
- [ ] Bundle 5 built-in sounds per category (Commute, Routine, Errand)
- [ ] Per-reminder sound selection storage
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Audio validation and storage
- [ ] Corrupted sound fallback to category default

**Endpoints:**
```
GET  /sounds/categories
GET  /sounds                 # List available sounds
POST /sounds/import          # Import custom sound (multipart/form-data)
DELETE /sounds/{id}          # Delete custom sound
```

**Scenarios to create:**
- [ ] `sound-builtin-playback.yaml`
- [ ] `sound-custom-import.yaml`
- [ ] `sound-custom-playback.yaml`
- [ ] `sound-corrupted-fallback.yaml`
- [ ] `sound-persistence-on-edit.yaml`

---

### 3.3 Database Schema Expansion & Migration System
**Spec:** Section 13.3 (FR #1-8)

**Current Schema Gaps:**
| Table | Missing Columns |
|-------|----------------|
| reminders | origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id, snoozed_at |
| anchors | tts_fallback, snoozed_to |
| history | actual_arrival, missed_reason |
| destination_adjustments | updated_at |
| - | Missing: calendar_sync table |
| - | Missing: custom_sounds table |
| - | Missing: schema_version table |

**Tasks:**
- [ ] Create migration system (versioned, sequential)
- [ ] Add all missing columns via migrations
- [ ] Create calendar_sync table
- [ ] Create custom_sounds table
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] UUID v4 generation verification

**Scenarios to create:**
- [ ] `migration-sequence.yaml`
- [ ] `inmemory-test-database.yaml`
- [ ] `foreign-key-enforcement.yaml`
- [ ] `uuid-generation.yaml`

---

## Task Dependencies

```
Phase 1.1 (Chain Engine - get_next_unfired_anchor)
    └── Phase 1.4 (Snooze & Dismissal)

Phase 1.4 (Snooze & Dismissal)
    └── Phase 1.5 (Feedback Loop)

Phase 1.2 (LLM Adapter) + Phase 1.3 (TTS Adapter)
    └── Phase 1.4 (Snooze & Dismissal)

Phase 3.3 (Database Schema)
    ├── Phase 1.1 (Chain Engine)
    ├── Phase 1.4 (Snooze)
    ├── Phase 2.4 (Calendar Integration)
    └── Phase 3.2 (Sound Library)

Phase 2.1 (Background Scheduling)
    ├── Phase 2.2 (Notification Behavior)
    └── Phase 2.3 (Location Awareness)
```

---

## Priority Order Summary

| # | Phase | Priority | Tasks | Dependencies |
|---|-------|----------|-------|--------------|
| 1 | 1.1 Chain Engine | HIGH | 4 | None |
| 2 | 1.2 LLM Adapter | HIGH | 6 | None |
| 3 | 1.3 TTS Adapter | HIGH | 7 | None |
| 4 | 1.4 Snooze & Dismissal | HIGH | 7 | 1.1 |
| 5 | 1.5 Feedback Loop | HIGH | 7 | 1.4 |
| 6 | 3.3 Database Schema | MEDIUM | 7 | None |
| 7 | 2.1 Background Scheduling | MEDIUM | 6 | None |
| 8 | 2.2 Notification Behavior | MEDIUM | 6 | 2.1 |
| 9 | 2.3 Location Awareness | MEDIUM | 6 | 2.1 |
| 10 | 2.4 Calendar Integration | MEDIUM | 8 | 3.3 |
| 11 | 3.1 Voice Enhancements | LOW | 4 | None |
| 12 | 3.2 Sound Library | LOW | 5 | 3.3 |

**Total: ~73 tasks across 12 phases**

---

## Missing Test Scenarios (to create in harness)

### Chain Engine (2)
- [ ] `chain-next-unfired-anchor.yaml`
- [ ] `chain-determinism.yaml`

### Parser (4)
- [ ] `parse-llm-success.yaml`
- [ ] `parse-llm-fallback-keyword.yaml`
- [ ] `parse-unintelligible-rejection.yaml`
- [ ] `parse-mock-adapter-test.yaml`

### TTS (4)
- [ ] `tts-clip-generation-at-creation.yaml`
- [ ] `tts-anchor-fires-from-cache.yaml`
- [ ] `tts-fallback-on-api-failure.yaml`
- [ ] `tts-cache-cleanup-on-delete.yaml`

### Snooze (6)
- [ ] `snooze-tap-1min.yaml`
- [ ] `snooze-custom-duration.yaml`
- [ ] `snooze-chain-recompute.yaml`
- [ ] `dismissal-feedback-timing-correct.yaml`
- [ ] `dismissal-feedback-left-too-late.yaml`
- [ ] `snooze-persistence-after-restart.yaml`

### Feedback Loop (5)
- [ ] `destination-adjustment-calculation.yaml`
- [ ] `destination-adjustment-cap.yaml`
- [ ] `common-miss-window.yaml`
- [ ] `streak-increment.yaml`
- [ ] `streak-reset.yaml`

### Background Scheduling (4)
- [ ] `background-anchor-scheduling.yaml`
- [ ] `background-recovery-scan.yaml`
- [ ] `background-pending-reregister.yaml`
- [ ] `background-late-fire-warning.yaml`

### Notification Behavior (6)
- [ ] `dnd-early-anchor-suppressed.yaml`
- [ ] `dnd-final-5min-override.yaml`
- [ ] `quiet-hours-suppression.yaml`
- [ ] `overdue-anchor-drop-15min.yaml`
- [ ] `chain-overlap-serialization.yaml`
- [ ] `t0-alarm-loops.yaml`

### Location (5)
- [ ] `location-still-at-origin.yaml`
- [ ] `location-already-left.yaml`
- [ ] `location-permission-request.yaml`
- [ ] `location-permission-denied.yaml`
- [ ] `location-single-check-only.yaml`

### Calendar (6)
- [ ] `calendar-apple-event-suggestion.yaml`
- [ ] `calendar-google-event-suggestion.yaml`
- [ ] `calendar-suggestion-to-reminder.yaml`
- [ ] `calendar-permission-denial.yaml`
- [ ] `calendar-sync-failure-degradation.yaml`
- [ ] `calendar-recurring-event.yaml`

### Database (4)
- [ ] `migration-sequence.yaml`
- [ ] `inmemory-test-database.yaml`
- [ ] `foreign-key-enforcement.yaml`
- [ ] `uuid-generation.yaml`

### Sound Library (5)
- [ ] `sound-builtin-playback.yaml`
- [ ] `sound-custom-import.yaml`
- [ ] `sound-custom-playback.yaml`
- [ ] `sound-corrupted-fallback.yaml`
- [ ] `sound-persistence-on-edit.yaml`

---

## Build & Run

```bash
# Start test server
python3 src/test_server.py &

# Run tests
python3 -m pytest harness/

# Lint
python3 -m py_compile harness/scenario_harness.py src/test_server.py
```

## Operational Notes

```bash
# Running the harness manually
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Creating scenarios (requires sudo)
sudo mkdir -p /var/otto-scenarios/urgent-alarm
sudo cp my-scenarios/*.yaml /var/otto-scenarios/urgent-alarm/
```
