# URGENT Voice Alarm - Implementation Plan

## Project Overview

This is a React Native mobile app for AI-powered escalating voice alarms. The current codebase (`src/test_server.py`) provides a Python test harness server implementing core logic. The full mobile app needs to be built according to `specs/urgent-voice-alarm-app-2026-04-08.spec.md`.

---

## Gap Analysis Summary

| Spec Section | Topic | Implementation Status |
|-------------|-------|----------------------|
| 2 | Escalation Chain Engine | **Partial** - Core logic exists; missing `get_next_unfired_anchor()`, snooze handling, determinism |
| 3 | Reminder Parsing & Creation | **Partial** - Keyword extraction exists; missing LLM adapter, mock interface |
| 4 | Voice & TTS Generation | **Partial** - Template-based messages exist; missing ElevenLabs adapter, clip caching |
| 5 | Notification & Alarm Behavior | **Missing** - DND, quiet hours, chain serialization, T-0 looping |
| 6 | Background Scheduling | **Missing** - Notifee integration, recovery scan |
| 7 | Calendar Integration | **Missing** - EventKit, Google Calendar API adapters |
| 8 | Location Awareness | **Missing** - Single-point departure check, 500m geofence |
| 9 | Snooze & Dismissal Flow | **Missing** - Tap/tap-hold snooze, chain recomputation, feedback |
| 10 | Voice Personality System | **Partial** - 5 personalities exist; missing custom prompts, message variations |
| 11 | History, Stats & Feedback Loop | **Partial** - Hit rate exists; missing streak, common miss window, cap enforcement |
| 12 | Sound Library | **Missing** - Per-reminder sounds, built-in bundles, custom import |
| 13 | Data Persistence | **Partial** - Basic schema exists; missing 15+ columns, migrations, WAL mode |

---

## Phase 1: Foundation (High Priority)

These are prerequisites for all other work.

### 1.1 Database Schema Expansion
**Priority: CRITICAL**

**Tasks:**
- [ ] Add missing columns to `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`, `snoozed_to`
- [ ] Add missing columns to `anchors`: `tts_fallback BOOLEAN DEFAULT FALSE`, `snoozed_to`
- [ ] Add missing columns to `history`: `actual_arrival`, `missed_reason`
- [ ] Add missing columns to `destination_adjustments`: `updated_at`
- [ ] Create `calendar_sync` table: `calendar_type PK`, `last_sync_at`, `sync_token`, `is_connected`
- [ ] Create `custom_sounds` table: `id PK`, `filename`, `original_name`, `category`, `file_path`, `duration_seconds`, `created_at`
- [ ] Add `schema_version` tracking table
- [ ] Implement sequential migration system (v1 → current)
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] Update test scenarios for new schema

**Validation:**
```bash
python3 -m py_compile src/test_server.py
python3 src/test_server.py &
curl http://localhost:8090/health
```

---

### 1.2 Chain Engine Completeness
**Priority: HIGH**

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add anchor sorting by timestamp in queries
- [ ] Implement chain recomputation after snooze (shift remaining anchors)
- [ ] Implement snooze persistence (`snoozed_to` field handling)
- [ ] Add unit tests for chain determinism (same inputs → same outputs)

