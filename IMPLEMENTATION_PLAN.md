# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Overview

This plan identifies gaps between `specs/urgent-voice-alarm-app-2026-04-08.spec.md` and the current implementation in `src/test_server.py`. The test server provides an HTTP API with core chain engine, parser, and voice personality logic, but has significant gaps from the full specification.

---

## Gap Analysis Summary

| Spec Section | Implementation Status | Priority | Gap |
|--------------|----------------------|----------|-----|
| 2. Escalation Chain Engine | ⚠️ Partial | P1 | 3-min buffer bug (missing critical anchor) |
| 3. Reminder Parsing | ⚠️ Partial | P1 | Regex bug in relative time; no LLM adapter interface |
| 4. Voice & TTS Generation | ⚠️ Text-only | P2 | No file caching, no adapter interface |
| 5. Notification & Alarm | ❌ Not implemented | P2 | DND, quiet hours, chain overlap missing |
| 6. Background Scheduling | ❌ Not implemented | P2 | No Notifee, no recovery scan |
| 7. Calendar Integration | ❌ Not implemented | P3 | — |
| 8. Location Awareness | ❌ Not implemented | P3 | — |
| 9. Snooze & Dismissal | ⚠️ Partial | P2 | Feedback loop started, snooze flow missing |
| 10. Voice Personality System | ⚠️ Partial | P2 | Missing message variations (spec: 3 min per tier) |
| 11. History, Stats & Feedback | ⚠️ Partial | P2 | Hit rate done; streaks, common miss missing |
| 12. Sound Library | ❌ Not implemented | P3 | — |
| 13. Data Persistence | ⚠️ Partial | P1 | Basic schema, missing fields, no migrations |

---

## Priority 1: Foundation (Must Fix First)

### Task 1.1: Fix Escalation Chain Engine Bugs
**Spec Reference:** Section 2

**Current Issues:**
- 3-min buffer produces only 2 anchors (missing `critical` anchor)
- 10-min buffer has ordering issues (`critical` appears before `pushing`)

**Test Results:**
```
30-min buffer: ✓ 8 anchors (correct)
10-min buffer: ✗ 4 anchors but wrong order (critical before pushing)
3-min buffer:  ✗ 2 anchors (missing critical)
```

**Tasks:**
- [ ] Fix 3-min buffer to produce 3 anchors: T-3 (firm), T-1 (critical), T-0 (alarm)
- [ ] Fix 10-min buffer anchor ordering
- [ ] Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Verify chain determinism (same inputs → same outputs)

**Acceptance Criteria:**
- 30-min drive → 8 anchors: 8:30(calm), 8:35(casual), 8:40(pointed), 8:45(urgent), 8:50(pushing), 8:55(firm), 8:59(critical), 9:00(alarm)
- 10-min drive → 4 anchors: 8:50(urgent), 8:55(pushing), 8:59(critical), 9:00(alarm)
- 3-min drive → 3 anchors: 8:57(firm), 8:59(critical), 9:00(alarm)
- `get_next_unfired_anchor` returns earliest unfired anchor

---

### Task 1.2: Fix Natural Language Parser Bugs
**Spec Reference:** Section 3

**Current Issues:**
- `"dryer in 3 min"` causes IndexError (regex group mismatch)
- No LLM adapter interface (keyword extraction only)

**Tasks:**
- [ ] Fix regex pattern for relative time `"in X minutes"`
- [ ] Implement `ILanguageModelAdapter` abstract interface
- [ ] Implement `MockLLMAdapter` for testing with fixture responses
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible)
- [ ] Implement `AnthropicAdapter`
- [ ] Add keyword extraction fallback on LLM failure

**Acceptance Criteria:**
- `"30 minute drive to Parker Dr, check-in at 9am"` → dest, arrival_time, drive_duration extracted
- `"dryer in 3 min"` → simple_countdown with arrival = now + 3 min
- `"meeting tomorrow 2pm, 20 min drive"` → next day's 2pm
- Mock adapter returns fixture without API call

---

### Task 1.3: Expand Data Persistence Schema
**Spec Reference:** Section 13

