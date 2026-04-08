# Urgent Voice Alarm - Implementation Plan

## Project Overview

This plan addresses gaps between `specs/urgent-voice-alarm-app-2026-04-08.spec.md` and the current codebase (`src/test_server.py`).

**Current State:** Basic chain computation, keyword parsing, and voice message templates exist. Most features are unimplemented.

---

## Phase 1: Foundation (Data Layer & Core Engine)

### 1.1 Complete Database Schema & Migrations
**Priority:** P0 (blocking all other work)

**Current:**
- Partial schema with 5 tables
- No migration system

**Required:**
- [ ] Implement versioned migration system (`migrations/` directory)
- [ ] Add missing tables: `calendar_sync`, `custom_sounds`
- [ ] Add missing fields to `reminders`: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `custom_sound_path`
- [ ] Add missing fields to `anchors`: `snoozed_to`, `tts_fallback`
- [ ] Add missing fields to `history`: `actual_arrival`, `missed_reason`
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] Create `lib/database.py` with:
  - `Database.get_instance()` / `Database.get_in_memory_instance()`
  - `Database.run_migrations()`
  - `Database.get_next_unfired_anchor(reminder_id)`

**Files:**
- `src/lib/database.py` (new)
- `src/migrations/` (new directory with `001_initial_schema.py`, etc.)

---

### 1.2 Enhance Chain Engine
**Priority:** P0 (blocking all other work)

**Current:**
- Basic `compute_escalation_chain()` with some tier logic
- Simple validation

**Required:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add comprehensive validation: `arrival_time > departure_time + minimum_drive_time`
- [ ] Add `snoozed_to` handling in chain re-computation
- [ ] Add chain determinism (seeded randomness for variations)
- [ ] Update `/chain/` endpoint to accept `reminder_id` for recovery

**Files:**
- `src/lib/chain_engine.py` (new - extract from test_server.py)
- `src/test_chain_engine.py` (new - TC-01 through TC-06 from spec)

---

### 1.3 LLM Adapter Interface
**Priority:** P1 (needed for reminder creation)

**Current:**
- Keyword extraction only in `parse_reminder_natural()`

