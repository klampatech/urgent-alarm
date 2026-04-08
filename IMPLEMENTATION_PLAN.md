# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Overview

This plan identifies gaps between `specs/urgent-voice-alarm-app-2026-04-08.spec.md` and the current implementation in `src/test_server.py`. The test server provides a basic HTTP API with some core logic, but lacks the full feature set required by the specification.

---

## Gap Analysis Summary

| Spec Section | Status | Priority |
|--------------|--------|----------|
| 2. Escalation Chain Engine | Partial - missing calm tier, validation gaps | P1 |
| 3. Reminder Parsing | Partial - keyword fallback only, no LLM adapter interface | P2 |
| 4. Voice & TTS Generation | Text-only - no file caching, no adapter interface | P3 |
| 5. Notification & Alarm | Not implemented - DND, quiet hours, chain overlap | P2 |
| 6. Background Scheduling | Not implemented - No Notifee, no recovery scan | P2 |
| 7. Calendar Integration | Not implemented | P3 |
| 8. Location Awareness | Not implemented | P3 |
| 9. Snooze & Dismissal | Partial - feedback loop started, snooze flow missing | P2 |
| 10. Voice Personality System | Partial - missing "calm" personality, no variations | P2 |
| 11. History, Stats & Feedback Loop | Partial - hit rate done, streaks, common miss window missing | P2 |
| 12. Sound Library | Not implemented | P3 |
| 13. Data Persistence | Partial - simplified schema, no migrations | P1 |

---

## Priority 1: Foundation (Core Infrastructure)

### Task 1.1: Complete Escalation Chain Engine
**Spec Reference:** Section 2

**Current State:** Chain computation exists but has gaps:
- Missing "calm" urgency tier in `URGENCY_TIERS`
- `compute_escalation_chain()` logic has off-by-one errors (e.g., 30-min buffer should produce 8 anchors, currently produces fewer)
- Missing `get_next_unfired_anchor()` function
- Missing validation for `arrival_time > departure_time`

**Tasks:**
- [ ] Add "calm" tier to `URGENCY_TIERS` dict
- [ ] Fix chain generation for full 8-anchor chains (departure + 7 subsequent)
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add full chain validation (reject if drive_duration exceeds time_to_arrival)
- [ ] Ensure chain determinism for unit testing

**Acceptance Criteria (from spec TC-01 through TC-06):**
- 30-min drive → 8 anchors (8:30 calm, 8:35 casual, 8:40 pointed, 8:45 urgent, 8:50 pushing, 8:55 firm, 8:59 critical, 9:00 alarm)
- 10-min drive → 4 anchors starting at T-5 urgent
- 3-min drive → 3 anchors (T-3 firm, T-1 critical, T-0 alarm)
- Invalid chains rejected with proper error
- `get_next_unfired_anchor` returns earliest unfired anchor
- Anchors sorted by timestamp ascending

---

### Task 1.2: Complete Data Persistence Schema
**Spec Reference:** Section 13

**Current State:** `init_db()` creates a simplified schema missing many fields from spec.

**Tasks:**
- [ ] Expand `reminders` table schema per spec (origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id, sound_category, selected_sound, etc.)
- [ ] Expand `anchors` table schema per spec (snoozed_to, tts_fallback)
- [ ] Add `history` table missing fields (missed_reason, actual_arrival)
- [ ] Add `calendar_sync` table
- [ ] Add `custom_sounds` table
- [ ] Implement migration system (versioned sequential migrations)
- [ ] Enable WAL mode and foreign key enforcement
- [ ] Implement in-memory test database support (`?mode=memory`)

**Schema Elements Required:**
```sql
-- reminders additions
reminders.origin_lat REAL,
reminders.origin_lng REAL,
reminders.origin_address TEXT,
reminders.sound_category TEXT,
reminders.selected_sound TEXT,
reminders.custom_sound_path TEXT,
reminders.calendar_event_id TEXT

-- anchors additions  
anchors.tts_fallback INTEGER DEFAULT 0,
anchors.snoozed_to TEXT

-- history additions
history.missed_reason TEXT,
history.actual_arrival TEXT

-- New tables
calendar_sync (calendar_type, last_sync_at, sync_token, is_connected)
custom_sounds (id, filename, original_name, category, file_path, duration_seconds, created_at)
```

