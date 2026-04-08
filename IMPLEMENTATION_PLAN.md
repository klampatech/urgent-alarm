# Implementation Plan: Urgent Voice Alarm

## Project Overview

A mobile alarm app that speaks escalating urgency messages, adapting based on remaining time and context. Users set reminders like "leave for Parker Dr in 30 minutes" and the app progressively nags with escalating messages.

## Gap Analysis Summary

**Current State:** `src/test_server.py` is a basic Python HTTP test server with partial implementations of:
- Chain computation with **bugs** in compressed/minimum chains (wrong timestamps)
- Keyword-based reminder parsing (limited patterns, no confidence scoring)
- Voice personality templates (5 personalities, but NO variations)
- Basic SQLite schema (missing 5+ fields from spec)
- Basic hit rate calculation (incomplete)

**Bugs Found:**
1. Compressed chain (10-24 min buffer): timestamps off by 5 min
2. Minimum chain (< 5 min): incorrect tier assignments
3. Missing `get_next_unfired_anchor()` function
4. Missing `snoozed_to` field in anchors table

**Not Yet Implemented:**
- All adapter interfaces (ILanguageModel, ITTS, ICalendar)
- TTS cache manager and ElevenLabs integration
- Notification & alarm behavior system
- Background scheduling (Notifee)
- Snooze/dismissal flow with chain re-computation
- History stats with feedback loop
- Calendar and location integration
- Sound library
- Test harness infrastructure

---

## Priority 1: Critical Bug Fixes (Must Fix First)

### 1.1 [x] Chain Engine Bug Fixes
**Status:** BUGS FOUND - Existing chain computation has wrong timestamps.

**Bugs Identified:**
1. **Compressed chain (10-24 min buffer):** Uses `drive_duration - 5` which puts urgent at T-10 instead of T-15
2. **Minimum chain (< 5 min):** Logic doesn't match spec TC-03 (3 anchors: T-3, T-1, T-0)

**Fix Tasks:**
- [ ] Fix compressed chain: urgent should be `drive_duration - 15` (T-15), not T-10
- [ ] Fix minimum chain for 3-min buffer: should produce 3 anchors at T-3, T-1, T-0
- [ ] Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Add `snoozed_to` field to anchor computation

**Code Location:** `src/test_server.py` → `compute_escalation_chain()`

**Dependencies:** None (immediate fix)

---

### 1.2 [ ] Complete Data Persistence Layer
**Why first:** All other systems depend on SQLite storage.

**Tasks:**
- [ ] Add missing reminder fields: `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`
- [ ] Add missing tables: `calendar_sync`, `custom_sounds`
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Enable foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Implement sequential migration system (start at schema_v1)
- [ ] UUID v4 generation for all primary keys
- [ ] ISO 8601 timestamp handling (UTC storage, local display)

**Dependencies:** None

---

### 1.3 [ ] LLM Adapter Interface & Parser
**Why first:** Natural language input is the primary UX entry point.

**Tasks:**
- [ ] Create `ILanguageModelAdapter` abstract interface
- [ ] Implement `MiniMaxAdapter` (primary, Anthropic-compatible)
- [ ] Implement `AnthropicAdapter` (fallback)
- [ ] Implement `MockLanguageModelAdapter` for tests
- [ ] Implement keyword extraction fallback (regex patterns):
  - "X min drive", "X-minute drive", "in X minutes"
  - "arrive at X", "check-in at X"
  - "tomorrow Xpm", "today Xam"
- [ ] Parse fields: `destination`, `arrival_time` (ISO 8601), `drive_duration`, `reminder_type`
- [ ] Return `confidence_score` from keyword fallback
- [ ] Reject unintelligible input with user-facing error

**Dependencies:** 1.2 Data Persistence

---

## Priority 2: Core Features (User-Facing)

### 2.1 [ ] Voice Personality System with Variations
**Why second:** Currently has NO message variations.

**Tasks:**
- [ ] Generate 3+ message variations per tier per personality
- [ ] Implement Custom mode: user prompt (max 200 chars) appended to generation
- [ ] Store selected personality in `user_preferences`
- [ ] Message templates must include: `{dest}`, `{dur}`, `{remaining}`, `{plural}`
- [ ] `generate_voice_message()` function for TTS adapter

**Dependencies:** None (foundational)

---

### 2.2 [ ] Voice & TTS Generation System
**Why second:** Pre-generated clips eliminate runtime latency.

**Tasks:**
- [ ] Create `ITTSAdapter` abstract interface
- [ ] Implement `ElevenLabsAdapter` with:
  - Voice ID mapping per personality
  - Custom prompt passthrough
  - Async API with polling (30s timeout)
  - Error handling + fallback to system sound
