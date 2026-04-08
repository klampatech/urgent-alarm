# Implementation Plan — Urgent Voice Alarm App

## Overview

**Spec Source:** `specs/urgent-voice-alarm-app-2026-04-08.spec.md`
**Current State:** Python test server with partial chain engine and parser logic — NOT a React Native mobile app
**Target:** Complete mobile app implementation per spec

---

## Phase 1: Foundation (Critical Path)

### Task 1.1 — Initialize React Native Project
- Initialize React Native 0.76+ project with TypeScript
- Install core dependencies: React Navigation, Zustand, SQLite (expo-sqlite or react-native-sqlite-storage)
- Set up project structure per CLAUDE.md (domain-driven design)

### Task 1.2 — Database Layer (Section 13)
- Implement SQLite schema per spec with migrations
- Create repository classes for: reminders, anchors, history, user_preferences, destination_adjustments, custom_sounds
- Enable WAL mode, foreign keys, UUID generation

### Task 1.3 — Chain Engine (Section 2)
- Port chain computation logic from test_server.py to TypeScript
- Implement `compute_escalation_chain()`, `validate_chain()`, `get_next_unfired_anchor()`
- Add deterministic unit tests

---

## Phase 2: Reminder Creation Flow

### Task 2.1 — LLM Parser (Section 3)
- Create `ILanguageModelAdapter` interface
- Implement MiniMax API adapter (or Anthropic fallback)
- Add keyword extraction fallback
- Build confirmation card UI with editable fields

### Task 2.2 — Quick Add UI
- Create reminder creation screen with text/speech input
- Display parsed interpretation card before confirmation
- Handle manual field correction

### Task 2.3 — Voice Personality System (Section 10)
- Define voice personality data structure with templates
- Implement `generate_voice_message()` function
- Store selected personality in user preferences

---

## Phase 3: Voice & Notifications

### Task 3.1 — TTS Generation (Section 4)
- Create `ITTSAdapter` interface
- Implement ElevenLabs API adapter (configurable via env var)
- Implement TTS cache storage (`/tts_cache/{reminder_id}/`)
- Add fallback: system notification sound + text

### Task 3.2 — Notification Layer (Section 5)
- Implement notification tier escalation (gentle → beep → siren → alarm)
- Handle DND awareness with visual override for final 5 min
- Implement quiet hours suppression with post-quiet-hours catch-up
- Implement chain overlap serialization (queue new anchors)

### Task 3.3 — Background Scheduling (Section 6)
- Integrate Notifee for iOS background tasks
- Implement recovery scan on app launch
- Handle missed anchors (15-min grace window, log missed_reason)

---

## Phase 4: User Interaction

### Task 4.1 — Snooze Flow (Section 9)
- Implement tap-snooze (1 min) with TTS confirmation
- Implement tap-and-hold custom snooze (1, 3, 5, 10, 15 min)
- Implement chain re-computation after snooze
- Persist snooze state for crash recovery

### Task 4.2 — Dismissal & Feedback (Section 9)
- Implement swipe-to-dismiss with feedback prompt
- Handle feedback responses: timing right, left too early, left too late
- Store feedback in history table

### Task 4.3 — History & Stats (Section 11)
- Implement hit rate calculation (trailing 7 days)
- Implement feedback loop adjustment (+2 min per late, capped at +15)
- Implement streak counter for recurring reminders
- Display "common miss window" analysis

---

## Phase 5: Integrations

### Task 5.1 — Calendar Integration (Section 7)
- Implement Apple Calendar adapter (EventKit)
- Implement Google Calendar adapter (Google Calendar API)
- Create suggestion cards for events with locations
- Handle recurring events

### Task 5.2 — Location Awareness (Section 8)
- Implement single location check at departure anchor
- Handle 500m geofence comparison
- Implement escalation if still at origin
- Request permission at first location-aware reminder

### Task 5.3 — Sound Library (Section 12)
- Bundle 5 built-in sounds per category (commute, routine, errand)
- Implement custom audio import (MP3, WAV, M4A, max 30 sec)
- Implement corrupted sound fallback

---

## Phase 6: Testing & Polish

### Task 6.1 — Unit Tests
- Chain engine determinism tests
- Parser fixtures and keyword extraction tests
- TTS adapter mock implementation
- LLM adapter mock implementation

### Task 6.2 — Integration Tests
- Full reminder creation flow (parse → chain → TTS → persist)
- Anchor firing (schedule → fire → mark fired)
- Snooze recovery (snooze → recompute → re-register)
- Feedback loop (dismiss → feedback → adjustment)

### Task 6.3 — E2E Tests (Detox)
- Quick Add flow
- Reminder confirmation
- Anchor firing sequence
- Snooze interaction
- Dismissal feedback
- Settings navigation
- Sound library browsing

---

## Priority Order (Dependencies)

```
1.1 Project Init ─────► 1.2 DB Layer ─────► 1.3 Chain Engine
                                                    │
                                                    ▼
                              2.1 Parser ◄── 2.2 Quick Add UI
                                    │
                                    ▼
                              2.3 Voice Personality
                                    │
                                    ▼
                              3.1 TTS Generation ◄── 3.2 Notifications ◄── 3.3 Background
                                    │                      │
                                    └──────────────────────┘
                                                     │
                                                     ▼
                              4.1 Snooze ◄── 4.2 Dismissal ◄── 4.3 History/Stats
                                                     │
                                                     ▼
                              5.1 Calendar ◄── 5.2 Location ◄── 5.3 Sound Library
                                                     │
                                                     ▼
                                           6.1 Unit Tests ◄── 6.2 Integration ◄── 6.3 E2E
```

---

## Gaps from Current State

| Component | Current | Required |
|-----------|---------|----------|
| Platform | Python server | React Native app |
| Chain Engine | Partial (Python) | Full (TypeScript) |
| Parser | Keyword only | LLM + fallback |
| TTS | Message templates | ElevenLabs adapter |
| Notifications | None | Full implementation |
| Background | None | Notifee integration |
| Calendar | None | EventKit + Google API |
| Location | None | CoreLocation check |
| Snooze/Dismissal | None | Full implementation |
| Sound Library | None | Full implementation |
| Tests | None | Unit + Integration + E2E |

---

## Notes

- The Python `test_server.py` serves as a reference implementation for chain logic and can be ported to TypeScript
- All external dependencies (LLM, TTS, Calendar, Location) must have mock-able interfaces per spec
- Use Zustand for state management per CLAUDE.md (global state last resort)
- All timestamps in ISO 8601, displayed in local time
- Target 80% test coverage minimum per CLAUDE.md