---

### Task 1.3: Implement LLM Adapter Interface
**Spec Reference:** Section 3

**Current State:** `parse_reminder_natural()` uses regex keyword extraction only.

**Tasks:**
- [ ] Define `ILanguageModelAdapter` abstract interface
- [ ] Implement `MiniMaxAdapter` class (Anthropic-compatible endpoint)
- [ ] Implement `AnthropicAdapter` class
- [ ] Implement mock adapter for testing with predefined fixture responses
- [ ] Add environment variable configuration for API selection
- [ ] Ensure fallback to keyword extraction on LLM API failure
- [ ] Support all reminder types: countdown_event, simple_countdown, morning_routine, standing_recurring

**Acceptance Criteria:**
- "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- "dryer in 3 min" parses as simple_countdown
- "meeting tomorrow 2pm, 20 min drive" resolves to next day
- Empty/unintelligible input returns error with retry prompt
- Mock adapter used in test mode returns fixture without API call

---

## Priority 2: Core Features

### Task 2.1: Implement Voice Personality System Fully
**Spec Reference:** Section 10

**Current State:** `VOICE_PERSONALITIES` dict exists with 5 personalities but:
- Missing "calm" personality (listed in spec but not in code)
- Only 1 message template per tier (spec requires minimum 3 variations per tier)

**Tasks:**
- [ ] Add "calm" personality to `VOICE_PERSONALITIES`
- [ ] Create minimum 3 message variations per urgency tier per personality
- [ ] Implement custom prompt storage in user_preferences
- [ ] Implement message generation with personality + urgency tier routing

**Acceptance Criteria:**
- "Coach" at T-5: motivational, exclamation present
- "No-nonsense" at T-5: brief, direct, no filler
- "Assistant" at T-5: calm, suggestive
- Custom prompt modifies tone appropriately
- Each personality generates at least 3 message variations per tier

---

### Task 2.2: Implement Snooze & Dismissal Flow
**Spec Reference:** Section 9

**Current State:** History endpoint partially handles feedback loop, but snooze flow is missing.

**Tasks:**
- [ ] Implement `POST /snooze` endpoint for tap snooze (default 1 min)
- [ ] Implement custom snooze duration picker (1, 3, 5, 10, 15 min options)
- [ ] Implement chain re-computation after snooze (`recompute_chain_after_snooze()`)
- [ ] Implement snooze persistence (re-register anchors with Notifee)
- [ ] Implement dismissal feedback prompt logic
- [ ] Implement feedback response storage ("Left too early", "Left too late", "Other")
- [ ] TTS confirmation message generation for snooze

**Chain Re-computation Logic:**
When snoozed, shift all remaining unfired anchors by snooze duration:
- Original anchors at 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- User snoozes at 8:45 for 3 minutes
- Remaining anchors shift: 8:48, 8:53, 8:59, 9:00

**Acceptance Criteria:**
- Tap snooze pauses and re-fires after 1 minute
- Custom snooze allows duration selection
- Chain re-computation shifts remaining anchors correctly
- Feedback prompt appears on dismiss with destination label
- "Left too late" increases drive_duration by 2 minutes
- TTS confirms: "Okay, snoozed X minutes"

---

### Task 2.3: Implement Feedback Loop for Drive Duration
**Spec Reference:** Section 11

**Current State:** History endpoint has partial implementation, but cap and common miss window missing.

**Tasks:**
- [ ] Implement `destination_adjustments` table population on feedback
- [ ] Add +15 minute cap on adjustment
- [ ] Implement "Common miss window" calculation (most frequently missed urgency tier)
- [ ] Implement streak counter for recurring reminders
- [ ] Implement `GET /stats/streaks` endpoint
- [ ] Implement `GET /stats/common-miss` endpoint
- [ ] Implement 90-day data retention logic (archive old data)

**Adjustment Formula:**
```
adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)
capped at +15 minutes
```

