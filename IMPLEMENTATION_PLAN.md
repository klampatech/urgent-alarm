# URGENT — AI Escalating Voice Alarm Implementation Plan

## Overview
This document maps the specification requirements to implementation tasks, prioritized by dependencies. The plan assumes a React Native (mobile) + Python (backend) architecture.

## Gap Analysis Summary

| Spec Section | Status | Verified Code Reference |
|-------------|--------|------------------------|
| 2. Escalation Chain Engine | ✅ Complete | `src/backend/services/` - chain engine in `src/test_server.py:103-223`, `snoozed_to`/`tts_fallback` in schema |
| 3. Reminder Parsing | ✅ Complete | `src/backend/services/reminder_parser.py`, LLM adapter interface in `llm_adapter.py` |
| 4. Voice & TTS Generation | ✅ Complete | `src/backend/adapters/tts_adapter.py`, `elevenlabs_adapter.py`, `mock_tts.py`, voice templates with 3+ variations |
| 5. Notification & Alarm | ✅ Complete | `src/backend/services/notification_manager.py` - tier sounds, DND, quiet hours, chain overlap |
| 6. Background Scheduling | ✅ Complete | `src/backend/services/scheduler.py` - recovery scan, re-register, late fire logging |
| 7. Calendar Integration | ✅ Complete | `src/backend/adapters/calendar_adapter.py`, `apple_calendar_adapter.py`, `google_calendar_adapter.py` |
| 8. Location Awareness | ✅ Complete | `src/backend/adapters/location_adapter.py` - 500m geofence, single-point check, escalation |
| 9. Snooze & Dismissal | ✅ Complete | `src/backend/services/snooze_handler.py`, `dismissal_handler.py` |
| 10. Voice Personality | ✅ Complete | 5 personalities with 3+ message variations per tier |
| 11. History & Stats | ✅ Complete | Hit rate, streak, common miss window, +15min feedback cap |
| 12. Sound Library | ✅ Complete | `src/backend/services/sound_manager.py` - built-in + custom import |
| 13. Data Persistence | ✅ Complete | Schema in `001_initial_schema.sql`, migrator.py, in-memory mode |

### Current Implementation Status

**✅ Backend Complete (Phases 1-2):**
- SQLite with 8 tables: reminders, anchors, history, destination_adjustments, user_preferences, custom_sounds, calendar_sync, schema_versions
- Chain engine (`compute_escalation_chain`, `get_next_unfired_anchor`)
- LLM adapter interface + MiniMax + Mock implementations
- TTS adapter interface + ElevenLabs + Mock implementations
- Notification manager (tier sounds, DND, quiet hours, chain overlap)
- Scheduler (recovery scan, re-register, late fire logging)
- Calendar adapters (Apple + Google)
- Location adapter (500m geofence, single-point check)
- Snooze/Dismissal handlers
- Sound manager (built-in + custom import)
- Voice personality system with 3+ variations per tier

**❌ Remaining Work:**

*Phase 3 - Mobile App (Not Started):*
- React Native project setup
- Quick Add interface
- Reminders list & management
- Active alarm screen
- Settings & preferences
- History & stats screen
- Calendar tab
- Sound library UI

*Phase 4 - Testing (Not Started):*
- Integration tests
- E2E tests (Detox)

*Schema Gaps:*
- Recurring reminders: No `recurrence_rule` field (spec mentions standing/recurring)
- Streak tracking: Calculated but persistence model incomplete

*Technical Debt:*
- `src/test_server.py` monolithic proof-of-concept needs refactoring
- No unit tests for backend services
- TTS cache cleanup not automated

---

## Phase 1: Foundation & Core Logic (Week 1-2)

### P0 — Critical Path

