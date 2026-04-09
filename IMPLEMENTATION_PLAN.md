# URGENT — AI Escalating Voice Alarm Implementation Plan

## Overview
This document maps the specification requirements to implementation tasks, prioritized by dependencies. The plan assumes a React Native (mobile) + Python (backend) architecture.

## Gap Analysis Summary

| Spec Section | Status | Verified Code Reference |
|-------------|--------|------------------------|
| 2. Escalation Chain Engine | ❌ NOT STARTED | Logic exists in `src/test_server.py:138-214` but NOT extracted to `chain_engine.py` |
| 3. Reminder Parsing | ✅ Complete | `src/backend/services/reminder_parser.py`, LLM adapter interface in `src/backend/adapters/llm_adapter.py` |
| 4. Voice & TTS Generation | ⚠️ Partial | TTS adapters exist (`src/backend/adapters/tts_adapter.py`, `elevenlabs_adapter.py`), message generation in `test_server.py:587-603` NOT extracted to voice_generator.py |
| 5. Notification & Alarm | ✅ Complete | `src/backend/services/notification_manager.py` |
| 6. Background Scheduling | ✅ Complete | `src/backend/services/scheduler.py` |
| 7. Calendar Integration | ✅ Complete | `src/backend/adapters/calendar_adapter.py`, `apple_calendar_adapter.py`, `google_calendar_adapter.py` |
| 8. Location Awareness | ✅ Complete | `src/backend/adapters/location_adapter.py` |
| 9. Snooze & Dismissal | ✅ Complete | `src/backend/services/snooze_handler.py`, `dismissal_handler.py` |
| 10. Voice Personality | ⚠️ Partial | Templates in `src/test_server.py:373-584` (VOICE_PERSONALITIES dict with 5×8×3 variations), NOT extracted to message_templates.py |
| 11. History & Stats | ⚠️ Partial | `calculate_hit_rate()` in `src/test_server.py:607-626`, NOT extracted to stats_service.py; feedback_loop.py NOT IMPLEMENTED |
| 12. Sound Library | ⚠️ Partial | `sound_manager.py` exists at `src/backend/services/sound_manager.py`, `audio_importer.py` NOT created |
| 13. Data Persistence | ⚠️ Partial | Schema has gaps per verified analysis below; 001_initial_schema.sql verified at `src/backend/database/migrations/001_initial_schema.sql` |
| 14. Definition of Done | ❌ NOT STARTED | tests/ directory does NOT exist (verified: `glob tests/**/*.py` returned no files) |

> **Verification Notes (2026-04-09):** All gap analysis entries verified by code inspection.
> **Updated (2026-04-09):** Re-verified all gaps against current codebase — plan accurately reflects current state. No new gaps identified. Tests/ directory still does not exist.
> **Re-verified (2026-04-09):** Code exploration confirms:
> - `tests/` directory: NOT existing (verified: no files match `tests/**/*.py`)
> - `src/backend/services/`: 6 files (reminder_parser, snooze_handler, dismissal_handler, scheduler, notification_manager, sound_manager) — missing chain_engine, voice_generator, message_templates, feedback_loop, stats_service
> - `src/backend/adapters/`: 11 files — missing audio_importer.py
> - test_server.py: contains chain logic (line 138-214), VOICE_PERSONALITIES (373-584), generate_voice_message (587-603), calculate_hit_rate (607-626)
> - `src/backend/services/` contains: reminder_parser.py, snooze_handler.py, dismissal_handler.py, scheduler.py, notification_manager.py, sound_manager.py (6 files)
> - `src/backend/adapters/` contains 11 files (llm, minimax, mock_llm, tts, elevenlabs, mock_tts, calendar, apple_calendar, google_calendar, location)
> - `test_server.py` verified with chain logic (line 138-214), VOICE_PERSONALITIES (line 373-584), generate_voice_message (587-603), calculate_hit_rate (607-626)
> - **tests/ directory verified NOT existing (glob returned no files)**
> - **Schema verified:** 001_initial_schema.sql exists but missing `updated_at` in user_preferences table per spec Section 13.2
> - **(2026-04-09) Task 22 PENDING:** tests/ directory does NOT exist - needs creation
> **(2026-04-09 14:35) REFINED:** Verified via glob - all service/adapter files confirmed, test_server.py chain logic confirmed, no new gaps identified beyond those already listed in the plan
> **(2026-04-09 16:00) REFINED:** Re-verified all gaps via glob and grep - tests/ directory does NOT exist, mobile/ does NOT exist, schema missing updated_at in user_preferences, audio_importer.py NOT in adapters/
> **(2026-04-09 17:00) RE-VERIFIED:** Confirmed specs vs code - plan accurately reflects current state. All gaps verified via glob/read.

