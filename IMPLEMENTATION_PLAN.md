# URGENT Alarm - Implementation Plan

## Executive Summary

The Urgent Alarm app is a mobile alarm application with AI-escalating voice messages. The current codebase (`src/test_server.py`) contains a minimal Python HTTP server with partial implementations of:
- Chain engine (basic anchor computation)
- Natural language parser (keyword extraction only)
- Voice message generation (5 personalities, no TTS)
- Simple SQLite database (incomplete schema)

**Gap Analysis**: ~85% of the spec remains unimplemented. The codebase lacks proper architecture, all external adapters, mobile framework, background scheduling, and most features.

---

## Priority 1: Foundation & Core Infrastructure

### 1.1 Project Structure & Architecture
**Status**: No structure exists  
**Priority**: Critical (blocks all development)

- [ ] Create `src/lib/` directory with modules:
  - `src/lib/chain_engine.py` - Escalation chain computation
  - `src/lib/parser.py` - LLM adapter + keyword fallback
  - `src/lib/voice.py` - Voice personality system + TTS adapter
  - `src/lib/database.py` - SQLite with full schema + migrations
  - `src/lib/adapters/` - Adapter interfaces (ILanguageModel, ITTS, ICalendar, ILocation)
  - `src/lib/notification.py` - Notification tier system
  - `src/lib/scheduler.py` - Background scheduling abstraction
  - `src/lib/stats.py` - History, hit rate, feedback loop

- [ ] Create `src/mobile/` directory (React Native project scaffold)
- [ ] Create `tests/` directory with pytest configuration

### 1.2 Complete Database Schema & Migrations
**Status**: Partial schema exists  
**Spec Section**: 13  
**Priority**: Critical (all features depend on it)

**Missing tables/columns:**
- [ ] `reminders`: Add `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id`
- [ ] `anchors`: Add `tts_fallback`, `snoozed_to`
- [ ] `history`: Add `actual_arrival`, `missed_reason`, `updated_at`
- [ ] `destination_adjustments`: Add `updated_at`
- [ ] `user_preferences`: Add `updated_at`
- [ ] Create `calendar_sync` table
- [ ] Create `custom_sounds` table
- [ ] Create `schema_migrations` table for versioning

**Migration system:**
- [ ] Create migration runner that applies sequential versions
- [ ] Add `mode=memory` for tests (fresh in-memory DB)
- [ ] Enable foreign keys and WAL mode

### 1.3 Refactor & Test Chain Engine
**Status**: Basic implementation exists  
**Spec Section**: 2  
**Priority**: Critical

**Current state**: `compute_escalation_chain()` partially implemented  
**Missing:**
- [ ] `get_next_unfired_anchor(reminder_id)` function
- [ ] Fix chain tier logic:
  - ≥25 min: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
  - 20-24 min: 7 anchors (skip calm)
  - 10-19 min: 5 anchors (urgent, pushing, firm, critical, alarm)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - <5 min: 2 anchors (critical/firm, alarm)
- [ ] Chain determinism guarantee (same inputs = same outputs)
- [ ] Unit tests for all 6 test scenarios (TC-01 through TC-06)

---

## Priority 2: Core Feature Adapters

### 2.1 LLM Parser Adapter
**Status**: Basic keyword extraction exists  
**Spec Section**: 3  
**Priority**: High

**Missing:**
- [ ] `ILanguageModelAdapter` interface
- [ ] `MinimaxAdapter` (Anthropic-compatible API)
- [ ] `AnthropicAdapter` 
- [ ] `MockLanguageModelAdapter` for tests
- [ ] System prompt for extraction schema
- [ ] Keyword extraction fallback improvements:
  - Handle "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X"
  - Handle "tomorrow", "today" date resolution
  - Handle simple countdowns: "dryer in 3 min" → arrival_time = now + 3min

**Test scenarios:**
- [ ] TC-01: Full natural language parse
- [ ] TC-02: Simple countdown parse
- [ ] TC-03: Tomorrow date resolution
- [ ] TC-04: LLM API failure fallback
- [ ] TC-05: Manual field correction (via confirmation card - mobile)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

### 2.2 Voice Personality System
**Status**: Basic templates exist  
**Spec Section**: 10  
**Priority**: High

**Current state**: `generate_voice_message()` with 5 personalities  
**Missing:**
- [ ] Minimum 3 message variations per tier per personality (avoid repetition)
- [ ] Custom personality prompt support (max 200 chars)
- [ ] ElevenLabs voice ID mapping per personality
- [ ] Voice settings/style parameters for custom prompts

