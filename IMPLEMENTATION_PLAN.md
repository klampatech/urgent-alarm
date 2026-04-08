# Implementation Plan — Urgent Voice Alarm App

## Overview

**Spec Source:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md`
**Current State:** Python HTTP test server (`src/test_server.py`) provides a validation harness with partial implementations of core logic. The actual mobile app (React Native + TypeScript) is NOT yet started.
**Target:** Complete React Native mobile app per spec sections 1-14.

---

## Phase 1: Foundation (Critical Path)

### Task 1.1 — Initialize React Native Project
- [ ] Initialize React Native 0.76+ project with TypeScript
- [ ] Install core dependencies:
  - React Navigation (stack + bottom tabs)
  - Zustand (state management)
  - SQLite: `expo-sqlite` or `react-native-quick-sqlite`
  - Notifee (background scheduling)
  - Audio player (expo-av)
- [ ] Set up project structure:
  ```
  src/
  ├── domain/           # Business logic (chain engine, parser)
  ├── data/             # Repositories, SQLite adapters
  ├── services/         # TTS, LLM, Calendar, Location
  ├── ui/               # Screens, components
  └── infrastructure/   # Background scheduler, notifications
  ```
- [ ] Configure ESLint, Prettier, Jest, Detox

### Task 1.2 — Database Layer (Section 13)
- [ ] Implement full SQLite schema per spec:
  ```sql
  reminders (
    id TEXT PRIMARY KEY,           -- UUID v4
    destination TEXT NOT NULL,
    arrival_time TEXT NOT NULL,    -- ISO 8601
    drive_duration INTEGER NOT NULL,
    reminder_type TEXT NOT NULL,   -- countdown_event | simple_countdown | morning_routine | standing_recurring
    voice_personality TEXT NOT NULL,
    sound_category TEXT,
    selected_sound TEXT,
    custom_sound_path TEXT,
    origin_lat REAL,
    origin_lng REAL,
    origin_address TEXT,
    status TEXT DEFAULT 'pending', -- pending | active | completed | cancelled
    calendar_event_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
  
  anchors (
    id TEXT PRIMARY KEY,
    reminder_id TEXT REFERENCES reminders(id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL,
    urgency_tier TEXT NOT NULL,     -- calm | casual | pointed | urgent | pushing | firm | critical | alarm
    tts_clip_path TEXT,
    tts_fallback BOOLEAN DEFAULT FALSE,
    fired BOOLEAN DEFAULT FALSE,
    fire_count INTEGER DEFAULT 0,
    snoozed_to TEXT,               -- new timestamp if snoozed
    UNIQUE(reminder_id, timestamp)
  )
  
  history (
    id TEXT PRIMARY KEY,
    reminder_id TEXT REFERENCES reminders(id),
    destination TEXT NOT NULL,
    scheduled_arrival TEXT NOT NULL,
    actual_arrival TEXT,
    outcome TEXT NOT NULL,         -- hit | miss | snoozed
    feedback_type TEXT,            -- timing_right | left_too_early | left_too_late | other
    missed_reason TEXT,             -- background_task_killed | dnd_suppressed | user_dismissed | null
    created_at TEXT NOT NULL
  )
  
  destination_adjustments (
    destination TEXT PRIMARY KEY,
    adjustment_minutes INTEGER DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
  )
  
  user_preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)
  calendar_sync (calendar_type TEXT PRIMARY KEY, last_sync_at TEXT, sync_token TEXT, is_connected BOOLEAN)
  custom_sounds (id TEXT PRIMARY KEY, filename TEXT, original_name TEXT, category TEXT, file_path TEXT, duration_seconds REAL, created_at TEXT)
  ```
- [ ] Enable WAL mode, foreign keys (`PRAGMA foreign_keys = ON`), UUID v4 generation
- [ ] Implement versioned migrations system (schema_v1, v2, v3...)
- [ ] Add in-memory test mode (`?mode=memory` for SQLite)
- [ ] **Acceptance:** Cascade delete works, FK enforcement works, UUIDs are valid v4

### Task 1.3 — Chain Engine (Section 2) — Port from test_server.py
- [ ] Port `compute_escalation_chain()` to TypeScript with exact logic:
  - ≥25 min buffer: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
  - 20-24 min: 7 anchors (skip calm)
  - 15-19 min: 6 anchors (skip calm/casual)
  - 10-14 min: 5 anchors (skip calm/casual/pointed)
  - 5-9 min: 3 anchors (firm, critical, alarm)
  - 3-4 min: 2 anchors (firm, alarm)
  - 1-2 min: 1 anchor (alarm)
- [ ] Port `validate_chain()` to TypeScript
- [ ] Implement `get_next_unfired_anchor(reminder_id)` for crash recovery
- [ ] Add unit tests for determinism (TC-06)
- [ ] **Acceptance (per spec TC-01 to TC-06):** All chain scenarios pass

---

## Phase 2: Reminder Creation Flow

### Task 2.1 — LLM Parser (Section 3)
- [ ] Create `ILanguageModelAdapter` interface (mock-able for tests)
- [ ] Implement MiniMax API adapter (configurable via env var `LLM_PROVIDER=minimax`)
- [ ] Implement Anthropic API adapter (configurable via env var `LLM_PROVIDER=anthropic`)
- [ ] Implement keyword extraction fallback (regex patterns):
  ```
  Patterns:
  - "X minute drive" / "X min drive" / "X-minute drive"
  - "in X minutes" (simple countdown)
  - "at HH:MMam/pm"
  - "tomorrow HH:MM"
  - "arrive at X" / "check-in at X"
  ```
- [ ] Handle all input formats per spec TC-01 to TC-07
- [ ] **Acceptance:** Full natural language parse, simple countdown parse, tomorrow date resolution, LLM failure fallback, manual field correction, unintelligible input rejection

### Task 2.2 — Quick Add UI
- [ ] Create reminder creation screen with text/speech input toggle
- [ ] Display parsed interpretation card before confirmation:
  ```
  ┌─────────────────────────────────────┐
  │ 📍 Parker Dr check-in              │
  │ ⏰ 9:00 AM (in 2 hours)            │
  │ 🚗 30 min drive | Depart 8:30 AM    │
  │                                     │
  │ [Edit destination] [Edit time]      │
  │ [Edit drive time]                   │
  │                                     │
  │ [Cancel]              [Create ✓]     │
  └─────────────────────────────────────┘
  ```
- [ ] Handle manual field correction (destination, arrival_time, drive_duration)
- [ ] Support 4 reminder types: countdown_event, simple_countdown, morning_routine, standing_recurring

### Task 2.3 — Voice Personality System (Section 10)
- [ ] Define personality data structure with templates (3 variations per tier per personality):
  ```typescript
  interface VoicePersonality {
    id: 'coach' | 'assistant' | 'best_friend' | 'no_nonsense' | 'calm' | 'custom';
    voice_id: string;  // ElevenLabs voice ID
    system_prompt: string;
    custom_prompt?: string;  // max 200 chars for custom mode
    templates: {
      [urgency_tier: string]: string[];  // 3 variations each
    };
  }
  ```
- [ ] Implement all 5 built-in personalities with message variations
- [ ] Implement custom personality mode
- [ ] Store selected personality in user preferences
- [ ] **Acceptance:** Coach at T-5 → "Let's GO! 5 min to Parker Dr!", No-nonsense → "5 min. Parker Dr. Leave."

### Task 2.4 — TTS Generation (Section 4)
- [ ] Create `ITTSAdapter` interface (mock-able)
- [ ] Implement ElevenLabs API adapter (configurable via env var)
- [ ] Implement TTS cache storage: `FileSystem.documentDirectory + '/tts_cache/{reminder_id}/'`
- [ ] Add fallback: system notification sound + text when TTS fails (`tts_fallback = true`)
- [ ] Invalidate cache on reminder deletion
- [ ] **Acceptance:** Clips generated at creation, played from cache at runtime, fallback works

---

## Phase 3: Voice & Notifications

### Task 3.1 — Notification Layer (Section 5)
- [ ] Implement notification tier escalation:
  | Tier | Sound |
  |------|-------|
  | calm/casual | gentle chime |
  | pointed/urgent | pointed beep |
  | pushing/firm | urgent siren |
  | critical/alarm | looping alarm |
- [ ] Handle system DND:
  - Early anchors: silent notification only
  - Final 5 minutes: visual override + vibration
- [ ] Implement quiet hours suppression (configurable, default 10pm–7am)
- [ ] Queue anchors skipped due to DND/quiet hours (fire after restriction ends)
- [ ] Drop anchors >15 minutes overdue
- [ ] Serialize chain execution (queue overlapping anchors)
- [ ] T-0 alarm loops until user dismisses or snoozes

### Task 3.2 — Background Scheduling (Section 6)
- [ ] Integrate Notifee for iOS (BGTaskScheduler) and Android (WorkManager)
- [ ] Register each anchor as individual background task with precise trigger timestamp
- [ ] Implement recovery scan on app launch:
  ```
  On app launch:
  1. Query all unfired anchors where scheduled time < now
  2. If anchor is within 15-minute grace window → fire it
  3. If anchor is >15 minutes overdue → mark missed and log missed_reason
  4. Re-register all remaining pending (unfired) anchors with Notifee
  ```
- [ ] Handle missed anchors (log missed_reason = "background_task_killed")
- [ ] Log warning for late fires (>60s after scheduled)

### Task 3.3 — Audio Player
- [ ] Play TTS clip from local cache via expo-av
- [ ] Layer notification sound under TTS (sound plays first, then TTS)
- [ ] Handle audio focus / interruption (pause TTS if phone call)

---

## Phase 4: User Interaction

### Task 4.1 — Snooze Flow (Section 9)
- [ ] Tap snooze: snooze 1 minute, TTS "Okay, snoozed 1 minute"
- [ ] Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation: shift remaining anchors by snooze duration
  ```
  Example: snooze at 8:45 with 3-min snooze
  Original: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
  Recomputed: 8:48, 8:53, 8:59, 9:00 (remaining anchors shifted +3)
  ```
- [ ] Re-register snoozed anchors with Notifee
- [ ] Persist snooze state for crash recovery (`snoozed_to` field in anchors table)
- [ ] **Acceptance:** After custom snooze and app restart, remaining anchors fire at adjusted times

### Task 4.2 — Dismissal & Feedback (Section 9)
- [ ] Swipe-to-dismiss: show feedback prompt "You missed Parker Dr — was the timing right?"
- [ ] Yes (timing right): store feedback, no adjustment
- [ ] No → "Left too early": store feedback
- [ ] No → "Left too late": +2 min adjustment per occurrence, capped at +15
- [ ] No → "Other": store feedback type
- [ ] **Acceptance:** 3 "Left too late" for "Parker Dr" → next reminder adds 6 min to drive_duration

### Task 4.3 — History & Stats (Section 11)
- [ ] Calculate hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days
- [ ] Feedback loop: adjust `drive_duration` per destination
  ```
  adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)
  Cap at +15 minutes maximum
  ```
- [ ] Display "common miss window" (most frequently missed urgency tier per destination)
- [ ] Streak counter for recurring reminders (increment on hit, reset on miss)
- [ ] Implement 90-day history retention (archive older data)
- [ ] **Acceptance:** Stats computable from history table alone

---

## Phase 5: Integrations

### Task 5.1 — Calendar Integration (Section 7)
- [ ] Create `ICalendarAdapter` interface (mock-able)
- [ ] Implement Apple Calendar adapter (EventKit via react-native-calendars or native module)
- [ ] Implement Google Calendar adapter (Google Calendar API via expo-google-sign-in)
- [ ] Sync on launch, every 15 minutes, via background refresh
- [ ] Surface suggestion cards for events with locations:
  ```
  ┌─────────────────────────────────────┐
  │ 📅 Parker Dr check-in              │
  │    9:00 AM — Calendar               │
  │                                     │
  │ [Add Reminder]  [Dismiss]           │
  └─────────────────────────────────────┘
  ```
- [ ] Handle recurring events (generate reminder for each occurrence)
- [ ] Handle permission denial gracefully (show explanation banner with settings link)
- [ ] **Acceptance:** Events with locations appear as suggestion cards within 2 min of sync

### Task 5.2 — Location Awareness (Section 8)
- [ ] Single location check at departure anchor only (T-drive_duration)
- [ ] Resolve origin from: user-specified address or current device location at creation
- [ ] Compare against 500m geofence using haversine distance
- [ ] If still at origin: fire firm/critical tier immediately instead of departure nudge
- [ ] If already left: normal chain proceeds from departure anchor
- [ ] Request permission at first location-aware reminder (not at app launch)
- [ ] Handle denied permission gracefully (show note "Location-based escalation disabled")
- [ ] **Acceptance:** Only one location API call per reminder (at departure fire)

### Task 5.3 — Sound Library (Section 12)
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 sec) via expo-document-picker
- [ ] Transcode and normalize imported sounds to AAC
- [ ] Per-reminder sound selection (stored in `selected_sound` field)
- [ ] Handle corrupted sound fallback (use category default, log error)
- [ ] **Acceptance:** Built-in sounds play without network, custom import works, corrupted fallback works

---

## Phase 6: Testing

### Task 6.1 — Unit Tests
- [ ] Chain engine determinism tests (TC-01 to TC-06 per spec)
- [ ] Parser fixture tests (mock ILanguageModelAdapter)
- [ ] TTS adapter mock implementation
- [ ] LLM adapter mock implementation
- [ ] Database migrations and cascade tests
- [ ] Voice personality message generation tests (3 variations each)
- [ ] Hit rate calculation tests

### Task 6.2 — Integration Tests
- [ ] Full reminder creation flow (parse → chain → TTS → persist)
- [ ] Anchor firing (schedule → fire → mark fired)
- [ ] Snooze recovery (snooze → recompute → re-register)
- [ ] Feedback loop (dismiss → feedback → adjustment)
- [ ] Calendar sync → suggestion → reminder creation

### Task 6.3 — E2E Tests (Detox)
- [ ] Quick Add flow (text input → confirmation → chain created)
- [ ] Reminder confirmation and display
- [ ] Anchor firing sequence
- [ ] Snooze interaction (tap and custom)
- [ ] Dismissal feedback
- [ ] Settings navigation
- [ ] Sound library browsing

---

## Priority Order (Dependencies)

```
Week 1: Foundation
┌─────────────────────────────────────────────────────────────┐
│ 1.1 React Native Project Init                               │
│ 1.2 Database Layer (full schema per spec)                   │
│ 1.3 Chain Engine (port from test_server.py + unit tests)    │
└─────────────────────────────────────────────────────────────┘