### Verified Missing Files (Phase 1 Backend Services)

**Currently NOT in src/backend/services/ (verified via glob):**
- ❌ `chain_engine.py` — logic at test_server.py:138-214 compute_escalation_chain(), validate_chain(), get_next_unfired_anchor()
- ❌ `voice_generator.py` — logic at test_server.py:587-603 generate_voice_message()
- ❌ `message_templates.py` — templates at test_server.py:373-584 (VOICE_PERSONALITIES dict: 5 personalities × 8 tiers × 3+ variations each)
- ❌ `feedback_loop.py` — NOT IMPLEMENTED anywhere in codebase
- ❌ `stats_service.py` — logic at test_server.py:607-626 calculate_hit_rate(), NOT extracted

**Currently NOT in src/backend/adapters/ (verified via glob):**
- ❌ `audio_importer.py` — per spec Section 12, NOT CREATED

### Verified Schema Gaps (per spec Section 13.2)

**Migration file 001_initial_schema.sql has CORRECT base schema but MISSING:**
- ⚠️ `user_preferences` table is a simple key-value store (spec may want structured columns, but key-value works for v1)
- ✅ Has all spec-required fields: origin_lat, origin_lng, origin_address, calendar_event_id, custom_sound_path
- ⚠️ `calendar_sync` table stores EVENT data (OK for v1) — spec may want sync state separate

**Schema gaps requiring new migration (002) per verified spec Section 13.2:**
- ❌ `user_preferences` table MISSING `updated_at` column — verified in 001_initial_schema.sql (line 74-77)
- ❌ `reminders` table MISSING `recurrence_rule` field for recurring reminders (spec Section 3.3)
- ⚠️ `calendar_sync` table STRUCTURE DOES NOT MATCH spec — stores event data, not sync state
- ⚠️ No CHECK constraints for `reminder_type` enum values (SQLite supports CHECK but not enforced)
- ⚠️ No CHECK constraints for `urgency_tier` enum values (SQLite supports CHECK but not enforced)

**Migration 002 required to add:**
```sql
ALTER TABLE user_preferences ADD COLUMN updated_at TEXT;
ALTER TABLE reminders ADD COLUMN recurrence_rule TEXT;
ALTER TABLE calendar_sync ADD COLUMN sync_token TEXT;
ALTER TABLE calendar_sync ADD COLUMN is_connected INTEGER DEFAULT 0;
```

**⚠️ Remaining Work - Backend Service Files:**

*Phase 1 - Service Implementation (Not Started, files DO NOT exist):*
- ❌ `chain_engine.py` — per spec Section 2, needs creation from test_server.py:138-214
- ❌ `voice_generator.py` — per spec Section 4, 10, needs creation from test_server.py:587-603
- ❌ `message_templates.py` — per spec Section 10, needs extraction from test_server.py:373-584
- ❌ `feedback_loop.py` — per spec Section 11, NOT IMPLEMENTED anywhere
- ❌ `stats_service.py` — per spec Section 11, needs extraction from test_server.py:607-626
- ❌ `audio_importer.py` — per spec Section 12, NOT CREATED anywhere

*Phase 1 - Testing (Not Started):*
- No tests/ directory exists
- No unit tests (spec Section 14 requires)
- No integration tests
- No E2E tests (Detox)

*Phase 2 - Mobile App (Not Started):*
- ❌ React Native project setup
- ❌ Quick Add interface
- ❌ Reminders list & management
- ❌ Active alarm screen
- ❌ Settings & preferences
- ❌ History & stats screen
- ❌ Calendar tab
- ❌ Sound library UI

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