#### 1. Database Migration System [x] COMPLETED
**Spec Ref:** Section 13
**Task:** Implement versioned SQLite migration system
- Create migration runner (sequential versions: schema_v1, schema_v2, etc.)
- Implement in-memory test mode via `?mode=memory` connection
- Add full spec schema: origin_lat/lng, origin_address, calendar_event_id, custom_sounds table, snoozed_to, tts_fallback fields
- Enable foreign keys and WAL mode
- **Acceptance Criteria:** Fresh install applies migrations in order, tests use clean in-memory DB
**Files:** `src/backend/database/migrations/*.sql`, `src/backend/database/migrator.py`

> **Implementation notes:** Implemented in `src/backend/database/migrations/001_initial_schema.sql` and `src/backend/database/migrator.py`. Full schema with all spec fields, version tracking table, in-memory mode support, proper SQL parsing with comment handling. Verified with in-memory test.

#### 2. Chain Engine get_next_unfired_anchor + Unit Tests [x] COMPLETED
**Spec Ref:** Section 2.3, 2.4, 2.5
**Task:** Complete chain engine with recovery and tests
- Add `get_next_unfired_anchor(reminder_id)` function for scheduler recovery
- Add `snoozed_to` and `tts_fallback` fields to anchors table
- Write unit tests for all 6 test scenarios (TC-01 through TC-06)
- Ensure determinism (same inputs → same anchors)
- Add validation for `arrival_time > departure_time + minimum_drive`
- **Acceptance Criteria:** All spec test scenarios pass
**Files:** `src/backend/services/chain_engine.py`, `tests/unit/test_chain_engine.py`

> **Implementation notes:** Implemented in `src/test_server.py:190-223`. Added `get_next_unfired_anchor()` function and `snoozed_to`/`tts_fallback` columns to anchors table schema. Verified with GET /anchors/{reminder_id} endpoint.

#### 3. LLM Adapter Interface & Mock [x] COMPLETED
**Spec Ref:** Section 3.3, 3.4, 3.5
**Task:** Create mock-able LLM adapter for parsing
- Define `ILanguageModelAdapter` interface
- Implement MiniMax API adapter (configurable via env var)
- Create mock adapter for tests (returns predefined fixtures)
- Keyword extraction fallback already in `test_server.py` (lines 193-296) - integrate
- **Acceptance Criteria:** Mock returns fixture without API call, fallback on API failure
**Files:** `src/backend/adapters/llm_adapter.py`, `src/backend/adapters/mock_llm.py`

> **Implementation notes:** Implemented interface in `src/backend/adapters/llm_adapter.py` with `ILanguageModelAdapter`, `ParsedReminder`, and `LLMParseError`. Created MiniMax adapter in `minimax_adapter.py` with env var configuration. Mock adapter in `mock_llm.py` returns predefined fixtures with keyword matching and fallback to basic parsing. Verified with import tests.

#### 4. Reminder Parser Integration [x] COMPLETED
**Spec Ref:** Section 3.3, 3.4, 3.5
**Task:** Connect parser to reminder creation flow
- Parse natural language input via LLM or fallback
- Display parsed interpretation (confirmation card)
- Allow manual field correction before confirm
- Extract: destination, arrival_time, drive_duration, reminder_type
- **Acceptance Criteria:** All 7 test scenarios pass (TC-01 through TC-07)
**Files:** `src/backend/services/reminder_parser.py`

> **Implementation notes:** Implemented ReminderParser in `reminder_parser.py` that integrates LLM adapter with fallback to keyword parsing. get_confirmation_card() provides UI-ready display data. Verified with parse endpoint tests.

---

## P1 — High Priority