**Required:**
- [ ] Define `ILanguageModelAdapter` abstract interface
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` for direct Anthropic API
- [ ] Implement `MockLanguageModelAdapter` for testing (returns fixture responses)
- [ ] Implement keyword extraction fallback when LLM fails
- [ ] Add reminder_type enum detection in parser

**Files:**
- `src/lib/adapters/llm_adapter.py` (new - interface + implementations)
- `src/lib/parser.py` (new - orchestrates LLM + fallback)

---

## Phase 2: Core Features

### 2.1 TTS Adapter & Voice Generation
**Priority:** P1 (needed before reminders can fire with audio)

**Current:**
- Static message templates in `VOICE_PERSONALITIES`
- Single template per tier

**Required:**
- [ ] Define `ITTSAdapter` abstract interface
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement `MockTTSAdapter` for testing
- [ ] Add message variations (minimum 3 per tier per personality)
- [ ] Implement `generate_message_variation()` with seeded randomness
- [ ] Add custom prompt support (append to system prompt)
- [ ] Create `lib/tts_cache.py` for file management

**Files:**
- `src/lib/adapters/tts_adapter.py` (new - interface + implementations)
- `src/lib/voice_personalities.py` (new - message templates with variations)

---

### 2.2 Reminder Service
**Priority:** P1 (user-facing feature)

**Current:**
- Basic `/reminders` POST endpoint
- No confirmation flow

**Required:**
- [ ] Create `ReminderService.create_reminder()` that:
  1. Parses input via parser
  2. Returns parsed result for user confirmation (not immediate creation)
  3. Creates reminder + anchors after confirmation
  4. Triggers TTS generation for all anchors
- [ ] Add `ReminderService.update_reminder()` with field correction support
- [ ] Add `ReminderService.delete_reminder()` with cascade and TTS cache cleanup
- [ ] Add destination adjustment lookup from `destination_adjustments` table

**Files:**
- `src/lib/reminder_service.py` (new)

---

### 2.3 Notification Service
**Priority:** P1 (needed for reminders to be heard)

**Current:**
- None

**Required:**
- [ ] Implement 4-tier notification sounds:
  - Calm/Casual → gentle chime
  - Pointed/Urgent → pointed beep
  - Pushing/Firm → urgent siren
  - Critical/Alarm → looping alarm
- [ ] Implement DND awareness:
  - Early anchors → silent notification
  - Final 5 minutes → visual override + vibration
- [ ] Implement quiet hours suppression (configurable start/end)
- [ ] Implement overdue anchor queue (fire after DND/quiet hours end)
- [ ] Implement 15-minute overdue drop rule
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] T-0 alarm must loop until user action

**Files:**
- `src/lib/notification_service.py` (new)

---

### 2.4 Background Scheduling
**Priority:** P1 (needed for reliable reminder firing)

**Current:**
- None

**Required:**
- [ ] Implement `NotifeeScheduler` (abstract scheduler interface)
- [ ] Implement `iOSBackgroundScheduler` using BGTaskScheduler
- [ ] Implement `AndroidBackgroundScheduler` using WorkManager
- [ ] Implement recovery scan on app launch:
  - Query all unfired anchors
  - Fire those within 15-minute grace window
  - Drop those >15 minutes overdue (log `missed_reason`)
- [ ] Re-register pending anchors on crash recovery
- [ ] Log warning for anchors firing >60 seconds late

**Files:**
- `src/lib/scheduler.py` (new - interface)
- `src/lib/platform/ios_scheduler.py` (new)
- `src/lib/platform/android_scheduler.py` (new)
- `src/lib/recovery.py` (new)

---

### 2.5 Snooze & Dismissal Flow
**Priority:** P2 (depends on notification service)

**Current:**
- None

**Required:**
- [ ] Implement tap snooze (1 minute default)
- [ ] Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze (shift remaining anchors)
- [ ] Implement re-registration of snoozed anchors with Notifee
- [ ] Implement swipe-to-dismiss feedback prompt:
  - "You missed [destination] — was the timing right? [Yes] [No]"
  - If "No": "What was wrong? [Left too early] [Left too late] [Other]"
- [ ] TTS confirmation: "Okay, snoozed [X] minutes"
- [ ] Handle snooze persistence across app restart

**Files:**
- `src/lib/snooze_service.py` (new)
- `src/lib/dismissal_service.py` (new)

---

### 2.6 History & Stats Service
**Priority:** P2 (depends on database)

**Current:**
- Basic `calculate_hit_rate()` function
- `/history` endpoint records outcomes

**Required:**
- [ ] Implement `HistoryService.calculate_hit_rate(days=7)`
- [ ] Implement `HistoryService.get_common_miss_window(destination)`
- [ ] Implement `HistoryService.get_streak(reminder_id)` for recurring reminders
- [ ] Implement feedback loop adjustment:
  - Query `destination_adjustments` for destination
  - `adjusted_drive_duration = base + (miss_count * 2)`, capped at +15 min
- [ ] Implement 90-day retention: archive older records
- [ ] Add `missed_reason` field population on anchor drop

**Files:**
- `src/lib/history_service.py` (new)

---

## Phase 3: Integrations

### 3.1 Calendar Integration
**Priority:** P2 (depends on database)

**Current:**
- None

**Required:**
- [ ] Define `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` using EventKit
- [ ] Implement `GoogleCalendarAdapter` using Google Calendar API
- [ ] Implement `MockCalendarAdapter` for testing
- [ ] Implement `CalendarSyncService`:
  - Sync on app launch
  - Sync every 15 minutes (foreground)
  - Sync via background refresh
  - Filter events with non-empty location
  - Generate suggestion cards for new events
- [ ] Implement recurring event handling (daily/weekday occurrences)
- [ ] Handle permission denial with explanation banner
- [ ] Handle sync failure gracefully (app continues working)

**Files:**
- `src/lib/adapters/calendar_adapter.py` (new - interface + implementations)
- `src/lib/calendar_sync.py` (new)

---

### 3.2 Location Awareness
**Priority:** P2 (depends on scheduler)

**Current:**
- None

**Required:**
- [ ] Implement `ILocationAdapter` interface
- [ ] Implement `iOSLocationAdapter` using CoreLocation
- [ ] Implement `AndroidLocationAdapter` using FusedLocationProvider
- [ ] Implement `MockLocationAdapter` for testing
- [ ] Implement `LocationService.check_at_origin()`:
  - Get current location at departure anchor
  - Compare against origin (500m geofence radius)
  - If within 500m: fire firm/critical tier immediately instead of calm departure
  - If outside: proceed with normal chain
- [ ] Request location permission at first location-aware reminder creation
- [ ] Handle denied permission gracefully (create reminder without location escalation)
- [ ] Ensure single location check only (no continuous tracking)

**Files:**
- `src/lib/adapters/location_adapter.py` (new - interface + implementations)
- `src/lib/location_service.py` (new)

---

### 3.3 Sound Library
**Priority:** P3

**Current:**
- None

**Required:**
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement `SoundLibrary` service:
  - Play built-in sound by category
  - List available sounds
  - Set per-reminder sound selection
- [ ] Implement custom audio import:
  - Support MP3, WAV, M4A (max 30 seconds)
  - Store in app sandbox
  - Reference in `custom_sounds` table
- [ ] Implement corrupted file fallback (use category default, log error)
- [ ] Implement sound picker UI component

**Files:**
- `src/lib/sound_library.py` (new)
- `assets/sounds/` (new - bundled sounds)

---

## Phase 4: Testing & Polish

### 4.1 Test Suite
**Priority:** P1 (ongoing, not final phase)

**Required:**
- [ ] Unit tests for chain engine (TC-01 through TC-06 from spec)
- [ ] Unit tests for parser (TC-01 through TC-07 from spec)
- [ ] Unit tests for TTS generation (TC-01 through TC-05 from spec)
- [ ] Unit tests for notification tiers
- [ ] Unit tests for background scheduler
- [ ] Unit tests for snooze chain re-computation
- [ ] Unit tests for hit rate calculation
- [ ] Integration tests using mock adapters
- [ ] End-to-end tests with in-memory SQLite

**Files:**
- `tests/test_chain_engine.py` (new)
- `tests/test_parser.py` (new)
- `tests/test_tts.py` (new)
- `tests/test_notifications.py` (new)
- `tests/test_scheduler.py` (new)
- `tests/test_snooze.py` (new)
- `tests/test_stats.py` (new)

---

### 4.2 API Cleanup
**Priority:** P2

**Required:**
- [ ] Refactor `test_server.py` into proper REST API with:
  - `/api/v1/reminders/` - CRUD operations
  - `/api/v1/reminders/{id}/anchors/` - list anchors
  - `/api/v1/parse/` - natural language parsing
  - `/api/v1/voice/message/` - message generation
  - `/api/v1/history/` - history operations
  - `/api/v1/stats/` - statistics endpoints
  - `/api/v1/calendar/events/` - calendar suggestions
  - `/api/v1/sounds/` - sound library
- [ ] Add request validation
- [ ] Add error responses matching spec

---

### 4.3 Configuration & Environment
**Priority:** P2

**Required:**
- [ ] `config.py` with environment variables:
  - `MINIMAX_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `ELEVENLABS_API_KEY`
  - `GOOGLE_CALENDAR_CREDENTIALS`
  - `DATABASE_PATH`
  - `TTS_CACHE_DIR`