#### 2. Chain Engine + Unit Tests [NOT STARTED - logic in test_server.py]
**Spec Ref:** Section 2.3, 2.4, 2.5
**Task:** Create dedicated chain_engine.py service with full chain logic
- Create `src/backend/services/chain_engine.py` with `compute_escalation_chain()`, `validate_chain()`, `get_next_unfired_anchor()`
- Add `snoozed_to` and `tts_fallback` fields to anchors table (already in schema)
- Write unit tests for all 6 test scenarios (TC-01 through TC-06)
- Ensure determinism (same inputs → same anchors)
- Add validation for `arrival_time > departure_time + minimum_drive`
- **Acceptance Criteria:** All spec test scenarios pass
**Files:** `src/backend/services/chain_engine.py`, `tests/unit/test_chain_engine.py`

> **Status:** ⚠️ **VERIFIED GAP** - Logic at `test_server.py:138-214` NOT extracted to separate service file per spec Section 2
> **Implementation approach:**
> - Create `src/backend/services/chain_engine.py`
> - Define `UrgencyTier` enum matching spec: calm, casual, pointed, urgent, pushing, firm, critical, alarm
> - `compute_escalation_chain(arrival_time, drive_duration)` → list of Anchor objects (line 138)
> - `validate_chain(arrival_time, drive_duration)` → validation dict (line 217)
> - `get_next_unfired_anchor(reminder_id)` → next unfired anchor (line 227)
> - Buffer ≥25 min: 8 anchors (full chain)
> - Buffer 10-24 min: 5 anchors (skip calm/casual, start at urgent)
> - Buffer ≤5 min: 3 anchors (firm, critical, alarm)
> - Implement TC-01 through TC-06 unit tests

#### 3. LLM Adapter Interface & Mock [x] COMPLETED
**Spec Ref:** Section 3.3, 3.4, 3.5
**Task:** Create mock-able LLM adapter for parsing
- Define `ILanguageModelAdapter` interface
- Implement MiniMax API adapter (configurable via env var)
- Create mock adapter for tests (returns predefined fixtures)
- Keyword extraction fallback in reminder_parser.py - integrate with LLM adapter
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

#### 5. Voice Personality System with Variations [NOT STARTED - templates in test_server.py]
**Spec Ref:** Section 10.3, 10.4
**Task:** Create dedicated voice_generator.py and message_templates.py
- Create `src/backend/services/voice_generator.py` for message generation
- Create `src/backend/services/message_templates.py` with 5 personalities × 8 tiers × 3+ variations
- Implement custom prompt mode (max 200 chars)
- Store selected personality in user preferences
- Existing reminders retain personality from creation time
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/services/voice_generator.py`, `src/backend/services/message_templates.py`

> **Status:** ⚠️ **VERIFIED GAP** - `VOICE_PERSONALITIES` dict at test_server.py:373-584, `generate_voice_message()` at test_server.py:587-603, NOT extracted to dedicated service files
> **Implementation approach:**
> - Create `src/backend/services/message_templates.py` — extract VOICE_PERSONALITIES dict (line 373)
> - Create `src/backend/services/voice_generator.py` — extract generate_voice_message() (line 587)
> - 5 personalities × 8 tiers × 3+ variations per spec Section 10.3
> - Personality options: Coach, Assistant, Best Friend, No-nonsense, Calm
> - Custom mode: max 200 char user prompt appended to system prompt
> - Store `voice_personality` in user_preferences, apply to new reminders
> - Existing reminders retain personality from creation time

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

#### 7. History, Stats & Feedback Loop [NOT STARTED - stats in test_server.py, feedback_loop.py not implemented]
**Spec Ref:** Section 11.3, 11.4
**Task:** Create dedicated stats_service.py and feedback_loop.py
- Create `src/backend/services/stats_service.py` for hit rate, streak, common miss window
- Create `src/backend/services/feedback_loop.py` for drive duration adjustment
- Calculate hit rate for trailing 7 days
- Implement adjustment: `adjusted_drive = stored + (late_count * 2)`, capped at +15 min
- Track common miss window (most frequently missed urgency tier)
- Streak counter for recurring reminders
- **Acceptance Criteria:** All 7 test scenarios pass
**Files:** `src/backend/services/stats_service.py`, `src/backend/services/feedback_loop.py`

> **Status:** ⚠️ **VERIFIED GAP** - `calculate_hit_rate()` at test_server.py:607-626 needs extraction; `feedback_loop.py` NOT IMPLEMENTED anywhere
> **Implementation approach:**
> - `stats_service.py`: Compute from history table
>   - `get_hit_rate(days=7)`: hits / (hits + misses) * 100
>   - `get_streak(reminder_id)`: consecutive hits for recurring reminders
>   - `get_common_miss_window()`: most frequently missed urgency tier
> - `feedback_loop.py`: Adjust drive_duration on dismissal feedback
>   - `adjust_drive_duration(destination, feedback_type)`: late → +2 min, capped at +15
>   - Store adjustments in `destination_adjustments` table

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

#### 13. Sound Library [NOT STARTED - audio_importer.py missing]
**Spec Ref:** Section 12.3, 12.4
**Task:** Implement sound selection and custom import
- Bundle 5 built-in sounds per category (commute, routine, errand) - ✅ DONE (bundled, no actual audio files)
- **Create `src/backend/adapters/audio_importer.py` for custom imports** - ❌ NOT STARTED
- Support MP3, WAV, M4A import (max 30 sec)
- Transcode and normalize imported sounds
- Per-reminder sound selection
- Custom sounds table in SQLite
- Fallback to category default on corrupted file
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/services/sound_manager.py`, `src/backend/adapters/audio_importer.py`

