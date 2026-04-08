# Implementation Plan: Urgent AI Escalating Voice Alarm

## Project Status

**Current State**: Single Python test server (`src/test_server.py`) implementing ~15% of the full specification. The server provides mock endpoints for scenario testing but lacks most core features.

**Target State**: Full mobile app (React Native) with Python backend services for LLM/TTS integration.

---

## Gap Analysis Summary

| Spec Section | Status | Coverage |
|--------------|--------|----------|
| 2. Escalation Chain Engine | Partial | ~60% |
| 3. Reminder Parsing & Creation | Minimal | ~30% |
| 4. Voice & TTS Generation | Absent | 0% |
| 5. Notification & Alarm Behavior | Absent | 0% |
| 6. Background Scheduling | Absent | 0% |
| 7. Calendar Integration | Absent | 0% |
| 8. Location Awareness | Absent | 0% |
| 9. Snooze & Dismissal Flow | Absent | 0% |
| 10. Voice Personality System | Partial | ~40% |
| 11. History, Stats & Feedback Loop | Minimal | ~20% |
| 12. Sound Library | Absent | 0% |
| 13. Data Persistence | Minimal | ~30% |

---

## Phase 1: Core Foundation (Foundation / High Priority)

### 1.1 Complete Escalation Chain Engine
**Priority**: P0 (Critical)
**Owner**: Backend
**Spec Ref**: Section 2

**What's Missing**:
- `get_next_unfired_anchor()` function for scheduler recovery
- Chain determinism validation (needed for testing)
- Validation that `arrival_time > departure_time + minimum_drive_time`
- Anchor sorting in database (ASC by timestamp)

**Tasks**:
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add chain determinism assertion (same inputs → same outputs)
- [ ] Add complete validation: `drive_duration < time_to_arrival` (not just past check)
- [ ] Add `ORDER BY timestamp ASC` to all anchor queries
- [ ] Add unit tests for all 6 test scenarios (TC-01 through TC-06)

**Acceptance Criteria**:
- Chain for "30 min drive, arrive 9am" produces exactly 8 anchors
- Chain for "10 min drive, arrive 9am" produces exactly 4 anchors
- Invalid chains (drive_duration > arrival_time) are rejected
- Recovery function returns earliest unfired anchor

---

### 1.2 Implement LLM Parser Adapter
**Priority**: P0 (Critical)
**Owner**: Backend
**Spec Ref**: Section 3

**What's Missing**:
- No LLM adapter interface (`ILanguageModelAdapter`)
- No MiniMax API integration (Anthropic-compatible endpoint)
- No proper Anthropic API fallback
- Only keyword extraction exists

**Tasks**:
- [ ] Create `ILanguageModelAdapter` interface/class hierarchy
- [ ] Implement `MockLanguageModelAdapter` for testing
- [ ] Implement `MiniMaxAdapter` with API configuration via env var
- [ ] Implement `AnthropicAdapter` as fallback
- [ ] Add proper fallback logic: LLM → keyword extraction
- [ ] Implement `confidence_score` calculation
- [ ] Handle "tomorrow" date resolution correctly
- [ ] Add unit tests for parsing scenarios (TC-01 through TC-07)

**Acceptance Criteria**:
- Parser extracts destination, arrival_time, drive_duration from natural language
- Empty input returns user-facing error
- LLM API failure falls back to keyword extraction
- Mock adapter returns fixture without real API call

---

### 1.3 Complete Data Persistence Schema
**Priority**: P0 (Critical)
**Owner**: Backend
**Spec Ref**: Section 13

