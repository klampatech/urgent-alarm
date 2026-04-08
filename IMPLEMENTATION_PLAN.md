# URGENT Alarm — Implementation Plan

## Executive Summary

The project has a basic proof-of-concept test server with core logic (chain engine, parser, voice templates). The full mobile app infrastructure is missing. This plan prioritizes building a functional app layer by layer, starting with the foundation (adapters, database) and working up to features.

---

## Phase 1: Foundation & Core Adapters (Week 1)

### 1.1 Define Adapter Interfaces
**Priority:** Critical — all features depend on these

Create proper mock-able interfaces for all external services:

```
src/lib/adapters/
├── __init__.py
├── ilanguage_model.py      # LLM parsing interface
├── itts_adapter.py         # TTS generation interface  
├── icalendar_adapter.py    # Calendar integration interface
├── ilocation_adapter.py    # Location check interface
├── inotification_adapter.py # Notifications/alarms interface
├── ischeduler_adapter.py   # Background scheduling interface
└── iaudio_player.py        # Audio playback interface
```

**Tasks:**
- [ ] Define `ILanguageModelAdapter` with `parse(input_text) -> ParsedReminder`
- [ ] Define `ITTSAdapter` with `generate(text, voice_id) -> audio_path`
- [ ] Define `ICalendarAdapter` with `sync_events() -> List[CalendarEvent]`
- [ ] Define `ILocationAdapter` with `check_current_location() -> (lat, lng)`
- [ ] Define `INotificationAdapter` with `show(tier, content)`, `play_sound()`, `vibrate()`
- [ ] Define `ISchedulerAdapter` with `schedule_anchor(anchor, timestamp)`
- [ ] Define `IAudioPlayer` with `play(file_path)`, `loop()`, `stop()`

**Rationale:** Without these interfaces, nothing can be mocked for testing.

---

### 1.2 Implement Mock Adapters
**Priority:** Critical — enables testing

```
src/lib/adapters/mock/
├── __init__.py
├── mock_llm.py
├── mock_tts.py
├── mock_calendar.py
├── mock_location.py
├── mock_notification.py
├── mock_scheduler.py
└── mock_audio.py
```

**Tasks:**
- [ ] Implement `MockLLMAdapter` returning fixture responses
- [ ] Implement `MockTTSAdapter` writing silent 1-second files
- [ ] Implement `MockCalendarAdapter` returning empty/synthetic events
- [ ] Implement `MockLocationAdapter` returning configurable coordinates
- [ ] Implement `MockNotificationAdapter` logging calls
- [ ] Implement `MockSchedulerAdapter` storing scheduled tasks in-memory
- [ ] Implement `MockAudioPlayer` logging play requests

**Tests:**
- [ ] All mock adapters can be instantiated without external dependencies
- [ ] Mock adapters return predictable fixture data

---

### 1.3 Enhance Database Schema & Migrations
**Priority:** Critical — all data depends on this

**Tasks:**
- [ ] Create migration system (`MigrationManager` class)
- [ ] Add schema version tracking table
- [ ] Create `schema_v1_initial.py` migration with full spec schema
- [ ] Add missing tables: `calendar_sync`, `custom_sounds`
- [ ] Add missing columns: `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`
- [ ] Add indexes for performance (`arrival_time`, `status`, `destination`)
- [ ] Enable foreign keys and WAL mode on connection

**Schema from spec (Section 13):**
```sql
-- Core tables: reminders, anchors, history, user_preferences
-- NEW: destination_adjustments, calendar_sync, custom_sounds
```

**Tests:**
- [ ] Fresh install applies all migrations in order
- [ ] In-memory test database works
- [ ] Cascade delete removes anchors when reminder deleted
- [ ] UUID v4 is always generated for new records

---

## Phase 2: Core Business Logic (Week 1-2)

### 2.1 Chain Engine Refinement
**Priority:** Critical — this IS the app

**Current state:** `test_server.py` has basic implementation
**Gaps:** Missing `get_next_unfired_anchor()`, no snooze re-computation