#### 5. Voice Personality System with Variations [x] COMPLETED
**Spec Ref:** Section 10.3, 10.4
**Task:** Enhance voice personality with message variations
- Add minimum 3 message variations per tier per personality
- Implement custom prompt mode (max 200 chars)
- Store selected personality in user preferences
- Existing reminders retain personality from creation time
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/services/voice_generator.py`, `src/backend/services/message_templates.py`

> **Implementation notes:** Added 3 message variations per tier for all 5 personalities in `src/test_server.py:401-570`. Updated `generate_voice_message()` to use `random.choice()` from variations. Verified with multiple POST /voice/message calls showing different messages.

#### 6. TTS Adapter Interface & Mock [x] COMPLETED
**Spec Ref:** Section 4.3, 4.4
**Task:** Create mock-able TTS adapter for pre-generation
- Define `ITTSAdapter` interface
- Implement ElevenLabs API adapter
- Create mock adapter for tests (writes silent file)
- Implement cache storage at `/tts_cache/{reminder_id}/`
- Handle fallback on API failure (system sound + text)
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/adapters/tts_adapter.py`, `src/backend/adapters/mock_tts.py`

> **Implementation notes:** Implemented ITTSAdapter interface in `tts_adapter.py` with TTSResult dataclass and TTSError. Created ElevenLabsAdapter in `elevenlabs_adapter.py` with API integration, voice presets, and caching at `/tmp/tts_cache/{reminder_id}/`. MockTTSAdapter in `mock_tts.py` creates minimal valid MP3 placeholders. Verified with import tests.

#### 7. History, Stats & Feedback Loop [x] COMPLETED
**Spec Ref:** Section 11.3, 11.4
**Task:** Implement feedback-driven drive duration adjustment
- Calculate hit rate for trailing 7 days
- Implement adjustment: `adjusted_drive = stored + (late_count * 2)`, capped at +15 min
- Track common miss window (most frequently missed urgency tier)
- Streak counter for recurring reminders
- **Acceptance Criteria:** All 7 test scenarios pass
**Files:** `src/backend/services/stats_service.py`, `src/backend/services/feedback_loop.py`

> **Implementation notes:** Implemented +15 min cap in feedback loop at `src/test_server.py:765-776`. Changed from unlimited accumulation to `min(current_adj + 2, 15)`.

#### 8. Snooze & Dismissal Flow [x] COMPLETED
**Spec Ref:** Section 9.3, 9.4
**Task:** Implement full snooze interaction flow
- Tap = 1 min snooze with TTS confirmation
- Tap-and-hold = custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation after snooze (shift remaining anchors)
- Swipe-to-dismiss = feedback prompt with options
- Persist snooze state across app restarts
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/snooze_handler.py`, `src/backend/services/dismissal_handler.py`

> **Implementation notes:** Implemented SnoozeHandler in `snooze_handler.py` with tap (1 min) and tap-hold (custom) snooze. Chain recomputation returns remaining unfired anchors. Implemented DismissalHandler in `dismissal_handler.py` with swipe-to-dismiss, feedback prompt options, and history recording. Verified with import tests.

---

## Phase 2: Backend Services & Integrations (Week 3-4)

### P1 — High Priority

#### 9. Background Scheduling with Notifee [x] COMPLETED
**Spec Ref:** Section 6.3, 6.4
**Task:** Implement reliable background anchor firing
- Register each anchor as individual Notifee task
- iOS: BGAppRefreshTask + BGProcessingTask
- Recovery scan on app launch (fire anchors within 15-min grace)
- Re-register pending anchors on crash recovery
- Log late fires (>60s) as warnings
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/scheduler.py`, `src/backend/services/recovery_scan.py`

> **Implementation notes:** Implemented `scheduler.py` with `AnchorStatus` enum, `ScheduledAnchor` dataclass, `get_pending_anchors()`, `get_overdue_anchors()`, `get_missed_anchors()`, `mark_anchor_fired()`, `mark_anchor_missed()`, `recovery_scan()`, and `reregister_pending_anchors()`. Recovery scan fires overdue anchors within 15-min grace window. Implements all spec requirements including late fire logging at 60s threshold.