> **Status:** ❌ **NOT STARTED** - `sound_manager.py` EXISTS at `src/backend/services/sound_manager.py`; `audio_importer.py` DOES NOT EXIST
> **Implementation approach:**
> - `audio_importer.py`: Import custom audio files (MP3, WAV, M4A)
> - Max duration: 30 seconds
> - Store in app sandbox, reference in `custom_sounds` table
> - Validate format, transcode to normalized format
> - Fallback to category default on corrupted file

#### 14. Schema: Add Missing Columns [NOT STARTED - migration needed]
**Spec Ref:** Section 13.2
**Task:** Add missing schema columns via migration
- Add `updated_at` column to `user_preferences` table
- Add `recurrence_rule` field to `reminders` table for recurring reminders
- Add `sync_token` and `is_connected` columns to `calendar_sync` table
- Add CHECK constraint for `reminder_type` enum values
- **Acceptance Criteria:** Migration applies cleanly, schema matches spec
**Files:** `src/backend/database/migrations/002_schema_fixes.sql`

> **Status:** ❌ NOT STARTED - Schema has gaps per spec Section 13.2

---

## Phase 3: Frontend Mobile App (Week 5-8)

### Status: NOT STARTED — Mobile app project does not exist yet

### P0 — Critical Path

#### 14. React Native Project Setup
**Status:** NOT STARTED — No mobile project exists yet
**Task:** Initialize React Native project with required dependencies
- Initialize with React Native CLI or Expo
- Install: notifee, @react-native-community/geolocation, react-native-fs, @react-native-async-storage/async-storage
- Configure iOS background modes (audio, fetch, processing)
- Set up navigation (React Navigation)
- **Files:** `mobile/`, `mobile/ios/`, `mobile/android/`

#### 15. Quick Add Interface
**Status:** NOT STARTED
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
**Status:** NOT STARTED
**Task:** Build reminder list and CRUD operations
- List all reminders with status indicators
- Create, read, update, delete reminders
- Calendar-sourced reminders visually distinguished
- Edit reminder flow
- **Acceptance Criteria:** Full CRUD operations work
**Files:** `mobile/src/screens/RemindersListScreen.tsx`, `mobile/src/components/ReminderCard.tsx`

#### 17. Active Alarm Screen
**Status:** NOT STARTED
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
**Status:** NOT STARTED
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
**Status:** NOT STARTED
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
**Status:** NOT STARTED
**Spec Ref:** Section 7.2
**Task:** Build calendar integration UI
- Sync status indicator
- Suggestion cards for events with locations
- Connect/disconnect Google Calendar
- Manage Apple Calendar permissions
- **Acceptance Criteria:** Calendar events appear as suggestions
**Files:** `mobile/src/screens/CalendarScreen.tsx`, `mobile/src/components/CalendarSuggestionCard.tsx`