- [ ] `src/lib/config.py` to manage settings
- [ ] `.env.example` file

---

## Implementation Order

```
Phase 1: Foundation
├── 1.1 Database Schema & Migrations (P0)
└── 1.2 Chain Engine Enhancement (P0)
    └── 1.3 LLM Adapter Interface (P1)

Phase 2: Core Features
├── 2.1 TTS Adapter & Voice Generation (P1)
├── 2.2 Reminder Service (P1)
├── 2.3 Notification Service (P1)
├── 2.4 Background Scheduling (P1)
├── 2.5 Snooze & Dismissal Flow (P2)
└── 2.6 History & Stats Service (P2)

Phase 3: Integrations
├── 3.1 Calendar Integration (P2)
├── 3.2 Location Awareness (P2)
└── 3.3 Sound Library (P3)

Phase 4: Testing & Polish
├── 4.1 Test Suite (P1, ongoing)
├── 4.2 API Cleanup (P2)
└── 4.3 Configuration (P2)
```

---

## Dependency Graph

```
1.1 Database ──┬──> 1.2 Chain Engine ──> 2.6 History
               │
               ├──> 2.2 Reminder Service
               │
               └──> 3.1 Calendar Integration

1.3 LLM Adapter ──> 2.2 Reminder Service ──> 2.1 TTS Adapter

2.4 Background Scheduler ──> 2.5 Snooze & Dismissal
     │
     └──> 3.2 Location Awareness

2.3 Notification Service ──> 2.5 Snooze & Dismissal
     │
     └──> 3.3 Sound Library
```

---

## Not in Scope (v1)

- Authentication / account management
- Smart home integration
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Password reset
- Cloud sound library
- Automatic calendar adjustment from feedback

---

## Definition of Done Checklist

- [ ] All acceptance criteria from Sections 2-13 have passing tests
- [ ] Each test scenario (Given/When/Then) maps to at least one test
- [ ] TTS clips cached at reminder creation (zero runtime latency)
- [ ] Background scheduling works with app closed
- [ ] DND and quiet hours respected
- [ ] Chain overlap serialized
- [ ] Snooze re-computes and re-registers anchors
- [ ] Feedback loop adjusts destination drive estimates
- [ ] Calendar events with locations surface suggestions
- [ ] Location check at departure (single call, 500m geofence)