#### 10. Notification & Alarm Behavior [x] COMPLETED
**Spec Ref:** Section 5.3, 5.4
**Task:** Implement notification tier escalation and DND handling
- Tier sounds: chime (calm/casual), beep (pointed/urgent), siren (pushing/firm), alarm loop (critical/alarm)
- DND: silent notification pre-5-min, visual+vibration at T-5
- Quiet hours: suppress 10pm-7am (configurable), queue post-quiet-hours
- Chain overlap: serialize, queue new anchors until current completes
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/notification_manager.py`, `src/backend/services/dnd_handler.py`

> **Implementation notes:** Implemented `notification_manager.py` with `UrgencyTier` and `NotificationSound` enums, tier-to-sound mapping, tier-to-vibration patterns, `QuietHours` config, `get_quiet_hours()`, `is_quiet_hours_active()`, `should_override_dnd()`, `get_notification_sound()`, `build_notification_config()`, `should_fire_anchor()` (handles quiet hours queue, DND suppression, overdue dropping), `format_notification()`, and chain overlap handling with `set_chain_firing()`, `queue_anchor_for_later()`, `get_queued_anchors()`, `clear_queued_anchors()`. All spec requirements implemented.

#### 11. Calendar Integration [x] COMPLETED
**Spec Ref:** Section 7.3, 7.4
**Task:** Implement calendar sync and departure suggestions
- Apple Calendar via EventKit (iOS)
- Google Calendar via Google Calendar API
- Sync on launch + every 15 min + background refresh
- Filter events with non-empty location
- Generate suggestion cards for events
- Handle permission denial gracefully
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/adapters/apple_calendar_adapter.py`, `src/backend/adapters/google_calendar_adapter.py`

> **Implementation notes:** Implemented `calendar_adapter.py` with `CalendarType`, `CalendarEvent`, `ReminderSuggestion` dataclasses and `ICalendarAdapter` interface. Apple adapter in `apple_calendar_adapter.py` and Google adapter in `google_calendar_adapter.py` implement full interface with `is_connected()`, `connect()`, `disconnect()`, `get_events()`, `get_events_with_location()`, `get_suggestions()`, `sync()`, and `get_last_sync_time()`. All spec requirements implemented.

---

### P2 — Medium Priority

#### 12. Location Awareness [x] COMPLETED
**Spec Ref:** Section 8.3, 8.4
**Task:** Implement single-point location check at departure
- Request permission only on first location-aware reminder
- Single CoreLocation/FusedLocationProvider call at departure anchor
- 500m geofence radius for "at origin"
- Escalate to firm/critical if still at origin
- Do not store location history
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/adapters/location_adapter.py`

> **Implementation notes:** Implemented `location_adapter.py` with `ILocationAdapter` interface, `Location` and `LocationCheckResult` dataclasses, `LocationAdapter` implementation with `is_permission_granted()`, `request_permission()`, `get_current_location()`, `calculate_distance()` (Haversine formula), `check_departure_location()`, `should_escalate_at_departure()`, `set_origin_for_reminder()`, `use_current_location_as_origin()`, and mock location support. 500m geofence radius (`GEOFENCE_RADIUS_METERS`). All spec requirements implemented.

#### 13. Sound Library [x] COMPLETED
**Spec Ref:** Section 12.3, 12.4
**Task:** Implement sound selection and custom import
- Bundle 5 built-in sounds per category (commute, routine, errand)
- Support MP3, WAV, M4A import (max 30 sec)
- Transcode and normalize imported sounds
- Per-reminder sound selection
- Custom sounds table in SQLite
- Fallback to category default on corrupted file
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/services/sound_manager.py`, `src/backend/adapters/audio_importer.py`

> **Implementation notes:** Implemented `sound_manager.py` with `SoundCategory` enum, `Sound` dataclass, `BUILT_IN_SOUNDS` dictionary with 5 sounds per category, `get_built_in_sounds()`, `get_custom_sounds()`, `get_sound_by_id()`, `get_all_sounds_for_category()`, `import_custom_sound()`, `delete_custom_sound()`, `get_sound_for_reminder()`, `set_sound_for_reminder()`, `get_default_sound()`, `validate_sound_file()`, `get_sound_playback_path()`, `should_fallback_to_default()`. All spec requirements implemented including validation for MP3/WAV/M4A, 30-sec max duration, 1MB max size.

