# URGENT — AI Escalating Voice Alarm Implementation Plan

## Overview
This document maps the specification requirements to implementation tasks, prioritized by dependencies. The plan assumes a React Native + Node.js backend architecture.

## Gap Analysis Summary

| Spec Section | Status | Gap |
|-------------|--------|-----|
| 2. Escalation Chain Engine | Partial | Basic logic exists, needs unit tests and get_next_unfired_anchor |
| 3. Reminder Parsing | Partial | Keyword fallback exists, needs LLM adapter, mock interface |
| 4. Voice & TTS Generation | None | ElevenLabs integration, caching, mock interface needed |
| 5. Notification & Alarm | None | DND, quiet hours, chain overlap, sound tiers not implemented |
| 6. Background Scheduling | None | Notifee, BGTaskScheduler, recovery scan not implemented |
| 7. Calendar Integration | None | EventKit, Google Calendar API not implemented |
| 8. Location Awareness | None | CoreLocation single-check not implemented |
| 9. Snooze & Dismissal | Partial | Basic history recording, needs full interaction flow |
| 10. Voice Personality | Partial | Templates exist, needs custom prompt, message variations |
| 11. History & Stats | Partial | Basic hit rate, needs feedback loop, common miss window |
| 12. Sound Library | None | Built-in sounds, custom import not implemented |
| 13. Data Persistence | Partial | Basic schema, needs migrations, in-memory mode |

---

## Phase 1: Foundation & Core Logic (Week 1-2)

### P0 — Critical Path

#### 1. Database Migration System
**Spec Ref:** Section 13
**Task:** Implement versioned SQLite migration system
- Create migration runner that applies sequential versions
- Implement in-memory test mode (`?mode=memory`)
- Add all schema tables from spec with proper foreign keys
- **Acceptance Criteria:** Fresh install applies migrations, tests use clean in-memory DB
**Files:** `src/backend/database/migrations/*.sql`, `src/backend/database/migrator.py`

#### 2. Chain Engine Unit Tests & get_next_unfired_anchor
**Spec Ref:** Section 2.3, 2.4
**Task:** Complete chain engine with recovery function
- Add `get_next_unfired_anchor(reminder_id)` function
- Write unit tests for all 6 test scenarios (TC-01 through TC-06)
- Ensure determinism for identical inputs
- **Acceptance Criteria:** All spec test scenarios pass
**Files:** `src/backend/services/chain_engine.py`, `tests/unit/test_chain_engine.py`

#### 3. LLM Adapter Interface & Mock Implementation
**Spec Ref:** Section 3.3, 3.4
**Task:** Create mock-able LLM adapter for parsing
- Define `ILanguageModelAdapter` interface
- Implement MiniMax API adapter (configurable endpoint)
- Create mock adapter for tests returning predefined fixtures
- Implement keyword extraction fallback
- **Acceptance Criteria:** Mock returns fixture without API call, fallback works on API failure
**Files:** `src/backend/adapters/llm_adapter.py`, `src/backend/adapters/mock_llm.py`

#### 4. Reminder Parser Integration
**Spec Ref:** Section 3.3, 3.4
**Task:** Connect LLM adapter to reminder creation flow
- Parse natural language input via LLM
- Display parsed interpretation for user confirmation
- Allow manual field correction before confirm
- Extract: destination, arrival_time, drive_duration, reminder_type
- **Acceptance Criteria:** All 7 test scenarios pass (TC-01 through TC-07)
**Files:** `src/backend/services/reminder_parser.py`

---

### P1 — High Priority

#### 5. Voice Personality System with Variations
**Spec Ref:** Section 10.3, 10.4
**Task:** Enhance voice personality with message variations
- Add minimum 3 message variations per tier per personality
- Implement custom prompt mode (max 200 chars)
- Store selected personality in user preferences
- Existing reminders retain personality from creation time
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/services/voice_generator.py`, `src/backend/services/message_templates.py`

#### 6. TTS Adapter Interface & Mock
**Spec Ref:** Section 4.3, 4.4
**Task:** Create mock-able TTS adapter for pre-generation
- Define `ITTSAdapter` interface
- Implement ElevenLabs API adapter
- Create mock adapter for tests (writes silent file)
- Implement cache storage at `/tts_cache/{reminder_id}/`
- Handle fallback on API failure (system sound + text)
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/adapters/tts_adapter.py`, `src/backend/adapters/mock_tts.py`

#### 7. History, Stats & Feedback Loop
**Spec Ref:** Section 11.3, 11.4
**Task:** Implement feedback-driven drive duration adjustment
- Calculate hit rate for trailing 7 days
- Implement adjustment: `adjusted_drive = stored + (late_count * 2)`, capped at +15 min
- Track common miss window (most frequently missed urgency tier)
- Streak counter for recurring reminders
- **Acceptance Criteria:** All 7 test scenarios pass
**Files:** `src/backend/services/stats_service.py`, `src/backend/services/feedback_loop.py`

#### 8. Snooze & Dismissal Flow
**Spec Ref:** Section 9.3, 9.4
**Task:** Implement full snooze interaction flow
- Tap = 1 min snooze with TTS confirmation
- Tap-and-hold = custom snooze picker (1, 3, 5, 10, 15 min)
- Chain re-computation after snooze (shift remaining anchors)
- Swipe-to-dismiss = feedback prompt with options
- Persist snooze state across app restarts
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/snooze_handler.py`, `src/backend/services/dismissal_handler.py`

---

## Phase 2: Backend Services & Integrations (Week 3-4)

### P1 — High Priority

#### 9. Background Scheduling with Notifee
**Spec Ref:** Section 6.3, 6.4
**Task:** Implement reliable background anchor firing
- Register each anchor as individual Notifee task
- iOS: BGAppRefreshTask + BGProcessingTask
- Recovery scan on app launch (fire anchors within 15-min grace)
- Re-register pending anchors on crash recovery
- Log late fires (>60s) as warnings
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/scheduler.py`, `src/backend/services/recovery_scan.py`