Week 2: Core Reminder Creation
┌─────────────────────────────────────────────────────────────┐
│ 2.1 LLM Parser (interface + MiniMax + keyword fallback)     │
│ 2.2 Quick Add UI (confirmation card)                        │
│ 2.3 Voice Personality (5 built-in + custom, 3 variations)   │
│ 2.4 TTS Generation (ElevenLabs + cache)                    │
└─────────────────────────────────────────────────────────────┘

Week 3: Notification & Audio
┌─────────────────────────────────────────────────────────────┐
│ 3.1 Notifications (tier escalation, DND, quiet hours)      │
│ 3.2 Background Scheduling (Notifee, recovery scan)          │
│ 3.3 Audio Player                                            │
└─────────────────────────────────────────────────────────────┘

Week 4: User Interaction
┌─────────────────────────────────────────────────────────────┐
│ 4.1 Snooze Flow (tap, custom, chain recompute)             │
│ 4.2 Dismissal & Feedback (prompt, adjustment)              │
│ 4.3 History & Stats (hit rate, streak, 90-day retention)   │
└─────────────────────────────────────────────────────────────┘

Week 5: Integrations
┌─────────────────────────────────────────────────────────────┐
│ 5.1 Calendar Integration (EventKit, Google Calendar)        │
│ 5.2 Location Awareness (500m geofence, single check)       │
│ 5.3 Sound Library (built-in + import + fallback)            │
└─────────────────────────────────────────────────────────────┘