**Current Schema Gaps:**
- Missing: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`
- Missing: `snoozed_to`, `tts_fallback` in anchors
- Missing: `missed_reason`, `actual_arrival` in history
- Missing: `calendar_sync` table, `custom_sounds` table
- Missing: migration system

**Tasks:**
- [ ] Add missing columns to `reminders` table
- [ ] Add `snoozed_to`, `tts_fallback` to `anchors` table
- [ ] Add `missed_reason`, `actual_arrival` to `history` table
- [ ] Create `calendar_sync` table
- [ ] Create `custom_sounds` table
- [ ] Implement sequential migration system
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Add in-memory test database support (`?mode=memory`)

**Schema Changes Required:**
```sql
-- reminders: add origin fields, calendar_event_id, sound fields
ALTER TABLE reminders ADD COLUMN origin_lat REAL;
ALTER TABLE reminders ADD COLUMN origin_lng REAL;
ALTER TABLE reminders ADD COLUMN origin_address TEXT;
ALTER TABLE reminders ADD COLUMN calendar_event_id TEXT;
ALTER TABLE reminders ADD COLUMN custom_sound_path TEXT;
ALTER TABLE reminders ADD COLUMN sound_category TEXT;
ALTER TABLE reminders ADD COLUMN selected_sound TEXT;

-- anchors: add snoozed_to, tts_fallback
ALTER TABLE anchors ADD COLUMN snoozed_to TEXT;
ALTER TABLE anchors ADD COLUMN tts_fallback INTEGER DEFAULT 0;

-- history: add missed_reason, actual_arrival
ALTER TABLE history ADD COLUMN missed_reason TEXT;
ALTER TABLE history ADD COLUMN actual_arrival TEXT;

-- New tables
CREATE TABLE calendar_sync (
  calendar_type TEXT PRIMARY KEY,
  last_sync_at TEXT,
  sync_token TEXT,
  is_connected INTEGER DEFAULT 0
);

