# URGENT Voice Alarm - Implementation Plan

## Project Overview

This is a mobile app for AI-powered escalating voice alarms. The current codebase (`src/test_server.py`) provides a Python test harness implementing core logic. The full mobile app needs to be built according to `specs/urgent-voice-alarm-app-2026-04-08.spec.md`.

---

## Current Implementation Status

### Implemented (17 scenarios passing)
| Component | Status | Scenarios |
|-----------|--------|-----------|
| Chain Engine - Full 30min | ✅ Complete | `chain-full-30min.yaml` |
| Chain Engine - Compressed 15min | ✅ Complete | `chain-compressed-15min.yaml` |
| Chain Engine - Minimum 3min | ✅ Complete | `chain-minimum-3min.yaml` |
| Chain Engine - Invalid rejection | ✅ Complete | `chain-invalid-rejected.yaml` |
| Parser - Natural language | ✅ Complete | `parse-natural-language.yaml` |
| Parser - Simple countdown | ✅ Complete | `parse-simple-countdown.yaml` |
| Parser - Tomorrow resolution | ✅ Complete | `parse-tomorrow.yaml` |
| Voice - Coach personality | ✅ Complete | `voice-coach-personality.yaml` |
| Voice - No-nonsense personality | ✅ Complete | `voice-no-nonsense.yaml` |
| Voice - All personalities | ✅ Complete | `voice-all-personalities.yaml` |
| History - Record outcome | ✅ Complete | `history-record-outcome.yaml` |
| History - Miss feedback | ✅ Complete | `history-record-miss-feedback.yaml` |
| Stats - Hit rate | ✅ Complete | `stats-hit-rate.yaml` |
| Reminder - CRUD | ✅ Complete | `reminder-creation-crud.yaml` |
| Reminder - Cascade delete | ✅ Complete | `reminder-creation-cascade-delete.yaml` |

### Partially Implemented
| Component | Status | Gap |
|----------|--------|-----|
| Chain Engine | Partial | Missing `get_next_unfired_anchor()`, chain recomputation, snooze handling |
| Parser | Partial | Missing LLM adapter (MiniMax, Anthropic), mock interface |
| Voice | Partial | Missing custom prompts, message variations (min 3 per tier) |
| Stats | Partial | Missing streak counter, common miss window, adjustment cap enforcement |
| Database | Partial | Missing 15+ columns, migration system, WAL mode |

### Not Implemented (MISSING)
| Component | Priority | Spec Section |
|-----------|----------|--------------|
| LLM Adapter (MiniMax, Anthropic, Mock) | HIGH | Section 3 |
| TTS Adapter (ElevenLabs, Mock, Clip caching) | HIGH | Section 4 |
| Snooze & Dismissal Flow | HIGH | Section 9 |
| Feedback Loop (adjustments, cap, streak) | HIGH | Section 11 |
| Background Scheduling (Notifee) | MEDIUM | Section 6 |
| Notification & Alarm Behavior (DND, quiet hours) | MEDIUM | Section 5 |
| Location Awareness | MEDIUM | Section 8 |
| Calendar Integration (EventKit, Google) | MEDIUM | Section 7 |
| Sound Library (bundled + custom import) | MEDIUM | Section 12 |
| Migration System | MEDIUM | Section 13 |
| Data Retention (90-day archiving) | LOW | Section 11 |

---

## Phase 1: Core API Completion (HIGH Priority)