Week 6: Testing
┌─────────────────────────────────────────────────────────────┐
│ 6.1 Unit Tests (chain, parser, TTS mock, LLM mock)         │
│ 6.2 Integration Tests (full flows)                          │
│ 6.3 E2E Tests (Detox)                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Gap Analysis: Current State vs. Spec

| Component | Current (Python test_server.py) | Required (TypeScript/Mobile) | Status |
|-----------|--------------------------------|------------------------------|--------|
| **Platform** | Python HTTP server (harness) | React Native mobile app | ❌ Missing |
| **Chain Engine** | ✓ Full Python impl | TypeScript + unit tests | ⚠️ Port needed |
| **Chain Compression** | ✓ Partial (all cases) | Full spec with exact anchor counts | ✓ Covered |
| **Parser** | Keyword regex only | LLM adapter + keyword fallback | ⚠️ Upgrade needed |
| **LLM Adapter** | None | ILanguageModelAdapter interface | ❌ Missing |
| **Voice Personalities** | ✓ 5 templates, 1 variation each | 5 built-in + custom, **3 variations each** | ⚠️ Add variations |
| **TTS** | Message templates only | ElevenLabs adapter + cache | ❌ Missing |
| **Database Schema** | Partial (missing fields) | Full spec schema (8 tables) | ⚠️ Upgrade needed |
| **Notifications** | None | Full mobile notification system | ❌ Missing |
| **Background** | None | Notifee + crash recovery | ❌ Missing |
| **Calendar** | None | EventKit + Google API | ❌ Missing |
| **Location** | None | CoreLocation single check | ❌ Missing |
| **Sound Library** | None | Built-in + import + fallback | ❌ Missing |
| **Snooze** | None | Tap, custom, chain recompute | ❌ Missing |
| **Dismissal/Feedback** | Basic HTTP endpoint | Full feedback flow + adjustment | ⚠️ Basic only |
| **History/Stats** | ✓ Basic hit rate | Full stats, streak, 90-day retention | ⚠️ Incomplete |
| **Tests** | Scenario harness | Unit + Integration + E2E | ❌ Missing |
| **Migration System** | None | Versioned migrations | ❌ Missing |