CREATE TABLE custom_sounds (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  category TEXT NOT NULL,
  file_path TEXT NOT NULL,
  duration_seconds REAL,
  created_at TEXT NOT NULL
);
```

---

## Priority 2: Core Features

### Task 2.1: Complete Voice Personality System
**Spec Reference:** Section 10

**Current State:** 5 personalities exist with 1 template per tier.
**Required:** Minimum 3 message variations per tier per personality.

**Tasks:**
- [ ] Create 3 variations for each urgency tier (8 tiers × 5 personalities = 120 messages minimum)
- [ ] Implement random variation selection in `generate_voice_message()`
- [ ] Add `custom_prompt` support in user preferences

**Variations Required Per Personality:**
| Tier | Current | Required | Gap |
|------|---------|----------|-----|
| calm | 1 | 3 | +2 |
| casual | 1 | 3 | +2 |
| pointed | 1 | 3 | +2 |
| urgent | 1 | 3 | +2 |
| pushing | 1 | 3 | +2 |
| firm | 1 | 3 | +2 |
| critical | 1 | 3 | +2 |
| alarm | 1 | 3 | +2 |

**Acceptance Criteria:**
- Each personality generates at least 3 distinct messages per tier
- "Coach" at T-5: motivational, exclamation present
- "No-nonsense" at T-5: brief, direct, no filler
- Custom prompt modifies tone appropriately

---

### Task 2.2: Implement Snooze & Dismissal Flow
**Spec Reference:** Section 9

**Current State:** History endpoint handles feedback loop; snooze flow not implemented.

**Tasks:**
- [ ] Add `POST /snooze` endpoint with `anchor_id` and `duration` (default 1 min)
- [ ] Implement `recompute_chain_after_snooze(reminder_id, snooze_minutes)` function
- [ ] Add `snoozed_to` timestamp update to anchor record
- [ ] Implement `POST /dismiss` endpoint with `reminder_id`
- [ ] Add feedback prompt display ("Was the timing right?")
- [ ] Implement feedback response storage ("Left too early", "Left too late", "Other")
- [ ] Generate TTS confirmation: "Okay, snoozed X minutes."

**Chain Re-computation Logic:**
```
Original: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
Snooze at 8:45 for 3 min → now = 8:48
Remaining shifted: 8:48, 8:53, 8:59, 9:00
```

**Acceptance Criteria:**
- Tap snooze re-fires after 1 minute
- Custom snooze allows 1, 3, 5, 10, 15 minute selection
- Chain re-computation shifts remaining anchors correctly
- Feedback prompt appears on dismiss
- "Left too late" increases drive_duration by 2 min for destination
- TTS confirms: "Okay, snoozed X minutes"

---

### Task 2.3: Complete Feedback Loop & Stats
**Spec Reference:** Section 11

**Current State:** `calculate_hit_rate()` implemented; streak counter and common miss window missing.

**Tasks:**
- [ ] Implement `GET /stats/streaks` for recurring reminder streaks
- [ ] Implement `GET /stats/common-miss` (most frequently missed urgency tier)
- [ ] Add adjustment cap at +15 minutes
- [ ] Implement streak increment on hit, reset on miss
- [ ] Implement 90-day data retention logic (archive old records)

**Adjustment Formula:**
```
adjusted_drive_duration = stored_drive_duration + (late_count * 2)
capped at +15 minutes
```

**Acceptance Criteria:**
- After 3 "Left too late" for "Parker Dr": next reminder adds 6 min
- After 10+ late feedback: adjustment capped at +15 min
- "Common miss window" identifies most missed urgency tier
- Streak increments on hit, resets on miss

---

### Task 2.4: Implement TTS Adapter Interface
**Spec Reference:** Section 4

**Current State:** `generate_voice_message()` produces text only.

**Tasks:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement `MockTTSAdapter` (writes silent file for tests)
- [ ] Implement `ElevenLabsAdapter` (actual TTS integration)
- [ ] Create TTS cache directory structure (`/tts_cache/{reminder_id}/`)
- [ ] Implement `generate_tts_clip()` at reminder creation
- [ ] Implement `play_tts_clip(anchor_id)` for anchor firing
- [ ] Implement cache invalidation on reminder deletion
- [ ] Implement fallback to notification sound on TTS failure

**Acceptance Criteria:**
- TTS clips stored in `/tts_cache/{reminder_id}/`
- Playing anchor uses local cached file
- TTS failure gracefully falls back to notification sound
- Reminder deletion removes cached TTS files

---

### Task 2.5: Implement Notification & Alarm Behavior
**Spec Reference:** Section 5

**Current State:** Not implemented.

**Tasks:**
- [ ] Implement DND status detection
- [ ] Implement silent notification for early anchors during DND
- [ ] Implement visual override + vibration for final 5 minutes during DND
- [ ] Implement quiet hours configuration and suppression
- [ ] Implement post-restriction queue with 15-minute grace window
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] Implement T-0 alarm looping until user action
- [ ] Implement notification tier escalation sounds

**Notification Tier Mapping:**
| Urgency Tier | Sound Tier |
|--------------|------------|
| calm, casual | gentle chime |
| pointed, urgent | pointed beep |
| pushing, firm | urgent siren |
| critical, alarm | looping alarm |

---

### Task 2.6: Implement Background Scheduling & Recovery
**Spec Reference:** Section 6

**Current State:** Not implemented.

**Tasks:**
- [ ] Define Notifee adapter interface (mock-able)
- [ ] Implement anchor registration with Notifee
- [ ] Implement iOS BGAppRefreshTask configuration
- [ ] Implement recovery scan on app launch
- [ ] Implement 15-minute grace window check
- [ ] Implement overdue anchor logging with `missed_reason`
- [ ] Implement pending anchors re-registration on restart
- [ ] Implement late fire warning (>60s after scheduled)

**Acceptance Criteria:**
- Closing app does not prevent anchors from firing
- Recovery scan fires only anchors within 15-minute grace window
- Overdue anchors dropped and logged with reason
- Pending anchors re-registered on restart

---

## Priority 3: Extended Features

### Task 3.1: Implement Calendar Integration
**Spec Reference:** Section 7

**Tasks:**
- [ ] Define `ICalendarAdapter` abstract interface
- [ ] Implement Apple Calendar adapter (EventKit simulation)
- [ ] Implement Google Calendar adapter
- [ ] Implement calendar sync on launch + every 15 minutes
- [ ] Implement suggestion card generation for events with locations
- [ ] Implement suggestion → reminder creation flow
- [ ] Implement permission denial handling
- [ ] Implement recurring event handling

**Acceptance Criteria:**
- Calendar events with locations appear as suggestion cards
- Confirming suggestion creates countdown_event reminder
- Calendar permission denial shows explanation banner
- Recurring events generate reminder for each occurrence

---

### Task 3.2: Implement Location Awareness
**Spec Reference:** Section 8

**Tasks:**
- [ ] Define location adapter interface
- [ ] Implement location check at departure anchor (single call)
- [ ] Implement 500m geofence comparison
- [ ] Implement immediate escalation to firm/critical if at origin
- [ ] Implement location permission request at first location-aware reminder
- [ ] Implement "Location-based escalation disabled" when denied

**Acceptance Criteria:**
- Only one location API call per reminder (at departure anchor)
- User still at origin → critical tier fires immediately
- User already left → normal chain proceeds
- No location history stored after comparison

---

### Task 3.3: Implement Sound Library
**Spec Reference:** Section 12

**Tasks:**
- [ ] Define sound categories (commute, routine, errand, custom)
- [ ] Bundle 5 built-in sounds per category
- [ ] Implement custom sound import (MP3, WAV, M4A, max 30 sec)
- [ ] Implement per-reminder sound selection
- [ ] Implement corrupted sound fallback to category default
- [ ] Implement `GET /sounds` endpoint

**Acceptance Criteria:**
- Built-in sounds play without network access
- Custom MP3 import appears in sound picker
- Corrupted custom sound falls back to category default

---

## Priority 4: Testing

### Task 4.1: Implement Scenario-Based Tests
**Spec Reference:** Section 14 (Definition of Done)

**Existing Scenarios (16 total):**
- chain-full-30min, chain-compressed-15min, chain-minimum-3min, chain-invalid-rejected
- parse-natural-language, parse-simple-countdown, parse-tomorrow
- voice-coach-personality, voice-no-nonsense, voice-all-personalities
- history-record-outcome, history-record-miss-feedback
- stats-hit-rate
- reminder-creation-crud, reminder-creation-cascade-delete

**Missing Scenarios:**
- [ ] snooze-tap
- [ ] snooze-custom-duration
- [ ] snooze-chain-recomputation
- [ ] dismissal-feedback-timing-correct
- [ ] dismissal-feedback-left-too-late
- [ ] feedback-loop-adjustment-cap
- [ ] stats-streaks
- [ ] stats-common-miss-window
- [ ] tts-clip-generation
- [ ] tts-fallback
- [ ] dnd-early-anchor-suppressed
- [ ] dnd-final-5min-override
- [ ] quiet-hours-suppression
- [ ] chain-overlap-serialization
- [ ] background-recovery-scan
- [ ] location-still-at-origin
- [ ] location-already-left

**Tasks:**
- [ ] Create scenario YAML files for all missing scenarios
- [ ] Copy scenarios to `/var/otto-scenarios/urgent-alarm/` (requires sudo)
- [ ] Run `python3 -m pytest harness/` to validate

---

## Implementation Order

```
Phase 1: Foundation (Must Fix)
├─ Task 1.1: Fix Escalation Chain Engine Bugs
├─ Task 1.2: Fix Natural Language Parser Bugs
└─ Task 1.3: Expand Data Persistence Schema