#### 10. Notification & Alarm Behavior
**Spec Ref:** Section 5.3, 5.4
**Task:** Implement notification tier escalation and DND handling
- Tier sounds: chime (calm/casual), beep (pointed/urgent), siren (pushing/firm), alarm loop (critical/alarm)
- DND: silent notification pre-5-min, visual+vibration at T-5
- Quiet hours: suppress 10pm-7am (configurable), queue post-quiet-hours
- Chain overlap: serialize, queue new anchors until current completes
- **Acceptance Criteria:** All 6 test scenarios pass
**Files:** `src/backend/services/notification_manager.py`, `src/backend/services/dnd_handler.py`

#### 11. Calendar Integration
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

---

### P2 — Medium Priority

#### 12. Location Awareness
**Spec Ref:** Section 8.3, 8.4
**Task:** Implement single-point location check at departure
- Request permission only on first location-aware reminder
- Single CoreLocation/FusedLocationProvider call at departure anchor
- 500m geofence radius for "at origin"
- Escalate to firm/critical if still at origin
- Do not store location history
- **Acceptance Criteria:** All 5 test scenarios pass
**Files:** `src/backend/adapters/location_adapter.py`

#### 13. Sound Library
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

---

## Phase 3: Frontend Mobile App (Week 5-8)

### P0 — Critical Path

#### 14. React Native Project Setup
**Task:** Initialize React Native project with required dependencies
- Initialize with React Native CLI or Expo
- Install: notifee, @react-native-community/geolocation, react-native-fs, @react-native-async-storage/async-storage
- Configure iOS background modes (audio, fetch, processing)
- Set up navigation (React Navigation)
- **Files:** `mobile/`, `mobile/ios/`, `mobile/android/`

#### 15. Quick Add Interface
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
**Task:** Build reminder list and CRUD operations
- List all reminders with status indicators
- Create, read, update, delete reminders
- Calendar-sourced reminders visually distinguished
- Edit reminder flow
- **Acceptance Criteria:** Full CRUD operations work
**Files:** `mobile/src/screens/RemindersListScreen.tsx`, `mobile/src/components/ReminderCard.tsx`

#### 17. Active Alarm Screen
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
**Spec Ref:** Section 7.2
**Task:** Build calendar integration UI
- Sync status indicator
- Suggestion cards for events with locations
- Connect/disconnect Google Calendar
- Manage Apple Calendar permissions
- **Acceptance Criteria:** Calendar events appear as suggestions
**Files:** `mobile/src/screens/CalendarScreen.tsx`, `mobile/src/components/CalendarSuggestionCard.tsx`

#### 21. Sound Library UI
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

### P1 — High Priority

#### 22. Integration Tests
**Spec Ref:** Section 14
**Task:** Write integration tests for critical flows
- Full reminder creation flow (parse → chain → TTS → persist)
- Anchor firing flow (schedule → fire → mark fired)
- Snooze recovery flow (snooze → recompute → re-register)
- Feedback loop flow (dismiss → feedback → adjustment)
- **Target:** All integration tests pass
**Files:** `tests/integration/*.py`

#### 23. E2E Tests (Detox)
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

## Dependency Map

```
Phase 1 (Foundation)
├── 1. Database Migration System
├── 2. Chain Engine + get_next_unfired_anchor
├── 3. LLM Adapter Interface + Mock
├── 4. Reminder Parser Integration
├── 5. Voice Personality Variations
├── 6. TTS Adapter + Mock
├── 7. History/Stats/Feedback Loop
└── 8. Snooze/Dismissal Flow
    │
    ├─depends on──► 2 (chain anchor recovery)
    ├─depends on──► 6 (TTS confirmation)
    └─depends on──► 7 (feedback storage)

Phase 2 (Backend Services)
├── 9. Background Scheduling (depends on 2, 8)
├── 10. Notification/Alarm (depends on 9)
├── 11. Calendar Integration (depends on 4)
└── 12. Location Awareness (depends on 2)
    └── 13. Sound Library

Phase 3 (Frontend)
├── 14. RN Project Setup
├── 15. Quick Add (depends on 3, 4)
├── 16. Reminders List (depends on 1, 2)
├── 17. Active Alarm (depends on 9, 10, 8)
├── 18. Settings (depends on 5, 11, 12)
├── 19. History/Stats (depends on 7)
├── 20. Calendar Tab (depends on 11)
└── 21. Sound Library (depends on 13)

Phase 4 (Testing)
└── 22. Integration Tests (depends on phases 1-3)
    └── 23. E2E Tests (depends on phases 1-3)
```

---

## Quick Start

To begin implementation:

1. **Day 1-2:** Set up database migration system (Task 1)
2. **Day 3-5:** Complete chain engine with unit tests (Task 2)
3. **Day 6-8:** Implement LLM adapter interface + mock (Task 3)
4. **Day 9-10:** Connect parser to reminder creation (Task 4)

---

## Notes

- Backend runs on Node.js with Express
- Database: SQLite with better-sqlite3 (synchronous) for performance
- TTS: ElevenLabs API with pre-generation at reminder creation
- Background: Notifee for cross-platform push notifications
- Calendar: EventKit (iOS) + Google Calendar API
- Location: Single check at departure anchor only