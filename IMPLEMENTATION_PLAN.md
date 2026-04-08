# Implementation Plan — Urgent Voice Alarm App

## Overview

**Spec Source:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md`
**Current State:** Python test server with partial chain engine, keyword parser, and voice message templates — NOT a React Native mobile app. Core logic is implemented but needs to be ported to TypeScript/mobile.
**Target:** Complete mobile app implementation per spec

---

## Phase 1: Foundation (Critical Path)

### Task 1.1 — Initialize React Native Project
- [ ] Initialize React Native 0.76+ project with TypeScript
- [ ] Install core dependencies: React Navigation, Zustand, SQLite (expo-sqlite)
- [ ] Set up project structure (domain-driven design)
- [ ] Configure ESLint, Prettier, Jest

### Task 1.2 — Database Layer (Section 13)
- [ ] Implement full SQLite schema per spec:
  - reminders (with all fields: destination_adjustments FK, origin lat/lng, calendar_event_id)
  - anchors (with tts_fallback, snoozed_to, fire_count)
  - history (with missed_reason field)
  - destination_adjustments
  - user_preferences
  - calendar_sync
  - custom_sounds
- [ ] Enable WAL mode, foreign keys, UUID v4 generation
- [ ] Implement versioned migrations system
- [ ] Add in-memory test mode support
- [ ] **Acceptance:** Cascade delete works, FK enforcement works, UUIDs are valid v4

### Task 1.3 — Chain Engine (Section 2) — Port from test_server.py
- [ ] Port `compute_escalation_chain()` to TypeScript
- [ ] Port `validate_chain()` to TypeScript
- [ ] Implement `get_next_unfired_anchor(reminder_id)` for crash recovery
- [ ] Add unit tests for determinism
- [ ] **Acceptance (per spec TC-01 to TC-06):**
  - Full chain: 8 anchors for ≥25 min buffer
  - Compressed: 5 anchors for 10-24 min buffer
  - Minimum: 3 anchors for ≤5 min buffer
  - Invalid chains rejected with validation error
  - Next unfired anchor correctly identified

---

## Phase 2: Reminder Creation Flow

### Task 2.1 — LLM Parser (Section 3)
- [ ] Create `ILanguageModelAdapter` interface (mock-able)
- [ ] Implement MiniMax API adapter (configurable via env var)
- [ ] Implement keyword extraction fallback (regex patterns)
- [ ] Handle all input formats per spec TC-01 to TC-06
- [ ] **Acceptance:** Full natural language parse, simple countdown parse, tomorrow date resolution, LLM failure fallback, manual field correction, unintelligible input rejection

### Task 2.2 — Quick Add UI
- [ ] Create reminder creation screen with text/speech input toggle
- [ ] Display parsed interpretation card before confirmation
- [ ] Handle manual field correction (destination, arrival_time, drive_duration)
- [ ] Support 4 reminder types: countdown_event, simple_countdown, morning_routine, standing_recurring

### Task 2.3 — Voice Personality System (Section 10)
- [ ] Define personality data structure with templates
- [ ] Implement all 5 built-in personalities: Coach, Assistant, Best Friend, No-nonsense, Calm
- [ ] Implement custom personality mode (max 200 chars)
- [ ] Generate **minimum 3 message variations per tier per personality**
- [ ] Store selected personality in user preferences
- [ ] **Acceptance:** Existing reminders retain their personality at creation time

### Task 2.4 — TTS Generation (Section 4)
- [ ] Create `ITTSAdapter` interface (mock-able)
- [ ] Implement ElevenLabs API adapter
- [ ] Implement TTS cache storage (`/tts_cache/{reminder_id}/`)
- [ ] Add fallback: system notification sound + text when TTS fails
- [ ] Invalidate cache on reminder deletion
- [ ] **Acceptance:** Clips generated at creation, played from cache at runtime, fallback works

---

## Phase 3: Voice & Notifications

### Task 3.1 — Notification Layer (Section 5)
- [ ] Implement notification tier escalation:
  - gentle chime (calm/casual)
  - pointed beep (pointed/urgent)
  - urgent siren (pushing/firm)
  - looping alarm (critical/alarm)
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
- [ ] Register each anchor as individual background task
- [ ] Implement recovery scan on app launch
- [ ] Re-register pending anchors after crash/termination
- [ ] Handle missed anchors (15-min grace window, log missed_reason)
- [ ] Log warning for late fires (>60s after scheduled)

### Task 3.3 — Audio Player
- [ ] Play TTS clip from local cache
- [ ] Layer notification sound under TTS
- [ ] Handle audio focus / interruption

---

## Phase 4: User Interaction

### Task 4.1 — Snooze Flow (Section 9)
- [ ] Tap: snooze 1 minute, TTS "Okay, snoozed 1 minute"
- [ ] Tap-and-hold: custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation: shift remaining anchors by snooze duration
- [ ] Re-register snoozed anchors with Notifee
- [ ] Persist snooze state for crash recovery
- [ ] **Acceptance:** After custom snooze and app restart, remaining anchors fire at adjusted times

### Task 4.2 — Dismissal & Feedback (Section 9)
- [ ] Swipe-to-dismiss: show feedback prompt "You missed [destination] — was the timing right?"
- [ ] Yes: store feedback, no adjustment needed
- [ ] No → "Left too early": store feedback, decrease estimate (optional)
- [ ] No → "Left too late": +2 min adjustment per occurrence, capped at +15
- [ ] No → "Other": prompt for details (optional)

### Task 4.3 — History & Stats (Section 11)
- [ ] Calculate hit rate: `hits / (total - pending) * 100` for trailing 7 days
- [ ] Feedback loop: adjust `drive_duration` per destination
- [ ] Display "common miss window" (most frequently missed urgency tier)
- [ ] Streak counter for recurring reminders (increment on hit, reset on miss)
- [ ] Implement 90-day history retention (archive older data)

---

## Phase 5: Integrations

### Task 5.1 — Calendar Integration (Section 7)
- [ ] Create `ICalendarAdapter` interface
- [ ] Implement Apple Calendar adapter (EventKit)
- [ ] Implement Google Calendar adapter (Google Calendar API)
- [ ] Sync on launch, every 15 minutes, via background refresh
- [ ] Surface suggestion cards for events with locations
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully
- [ ] **Acceptance:** Events with locations appear as suggestion cards within 2 min

### Task 5.2 — Location Awareness (Section 8)
- [ ] Single location check at departure anchor only
- [ ] Resolve origin from user-specified address or current location at creation
- [ ] Compare against 500m geofence
- [ ] If still at origin: fire firm/critical tier immediately instead of departure nudge
- [ ] Request permission at first location-aware reminder (not at app launch)
- [ ] Handle denied permission gracefully
- [ ] **Acceptance:** Only one location API call per reminder (at departure fire)

### Task 5.3 — Sound Library (Section 12)
- [ ] Bundle 5 built-in sounds per category (commute, routine, errand)
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 sec)
- [ ] Transcode and normalize imported sounds
- [ ] Per-reminder sound selection
- [ ] Handle corrupted sound fallback (use category default, log error)
- [ ] **Acceptance:** Built-in sounds play without network, custom import works, corrupted fallback works

---

## Phase 6: Testing

### Task 6.1 — Unit Tests
- [ ] Chain engine determinism tests (TC-06)
- [ ] Parser fixture tests (mock adapter)
- [ ] TTS adapter mock implementation
- [ ] LLM adapter mock implementation
- [ ] Database migrations and cascade tests
- [ ] Voice personality message generation tests
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
┌─────────────────────────────────────────────────────────────┐
│ 1.1 Project Init                                            │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1.2 Database Layer (full schema per spec)                   │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1.3 Chain Engine (port from test_server.py + unit tests)    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2.1 LLM Parser (interface + MiniMax + keyword fallback)     │
│ 2.2 Quick Add UI (confirmation card)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────────┐   ┌─────────────────────┐
│ 2.3 Voice Personality│   │ 2.4 TTS Generation   │
│ (5 built-in + custom│   │ (ElevenLabs + cache) │
│  3 variations each) │   └─────────────────────┘
└─────────────────────┘            │
          │                        │
          └────────────┬───────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3.1 Notifications (tier escalation, DND, quiet hours)      │
│ 3.2 Background Scheduling (Notifee, recovery scan)          │
│ 3.3 Audio Player                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4.1 Snooze Flow (tap, custom, chain recompute)             │
│ 4.2 Dismissal & Feedback (prompt, adjustment)               │
│ 4.3 History & Stats (hit rate, streak, 90-day retention)   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5.1 Calendar Integration (EventKit, Google Calendar)         │
│ 5.2 Location Awareness (500m geofence, single check)        │
│ 5.3 Sound Library (built-in + import + fallback)            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 6.1 Unit Tests (chain, parser, TTS mock, LLM mock)         │
│ 6.2 Integration Tests (full flows)                         │
│ 6.3 E2E Tests (Detox)                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Gap Analysis: Current State vs. Spec

| Component | Current (test_server.py) | Required | Status |
|------------|--------------------------|----------|--------|
| Platform | Python HTTP server | React Native mobile app | ❌ Missing |
| Chain Engine | ✓ Partial (Python) | TypeScript, full spec | ⚠️ Port needed |
| Parser | Keyword only | LLM adapter + keyword fallback | ⚠️ Upgrade needed |
| LLM Adapter | None | ILanguageModelAdapter interface | ❌ Missing |
| Voice Personalities | ✓ 5 templates, 1 variation | 5 built-in + custom, 3 variations each | ⚠️ Add variations |
| TTS | Message templates only | ElevenLabs adapter + cache | ❌ Missing |
| Notifications | HTTP endpoints | Full mobile notification system | ❌ Missing |
| Background | None | Notifee + crash recovery | ❌ Missing |
| Calendar | None | EventKit + Google API | ❌ Missing |
| Location | None | CoreLocation single check | ❌ Missing |
| Sound Library | None | Built-in + import | ❌ Missing |
| Snooze | None | Tap, custom, chain recompute | ❌ Missing |
| Dismissal | HTTP endpoint | Full feedback flow | ⚠️ Basic only |
| History | ✓ Basic hit rate | Full stats, streak, 90-day retention | ⚠️ Incomplete |
| Database | ✓ Basic schema | Full spec schema + migrations | ⚠️ Upgrade needed |
| Tests | None | Unit + Integration + E2E | ❌ Missing |

---

## Key Spec Details to Implement

### Reminder Types (Section 3)
- `countdown_event`: drive duration + arrival time
- `simple_countdown`: no drive, just time remaining
- `morning_routine`: anchor points per routine step
- `standing_recurring`: repeat daily/weekdays/custom

### Urgency Tiers (Section 2)
| Tier | Minutes Before | Sound |
|------|---------------|-------|
| calm | 30 | gentle chime |
| casual | 25 | gentle chime |
| pointed | 20 | pointed beep |
| urgent | 15 | pointed beep |
| pushing | 10 | urgent siren |
| firm | 5 | urgent siren |
| critical | 1 | alarm |
| alarm | 0 | looping alarm |

### Chain Compression Rules (Section 2)
- ≥25 min buffer: full 8-anchor chain
- 20-24 min: skip calm (7 anchors)
- 15-19 min: skip calm/casual (6 anchors)
- 10-14 min: skip calm/casual/pointed (5 anchors)
- 5-9 min: start at firm (3 anchors)
- ≤5 min: firm + alarm (2 anchors) or alarm only (1 anchor)

### Feedback Loop Adjustment (Section 11)
- `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`
- Capped at +15 minutes maximum

---

## Reference Implementation

The Python `test_server.py` provides working implementations of:
- Chain engine computation (`compute_escalation_chain`)
- Keyword parser (`parse_reminder_natural`)
- Voice message generation (`generate_voice_message`)
- Hit rate calculation (`calculate_hit_rate`)

These should be ported to TypeScript and adapted for mobile context.

---

## Out of Scope (per spec)
- Password reset / account management (local-only data in v1)
- Smart home integration
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing (speaker-only in v1)
- Sound recording / trimming
- Cloud sound library