- [ ] Implement `MockTTSAdapter` for tests
- [ ] Implement TTS cache manager:
  - Storage: `/tts_cache/{reminder_id}/{anchor_id}.mp3`
  - Cleanup on reminder deletion
  - Validation on load (file exists)
- [ ] Fallback behavior: system notification sound + text body if TTS fails
- [ ] Generate clips at reminder creation only

**Dependencies:** 1.2 Data Persistence, 2.1 Voice Personality System

---

### 2.3 [ ] Reminder Quick Add Flow
**Why second:** Primary user interaction.

**Tasks:**
- [ ] Create reminder form (text/speech input)
- [ ] Send input to LLM parser → get parsed result
- [ ] Display confirmation card with parsed fields
- [ ] Allow manual field correction before confirm
- [ ] On confirm: validate → compute chain → queue TTS generation
- [ ] Persist reminder with status "pending"
- [ ] Show progress indicator during TTS generation
- [ ] Handle reminder types: `countdown_event`, `simple_countdown`, `morning_routine`, `standing_recurring`

**Dependencies:** 1.3 LLM Adapter, 2.2 TTS System

---

### 2.4 [ ] Notification & Alarm Behavior
**Why second:** Users must receive reminders reliably.

**Tasks:**
- [ ] Implement notification tier escalation:
  - calm/casual: gentle chime
  - pointed/urgent: pointed beep
  - pushing/firm: urgent siren
  - critical/alarm: looping alarm
- [ ] Implement DND handling:
  - Pre-5-min anchors during DND: silent notification only
  - Final 5 min during DND: visual override + vibration + TTS
- [ ] Implement quiet hours (configurable, default 10pm-7am)
- [ ] Implement overdue anchor queue (≤15 min: fire after restriction; >15 min: drop)
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm loop (until dismiss/snooze)
- [ ] Notification display: destination, time remaining, personality icon

**Dependencies:** 2.2 TTS System, 2.1 Voice System

---

### 2.5 [ ] Snooze & Dismissal Flow
**Why third:** Interaction with active reminders.

**Tasks:**
- [ ] Tap snooze: pause 1 minute, TTS "Okay, snoozed 1 minute"
- [ ] Tap-and-hold snooze: picker with 1, 3, 5, 10, 15 min options
- [ ] Implement chain re-computation after snooze:
  - Shift remaining anchors by snooze duration
  - Re-register with Notifee with new timestamps
- [ ] Swipe-to-dismiss: show feedback prompt
- [ ] Feedback options: "Yes — timing was right" / "No — timing was off"
- [ ] If "timing was off": show "Left too early" / "Left too late" / "Other"
- [ ] Store feedback in `history` table
- [ ] TTS confirmation for all snooze actions
- [ ] Persist snooze state for app restart recovery

**Dependencies:** 2.4 Notification System, 1.2 Data Persistence

---

### 2.6 [ ] History, Stats & Feedback Loop
**Why concurrent:** Uses existing data structures.

**Tasks:**
- [ ] Calculate hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for 7 days
- [ ] Implement destination adjustment: `adjusted_drive_duration = original + (late_count * 2min)`, capped at +15 min
- [ ] Identify common miss window (most frequently missed urgency tier)
- [ ] Implement streak counter for standing/recurring reminders
- [ ] Store all history in `history` table (90-day retention)
- [ ] Archive data older than 90 days (accessible, not deleted)
- [ ] Stats derived entirely from history table (no separate store)

**Dependencies:** 2.5 Snooze Flow, 1.2 Data Persistence

---

## Priority 3: Background & Platform Integration

### 3.1 [ ] Background Scheduling (Notifee)
**Why third:** Reminders must fire when app is closed.

**Tasks:**
- [ ] Integrate Notifee for iOS/Android background tasks
- [ ] Register each anchor as individual Notifee task with trigger timestamp
- [ ] iOS: use BGAppRefreshTask for timing, BGProcessingTask for TTS pre-warm
- [ ] Implement recovery scan on app launch:
  - Find overdue unfired anchors within 15-min grace window
  - Fire them in timestamp order
  - Drop anchors >15 min overdue, log with `missed_reason`
- [ ] Re-register all pending anchors on app restart after crash
- [ ] Log warning if anchor fires >60s after scheduled time
- [ ] Persist all anchor state to SQLite (survives termination)

**Dependencies:** 1.1 Chain Engine, 2.4 Notification System

---

### 3.2 [ ] Calendar Integration
**Why fourth:** Optional but high-value feature.