### 1.1 Chain Engine Completeness
**Spec:** Section 2.3 (FR #6, #7), TC-05, TC-06

**Tasks:**
- [ ] `get_next_unfired_anchor(reminder_id)` - Returns earliest unfired anchor
- [ ] Anchor sorting by timestamp ascending
- [ ] Chain recomputation after snooze (shift remaining anchors)
- [ ] Snooze persistence (`snoozed_to` field)
- [ ] Unit tests for chain determinism (same inputs → same outputs)

**Endpoints to add:**
```
GET  /anchors/next?reminder_id={id}  # get next unfired anchor
POST /reminders/{id}/snooze          # snooze with duration param
POST /reminders/{id}/dismiss         # dismiss with feedback
```

**Validation:**
```yaml
# chain-next-unfired-anchor.yaml
# chain-determinism.yaml
```

---

### 1.2 LLM Adapter for Parsing
**Spec:** Section 3.3 (FR #1-8), TC-01 to TC-07

**Tasks:**
- [ ] `ILanguageModelAdapter` interface (mock-able)
- [ ] `MinimaxAdapter` (Anthropic-compatible endpoint)
- [ ] `AnthropicAdapter` for direct API
- [ ] Mock adapter for testing with fixture responses
- [ ] Wire adapter into `/parse` endpoint with keyword fallback
- [ ] Handle "unintelligible input" error case

**Configuration:**
```bash
LLM_PROVIDER=minimax|anthropic
MINIMAX_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
```

**Scenarios:**
- [ ] `parse-llm-fallback-keyword.yaml` (TC-04)
- [ ] `parse-manual-field-correction.yaml` (TC-05)
- [ ] `parse-unintelligible-rejection.yaml` (TC-06)
- [ ] `parse-mock-adapter-test.yaml` (TC-07)

---

### 1.3 TTS Adapter & Clip Caching
**Spec:** Section 4.3 (FR #1-9), TC-01 to TC-05

**Tasks:**
- [ ] `ITTSAdapter` interface (mock-able)
- [ ] `ElevenLabsAdapter` with voice ID mapping
- [ ] Mock TTS adapter for testing (writes silent file)
- [ ] TTS generation at reminder creation (async with 30s timeout)
- [ ] Clip caching at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- [ ] Cache invalidation on reminder deletion
- [ ] Fallback behavior on API failure (`tts_fallback=true`)

**Configuration:**
```bash
ELEVENLABS_API_KEY=xxx
TTS_CACHE_DIR=/tts_cache
```

**Endpoints:**
```
POST /tts/generate        # Pre-generate clips for reminder
DELETE /tts/cache/{id}   # Clear cache for reminder
```

**Scenarios:**
- [ ] `tts-clip-generation-at-creation.yaml` (TC-01)
- [ ] `tts-anchor-fires-from-cache.yaml` (TC-02)
- [ ] `tts-fallback-on-api-failure.yaml` (TC-03)
- [ ] `tts-cache-cleanup-on-delete.yaml` (TC-04)
- [ ] `tts-mock-in-tests.yaml` (TC-05)

---

### 1.4 Snooze & Dismissal Flow
**Spec:** Section 9.3 (FR #1-9), TC-01 to TC-06

**Tasks:**
- [ ] Tap snooze (1 min default)
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain recomputation after snooze
- [ ] Re-registration of snoozed anchors
- [ ] Feedback prompt on dismiss
- [ ] TTS snooze confirmation: "Okay, snoozed {X} minutes"
- [ ] Snooze persistence after restart

**Endpoints:**
```
POST /reminders/{id}/snooze   # body: {duration: 1|3|5|10|15}
POST /reminders/{id}/dismiss   # body: {feedback_type: "timing_right"|"left_too_early"|"left_too_late"|"other"}
```

**Scenarios:**
- [ ] `snooze-tap-1min.yaml` (TC-01)
- [ ] `snooze-custom-duration.yaml` (TC-02)
- [ ] `snooze-chain-recompute.yaml` (TC-03)
- [ ] `dismissal-feedback-timing-correct.yaml` (TC-04)
- [ ] `dismissal-feedback-left-too-late.yaml` (TC-05)
- [ ] `snooze-persistence-after-restart.yaml` (TC-06)

---

### 1.5 Feedback Loop & Destination Adjustments
**Spec:** Section 11.3 (FR #1-7), TC-02 to TC-06

**Tasks:**
- [ ] Adjustment calculation: `stored_drive_duration + (late_count * 2_minutes)`
- [ ] +15 minute cap on adjustment
- [ ] Apply adjustments on new reminder creation
- [ ] Common miss window tracking
- [ ] Streak counter for recurring reminders
- [ ] `GET /stats/destination/{destination}`
- [ ] `GET /stats/streak`

**Endpoints:**
```
GET  /stats/destination/{destination}  # adjustment info
GET  /stats/streak                      # streak counter
```

**Scenarios:**
- [ ] `destination-adjustment-calculation.yaml` (TC-02)
- [ ] `destination-adjustment-cap.yaml` (TC-03)
- [ ] `common-miss-window.yaml` (TC-04)
- [ ] `streak-increment.yaml` (TC-05)
- [ ] `streak-reset.yaml` (TC-06)

---

## Phase 2: System Integration (MEDIUM Priority)

### 2.1 Background Scheduling & Reliability
**Spec:** Section 6.3 (FR #1-8), TC-01 to TC-06

**Tasks:**
- [ ] Notifee integration for background tasks
- [ ] Register anchors with Notifee at reminder creation
- [ ] Recovery scan on app launch
- [ ] Re-registration after crash
- [ ] Late-fire warning (>60s)

**Endpoints:**
```
POST /anchors/{id}/schedule     # Register with Notifee
GET  /anchors/pending            # List pending anchors
GET  /anchors/overdue            # List overdue anchors
POST /scheduler/recovery-scan   # Run recovery scan
```

**Scenarios:**
- [ ] `background-anchor-scheduling.yaml` (TC-01)
- [ ] `background-recovery-scan.yaml` (TC-03, TC-04)
- [ ] `background-pending-reregister.yaml` (TC-05)
- [ ] `background-late-fire-warning.yaml` (TC-06)

---

### 2.2 Notification & Alarm Behavior
**Spec:** Section 5.3 (FR #1-8), TC-01 to TC-06

**Tasks:**
- [ ] DND detection and handling
- [ ] Quiet hours suppression (default 10pm-7am)
- [ ] Post-DND/quiet-hours catch-up queue
- [ ] 15-minute overdue anchor drop
- [ ] Chain overlap serialization
- [ ] T-0 alarm looping

**Scenarios:**
- [ ] `dnd-early-anchor-suppressed.yaml` (TC-01)
- [ ] `dnd-final-5min-override.yaml` (TC-02)
- [ ] `quiet-hours-suppression.yaml` (TC-03)
- [ ] `overdue-anchor-drop-15min.yaml` (TC-04)
- [ ] `chain-overlap-serialization.yaml` (TC-05)
- [ ] `t0-alarm-loops.yaml` (TC-06)

---

### 2.3 Location Awareness
**Spec:** Section 8.3 (FR #1-8), TC-01 to TC-05

**Tasks:**
- [ ] Single-point location check at departure anchor
- [ ] Origin resolution (address or device location)
- [ ] 500m geofence comparison
- [ ] "Still at origin" escalation
- [ ] Location permission request timing
- [ ] No location history storage

**Scenarios:**
- [ ] `location-still-at-origin.yaml` (TC-01)
- [ ] `location-already-left.yaml` (TC-02)
- [ ] `location-permission-request.yaml` (TC-03)
- [ ] `location-permission-denied.yaml` (TC-04)
- [ ] `location-single-check-only.yaml` (TC-05)

---

### 2.4 Calendar Integration
**Spec:** Section 7.3 (FR #1-9), TC-01 to TC-06

**Tasks:**
- [ ] `ICalendarAdapter` interface
- [ ] `AppleCalendarAdapter` (EventKit)
- [ ] `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Calendar sync on launch + every 15 min
- [ ] Suggestion card generation
- [ ] Recurring event handling
- [ ] Permission denial handling
- [ ] Sync failure graceful degradation

**Endpoints:**
```
GET  /calendar/events           # List calendar events with locations
POST /calendar/suggestions/{id} # Create reminder from suggestion
```

**Scenarios:**
- [ ] `calendar-apple-event-suggestion.yaml` (TC-01)
- [ ] `calendar-google-event-suggestion.yaml` (TC-02)
- [ ] `calendar-suggestion-to-reminder.yaml` (TC-03)
- [ ] `calendar-permission-denial.yaml` (TC-04)
- [ ] `calendar-sync-failure-degradation.yaml` (TC-05)
- [ ] `calendar-recurring-event.yaml` (TC-06)

---

## Phase 3: Polish & Extensions (LOWER Priority)

### 3.1 Voice Personality System Enhancements
**Spec:** Section 10.3 (FR #1-6), TC-01 to TC-05

**Tasks:**
- [ ] Custom voice prompt support (max 200 chars)
- [ ] Message template variations (min 3 per tier per personality)
- [ ] Personality immutability for existing reminders
- [ ] Voice preview functionality

**Endpoints:**
```
POST /voice/personality  # Set custom prompt
GET  /voice/preview      # Preview voice message
```

---

### 3.2 Sound Library
**Spec:** Section 12.3 (FR #1-8), TC-01 to TC-05

**Tasks:**
- [ ] Bundle 5 built-in sounds per category (Commute, Routine, Errand)
- [ ] Per-reminder sound selection storage
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Audio transcoding to normalized format
- [ ] Corrupted sound fallback

**Endpoints:**
```
GET  /sounds/categories     # List sound categories
GET  /sounds                 # List available sounds
POST /sounds/import          # Import custom sound
```

**Scenarios:**
- [ ] `sound-builtin-playback.yaml` (TC-01)
- [ ] `sound-custom-import.yaml` (TC-02)
- [ ] `sound-custom-playback.yaml` (TC-03)
- [ ] `sound-corrupted-fallback.yaml` (TC-04)
- [ ] `sound-persistence-on-edit.yaml` (TC-05)

---

### 3.3 Database Schema Expansion
**Spec:** Section 13.3 (FR #1-8)

**Missing tables/columns:**
- [ ] `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`, `snoozed_to`
- [ ] `anchors`: `tts_fallback BOOLEAN`, `snoozed_to`
- [ ] `history`: `actual_arrival`, `missed_reason`
- [ ] `destination_adjustments`: `updated_at`
- [ ] `calendar_sync` table
- [ ] `custom_sounds` table
- [ ] `schema_version` tracking table
- [ ] Migration system (sequential, versioned)
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`

**Scenarios:**
- [ ] `migration-sequence.yaml` (TC-01)
- [ ] `inmemory-test-database.yaml` (TC-02)
- [ ] `foreign-key-enforcement.yaml` (TC-04)
- [ ] `uuid-generation.yaml` (TC-05)

---

### 3.4 Data Retention & Archiving
**Spec:** Section 11.3 (FR #7)

**Tasks:**
- [ ] 90-day history retention policy
- [ ] Data archiving for history > 90 days
- [ ] Archive access functionality

---

## Task Dependencies Graph

```
Phase 1.1 (Chain Engine)
    └── Phase 1.4 (Snooze & Dismissal)

Phase 1.1 + Phase 1.2 + Phase 1.3
    └── Phase 1.4 (Snooze & Dismissal)

Phase 1.4 (Snooze & Dismissal)
    └── Phase 1.5 (Feedback Loop)

Phase 3.3 (Database Schema)
    ├── Phase 1.1 (Chain Engine)
    ├── Phase 2.4 (Calendar Integration)
    └── Phase 3.2 (Sound Library)

Phase 2.1 (Background Scheduling)
    ├── Phase 2.2 (Notification Behavior)
    └── Phase 2.3 (Location Awareness)

Phase 1.5 (Feedback Loop)
    └── Phase 3.1 (Voice Enhancements)
```

---

## Priority Order Summary

| # | Phase | Priority | Tasks |
|---|-------|----------|-------|
| 1 | 1.1 Chain Engine | HIGH | 5 |
| 2 | 1.2 LLM Adapter | HIGH | 6 |
| 3 | 1.3 TTS Adapter | HIGH | 7 |
| 4 | 1.4 Snooze & Dismissal | HIGH | 7 |
| 5 | 1.5 Feedback Loop | HIGH | 7 |
| 6 | 3.3 Database Schema | MEDIUM | 8 |
| 7 | 2.1 Background Scheduling | MEDIUM | 4 |
| 8 | 2.2 Notification Behavior | MEDIUM | 6 |
| 9 | 2.3 Location Awareness | MEDIUM | 6 |
| 10 | 2.4 Calendar Integration | MEDIUM | 8 |
| 11 | 3.1 Voice Enhancements | LOW | 4 |
| 12 | 3.2 Sound Library | LOW | 5 |
| 13 | 3.4 Data Retention | LOW | 3 |

**Total: ~83 tasks across 13 phases**

---

## Missing Scenarios (40+)

### Chain Engine (2 remaining)
- [ ] `chain-next-unfired-anchor.yaml` (TC-05)
- [ ] `chain-determinism.yaml` (TC-06)

### Parser (4 remaining)
- [ ] `parse-llm-fallback-keyword.yaml` (TC-04)
- [ ] `parse-manual-field-correction.yaml` (TC-05)
- [ ] `parse-unintelligible-rejection.yaml` (TC-06)
- [ ] `parse-mock-adapter-test.yaml` (TC-07)

### TTS (5 remaining)
- [ ] `tts-clip-generation-at-creation.yaml` (TC-01)
- [ ] `tts-anchor-fires-from-cache.yaml` (TC-02)
- [ ] `tts-fallback-on-api-failure.yaml` (TC-03)
- [ ] `tts-cache-cleanup-on-delete.yaml` (TC-04)
- [ ] `tts-mock-in-tests.yaml` (TC-05)

### Snooze & Dismissal (6 remaining)
- [ ] `snooze-tap-1min.yaml` (TC-01)
- [ ] `snooze-custom-duration.yaml` (TC-02)
- [ ] `snooze-chain-recompute.yaml` (TC-03)
- [ ] `dismissal-feedback-timing-correct.yaml` (TC-04)
- [ ] `dismissal-feedback-left-too-late.yaml` (TC-05)
- [ ] `snooze-persistence-after-restart.yaml` (TC-06)

### Feedback Loop (5 remaining)
- [ ] `destination-adjustment-calculation.yaml` (TC-02)
- [ ] `destination-adjustment-cap.yaml` (TC-03)
- [ ] `common-miss-window.yaml` (TC-04)
- [ ] `streak-increment.yaml` (TC-05)
- [ ] `streak-reset.yaml` (TC-06)

### Background Scheduling (4 remaining)
- [ ] `background-anchor-scheduling.yaml` (TC-01)
- [ ] `background-recovery-scan.yaml` (TC-03, TC-04)
- [ ] `background-pending-reregister.yaml` (TC-05)
- [ ] `background-late-fire-warning.yaml` (TC-06)

### Notification Behavior (6 remaining)
- [ ] `dnd-early-anchor-suppressed.yaml` (TC-01)
- [ ] `dnd-final-5min-override.yaml` (TC-02)
- [ ] `quiet-hours-suppression.yaml` (TC-03)
- [ ] `overdue-anchor-drop-15min.yaml` (TC-04)
- [ ] `chain-overlap-serialization.yaml` (TC-05)
- [ ] `t0-alarm-loops.yaml` (TC-06)

### Location (5 remaining)
- [ ] `location-still-at-origin.yaml` (TC-01)
- [ ] `location-already-left.yaml` (TC-02)
- [ ] `location-permission-request.yaml` (TC-03)
- [ ] `location-permission-denied.yaml` (TC-04)
- [ ] `location-single-check-only.yaml` (TC-05)

### Calendar (6 remaining)
- [ ] `calendar-apple-event-suggestion.yaml` (TC-01)
- [ ] `calendar-google-event-suggestion.yaml` (TC-02)
- [ ] `calendar-suggestion-to-reminder.yaml` (TC-03)
- [ ] `calendar-permission-denial.yaml` (TC-04)
- [ ] `calendar-sync-failure-degradation.yaml` (TC-05)
- [ ] `calendar-recurring-event.yaml` (TC-06)

### Database (4 remaining)
- [ ] `migration-sequence.yaml` (TC-01)
- [ ] `inmemory-test-database.yaml` (TC-02)
- [ ] `foreign-key-enforcement.yaml` (TC-04)
- [ ] `uuid-generation.yaml` (TC-05)

### Sound Library (5 remaining)
- [ ] `sound-builtin-playback.yaml` (TC-01)
- [ ] `sound-custom-import.yaml` (TC-02)
- [ ] `sound-custom-playback.yaml` (TC-03)
- [ ] `sound-corrupted-fallback.yaml` (TC-04)
- [ ] `sound-persistence-on-edit.yaml` (TC-05)

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