**Acceptance Criteria:**
- After 3 "Left too late" for "Parker Dr", next reminder adds 6 minutes
- After 10+ late feedback, adjustment capped at +15 minutes
- Common miss window identifies most missed urgency tier
- Streak increments on hit, resets on miss for recurring reminders

---

### Task 2.4: Implement Notification & Alarm Behavior
**Spec Reference:** Section 5

**Current State:** No notification behavior implemented.

**Tasks:**
- [ ] Implement DND detection (check system DND status)
- [ ] Implement DND handling: silent notification for early anchors, visual override + vibration for final 5 minutes
- [ ] Implement quiet hours configuration and suppression
- [ ] Implement post-DND/quiet-hours queue (15-minute grace window)
- [ ] Implement chain overlap serialization (queue new anchors until current chain completes)
- [ ] Implement T-0 alarm looping until user action
- [ ] Implement notification tier escalation (gentle chime → pointed beep → urgent siren → looping alarm)

**Notification Tier Mapping:**
| Urgency Tier | Sound Tier |
|--------------|------------|
| calm, casual | gentle chime |
| pointed, urgent | pointed beep |
| pushing, firm | urgent siren |
| critical, alarm | looping alarm |

---

### Task 2.5: Implement Background Scheduling & Recovery
**Spec Reference:** Section 6

**Current State:** No background scheduling implemented.

**Tasks:**
- [ ] Define Notifee adapter interface (mock-able)
- [ ] Implement anchor registration with Notifee per anchor
- [ ] Implement iOS BGAppRefreshTask configuration
- [ ] Implement recovery scan on app launch
- [ ] Implement 15-minute grace window check during recovery
- [ ] Implement overdue anchor logging with missed_reason
- [ ] Implement pending anchors re-registration on crash recovery
- [ ] Implement late fire warning (>60 seconds after scheduled)

**Acceptance Criteria:**
- Closing app does not prevent anchors from firing
- Recovery scan fires only anchors within 15-minute grace window
- Overdue anchors dropped and logged with reason
- Pending anchors re-registered on restart

---

## Priority 3: Extended Features

### Task 3.1: Implement TTS Adapter Interface & File Caching
**Spec Reference:** Section 4

**Current State:** `generate_voice_message()` produces text only.

**Tasks:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement ElevenLabs adapter class
- [ ] Implement mock TTS adapter for testing
- [ ] Implement TTS cache directory structure (`/tts_cache/{reminder_id}/`)
- [ ] Implement clip generation at reminder creation time
- [ ] Implement cache invalidation on reminder deletion
- [ ] Implement fallback to system notification sound on TTS failure
- [ ] Implement 30-second timeout for TTS generation

**Note:** Since this is a Python backend, actual TTS file generation would require either:
- Mock implementation for testing
- Integration with external TTS service
- Local TTS library (gTTS, pyttsx3)

**Acceptance Criteria:**
- TTS clips stored in `/tts_cache/{reminder_id}/`
- Playing anchor uses local cached file
- TTS failure gracefully falls back to notification sound
- Reminder deletion removes cached TTS files

---

### Task 3.2: Implement Calendar Integration
**Spec Reference:** Section 7

**Current State:** No calendar integration.

**Tasks:**
- [ ] Define `ICalendarAdapter` abstract interface
- [ ] Implement Apple Calendar adapter (EventKit simulation)
- [ ] Implement Google Calendar adapter
- [ ] Implement calendar sync on launch and every 15 minutes
- [ ] Implement suggestion card generation for events with locations
- [ ] Implement suggestion → reminder creation flow
- [ ] Implement permission denial handling
- [ ] Implement recurring event handling
- [ ] Implement `calendar_sync` table population

**Acceptance Criteria:**
- Calendar events with locations appear as suggestion cards
- Confirming suggestion creates countdown_event reminder
- Calendar permission denial shows explanation banner
- Sync failure does not prevent manual reminder creation
- Recurring events generate reminder for each occurrence

---

### Task 3.3: Implement Location Awareness
**Spec Reference:** Section 8

**Current State:** No location awareness.