**What's Missing**:
- Missing columns: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`
- Missing tables: `calendar_sync`, `custom_sounds`
- Missing columns: `snoozed_to`, `actual_arrival`, `missed_reason` in anchors/history
- No migration system (sequential, versioned)
- No UUID v4 enforcement on `reminders.id`

**Tasks**:
- [ ] Add missing columns to `reminders` table
- [ ] Add `snoozed_to` column to `anchors` table
- [ ] Add missing columns to `history` table (`actual_arrival`, `missed_reason`)
- [ ] Create `calendar_sync` table
- [ ] Create `custom_sounds` table
- [ ] Implement sequential migration system (v1 through current)
- [ ] Enforce UUID v4 validation on reminder creation
- [ ] Enable foreign key enforcement (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)

**Acceptance Criteria**:
- Fresh install applies all migrations in order
- Cascade delete works (deleting reminder deletes anchors)
- UUID v4 is validated on insert
- Foreign key violations return errors

---

## Phase 2: External Integrations (Medium Priority)

### 2.1 TTS Adapter (ElevenLabs)
**Priority**: P1 (High)
**Owner**: Backend
**Spec Ref**: Section 4

**What's Missing**:
- No `ITTSAdapter` interface
- No ElevenLabs API integration
- TTS clips not actually generated (just template strings)
- No `/tts_cache/` directory structure
- No cache cleanup on reminder deletion

**Tasks**:
- [ ] Create `ITTSAdapter` interface
- [ ] Implement `MockTTSAdapter` for testing
- [ ] Implement `ElevenLabsAdapter` with API config via env var
- [ ] Create `/tts_cache/{reminder_id}/` directory structure
- [ ] Implement TTS generation at reminder creation
- [ ] Implement fallback: system sound + notification text on API failure
- [ ] Implement cache cleanup on reminder deletion
- [ ] Add unit tests (TC-01 through TC-05)

**Acceptance Criteria**:
- TTS generation runs at reminder creation only (not runtime)
- Generated clips cached in local filesystem
- Failed TTS falls back to system sound gracefully
- Reminder deletion removes all cached TTS files

---

### 2.2 Voice Personality System
**Priority**: P1 (High)
**Owner**: Backend
**Spec Ref**: Section 10

**What's Missing**:
- Only 5 personalities exist, but "custom" mode not implemented
- No per-tier message variations (minimum 3 per tier required)
- No personality stored per reminder (hardcoded in templates)
- No system prompt fragments for LLM message generation

**Tasks**:
- [ ] Expand each personality to 3+ message variations per tier
- [ ] Implement custom prompt mode (user-written, max 200 chars)
- [ ] Add `voice_personality` to reminder record
- [ ] Create personality system prompt fragments for LLM
- [ ] Add per-reminder personality override capability
- [ ] Add unit tests for personality message generation (TC-01 through TC-05)

**Acceptance Criteria**:
- Each personality generates at least 3 distinct messages per tier
- Custom prompts modify message tone appropriately
- Existing reminders retain personality from creation time
- "Coach" at T-5 produces motivating message with exclamation

---

## Phase 3: Mobile Features (High Priority)

### 3.1 Snooze & Dismissal Flow
**Priority**: P1 (High)
**Owner**: Mobile
**Spec Ref**: Section 9

**What's Missing**:
- No tap-snooze (1 min) implementation
- No tap-and-hold custom snooze picker
- No chain re-computation after snooze
- No feedback prompt UI
- No feedback storage and drive_duration adjustment

**Tasks**:
- [ ] Implement tap-snooze: pause current anchor, re-fire after 1 min
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation: shift remaining anchors
- [ ] Implement swipe-dismiss feedback prompt UI
- [ ] Store feedback in SQLite
- [ ] Implement drive_duration adjustment (+2 min per "left_too_late", cap +15)
- [ ] Implement TTS snooze confirmation: "Okay, snoozed X minutes"
- [ ] Persist snoozed timestamps across app restart

**Acceptance Criteria**:
- Tap snooze pauses and re-fires after 1 minute
- Chain re-computation shifts all remaining anchors correctly
- Feedback prompt appears on swipe-dismiss
- "Left too late" increases future drive_duration by 2 min

---

### 3.2 Notification & Alarm Behavior
**Priority**: P1 (High)
**Owner**: Mobile
**Spec Ref**: Section 5

**What's Missing**:
- No notification tier escalation (gentle → pointed → urgent → alarm)
- No DND awareness
- No quiet hours / sleep mode
- No chain overlap serialization (queue new anchors)
- No T-0 alarm looping

**Tasks**:
- [ ] Implement notification tier escalation per urgency tier
- [ ] Integrate iOS notification categories and actions
- [ ] Implement DND detection and suppression
- [ ] Implement quiet hours configuration and enforcement
- [ ] Implement anchor queue for chain overlap
- [ ] Implement T-0 alarm looping until user action
- [ ] Display notification: destination, time remaining, personality icon

**Acceptance Criteria**:
- Early anchors use gentle notification sounds
- Final 5 minutes use alarm sounds with vibration
- DND suppresses early anchors, final 5 minutes override
- T-0 alarm loops until dismissed or snoozed

---

### 3.3 Background Scheduling (Notifee)
**Priority**: P1 (High)
**Owner**: Mobile
**Spec Ref**: Section 6

**What's Missing**:
- No Notifee integration (BGTaskScheduler / WorkManager)
- No anchor re-registration on crash recovery
- No recovery scan on app launch
- No 15-minute grace window enforcement

**Tasks**:
- [ ] Integrate Notifee for iOS background scheduling
- [ ] Register each anchor as individual background task
- [ ] Implement recovery scan on app launch
- [ ] Implement 15-minute grace window for overdue anchors
- [ ] Log missed anchors with `missed_reason = "background_task_killed"`
- [ ] Re-register pending anchors on crash recovery
- [ ] Add late firing warning (>60s delay logged)

**Acceptance Criteria**:
- App closed does not prevent anchors from firing
- Recovery scan fires anchors within 15-min grace window
- Anchors >15 min overdue are dropped and logged
- Late firing (>60s) triggers warning log

---

### 3.4 History, Stats & Feedback Loop
**Priority**: P2 (Medium)
**Owner**: Backend + Mobile
**Spec Ref**: Section 11

**What's Missing**:
- Hit rate calculation (basic exists)
- "Common miss window" calculation
- Streak counter for recurring reminders
- 90-day data retention/archival
- Full stats computable from history table

**Tasks**:
- [ ] Implement "common miss window" query (most frequently missed tier)
- [ ] Implement streak counter logic (increment on hit, reset on miss)
- [ ] Implement 90-day data archival
- [ ] Create stats API endpoints
- [ ] Implement weekly hit rate display
- [ ] Create history UI (list view with outcomes)
- [ ] Add stats test scenarios (TC-01 through TC-07)

**Acceptance Criteria**:
- Weekly hit rate displays correctly (4 hits, 1 miss = 80%)
- "Common miss window" identifies most missed tier
- Streak increments on hit, resets on miss
- All stats derived from history table

---

## Phase 4: External Services (Medium Priority)

### 4.1 Calendar Integration
**Priority**: P2 (Medium)
**Owner**: Backend + Mobile
**Spec Ref**: Section 7

**What's Missing**:
- No Apple Calendar (EventKit) integration
- No Google Calendar API integration
- No `ICalendarAdapter` interface
- No calendar sync scheduler (15-min interval)
- No suggestion cards UI

**Tasks**:
- [ ] Create `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement calendar sync scheduler (launch + 15-min refresh)
- [ ] Filter events with non-empty location only
- [ ] Create suggestion card UI
- [ ] Handle permission denial gracefully
- [ ] Implement recurring event handling
- [ ] Add unit tests (TC-01 through TC-06)