**Test scenarios:**
- [ ] TC-01: Coach personality message format
- [ ] TC-02: No-nonsense personality brevity
- [ ] TC-03: Custom personality tone
- [ ] TC-04: Personality immutability for existing reminders
- [ ] TC-05: Message variation (distinct phrasings)

### 2.3 TTS Adapter
**Status**: Not implemented  
**Spec Section**: 4  
**Priority**: High

**Missing:**
- [ ] `ITTSAdapter` interface
- [ ] `ElevenLabsAdapter` with environment variable configuration
- [ ] `MockTTSAdapter` for tests (writes 1-sec silent file)
- [ ] TTS cache directory: `/tts_cache/{reminder_id}/`
- [ ] Async generation with 30-second timeout
- [ ] Fallback: system notification sound + text on TTS failure
- [ ] Cache invalidation on reminder deletion

**Test scenarios:**
- [ ] TC-01: TTS clip generation at creation (8 MP3 files)
- [ ] TC-02: Anchor fires from cache (no network call)
- [ ] TC-03: TTS fallback on API failure
- [ ] TC-04: TTS cache cleanup on delete
- [ ] TC-05: Mock TTS in tests

---

## Priority 3: HTTP API & Web Server

### 3.1 Expand HTTP Endpoints
**Status**: Basic endpoints exist  
**Spec Section**: N/A (infrastructure)  
**Priority**: High

**Existing:**
- `GET /health`
- `GET /chain?arrival=X&duration=Y`
- `GET /reminders`
- `POST /reminders`
- `POST /parse`
- `POST /voice/message`
- `POST /history`
- `POST /anchors/fire`

**Missing:**
- [ ] `GET /reminders/{id}` - Get single reminder
- [ ] `DELETE /reminders/{id}` - Delete reminder (cascade to anchors)
- [ ] `PUT /reminders/{id}` - Update reminder
- [ ] `GET /anchors?reminder_id=X` - Get anchors for reminder
- [ ] `GET /anchors/next?reminder_id=X` - Get next unfired anchor
- [ ] `POST /anchors/snooze` - Snooze anchor with duration
- [ ] `POST /anchors/fire` - Already exists, verify implementation
- [ ] `GET /stats/hit-rate?days=7` - Parameterized hit rate
- [ ] `GET /stats/streaks` - Streak counters
- [ ] `GET /stats/common-miss` - Common miss window
- [ ] `GET /adjustments?destination=X` - Get destination adjustment
- [ ] `POST /preferences` - Set user preference
- [ ] `GET /preferences/{key}` - Get user preference

### 3.2 Database Session Management
**Status**: Simple connect/disconnect per request  
**Priority**: Medium

- [ ] Add connection pooling or thread-local sessions
- [ ] Ensure foreign keys enabled per connection
- [ ] Handle concurrent requests safely

---

## Priority 4: Mobile App (React Native)

### 4.1 Project Setup
**Status**: Not started  
**Spec Section**: Technical Approach  
**Priority**: High

- [ ] Initialize React Native project (npx react-native init UrgentAlarm)
- [ ] Install dependencies:
  - `@notifee/react-native` - Background notifications
  - `react-native-event-kit` or `react-native-apple-calendar` - Calendar access
  - `@react-native-community/geolocation` - Location check
  - `elevenlabs-react-native` or REST API calls to ElevenLabs
  - `expo-av` or `react-native-sound` - Audio playback
  - `@react-native-async-storage/async-storage` - Local preferences
- [ ] Configure iOS/Android native modules

### 4.2 Quick Add Screen
**Status**: Not started  
**Spec Section**: Features (Quick Add)  
**Priority**: High

- [ ] Single text/speech input field
- [ ] Speech-to-text integration
- [ ] Parsed interpretation confirmation card
- [ ] Manual field correction UI
- [ ] Voice personality selector
- [ ] Sound category selector

### 4.3 Reminder List & Detail Screens
**Status**: Not started  
**Spec Section**: N/A  
**Priority**: Medium

- [ ] List all active reminders
- [ ] Swipe to delete
- [ ] Tap to view/edit
- [ ] Status indicators (pending, active, completed)

### 4.4 Notification & Alarm UI
**Status**: Not started  
**Spec Section**: 5, 9  
**Priority**: High

- [ ] Tap snooze (1 min)
- [ ] Tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Swipe-to-dismiss with feedback prompt
- [ ] Visual notification tier escalation
- [ ] TTS confirmation: "Okay, snoozed X minutes"
- [ ] T-0 alarm looping until user action