**Tasks:**
- [ ] Refactor chain engine to use adapter interfaces
- [ ] Add `get_next_unfired_anchor(reminder_id) -> Anchor | None`
- [ ] Add `get_remaining_anchors(reminder_id) -> List[Anchor]`
- [ ] Add `shift_anchors(reminder_id, minutes_to_shift) -> None` for snooze
- [ ] Add `cancel_remaining_anchors(reminder_id) -> None` for dismissal
- [ ] Add deterministic unit tests for all chain scenarios (TC-01 through TC-06 from spec)

**Tests:**
- [ ] TC-01: Full chain (≥25 min buffer) — 8 anchors
- [ ] TC-02: Compressed chain (10-24 min buffer) — 5 anchors
- [ ] TC-03: Minimum chain (≤5 min buffer) — 3 anchors
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism

---

### 2.2 LLM Parser Refinement
**Priority:** High — enables natural language reminders

**Current state:** `parse_reminder_natural()` uses regex patterns
**Gaps:** No proper LLM adapter, no confidence scoring UI, no confirmation card

**Tasks:**
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` (direct Claude API)
- [ ] Implement keyword extraction fallback (`KeywordParser`)
- [ ] Add confidence scoring (0.0-1.0) to parsed results
- [ ] Create `ReminderParser` that tries LLM → falls back to keywords → returns error
- [ ] Add test fixtures for all TC scenarios

**Tests:**
- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] TC-02: "dryer in 3 min" parses as simple_countdown
- [ ] TC-03: Tomorrow date resolution
- [ ] TC-04: LLM API failure falls back to keyword extraction
- [ ] TC-05: Manual field correction flow (UI concern, unit test parser output)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

### 2.3 Voice Personality System
**Priority:** High — core user experience differentiator

**Current state:** `VOICE_PERSONALITIES` dict in test_server.py
**Gaps:** Not structured as a service, no message variation, no custom prompts

**Tasks:**
- [ ] Create `VoicePersonalityService` class
- [ ] Add minimum 3 message variations per tier per personality
- [ ] Implement custom prompt support (max 200 chars)
- [ ] Add message generation with variation rotation
- [ ] Create personality storage/retrieval from user_preferences
- [ ] Map personalities to ElevenLabs voice IDs (configurable)

**Tests:**
- [ ] TC-01: Coach personality produces motivating messages
- [ ] TC-02: No-nonsense personality produces brief direct messages
- [ ] TC-03: Custom prompt modifies tone
- [ ] TC-04: Existing reminders retain original personality
- [ ] TC-05: Message variation (at least 3 distinct messages per tier)

---

## Phase 3: TTS Generation (Week 2)

### 3.1 ElevenLabs Adapter
**Priority:** High — enables voice output

**Tasks:**
- [ ] Implement `ElevenLabsAdapter` with API key from environment
- [ ] Implement `generate(text, voice_id, voice_settings) -> audio_path`
- [ ] Implement async generation with polling (up to 30 sec timeout)
- [ ] Implement audio file download and local caching
- [ ] Implement cache invalidation on reminder delete

**Tests:**
- [ ] TC-01: TTS clip generated at creation
- [ ] TC-02: Anchor fires from cache (no network call)
- [ ] TC-03: TTS fallback on API failure
- [ ] TC-04: TTS cache cleanup on delete
- [ ] TC-05: Mock TTS in tests

---

### 3.2 TTS Cache Management
**Priority:** Medium — performance concern

**Tasks:**
- [ ] Create `TTSCacheManager` for file operations
- [ ] Implement `/tts_cache/{reminder_id}/` directory structure
- [ ] Add cache size monitoring (warn if > 100MB)
- [ ] Implement LRU eviction for old reminders
- [ ] Add corruption detection (file exists but unreadable)

**Tests:**
- [ ] Cache directory created correctly
- [ ] Files deleted on reminder delete
- [ ] Fallback used if file corrupted

---

## Phase 4: Scheduling & Notifications (Week 2-3)

### 4.1 Background Scheduler (Notifee)
**Priority:** Critical — app must fire in background

**Tasks:**
- [ ] Implement `NotifeeSchedulerAdapter`
- [ ] Register each anchor as individual background task
- [ ] Implement recovery scan on app launch
- [ ] Implement overdue anchor dropping (>15 min)
- [ ] Implement late-fire warning logging (>60 sec)

**Tests:**
- [ ] TC-01: All anchors registered with correct timestamps
- [ ] TC-02: Background fire with app closed
- [ ] TC-03: Recovery scan on launch
- [ ] TC-04: Overdue anchor drop (15 min rule)
- [ ] TC-05: Pending anchors re-registered on crash recovery
- [ ] TC-06: Late fire warning (>60 sec)

---

### 4.2 Notification & Alarm Behavior
**Priority:** Critical — user must be alerted

**Tasks:**
- [ ] Implement urgency tier → notification tier mapping
- [ ] Implement DND detection and handling
- [ ] Implement DND override for final 5 minutes
- [ ] Implement quiet hours suppression
- [ ] Implement quiet hours end queue processing
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping

**Tests:**
- [ ] TC-01: DND — early anchor suppressed (silent notification)
- [ ] TC-02: DND — final 5-minute override (visual + vibration)
- [ ] TC-03: Quiet hours suppression
- [ ] TC-04: Overdue anchor drop (15 min rule)
- [ ] TC-05: Chain overlap serialization
- [ ] TC-06: T-0 alarm loops until action

---

### 4.3 Snooze & Dismissal Flow
**Priority:** High — core user interaction

**Tasks:**
- [ ] Implement tap snooze (1 minute)
- [ ] Implement tap-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze
- [ ] Implement snoozed anchor re-registration
- [ ] Implement swipe-dismiss feedback prompt
- [ ] Implement feedback options: timing_right, left_too_early, left_too_late, other
- [ ] Implement TTS snooze confirmation

**Tests:**
- [ ] TC-01: Tap snooze
- [ ] TC-02: Custom snooze
- [ ] TC-03: Chain re-computation after snooze
- [ ] TC-04: Dismissal feedback — timing correct
- [ ] TC-05: Dismissal feedback — timing off (left too late)
- [ ] TC-06: Snooze persistence after restart

---

## Phase 5: History & Feedback (Week 3)

### 5.1 History & Stats Service
**Priority:** Medium — user-facing feature

**Tasks:**
- [ ] Create `HistoryService` class
- [ ] Implement outcome recording (hit, miss, snoozed)
- [ ] Implement hit rate calculation (trailing 7 days)
- [ ] Implement streak counter for recurring reminders
- [ ] Implement common miss window identification
- [ ] Implement stats derivation from history table

**Tests:**
- [ ] TC-01: Hit rate calculation
- [ ] TC-04: Common miss window identification
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table alone

---

### 5.2 Feedback Loop & Destination Adjustments
**Priority:** Medium — intelligent learning

**Tasks:**
- [ ] Implement `DestinationAdjustmentService`
- [ ] Track late/early feedback per destination
- [ ] Apply +2 minute adjustment per late feedback
- [ ] Cap adjustments at +15 minutes
- [ ] Pre-populate drive_duration with adjustment on reminder creation

**Tests:**
- [ ] TC-02: Feedback loop — drive duration adjustment (+2 min per late)
- [ ] TC-03: Feedback loop cap (+15 min max)

---

## Phase 6: Integrations (Week 3-4)

### 6.1 Calendar Integration
**Priority:** Medium — calendar events → reminders

**Tasks:**
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement calendar sync scheduler (every 15 min)
- [ ] Implement suggestion card generation
- [ ] Implement recurring event handling
- [ ] Implement permission denial handling
- [ ] Implement sync failure graceful degradation

**Tests:**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

### 6.2 Location Awareness
**Priority:** Medium — adaptive escalation

**Tasks:**
- [ ] Implement `LocationAdapter` (CoreLocation on iOS)
- [ ] Implement origin resolution (user address or current location)
- [ ] Implement single-point location check at departure anchor
- [ ] Implement 500m geofence comparison
- [ ] Implement immediate escalation if user at origin
- [ ] Implement location permission request at reminder creation
- [ ] Implement no-location fallback (reminder without location awareness)

**Tests:**
- [ ] TC-01: User still at origin → immediate escalation
- [ ] TC-02: User already left → normal chain proceeds
- [ ] TC-03: Location permission request
- [ ] TC-04: Location permission denied
- [ ] TC-05: Single location check only (no continuous tracking)

---

### 6.3 Sound Library
**Priority:** Low-Medium — personalization

**Tasks:**
- [ ] Bundle built-in sounds (5 per category: commute, routine, errand)
- [ ] Implement custom sound import (MP3, WAV, M4A, max 30 sec)
- [ ] Implement sound transcoding to normalized format
- [ ] Implement sound picker UI
- [ ] Implement corrupted sound fallback
- [ ] Implement sound selection persistence

**Tests:**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Phase 7: Mobile App UI (Week 4-6)

### 7.1 Project Setup
**Priority:** Critical — need app to run

**Tasks:**
- [ ] Initialize React Native project (or Flutter)
- [ ] Set up project structure (screens/, components/, services/)
- [ ] Configure navigation (React Navigation or GoRouter)
- [ ] Set up state management (Zustand or similar)
- [ ] Set up local storage (SQLite with expo or react-native-sqlite-storage)

---

### 7.2 Core Screens

**Quick Add Screen:**
- [ ] Text/speech input field
- [ ] Confirmation card with parsed fields
- [ ] Manual field correction
- [ ] Voice personality selector
- [ ] Sound category selector
- [ ] Save button

**Home Screen:**
- [ ] Active reminders list
- [ ] Quick-add FAB button
- [ ] Calendar suggestions section

**History Screen:**
- [ ] Weekly hit rate display
- [ ] Streak counter
- [ ] Common miss window
- [ ] Reminder history list

**Settings Screen:**
- [ ] Voice personality default
- [ ] Quiet hours configuration
- [ ] Calendar integration
- [ ] Sound library access

---

## Phase 8: Testing & Polish (Week 6-7)

### 8.1 Test Suite
**Priority:** Critical — must verify all spec criteria

**Tasks:**
- [ ] Unit tests for all business logic
- [ ] Integration tests for adapters
- [ ] End-to-end tests for critical paths
- [ ] Test coverage reporting

---

### 8.2 Error Handling & Edge Cases
**Priority:** High

**Tasks:**
- [ ] All external dependency failures have graceful fallback
- [ ] Network errors handled without crash
- [ ] Invalid user input rejected with helpful message
- [ ] Background task failures logged and recovered

---

## Dependency Graph

```
[Adapter Interfaces] ──► [Mock Adapters] ──► [Unit Tests]
       │
       ▼
[Chain Engine] ◄──── [Database/Migrations]
       │
       ▼
[LLM Parser] ──► [Voice Personality] ──► [TTS Generation]
       │
       ▼
[Background Scheduler] ──► [Notifications] ─�► [Snooze/Dismissal]
       │                           ▲
       │                           │
       ▼                           ▼
[Location Awareness] ◄──── [History/Stats] ◄──── [Calendar Integration]
       │
       ▼
[Sound Library] ──► [Mobile App UI]
```

---

## Quick Wins (Days 1-3)

1. **Define adapter interfaces** — unlocks all testing
2. **Create mock adapters** — enables rapid development
3. **Enhance chain engine tests** — validates core algorithm
4. **Refactor VOICE_PERSONALITIES** into proper service

---

## Out of Scope (v1)

- Password/auth (local-only data in v1)
- Smart home integration (Hue lights, etc.)
- Voice reply ("snooze 5 min" spoken)
- Multi-device sync
- Bluetooth audio routing
- Per-reminder personality override
- Voice recording import
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