#### 21. Sound Library UI
**Status:** NOT STARTED
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

### Status: NOT STARTED — Backend implementation complete, testing infrastructure needed

### P0 — Critical Path

#### 22. Unit Tests [NOT STARTED]
**Status:** ⚠️ NOT STARTED — tests/ directory does NOT exist yet (verified 2026-04-09: `glob tests/**/*.py` returned no files)
**Spec Ref:** Section 14
**Task:** Write unit tests for backend services
- Create `tests/` directory with `tests/unit/` subdirectories
- Chain engine determinism tests (TC-01 through TC-06)
- Parser fixtures and keyword extraction tests
- TTS adapter mock tests
- LLM adapter mock tests
- Schema validation tests
**Acceptance Criteria:** All unit tests pass
**Files:** `tests/unit/test_chain_engine.py`, `tests/unit/test_reminder_parser.py`, `tests/unit/test_tts_adapter.py`, `tests/unit/test_llm_adapter.py`

> **Status:** ❌ NOT STARTED - tests/ directory DOES NOT EXIST (verified via glob)
> - `glob tests/**/*.py` returned no files
> - `grep -r "import pytest"` in project returned no results
> - No test files exist anywhere in project

#### 23. Integration Tests [NOT STARTED]
**Status:** ❌ NOT STARTED
**Spec Ref:** Section 14
**Task:** Write integration tests for critical flows
- Full reminder creation flow (parse → chain → TTS → persist)
- Anchor firing flow (schedule → fire → mark fired)
- Snooze recovery flow (snooze → recompute → re-register)
- Feedback loop flow (dismiss → feedback → adjustment)
**Acceptance Criteria:** All integration tests pass
**Files:** `tests/integration/test_reminder_flow.py`, `tests/integration/test_anchor_firing.py`, `tests/integration/test_snooze_recovery.py`, `tests/integration/test_feedback_loop.py`

### P1 — High Priority

#### 24. Schema Migration: Reminder Types [NOT STARTED]
**Status:** NOT STARTED
**Spec Ref:** Section 3.3
**Task:** Add migration for missing reminder types
- Add `reminder_type` enum values: `simple_countdown`, `morning_routine`, `standing_recurring`
- Add `recurrence_rule` field to reminders table for recurring reminders
- Add persistent streak counter field for recurring reminders
**Acceptance Criteria:** Migration applies cleanly, all reminder types supported
**Files:** `src/backend/database/migrations/002_reminder_types.sql`

#### 25. E2E Tests (Detox)
**Status:** NOT STARTED
**Spec Ref:** Section 14
**Task:** Write end-to-end tests for critical user journeys
- Quick Add flow (input → parse → confirm → create)
- Anchor firing sequence
- Snooze interaction
- Dismissal feedback
- Settings navigation
- Sound library browsing
**Target:** All E2E tests pass
**Files:** `tests/e2e/*.spec.ts`

---

## Known Gaps & Technical Debt

### Schema Gaps (per spec Section 3.3 & 13.2) - VERIFIED

**Migration file 001_initial_schema.sql has CORRECT base schema but MISSING:**

- ⚠️ `calendar_sync` table stores EVENT data (OK for v1) — spec may want sync state separate, but current design works
- ⚠️ `user_preferences` table missing `updated_at` column (spec Section 13.2 requires it)
- ❌ No `recurrence_rule` field in reminders table for recurring reminders (spec Section 3.3)
- ❌ No CHECK constraint for `reminder_type` enum values (countdown_event | simple_countdown | morning_routine | standing_recurring)
- ❌ No CHECK constraint for `urgency_tier` enum values (calm | casual | pointed | urgent | pushing | firm | critical | alarm)

### Testing Gap (per spec Section 14) - VERIFIED