### 4.5 Settings Screen
**Status**: Not started  
**Spec Section**: N/A  
**Priority**: Medium

- [ ] Voice personality selection
- [ ] Quiet hours configuration (default: 10pm-7am)
- [ ] Calendar integration toggle + permissions
- [ ] Location awareness toggle + permissions
- [ ] Sound library access

### 4.6 History & Stats Screen
**Status**: Not started  
**Spec Section**: 11  
**Priority**: Medium

- [ ] Weekly hit rate display
- [ ] Current streak counter
- [ ] Common miss window indicator
- [ ] Per-destination adjustment display

---

## Priority 5: Background Scheduling & Notifications

### 5.1 Notifee Integration
**Status**: Not started  
**Spec Section**: 6  
**Priority**: Critical

**Missing:**
- [ ] Register each anchor as Notifee task with trigger timestamp
- [ ] iOS: Use `BGAppRefreshTask` for timing + `BGProcessingTask` for TTS pre-warm
- [ ] Recovery scan on app launch:
  - Fire overdue unfired anchors within 15-minute grace window
  - Drop anchors >15 minutes overdue, log with `missed_reason`
- [ ] Re-register pending anchors on crash recovery
- [ ] Late fire warning (>60 seconds after scheduled)

### 5.2 Notification Behavior
**Status**: Not started  
**Spec Section**: 5  
**Priority**: High

**Missing:**
- [ ] Notification tier escalation:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm
- [ ] DND awareness:
  - Pre-5-minute during DND → silent notification
  - Final 5 minutes during DND → visual override + vibration
- [ ] Quiet hours suppression (queue for post-quiet-hours)
- [ ] Overdue anchor drop (>15 minutes overdue)
- [ ] Chain overlap serialization (queue new anchors until current chain completes)

### 5.3 Snooze & Dismissal Flow
**Status**: Not started  
**Spec Section**: 9  
**Priority**: High

**Missing:**
- [ ] Tap snooze: 1 minute, TTS confirmation
- [ ] Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze:
  - Shift remaining anchors: `new_timestamp = now + original_time_remaining`
  - Re-register with Notifee
- [ ] Swipe dismiss: feedback prompt ("Was timing right?")
- [ ] Feedback: "Left too early" / "Left too late" / "Other"
- [ ] Feedback persistence (adjust future departure estimates)

---

## Priority 6: External Integrations

### 6.1 Calendar Integration
**Status**: Not started  
**Spec Section**: 7  
**Priority**: Medium

**Missing:**
- [ ] `ICalendarAdapter` interface
- [ ] `AppleCalendarAdapter` (EventKit)
- [ ] `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Sync scheduler (on launch + every 15 minutes + background refresh)
- [ ] Event filtering (only events with location)
- [ ] Suggestion cards for calendar events
- [ ] Recurring event handling
- [ ] Permission denial handling with settings link
- [ ] Sync failure graceful degradation

**Test scenarios:**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

### 6.2 Location Awareness
**Status**: Not started  
**Spec Section**: 8  
**Priority**: Medium

**Missing:**
- [ ] Single location check at departure anchor (T-drive_duration)
- [ ] Origin resolution: user-specified address OR current device location
- [ ] CoreLocation (iOS) / FusedLocationProvider (Android) call
- [ ] Geofence comparison (500m radius)
- [ ] Escalation if user still at origin:
  - Fire firm/critical tier immediately instead of calm departure nudge
- [ ] Location permission request at first location-aware reminder (not on launch)
- [ ] No location history storage

**Test scenarios:**
- [ ] TC-01: User still at origin at departure
- [ ] TC-02: User already left at departure
- [ ] TC-03: Location permission request
- [ ] TC-04: Location permission denied
- [ ] TC-05: Single location check only

### 6.3 Sound Library
**Status**: Not started  
**Spec Section**: 12  
**Priority**: Low (Phase 2)

**Missing:**
- [ ] Built-in sounds bundled with app (5 per category)
- [ ] Sound categories: Commute, Routine, Errand, Custom
- [ ] Custom audio import: MP3, WAV, M4A (max 30 seconds)
- [ ] File picker integration
- [ ] Sound transcoding to normalized format
- [ ] Corrupted sound fallback + error display

---

## Priority 7: Feedback Loop & Stats

### 7.1 Feedback Loop Implementation
**Status**: Basic history recording exists  
**Spec Section**: 11  
**Priority**: High

**Current state**: `POST /history` records outcomes  
**Missing:**
- [ ] Destination adjustment calculation:
  - `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
  - Cap at +15 minutes