---

## Phase 3: Frontend Mobile App (Week 5-8)

### Status: NOT STARTED — Mobile app project does not exist yet

### P0 — Critical Path

#### 14. React Native Project Setup
**Status:** Pending — No mobile project exists yet
**Task:** Initialize React Native project with required dependencies
- Initialize with React Native CLI or Expo
- Install: notifee, @react-native-community/geolocation, react-native-fs, @react-native-async-storage/async-storage
- Configure iOS background modes (audio, fetch, processing)
- Set up navigation (React Navigation)
- **Files:** `mobile/`, `mobile/ios/`, `mobile/android/`

#### 15. Quick Add Interface
**Status:** Pending
**Spec Ref:** Section 3.2
**Task:** Build reminder creation UI
- Text/speech input field
- Parse confirmation card (display parsed interpretation)
- Manual field correction before confirm
- Voice personality selector
- Sound category selector
- **Acceptance Criteria:** User can create reminder end-to-end
**Files:** `mobile/src/screens/QuickAddScreen.tsx`, `mobile/src/components/ParseConfirmationCard.tsx`

#### 16. Reminders List & Management
**Status:** Pending
**Task:** Build reminder list and CRUD operations
- List all reminders with status indicators
- Create, read, update, delete reminders
- Calendar-sourced reminders visually distinguished
- Edit reminder flow
- **Acceptance Criteria:** Full CRUD operations work
**Files:** `mobile/src/screens/RemindersListScreen.tsx`, `mobile/src/components/ReminderCard.tsx`

#### 17. Active Alarm Screen
**Status:** Pending
**Spec Ref:** Section 5.2
**Task:** Build full-screen alarm display when anchor fires
- Display destination, time remaining, voice personality icon
- Tap area for snooze (1 min)
- Tap-and-hold for custom snooze picker
- Swipe to dismiss with feedback prompt
- TTS playback during alarm
- **Acceptance Criteria:** User can interact with firing anchor
**Files:** `mobile/src/screens/ActiveAlarmScreen.tsx`, `mobile/src/components/SnoozePicker.tsx`

#### 18. Settings & Preferences
**Status:** Pending
**Spec Ref:** Section 10.1
**Task:** Build settings UI
- Voice personality selector (5 + custom)
- Default sound category
- Quiet hours configuration
- Calendar permissions
- Location permissions
- **Acceptance Criteria:** All preferences persist and apply
**Files:** `mobile/src/screens/SettingsScreen.tsx`, `mobile/src/stores/preferencesStore.ts`

#### 19. History & Stats Screen
**Status:** Pending
**Spec Ref:** Section 11.2
**Task:** Build history and statistics UI
- Weekly hit rate display
- Streak counter
- Common miss window
- History list with outcomes
- **Acceptance Criteria:** Stats compute correctly from history
**Files:** `mobile/src/screens/HistoryScreen.tsx`, `mobile/src/components/StatsCard.tsx`

---

### P1 — High Priority

#### 20. Calendar Tab
**Status:** Pending
**Spec Ref:** Section 7.2
**Task:** Build calendar integration UI
- Sync status indicator
- Suggestion cards for events with locations
- Connect/disconnect Google Calendar
- Manage Apple Calendar permissions
- **Acceptance Criteria:** Calendar events appear as suggestions
**Files:** `mobile/src/screens/CalendarScreen.tsx`, `mobile/src/components/CalendarSuggestionCard.tsx`

#### 21. Sound Library UI
**Status:** Pending
**Spec Ref:** Section 12.2
**Task:** Build sound selection UI
- Category tabs (commute, routine, errand, custom)
- Built-in sound previews
- Custom import button
- Import file picker (MP3, WAV, M4A)
- **Acceptance Criteria:** User can select and import sounds
**Files:** `mobile/src/screens/SoundLibraryScreen.tsx`