**Tasks:**
- [ ] Create `ICalendarAdapter` abstract interface
- [ ] Implement `AppleCalendarAdapter` (EventKit, iOS)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement calendar sync:
  - On app launch, every 15 min while app open, via background refresh
  - Only events with `location` field
- [ ] Surface suggestion card for location events
- [ ] On confirm: create countdown_event reminder with event data
- [ ] Calendar-sourced reminders: show calendar icon
- [ ] Handle recurring events (generate reminder per occurrence)
- [ ] Permission denial: show explanation banner with settings link
- [ ] Sync failure: graceful degradation, error banner

**Dependencies:** 1.3 LLM Adapter

---

### 3.3 [ ] Location Awareness
**Why fourth:** Optional escalation enhancement.

**Tasks:**
- [ ] Implement single location check at departure anchor (T-drive_duration)
- [ ] Origin resolution: user-specified address or device location at creation
- [ ] CoreLocation (iOS) / FusedLocationProvider (Android) single call at trigger
- [ ] Geofence comparison: 500m radius
- [ ] If within 500m of origin: fire firm/critical tier immediately instead of calm departure
- [ ] If >500m: proceed with normal chain
- [ ] Request location permission at first location-aware reminder (not app launch)
- [ ] If denied: create reminder without location escalation, show note
- [ ] Do NOT store location history

**Dependencies:** 3.1 Background Scheduling

---

### 3.4 [ ] Sound Library
**Why fifth:** Nice-to-have enhancement.

**Tasks:**
- [ ] Bundle built-in sounds: Commute (5), Routine (5), Errand (5)
- [ ] Support Custom category: import MP3, WAV, M4A (max 30 sec)
- [ ] Transcode imported sounds to normalized format
- [ ] Store custom sound references in `custom_sounds` table
- [ ] Per-reminder sound selection (override category default)
- [ ] Corrupted/missing file: fallback to category default, log error
- [ ] Sound selection persists on reminder edit

**Dependencies:** 1.2 Data Persistence

---

## Priority 4: Testing & Quality

### 4.1 [ ] Test Harness Infrastructure
**Why concurrent:** The `harness/` directory is empty; scenarios exist but can't run.

**Tasks:**
- [ ] Create `harness/scenario_harness.py` - main test runner
- [ ] Implement scenario loader from YAML files
- [ ] Implement HTTP client for API calls
- [ ] Implement SQLite assertions for DB verification
- [ ] Implement LLM judge assertions (uses sonnet-4-20250514)
- [ ] Support `OTTO_SCENARIO_DIR` environment variable
- [ ] Support `--project` CLI flag

**Dependencies:** None

---

### 4.2 [ ] Unit Test Suite
**Why second:** Ensure correctness as we build.

**Tasks:**
- [ ] Test escalation chain (TC-01 through TC-06 from spec)
- [ ] Test parser with mock adapter (TC-01 through TC-07)
- [ ] Test TTS adapter mock
- [ ] Test voice personality message generation
- [ ] Test hit rate calculation (TC-01 through TC-07)
- [ ] Test snooze chain re-computation
- [ ] Test database migrations and cascade delete
- [ ] All tests use in-memory SQLite

**Dependencies:** 1.1, 1.2, 1.3, 2.1, 2.2, 2.6

---

### 4.3 [ ] Integration Tests
**Why last:** Validate end-to-end flows.

**Tasks:**
- [ ] Test reminder creation → chain → TTS generation flow
- [ ] Test anchor firing with mock TTS
- [ ] Test background scheduling with mock Notifee
- [ ] Test snooze → re-computation → re-registration flow
- [ ] Test calendar sync → suggestion → reminder creation
- [ ] Test location check → immediate escalation flow

**Dependencies:** 3.1, 3.2, 3.3, 4.2

---

## Implementation Order Summary

```
Phase 0: Critical Fixes (Do First!)
  1.1 Chain Engine Bug Fixes (timestamp corrections)

Phase 1: Foundation
  1.2 Data Persistence Layer (complete schema)
  1.3 LLM Adapter & Parser

Phase 2: Core Features
  2.1 Voice Personality System (add variations)
  2.2 Voice & TTS Generation
  2.3 Reminder Quick Add Flow
  2.4 Notification & Alarm Behavior
  2.5 Snooze & Dismissal Flow
  2.6 History, Stats & Feedback Loop

Phase 3: Platform Integration
  3.1 Background Scheduling (Notifee)
  3.2 Calendar Integration
  3.3 Location Awareness
  3.4 Sound Library

Phase 4: Testing
  4.1 Test Harness Infrastructure
  4.2 Unit Test Suite
  4.3 Integration Tests
```

## Scenario Files Coverage