**Tasks:**
- [ ] Define location adapter interface
- [ ] Implement CoreLocation adapter (mock-able for testing)
- [ ] Implement origin storage (address or current location at creation)
- [ ] Implement departure-time location check (single call, not continuous)
- [ ] Implement 500m geofence comparison
- [ ] Implement immediate escalation to firm/critical if user still at origin
- [ ] Implement location permission request at first location-aware reminder
- [ ] Implement "Location-based escalation disabled" note when permission denied

**Acceptance Criteria:**
- Only one location API call per reminder (at departure anchor)
- User still at origin → critical tier fires immediately instead of calm departure
- User already left → normal chain proceeds
- No location history stored after comparison

---

### Task 3.4: Implement Sound Library
**Spec Reference:** Section 12

**Current State:** No sound library.

**Tasks:**
- [ ] Define sound categories (commute, routine, errand, custom)
- [ ] Bundle 5 built-in sounds per category (metadata/paths)
- [ ] Implement custom sound import endpoint (MP3, WAV, M4A, max 30 seconds)
- [ ] Implement per-reminder sound selection
- [ ] Implement sound selection persistence in reminder record
- [ ] Implement corrupted sound fallback to category default
- [ ] Implement `GET /sounds` endpoint for library browsing

**Acceptance Criteria:**
- Built-in sounds play without network access
- Custom MP3 import appears in sound picker
- Corrupted custom sound falls back to category default
- Sound selection persists on reminder edit

---

## Priority 4: Testing & Polish

### Task 4.1: Implement Test Suite
**Spec Reference:** Section 14 (Definition of Done)

**Current State:** No formal test suite exists.

**Tasks:**
- [ ] Unit tests for chain engine determinism
- [ ] Unit tests for parser fixtures
- [ ] Unit tests for TTS adapter mock
- [ ] Unit tests for LLM adapter mock
- [ ] Unit tests for keyword extraction
- [ ] Unit tests for schema validation
- [ ] Integration tests for reminder creation flow
- [ ] Integration tests for anchor firing sequence
- [ ] Integration tests for snooze recovery
- [ ] Integration tests for feedback loop
- [ ] E2E tests for Quick Add flow (via harness)

**Run tests:** `python3 -m pytest harness/` (or manual harness test)

---

### Task 4.2: Lint & Typecheck

**Tasks:**
- [ ] Run `python3 -m py_compile harness/scenario_harness.py src/test_server.py`
- [ ] Fix any linting errors
- [ ] Add type annotations where beneficial

---

## Implementation Order

```
Phase 1: Foundation (Core Infrastructure)
├─ Task 1.1: Complete Escalation Chain Engine
├─ Task 1.2: Complete Data Persistence Schema  
└─ Task 1.3: Implement LLM Adapter Interface

Phase 2: Core Features
├─ Task 2.1: Implement Voice Personality System Fully
├─ Task 2.2: Implement Snooze & Dismissal Flow
├─ Task 2.3: Implement Feedback Loop for Drive Duration
├─ Task 2.4: Implement Notification & Alarm Behavior
└─ Task 2.5: Implement Background Scheduling & Recovery

Phase 3: Extended Features
├─ Task 3.1: Implement TTS Adapter Interface & File Caching
├─ Task 3.2: Implement Calendar Integration
├─ Task 3.3: Implement Location Awareness
└─ Task 3.4: Implement Sound Library

Phase 4: Testing & Polish
├─ Task 4.1: Implement Test Suite
└─ Task 4.2: Lint & Typecheck
```

---

## Key Dependencies

| Task | Depends On |
|------|------------|
| Task 2.4 (Notification & Alarm) | Task 1.2 (Schema) |
| Task 2.5 (Background Scheduling) | Task 1.2 (Schema), Task 2.4 |
| Task 3.1 (TTS Adapter) | Task 1.1 (Chain Engine), Task 1.2 (Schema) |
| Task 3.2 (Calendar Integration) | Task 1.2 (Schema) |
| Task 3.3 (Location Awareness) | Task 1.2 (Schema) |
| Task 4.1 (Test Suite) | All Phase 1-3 tasks |

---

## Out of Scope (Per Spec)

The following are explicitly excluded from this implementation:
- Password reset / account management (local-only data in v1)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing preference
- Sound recording within app
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
