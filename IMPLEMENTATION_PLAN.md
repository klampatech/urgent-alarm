# Implementation Plan: Urgent Voice Alarm

## Project Overview

A mobile alarm app that speaks escalating urgency messages, adapting based on remaining time and context. Users set reminders like "leave for Parker Dr in 30 minutes" and the app progressively nags with escalating messages.

## Gap Analysis Summary

**Current State:** `src/test_server.py` is a basic Python HTTP test server with minimal implementations of:
- Simple chain computation (partial)
- Keyword-based reminder parsing
- Template-based voice messages
- Basic SQLite schema

**Not Yet Implemented (per spec):** All core systems below.

---

## Priority 1: Foundation (Must Have First)

### 1.1 [ ] Complete Data Persistence Layer
**Why first:** All other systems depend on SQLite storage.

**Tasks:**
- [ ] Implement full schema from spec Section 13.3 (`reminders`, `anchors`, `history`, `user_preferences`, `destination_adjustments`, `calendar_sync`, `custom_sounds`)
- [ ] Add missing reminder fields: `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)
- [ ] Enable foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Implement sequential migration system (start at schema_v1)
- [ ] UUID v4 generation for all primary keys
- [ ] ISO 8601 timestamp handling (UTC storage, local display)

**Dependencies:** None

---

### 1.2 [ ] Complete Escalation Chain Engine
**Why first:** Core app logic; all reminders need anchors.

**Tasks:**
- [ ] Implement `compute_escalation_chain(arrival_time, drive_duration)` matching spec rules:
  - buffer ≥ 25 min: 8 anchors (full)
  - buffer 20-24 min: 7 anchors (skip calm)
  - buffer 10-19 min: 5 anchors (start at urgent)
  - buffer 5-9 min: 3 anchors (firm, critical, alarm)
  - buffer 1-4 min: 2 anchors (firm, alarm)
- [ ] Implement `get_next_unfired_anchor(reminder_id)` for scheduler recovery
- [ ] Add validation: `arrival_time > departure_time + minimum_drive_time`
- [ ] Ensure deterministic output for unit testing
- [ ] Store anchor records with: `id`, `reminder_id`, `timestamp`, `urgency_tier`, `tts_clip_path`, `tts_fallback`, `fired`, `fire_count`, `snoozed_to`
- [ ] Implement `get_anchors_sorted_by_timestamp(reminder_id)`

**Dependencies:** 1.1 Data Persistence

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

**Dependencies:** 1.1 Data Persistence

---

## Priority 2: Core Features (User-Facing)

### 2.1 [ ] Voice & TTS Generation System
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

**Dependencies:** 1.1 Data Persistence, 2.3 Voice Personality System

---

### 2.2 [ ] Voice Personality System
**Why concurrent with TTS:** Personality defines message generation.

**Tasks:**
- [ ] Implement 5 built-in personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
- [ ] Define per-personality: `voice_id`, `system_prompt` fragment, tier templates
- [ ] Implement Custom mode: user prompt (max 200 chars) appended to generation
- [ ] Store selected personality in `user_preferences`
- [ ] Generate 3+ message variations per tier per personality
- [ ] Message templates must include: `{dest}`, `{dur}`, `{remaining}`, `{plural}`
- [ ] `generate_voice_message()` function for TTS adapter

**Dependencies:** None (foundational)

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

**Dependencies:** 1.3 LLM Adapter, 2.1 TTS System

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

**Dependencies:** 2.1 TTS System, 2.2 Voice System

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

**Dependencies:** 2.4 Notification System, 1.1 Data Persistence

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

**Dependencies:** 2.5 Snooze Flow, 1.1 Data Persistence

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

**Dependencies:** 1.2 Chain Engine, 2.4 Notification System

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

**Dependencies:** 1.1 Data Persistence

---

## Priority 4: Testing & Quality

### 4.1 [ ] Unit Test Suite
**Why concurrent:** Ensure correctness as we build.

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

### 4.2 [ ] Integration Tests
**Why last:** Validate end-to-end flows.

**Tasks:**
- [ ] Test reminder creation → chain → TTS generation flow
- [ ] Test anchor firing with mock TTS
- [ ] Test background scheduling with mock Notifee
- [ ] Test snooze → re-computation → re-registration flow
- [ ] Test calendar sync → suggestion → reminder creation
- [ ] Test location check → immediate escalation flow

**Dependencies:** 3.1, 3.2, 3.3, 4.1

---

## Implementation Order Summary

```
Phase 1: Foundation
  1.1 Data Persistence Layer
  1.2 Escalation Chain Engine
  1.3 LLM Adapter & Parser

Phase 2: Core Features
  2.1 Voice Personality System (parallel with TTS)
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
  4.1 Unit Test Suite
  4.2 Integration Tests
```

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
# Validate test server
python3 -m py_compile src/test_server.py

# Run unit tests (when implemented)
python3 -m pytest harness/

# Manual harness test
sudo python3 harness/scenario_harness.py --project otto-matic
```