Phase 2: Core Features
├─ Task 2.1: Complete Voice Personality System
├─ Task 2.2: Implement Snooze & Dismissal Flow
├─ Task 2.3: Complete Feedback Loop & Stats
├─ Task 2.4: Implement TTS Adapter Interface
├─ Task 2.5: Implement Notification & Alarm Behavior
└─ Task 2.6: Implement Background Scheduling & Recovery

Phase 3: Extended Features
├─ Task 3.1: Implement Calendar Integration
├─ Task 3.2: Implement Location Awareness
└─ Task 3.3: Implement Sound Library

Phase 4: Testing
└─ Task 4.1: Implement Scenario-Based Tests
```

---

## Key Dependencies

| Task | Depends On |
|------|------------|
| Task 2.4 (TTS Adapter) | Task 1.1 (Chain Engine), Task 1.3 (Schema) |
| Task 2.5 (Notifications) | Task 1.3 (Schema), Task 2.4 (TTS) |
| Task 2.6 (Background) | Task 1.3 (Schema), Task 2.5 |
| Task 3.1 (Calendar) | Task 1.3 (Schema) |
| Task 3.2 (Location) | Task 1.3 (Schema) |
| Task 3.3 (Sound Library) | Task 1.3 (Schema) |
| Task 4.1 (Tests) | Phase 1 + Phase 2 tasks |

---

## Out of Scope (Per Spec)

The following are explicitly excluded from this implementation:
- Password reset / account management (local-only data in v1)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min" spoken)
- Multi-device sync (future consideration)
- Bluetooth audio routing preference (speaker-only in v1)
- Sound recording within app
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations

---

## Validation

Run these after implementing to get immediate feedback:

```bash
# Syntax check
python3 -m py_compile src/test_server.py

# Start test server
python3 src/test_server.py &

# Run scenario tests (requires sudo)
sudo python3 harness/scenario_harness.py --project urgent-alarm
```