---

## Key Spec Details to Implement

### Reminder Types (Section 3)
- `countdown_event`: drive duration + arrival time → full departure chain
- `simple_countdown`: no drive, just time remaining → escalating single countdown
- `morning_routine`: anchor points per routine step (reusable template)
- `standing_recurring`: repeat daily/weekdays/custom

### Urgency Tiers & Timestamps (Section 2)

For 30-min buffer (full chain):
| Tier | Minutes Before | Timestamp (arrival 9:00) |
|------|---------------|--------------------------|
| calm | 30 | 8:30 AM |
| casual | 25 | 8:35 AM |
| pointed | 20 | 8:40 AM |
| urgent | 15 | 8:45 AM |
| pushing | 10 | 8:50 AM |
| firm | 5 | 8:55 AM |
| critical | 1 | 8:59 AM |
| alarm | 0 | 9:00 AM |

### Chain Compression Rules (Section 2.3)
```
buffer >= 25 min: 8 anchors (full chain)
buffer 20-24 min: 7 anchors (skip calm)
buffer 15-19 min: 6 anchors (skip calm/casual)
buffer 10-14 min: 5 anchors (skip calm/casual/pointed)
buffer 5-9 min: 3 anchors (firm, critical, alarm)
buffer 3-4 min: 2 anchors (firm, alarm)
buffer 1-2 min: 1 anchor (alarm)
```