- [ ] Auto-apply adjustments to new reminders for same destination

### 7.2 Stats Calculations
**Status**: Basic hit rate exists  
**Spec Section**: 11  
**Priority**: Medium

**Missing:**
- [ ] Hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
- [ ] Common miss window: most frequently missed urgency tier
- [ ] Streak counter: increment on hit, reset on miss for recurring reminders
- [ ] All stats derived from history table (no separate stats store)

### 7.3 Data Retention
**Status**: Not specified  
**Spec Section**: 11  
**Priority**: Low

- [ ] Archive history entries older than 90 days
- [ ] Keep archived data accessible

---

## Priority 8: Test Coverage

### 8.1 Unit Tests
**Status**: None  
**Spec Section**: 14  
**Priority**: High

**Missing:**
- [ ] Chain engine determinism tests
- [ ] Parser fixtures (mock LLM adapter)
- [ ] TTS adapter mock tests
- [ ] LLM adapter mock tests
- [ ] Keyword extraction tests
- [ ] Schema validation tests
- [ ] Stats calculation tests

### 8.2 Integration Tests
**Status**: None  
**Spec Section**: 14  
**Priority**: High

**Missing:**
- [ ] Full reminder creation flow (parse → chain → TTS → persist)
- [ ] Anchor firing (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment applied)

### 8.3 E2E Tests (Detox)
**Status**: Not started  
**Spec Section**: 14  
**Priority**: Medium (Phase 2)

- [ ] Quick Add flow
- [ ] Reminder confirmation
- [ ] Anchor firing sequence
- [ ] Snooze interaction
- [ ] Dismissal feedback
- [ ] Settings navigation
- [ ] Sound library browsing

---

## Priority 9: Project Configuration

### 9.1 Environment Configuration
**Status**: Hardcoded values  
**Priority**: Medium

- [ ] Environment variables:
  - `ELEVENLABS_API_KEY` - TTS API
  - `LLM_API_KEY` - MinMax or Anthropic
  - `LLM_PROVIDER` - "minimax" or "anthropic"
  - `DB_PATH` - SQLite database path
  - `TTS_CACHE_DIR` - TTS clip cache directory

### 9.2 Dependencies
**Status**: Minimal  
**Priority**: Medium

**Python (server):**
- [ ] flask or fastapi (API framework)
- [ ] requests (HTTP client for LLM/TTS APIs)
- [ ] pytest (testing)
- [ ] python-dateutil (date parsing)

**React Native (mobile):**
- [ ] @notifee/react-native
- [ ] @react-native-community/geolocation
- [ ] @react-native-async-storage/async-storage
- [ ] react-native-sound or expo-av
- [ ] @react-native-picker/picker (snooze duration)

---

## Implementation Order Summary

### Phase 1: Core Foundation (Week 1-2)
1. Create project structure (`src/lib/`, `src/mobile/`, `tests/`)
2. Complete database schema + migration system
3. Refactor and test chain engine
4. Expand HTTP API endpoints
5. Implement LLM adapter interface + mock

### Phase 2: Feature Core (Week 3-4)
6. Implement TTS adapter interface + mock
7. Complete voice personality system
8. Implement stats calculations
9. Implement feedback loop

### Phase 3: Mobile App (Week 5-6)
10. React Native project setup
11. Quick Add screen
12. Reminder list/detail screens
13. Notification + snooze UI
14. Settings screen

### Phase 4: Background & Integrations (Week 7-8)
15. Notifee background scheduling
16. Calendar integration (Apple + Google)
17. Location awareness
18. DND + quiet hours handling

### Phase 5: Polish & Testing (Week 9)
19. Sound library
20. Integration tests
21. E2E test setup
22. CI/CD pipeline

---

## Notes

- **Spec mismatch found**: The `chain-engine` implementation in `test_server.py` has incorrect tier logic. The tiers use `drive_duration - X` but should use `minutes_before_arrival` directly.
  - Current: `('calm', drive_duration)` = 30 min before arrival (correct)
  - Current: `('casual', drive_duration - 5)` = 25 min before arrival (correct)
  - But the compressed chains don't match spec

- **Database**: Spec TC-04 says "drive_duration > arrival_time" but this should be "drive_duration > (arrival_time - now)" (i.e., departure time is in the past). Current validation is slightly wrong.

- **No mobile framework selected**: The spec mentions React Native OR Flutter but hasn't made a decision. Recommend React Native for faster development given existing Python server.

- **API-only testing**: Current harness tests run against HTTP API. Mobile app will need separate test coverage.