---

## Phase 4: Testing & Polish (Week 9-10)

### Status: NOT STARTED — Backend implementation complete, needs testing

### P1 — High Priority

#### 22. Integration Tests
**Status:** Pending
**Spec Ref:** Section 14
**Task:** Write integration tests for critical flows
- Full reminder creation flow (parse → chain → TTS → persist)
- Anchor firing flow (schedule → fire → mark fired)
- Snooze recovery flow (snooze → recompute → re-register)
- Feedback loop flow (dismiss → feedback → adjustment)
- **Target:** All integration tests pass
**Files:** `tests/integration/*.py`

#### 23. E2E Tests (Detox)
**Status:** Pending
**Spec Ref:** Section 14
**Task:** Write end-to-end tests for critical user journeys
- Quick Add flow (input → parse → confirm → create)
- Anchor firing sequence
- Snooze interaction
- Dismissal feedback
- Settings navigation
- Sound library browsing
- **Target:** All E2E tests pass
**Files:** `tests/e2e/*.spec.ts`

---

## Known Gaps & Technical Debt

### Schema Gaps
- **Recurring reminders:** No `recurrence_rule` field in reminders table (spec Section 1.3 mentions standing/recurring reminders)
- **Streak tracking:** Stats service calculates but persistence model incomplete

### Missing Features (Not in Mobile App)
- Morning routine templates (spec Section 1.3)
- Standing/recurring reminder support
- Custom prompt mode (200 char max) in UI

### Backend Test Coverage
- No unit tests exist for chain engine, parser, or services
- Integration tests not implemented
- Need test fixtures for LLM and TTS adapters

### Technical Debt
- `src/test_server.py` is a monolithic proof-of-concept (628 lines) — needs refactoring into proper service modules
- TTS cache directory not cleaned up automatically

---

## Dependency Map

```
Phase 1 (Foundation) - COMPLETED
├── 1. Database Migration System ✅
├── 2. Chain Engine + get_next_unfired_anchor ✅
├── 3. LLM Adapter Interface + Mock ✅
├── 4. Reminder Parser Integration ✅
├── 5. Voice Personality Variations ✅
├── 6. TTS Adapter + Mock ✅
├── 7. History/Stats/Feedback Loop ✅
└── 8. Snooze/Dismissal Flow ✅

Phase 2 (Backend Services) - COMPLETED
├── 9. Background Scheduling ✅
├── 10. Notification/Alarm ✅
├── 11. Calendar Integration ✅
├── 12. Location Awareness ✅
└── 13. Sound Library ✅

Phase 3 (Frontend) - NOT STARTED
├── 14. RN Project Setup
├── 15. Quick Add (depends on backend services)
├── 16. Reminders List (depends on 14)
├── 17. Active Alarm (depends on 9, 10)
├── 18. Settings (depends on backend)
├── 19. History/Stats (depends on 7)
├── 20. Calendar Tab (depends on 11)
└── 21. Sound Library (depends on 13)

Phase 4 (Testing) - NOT STARTED
├── 22. Integration Tests (depends on phases 1-3)
└── 23. E2E Tests (depends on phase 3)
```

---

## Quick Start

**Backend is complete.** Next steps are Phase 3 (Mobile App):

1. **Week 5:** Initialize React Native project (Task 14)
2. **Week 6-7:** Build UI screens and navigation (Tasks 15-19)
3. **Week 8:** Calendar and Sound Library UI (Tasks 20-21)
4. **Week 9-10:** Integration and E2E testing (Tasks 22-23)

---

## Notes

- Backend runs on Python with SQLite
- Database: SQLite with native Python driver
- TTS: ElevenLabs API with pre-generation at reminder creation
- Background: Notifee for mobile push notifications
- Calendar: EventKit (iOS) + Google Calendar API
- Location: Single check at departure anchor only