### Feedback Loop Adjustment (Section 11.3)
```typescript
adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)
// Capped at +15 minutes maximum
```

### Database Migration Versioning (Section 13.3)
```sql
-- Migrations must be sequential and versioned
-- Example:
-- schema_v1: initial tables (reminders, anchors, history)
-- schema_v2: add destination_adjustments, user_preferences
-- schema_v3: add calendar_sync, custom_sounds
-- schema_v4: add missing columns (tts_fallback, snoozed_to, origin_lat/lng, etc.)
```

---

## Reference Implementation

The Python `src/test_server.py` provides working implementations of:
- `compute_escalation_chain(arrival_time, drive_duration)` — **Port to TypeScript**
- `parse_reminder_natural(input_text)` — **Port + enhance with LLM adapter**
- `generate_voice_message(personality, tier, dest, dur, remaining)` — **Port + add 3 variations per tier**
- `calculate_hit_rate(days)` — **Port to TypeScript**
- Database schema — **Upgrade to full spec schema with migrations**

---

## Out of Scope (per spec Section 1.3)
- Password reset / account management (local-only data in v1)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min")
- Multi-device sync (future consideration)
- Bluetooth audio routing (speaker-only in v1)
- Sound recording / trimming
- Cloud sound library / purchases
- Calendar write operations
- Two-way calendar sync
- Continuous location tracking
- Origin address autocomplete
- ETA-based dynamic drive duration