**Spec Reference:** Section 2.3 (FR #6, #7), TC-05, TC-06

**Validation:**
```yaml
# New scenario needed: chain-next-unfired-anchor
name: chain-next-unfired-anchor
trigger:
  type: api_sequence
  steps:
    - POST /reminders {...}
    # ... fire some anchors ...
    - GET /anchors/next?reminder_id={id}
assertions:
  - type: http_status
    expect: 200
```

---

## Phase 2: Core Features (High Priority)

### 2.1 LLM Adapter for Parsing
**Priority: HIGH**

**Tasks:**
- [ ] Create `ILanguageModelAdapter` interface (mock-able)
- [ ] Implement `MinimaxAdapter` (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter` for direct API
- [ ] Implement mock adapter for testing with fixture responses
- [ ] Wire adapter into `/parse` endpoint with keyword fallback on API failure
- [ ] Handle "unintelligible input" case with user-facing error

**Spec Reference:** Section 3.3 (FR #1-8), TC-01 to TC-07

**Dependencies:** Phase 1.1 (database schema for testing)

---

### 2.2 TTS Adapter & Clip Caching
**Priority: HIGH**

**Tasks:**
- [ ] Create `ITTSAdapter` interface (mock-able)
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement mock TTS adapter for testing (writes silent file)
- [ ] Implement `/tts/generate` endpoint to pre-generate clips at reminder creation
- [ ] Implement TTS cache storage at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
- [ ] Implement cache invalidation on reminder deletion
- [ ] Implement fallback behavior (skip clip, mark `tts_fallback=true`) on API failure
- [ ] Ensure total TTS generation completes within 30 seconds (async with polling)

**Spec Reference:** Section 4.3 (FR #1-9), TC-01 to TC-05

**Dependencies:** Phase 1.1 (database schema), Phase 2.1 (reminder creation)

---

### 2.3 Snooze & Dismissal Flow
**Priority: HIGH**

**Tasks:**
- [ ] Implement `POST /reminders/{id}/snooze` with duration param
- [ ] Implement `POST /reminders/{id}/dismiss` with feedback
- [ ] Implement chain recomputation on snooze (shift remaining anchors by snooze duration)
- [ ] Implement re-registration of snoozed anchors with Notifee (via background scheduler)
- [ ] Implement feedback prompt data collection:
  - "Yes — timing was right" → outcome = 'hit'
  - "No — timing was off" + sub-prompt → adjust destination estimate
- [ ] Implement TTS snooze confirmation: "Okay, snoozed {X} minutes"

**Spec Reference:** Section 9.3 (FR #1-9), TC-01 to TC-06

**Dependencies:** Phase 1.2 (chain recomputation), Phase 2.2 (TTS)

---

### 2.4 Feedback Loop & Destination Adjustments
**Priority: HIGH**

**Tasks:**
- [ ] Implement adjustment calculation: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
- [ ] Implement +15 minute cap on adjustment
- [ ] Apply adjustments when creating new reminders to same destination
- [ ] Implement common miss window tracking (most frequently missed urgency tier)
- [ ] Implement streak counter for standing/recurring reminders
- [ ] Add `GET /stats/destination/{destination}` endpoint
- [ ] Add `GET /stats/streak` endpoint

**Spec Reference:** Section 11.3 (FR #1-7), TC-02, TC-03, TC-04, TC-05, TC-06

**Dependencies:** Phase 1.1 (database schema), Phase 2.3 (dismissal flow)

---

## Phase 3: System Integration (Medium Priority)

### 3.1 Background Scheduling & Reliability
**Priority: MEDIUM**

**Tasks:**
- [ ] Integrate Notifee for background task scheduling
- [ ] Implement `POST /anchors/{id}/schedule` to register anchor with Notifee
- [ ] Implement recovery scan on app launch:
  - Query all unfired anchors
  - Fire only those within 15-minute grace window
  - Drop anchors >15 minutes overdue, log with `missed_reason`
- [ ] Implement re-registration of pending anchors after crash
- [ ] Implement late-fire warning (>60s after scheduled time)
- [ ] Add `GET /anchors/pending` and `GET /anchors/overdue` endpoints

**Spec Reference:** Section 6.3 (FR #1-8), TC-01 to TC-06

**Dependencies:** Phase 1.1, Phase 2.2 (TTS caching for background play)

---

### 3.2 Notification & Alarm Behavior
**Priority: MEDIUM**

**Tasks:**
- [ ] Implement DND detection and handling:
  - Pre-5-minute: silent notification only
  - Final 5 minutes: visual override + vibration
- [ ] Implement quiet hours suppression (10pm–7am default, configurable)
- [ ] Implement post-DND/quiet-hours catch-up queue
- [ ] Implement 15-minute overdue anchor drop
- [ ] Implement chain overlap serialization (queue new anchors until current chain completes)
- [ ] Implement T-0 alarm looping until user action
- [ ] Implement notification display: destination label, time remaining, voice personality icon

**Spec Reference:** Section 5.3 (FR #1-8), TC-01 to TC-06

**Dependencies:** Phase 3.1 (background scheduling)

---

### 3.3 Location Awareness
**Priority: MEDIUM**

**Tasks:**
- [ ] Implement single-point location check at departure anchor (T-drive_duration)
- [ ] Implement origin resolution: user-specified address OR current device location at creation
- [ ] Implement 500m geofence comparison
- [ ] Implement "still at origin" escalation: fire firm/critical tier immediately
- [ ] Implement location permission request at first location-aware reminder (not at launch)
- [ ] Implement graceful degradation when permission denied
- [ ] Ensure no location history is stored

**Spec Reference:** Section 8.3 (FR #1-8), TC-01 to TC-05

**Dependencies:** Phase 3.1 (departure anchor trigger)

---

### 3.4 Calendar Integration
**Priority: MEDIUM**

**Tasks:**
- [ ] Create `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement calendar sync on launch + every 15 minutes
- [ ] Filter events with non-empty `location` field
- [ ] Implement suggestion card generation for events with locations
- [ ] Implement calendar-sourced reminder creation
- [ ] Implement recurring event handling (generate reminder for each occurrence)
- [ ] Implement permission denial handling with explanation banner
- [ ] Implement sync failure graceful degradation

**Spec Reference:** Section 7.3 (FR #1-9), TC-01 to TC-06

**Dependencies:** Phase 1.1 (schema), Phase 2.1 (LLM parsing)

---

## Phase 4: Polish & Extensions (Lower Priority)

### 4.1 Voice Personality System Enhancements
**Priority: MEDIUM**

**Tasks:**
- [ ] Implement custom voice prompt support (max 200 chars) via `/voice/personality`
- [ ] Implement message template variations (minimum 3 per tier per personality)
- [ ] Update personality immutability for existing reminders
- [ ] Add voice preview functionality

**Spec Reference:** Section 10.3 (FR #1-6), TC-01 to TC-05

---

### 4.2 Sound Library
**Priority: MEDIUM**

**Tasks:**
- [ ] Bundle 5 built-in sounds per category (Commute, Routine, Errand)
- [ ] Implement per-reminder sound selection storage
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 seconds)
- [ ] Implement file picker integration
- [ ] Implement audio transcoding to normalized format
- [ ] Implement corrupted sound file fallback to category default
- [ ] Add `GET /sounds/categories`, `POST /sounds/import`, `GET /sounds` endpoints

**Spec Reference:** Section 12.3 (FR #1-8), TC-01 to TC-05

**Dependencies:** Phase 1.1 (schema)

---

### 4.3 Data Retention & Archiving
**Priority: LOW**

**Tasks:**
- [ ] Implement 90-day history retention policy
- [ ] Implement data archiving for history > 90 days
- [ ] Implement archive access functionality

**Spec Reference:** Section 11.3 (FR #7)

---

## Phase 5: Testing & Documentation (Ongoing)

### 5.1 Test Coverage
**Priority: HIGH**

**Missing Scenarios:**
- [ ] `chain-next-unfired-anchor.yaml` - TC-05 from Section 2
- [ ] `chain-determinism.yaml` - TC-06 from Section 3
- [ ] `snooze-tap-1min.yaml` - TC-01 from Section 9
- [ ] `snooze-custom-duration.yaml` - TC-02 from Section 9
- [ ] `snooze-chain-recompute.yaml` - TC-03 from Section 9
- [ ] `dismissal-feedback-timing-correct.yaml` - TC-04 from Section 9
- [ ] `dismissal-feedback-left-too-late.yaml` - TC-05 from Section 9
- [ ] `snooze-persistence-after-restart.yaml` - TC-06 from Section 9
- [ ] `destination-adjustment-cap.yaml` - TC-03 from Section 11
- [ ] `common-miss-window.yaml` - TC-04 from Section 11
- [ ] `streak-increment-reset.yaml` - TC-05, TC-06 from Section 11
- [ ] `dnd-early-anchor-suppressed.yaml` - TC-01 from Section 5
- [ ] `dnd-final-5min-override.yaml` - TC-02 from Section 5
- [ ] `quiet-hours-suppression.yaml` - TC-03 from Section 5
- [ ] `overdue-anchor-drop-15min.yaml` - TC-04 from Section 5
- [ ] `chain-overlap-serialization.yaml` - TC-05 from Section 5
- [ ] `t0-alarm-loops.yaml` - TC-06 from Section 5
- [ ] `background-recovery-scan.yaml` - TC-03, TC-04 from Section 6
- [ ] `background-pending-reregister.yaml` - TC-05 from Section 6
- [ ] `background-late-fire-warning.yaml` - TC-06 from Section 6
- [ ] `location-still-at-origin.yaml` - TC-01 from Section 8
- [ ] `location-already-left.yaml` - TC-02 from Section 8
- [ ] `location-permission-request.yaml` - TC-03 from Section 8
- [ ] `location-single-check-only.yaml` - TC-05 from Section 8
- [ ] `tts-fallback-on-api-failure.yaml` - TC-03 from Section 4
- [ ] `tts-cache-cleanup-on-delete.yaml` - TC-04 from Section 4
- [ ] `calendar-apple-event-suggestion.yaml` - TC-01 from Section 7
- [ ] `calendar-google-event-suggestion.yaml` - TC-02 from Section 7
- [ ] `calendar-permission-denial.yaml` - TC-04 from Section 7
- [ ] `calendar-sync-failure-degradation.yaml` - TC-05 from Section 7
- [ ] `calendar-recurring-event.yaml` - TC-06 from Section 7
- [ ] `migration-sequence.yaml` - TC-01 from Section 13
- [ ] `inmemory-test-database.yaml` - TC-02 from Section 13
- [ ] `cascade-delete.yaml` - TC-03 from Section 13 (update existing)
- [ ] `foreign-key-enforcement.yaml` - TC-04 from Section 13
- [ ] `uuid-generation.yaml` - TC-05 from Section 13

### 5.2 Integration & E2E Tests
**Priority: MEDIUM**

- [ ] Full reminder creation flow (parse → chain → TTS → persist)
- [ ] Anchor firing sequence (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment applied)
- [ ] Quick Add flow (text/speech → parse → confirm)
- [ ] Settings navigation
- [ ] Sound library browsing

---

## Task Dependencies Graph

```
Phase 1.1 (Database Schema)
    ├── Phase 1.2 (Chain Engine)
    ├── Phase 2.1 (LLM Adapter)
    ├── Phase 2.2 (TTS Adapter)
    ├── Phase 3.4 (Calendar Integration)
    └── Phase 4.2 (Sound Library)

Phase 1.2 (Chain Engine)
    └── Phase 2.3 (Snooze & Dismissal)

Phase 2.1 (LLM Adapter)
    └── Phase 3.4 (Calendar Integration)

Phase 2.2 (TTS Adapter)
    ├── Phase 2.3 (Snooze & Dismissal)
    └── Phase 3.1 (Background Scheduling)

Phase 2.3 (Snooze & Dismissal)
    └── Phase 2.4 (Feedback Loop)

Phase 3.1 (Background Scheduling)
    ├── Phase 3.2 (Notification Behavior)
    └── Phase 3.3 (Location Awareness)

Phase 3.2 (Notification Behavior)
    └── Phase 4.1 (Voice Enhancements)

Phase 3.4 (Calendar Integration)
    └── Phase 5.1 (Testing)
```

---

## Priority Order Summary

1. **CRITICAL** - Phase 1.1: Database Schema Expansion
2. **HIGH** - Phase 1.2: Chain Engine Completeness
3. **HIGH** - Phase 2.1: LLM Adapter
4. **HIGH** - Phase 2.2: TTS Adapter & Clip Caching
5. **HIGH** - Phase 2.3: Snooze & Dismissal Flow
6. **HIGH** - Phase 2.4: Feedback Loop & Destination Adjustments
7. **MEDIUM** - Phase 3.1: Background Scheduling
8. **MEDIUM** - Phase 3.2: Notification & Alarm Behavior
9. **MEDIUM** - Phase 3.3: Location Awareness
10. **MEDIUM** - Phase 3.4: Calendar Integration
11. **MEDIUM** - Phase 4.1: Voice Personality Enhancements
12. **MEDIUM** - Phase 4.2: Sound Library
13. **LOW** - Phase 4.3: Data Retention
14. **HIGH** - Phase 5.1: Test Coverage (scenarios)
15. **MEDIUM** - Phase 5.2: Integration & E2E Tests