**Acceptance Criteria**:
- Apple Calendar events with locations appear as suggestions
- Google Calendar events with locations appear as suggestions
- Calendar permission denial shows explanation banner
- Recurring events generate reminder for each occurrence

---

### 4.2 Location Awareness
**Priority**: P2 (Medium)
**Owner**: Mobile
**Spec Ref**: Section 8

**What's Missing**:
- No CoreLocation integration (single check)
- No origin location storage/retrieval
- No geofence comparison (500m radius)
- No "still at origin" escalation trigger

**Tasks**:
- [ ] Request location permission at first location-aware reminder creation
- [ ] Store origin location (user-specified or current device location)
- [ ] Implement single location check at departure anchor fire
- [ ] Implement geofence comparison (500m radius = "at origin")
- [ ] Implement "still at origin" escalation: fire critical/urgent tier immediately
- [ ] Implement location permission denied handling
- [ ] Ensure no location history stored beyond comparison
- [ ] Add unit tests (TC-01 through TC-05)

**Acceptance Criteria**:
- Location check occurs only at departure anchor (not continuous)
- User at origin triggers immediate escalation
- User already left proceeds with normal chain
- Location data not stored after comparison

---

### 4.3 Sound Library
**Priority**: P3 (Lower)
**Owner**: Mobile
**Spec Ref**: Section 12

**What's Missing**:
- No built-in sound library (5 per category)
- No custom audio import (MP3, WAV, M4A)
- No file picker integration
- No per-reminder sound selection
- No corrupted sound fallback

**Tasks**:
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom sound import (file picker)
- [ ] Validate imported audio (MP3/WAV/M4A, max 30 sec)
- [ ] Store custom sounds in app sandbox
- [ ] Implement per-reminder sound selection
- [ ] Implement corrupted sound fallback (category default + error)
- [ ] Add unit tests (TC-01 through TC-05)

**Acceptance Criteria**:
- Built-in sounds play without network access
- Custom MP3 import appears in sound picker
- Corrupted custom sound uses category default

---

## Implementation Order

```
Phase 1 (Foundation)
├── 1.1 Complete Escalation Chain Engine
├── 1.2 Implement LLM Parser Adapter
└── 1.3 Complete Data Persistence Schema

Phase 2 (External Integrations)
├── 2.1 TTS Adapter (ElevenLabs)
└── 2.2 Voice Personality System

Phase 3 (Mobile Features)
├── 3.1 Snooze & Dismissal Flow
├── 3.2 Notification & Alarm Behavior
├── 3.3 Background Scheduling (Notifee)
└── 3.4 History, Stats & Feedback Loop

Phase 4 (External Services)
├── 4.1 Calendar Integration
├── 4.2 Location Awareness
└── 4.3 Sound Library
```

---

## Testing Requirements

Per spec Section 14, every acceptance criterion must have a passing test. Test scenarios are defined per section (TC-01 through TC-0N).

**Immediate Test Coverage Needed**:
1. Chain Engine (6 scenarios)
2. Reminder Parsing (7 scenarios)
3. TTS Generation (5 scenarios)
4. Voice Personality (5 scenarios)
5. Notification Behavior (6 scenarios)
6. Background Scheduling (6 scenarios)
7. Calendar Integration (6 scenarios)
8. Location Awareness (5 scenarios)
9. Snooze & Dismissal (6 scenarios)
10. History & Stats (7 scenarios)
11. Sound Library (5 scenarios)
12. Data Persistence (5 scenarios)

**Total**: 74 test scenarios minimum

---

## Open Questions (From Spec)

1. Speaker vs. Bluetooth audio routing (speaker-only in v1 per spec)
2. Voice reply / spoken snooze (future consideration)
3. Gentle mode for calm-only nudges (user preference)
4. Smart home integration (Hue lights - future consideration)

These are explicitly marked out of scope or future consideration. Do not implement in v1.