| Scenario | Spec Section | Current Status |
|----------|-------------|----------------|
| `chain-full-30min.yaml` | 2, TC-01 | ⚠️ Partial (code exists, has bugs) |
| `chain-compressed-15min.yaml` | 2, TC-02 | ❌ BUGGY (wrong timestamps) |
| `chain-minimum-3min.yaml` | 2, TC-03 | ❌ BUGGY (wrong tiers) |
| `chain-invalid-rejected.yaml` | 2, TC-04 | ✅ Works |
| `parse-natural-language.yaml` | 3, TC-01 | ⚠️ Partial (basic patterns) |
| `parse-simple-countdown.yaml` | 3, TC-02 | ⚠️ Partial |
| `parse-tomorrow.yaml` | 3, TC-03 | ⚠️ Partial |
| `voice-coach-personality.yaml` | 10, TC-01 | ❌ NO VARIATIONS |
| `voice-no-nonsense.yaml` | 10, TC-02 | ❌ NO VARIATIONS |
| `voice-all-personalities.yaml` | 10 | ❌ NO VARIATIONS |
| `history-record-outcome.yaml` | 11 | ✅ Works |
| `history-record-miss-feedback.yaml` | 11, TC-05 | ✅ Works |
| `stats-hit-rate.yaml` | 11, TC-01 | ⚠️ Partial |
| `reminder-creation-crud.yaml` | 13 | ✅ Works |
| `reminder-creation-cascade-delete.yaml` | 13, TC-03 | ⚠️ Partial (no cascade) |
| `chain-20-24min-buffer.yaml` | 2 | ❌ Missing |
| `parse-api-failure-fallback.yaml` | 3, TC-04 | ❌ Missing |
| `parse-manual-correction.yaml` | 3, TC-05 | ❌ Missing |
| `parse-unintelligible.yaml` | 3, TC-06 | ❌ Missing |
| `tts-fallback-on-error.yaml` | 4, TC-03 | ❌ Missing |
| `snooze-chain-recomputation.yaml` | 9, TC-03 | ❌ Missing |
| `feedback-loop-adjustment.yaml` | 11, TC-02 | ❌ Missing |
| `feedback-loop-cap.yaml` | 11, TC-03 | ❌ Missing |
| `common-miss-window.yaml` | 11, TC-04 | ❌ Missing |
| `streak-increment.yaml` | 11, TC-05 | ❌ Missing |
| `streak-reset.yaml` | 11, TC-06 | ❌ Missing |
| `quiet-hours.yaml` | 5, TC-03 | ❌ Missing |
| `dnd-final-5min-override.yaml` | 5, TC-02 | ❌ Missing |
| `overdue-anchor-drop.yaml` | 5, TC-04 | ❌ Missing |
| `chain-overlap-serialization.yaml` | 5, TC-05 | ❌ Missing |
| `recovery-scan.yaml` | 6, TC-03 | ❌ Missing |
| `pending-anchors-reregister.yaml` | 6, TC-05 | ❌ Missing |

**Legend:** ✅ Works | ⚠️ Partial/Buggy | ❌ Missing

## Out of Scope (Per Spec)

- Password reset / auth (v1: local-only)
- Smart home integration
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Continuous location tracking
- Voice recording import
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search

---

## Verification Commands

```bash
# Validate test server (syntax check)
python3 -m py_compile src/test_server.py

# Start test server
python3 src/test_server.py &

# Run unit tests (when harness is implemented)
python3 -m pytest harness/

# Manual harness test
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Test specific scenario directory
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project urgent-alarm
```

## Quick Fix Checklist

Before moving to new features, verify these work:

- [ ] **Chain full (30min):** `GET /chain?arrival=2026-04-09T09:00:00&duration=30` returns 8 anchors
- [ ] **Chain compressed (15min):** Timestamps should be 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] **Chain minimum (3min):** Should produce 3 anchors at T-3, T-1, T-0
- [ ] **Invalid chain:** `POST /reminders` with drive_duration=120 returns 400
- [ ] **Parse NL:** `POST /parse` extracts destination, arrival_time, drive_duration
- [ ] **Voice messages:** All 5 personalities generate appropriate messages
- [ ] **Stats:** Hit rate calculation is correct

## Key Files to Modify

| File | Purpose | Change Type |
|------|---------|-------------|
| `src/test_server.py` | Main HTTP API server | Bug fixes + features |
| `src/test_server.py` | `compute_escalation_chain()` | Fix timestamps |
| `src/test_server.py` | Database schema | Add missing tables/fields |
| `harness/scenario_harness.py` | Test runner | New file |
| `scenarios/*.yaml` | Validation tests | Add missing scenarios |