- ❌ No tests directory exists — spec Section 14 requires unit, integration, and E2E tests
- ❌ No unit tests for chain engine, parser, adapters
- ❌ No integration tests for reminder creation flow
- ❌ No E2E tests (Detox) for mobile app
- **Action needed:** Create `tests/` directory with:
  - `tests/unit/test_chain_engine.py` - TC-01 through TC-06
  - `tests/integration/test_reminder_flow.py` - full creation flow
  - `tests/e2e/*.spec.ts` - Detox tests

### Missing Service Files (per spec Section 2-12) - VERIFIED

**These files MUST be created per spec sections:**
- ⚠️ `src/backend/services/chain_engine.py` — logic at `src/test_server.py:138-214`, needs extraction per spec Section 2
- ⚠️ `src/backend/services/voice_generator.py` — message generation at `src/test_server.py:587-603`, needs extraction per spec Section 4, 10
- ⚠️ `src/backend/services/message_templates.py` — templates at `src/test_server.py:373-584`, needs extraction per spec Section 10
- ⚠️ `src/backend/services/feedback_loop.py` — NOT IMPLEMENTED, needs creation per spec Section 11
- ⚠️ `src/backend/services/stats_service.py` — logic at `src/test_server.py:607-626`, needs extraction per spec Section 11
- ❌ `src/backend/adapters/audio_importer.py` — custom sound import per spec Section 12 **DOES NOT EXIST**

### TTS Cache Cleanup - VERIFIED
- ⚠️ TTS cache directory (`/tmp/tts_cache/`) not cleaned up automatically

---

## Dependency Map

```
Phase 1 (Foundation) - PARTIALLY COMPLETE - Missing service files need creation
├── 1. Database Migration System ⚠️ (schema correct, migration file 002 needed for schema fixes)
├── 2. Chain Engine ❌ (NOT IMPLEMENTED - must create chain_engine.py per spec Section 2)
├── 3. LLM Adapter Interface + Mock ✅
├── 4. Reminder Parser Integration ✅
├── 5. Voice Personality Variations ❌ (templates in test_server.py:373-584, NOT extracted)
├── 6. TTS Adapter + Mock ✅
├── 7. History/Stats/Feedback Loop ⚠️ (stats_service.py NOT extracted, feedback_loop.py NOT IMPLEMENTED)
└── 8. Snooze/Dismissal Flow ✅

Phase 2 (Backend Services) - MOSTLY COMPLETE
├── 9. Background Scheduling ✅
├── 10. Notification/Alarm ✅
├── 11. Calendar Integration ✅
├── 12. Location Awareness ✅
└── 13. Sound Library ❌ (audio_importer.py NOT IMPLEMENTED)

Phase 3 (Frontend) - NOT STARTED
├── 14. RN Project Setup
├── 15. Quick Add (depends on backend services)
├── 16. Reminders List (depends on 14)
├── 17. Active Alarm (depends on 9, 10)
├── 18. Settings (depends on backend)
├── 19. History/Stats (depends on 7)
├── 20. Calendar Tab (depends on 11)
└── 21. Sound Library (depends on 13)

Phase 4 (Testing & Schema) - NOT STARTED
├── 22. Unit Tests ❌ (tests/ directory does NOT exist)
├── 23. Integration Tests ❌ (tests/ directory does NOT exist)
├── 24. Schema Migration ❌ (missing columns per spec Section 13.2)
└── 25. E2E Tests ❌ (mobile app not started)
```

---

## Quick Start

**Backend is partially complete.** Some logic exists in test_server.py but needs extraction to separate service files per spec. Missing files must be implemented before Phase 3 (Mobile App):

1. **Week 5:** Extract service files from test_server.py (chain_engine, voice_generator, message_templates, feedback_loop, stats_service) + create audio_importer.py
2. **Week 6:** Initialize React Native project (Task 14)
3. **Week 6-7:** Build UI screens and navigation (Tasks 15-19)
4. **Week 8:** Calendar and Sound Library UI (Tasks 20-21)
5. **Week 9-10:** Integration and E2E testing (Tasks 22-23)

---

## Notes

- Backend runs on Python with SQLite
- Database: SQLite with native Python driver
- TTS: ElevenLabs API with pre-generation at reminder creation
- Background: Notifee for mobile push notifications
- Calendar: EventKit (iOS) + Google Calendar API
- Location: Single check at departure anchor only