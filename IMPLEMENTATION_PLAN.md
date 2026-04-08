# Implementation Plan: URGENT — AI Escalating Voice Alarm

## Gap Analysis Summary

**Spec Coverage vs Current Codebase:**

| Spec Section | Status | Notes |
|--------------|--------|-------|
| 1. Overview & Goals | ⚠️ Partial | Python HTTP test server, not a mobile app |
| 2. Escalation Chain Engine | ✅ Done | Implemented in `test_server.py` |
| 3. Reminder Parsing | ⚠️ Partial | Keyword parsing only, no LLM adapter |
| 4. Voice & TTS Generation | ❌ Missing | Template messages only, no ElevenLabs |
| 5. Notification & Alarm | ❌ Missing | No notification system |
| 6. Background Scheduling | ❌ Missing | No Notifee/WorkManager integration |
| 7. Calendar Integration | ❌ Missing | No EventKit/Google Calendar |
| 8. Location Awareness | ❌ Missing | No CoreLocation integration |
| 9. Snooze & Dismissal | ❌ Missing | No UI/notification handling |
| 10. Voice Personality | ⚠️ Partial | Templates done, no custom prompts |
| 11. History & Stats | ⚠️ Partial | Basic hit rate only |
| 12. Sound Library | ❌ Missing | No audio assets |
| 13. Data Persistence | ⚠️ Partial | Basic schema, missing tables |
| 14. Definition of Done | ❌ Missing | No test suite |

**Critical Finding:** The codebase is a Python HTTP demo server—**not a mobile app**. The spec requires a React Native or Flutter application with native iOS/Android integrations.

---

## Priority 1: Foundation (Must Implement First)

### 1.1 Mobile App Scaffold
- **Task:** Set up React Native or Flutter project
- **Details:** Choose platform (React Native recommended for faster TTS integration); configure build tools, TypeScript/Flow, ESLint
- **Dependencies:** `react-navigation`, `zustand` (state), `@react-native-async-storage/async-storage`
- **Files:** `src/App.tsx`, `src/navigation/`, `src/store/`

### 1.2 Data Persistence Layer
- **Task:** Implement full SQLite schema per spec section 13
- **Details:** Add missing tables: `user_preferences`, `calendar_sync`, `custom_sounds`, `destination_adjustments`
- **Dependencies:** `react-native-sqlite-storage` or `expo-sqlite`
- **Files:** `src/lib/database.ts`, `src/lib/migrations/`

### 1.3 Chain Engine Module (Extract/Polish)
- **Task:** Extract chain engine from test_server.py into reusable module
- **Details:** Unit test the 6 test scenarios from spec TC-01 through TC-06
- **Files:** `src/lib/chain-engine.ts`, `src/__tests__/chain-engine.test.ts`

### 1.4 Reminder Parser Module
- **Task:** Create LLM adapter interface + keyword fallback implementation
- **Details:** Implement `ILanguageModelAdapter` interface; add mock adapter for tests
- **Files:** `src/lib/parsers/reminder-parser.ts`, `src/lib/parsers/llm-adapter.ts`, `src/lib/parsers/keyword-fallback.ts`

---

## Priority 2: Core User Flows

### 2.1 Quick Add UI + Flow
- **Task:** Build reminder creation screen with text/speech input
- **Details:** Display parsed confirmation card; allow manual field correction
- **Files:** `src/screens/QuickAddScreen.tsx`, `src/components/ParsedReminderCard.tsx`

### 2.2 Voice Personality Selection
- **Task:** Onboarding flow + settings for voice personality
- **Details:** 5 built-in personalities + custom prompt option (max 200 chars)
- **Files:** `src/screens/OnboardingScreen.tsx`, `src/screens/SettingsScreen.tsx`, `src/lib/voice-personalities.ts`

### 2.3 TTS Generation Service
- **Task:** ElevenLabs adapter with local file caching
- **Details:** Pre-generate clips at reminder creation; cache in `/tts_cache/{reminder_id}/`; implement fallback to notification sound
- **Files:** `src/lib/tts/elevenlabs-adapter.ts`, `src/lib/tts/cache-manager.ts`

### 2.4 Reminders List & Management UI
- **Task:** View, edit, delete existing reminders
- **Details:** Show destination, arrival time, status; swipe-to-delete
- **Files:** `src/screens/RemindersListScreen.tsx`, `src/components/ReminderCard.tsx`

---

## Priority 3: Notifications & Background

### 3.1 Notification System
- **Task:** Implement notification + alarm behavior per spec section 5
- **Details:** 
  - Sound escalation by urgency tier (gentle chime → alarm loop)
  - DND-aware: silent early, vibrate late
  - Quiet hours suppression (10pm–7am default, configurable)
  - Chain overlap serialization (queue new anchors)
- **Files:** `src/lib/notifications/notification-manager.ts`, `src/lib/notifications/sound-tiers.ts`

### 3.2 Background Scheduling
- **Task:** Integrate Notifee for iOS/Android background tasks
- **Details:**
  - Register each anchor as individual Notifee task
  - iOS: BGAppRefreshTask + BGProcessingTask for clip pre-warming
  - Recovery scan on app launch (15-min grace window)
  - Re-register pending anchors after crash
- **Files:** `src/lib/scheduling/notifee-service.ts`, `src/lib/scheduling/recovery-scanner.ts`

### 3.3 Snooze & Dismissal Flow
- **Task:** Implement notification interactions
- **Details:**
  - Tap → 1-min snooze with TTS confirmation
  - Tap-and-hold → custom snooze picker (1, 3, 5, 10, 15 min)
  - Swipe dismiss → feedback prompt
  - Chain re-computation after snooze
- **Files:** `src/lib/notifications/snooze-handler.ts`, `src/components/FeedbackPrompt.tsx`

---

## Priority 4: Integrations

### 4.1 Calendar Integration
- **Task:** Apple Calendar (EventKit) + Google Calendar API adapters
- **Details:**
  - `ICalendarAdapter` interface with both implementations
  - Sync on launch + every 15 minutes
  - Suggestion cards for events with locations
  - Recurring event handling
  - Permission denial handling with settings link
- **Files:** `src/lib/calendar/apple-calendar-adapter.ts`, `src/lib/calendar/google-calendar-adapter.ts`, `src/screens/CalendarScreen.tsx`

### 4.2 Location Awareness
- **Task:** Single-point location check at departure anchor
- **Details:**
  - CoreLocation (iOS) / FusedLocationProvider (Android)
  - 500m geofence radius
  - Escalate immediately if still at origin
  - Location permission requested at first location-aware reminder creation
- **Files:** `src/lib/location/location-service.ts`

---

## Priority 5: Intelligence & Polish

### 5.1 History & Stats
- **Task:** Full stats implementation per spec section 11
- **Details:**
  - Weekly hit rate calculation
  - Streak counter for recurring reminders
  - Common miss window identification
  - Feedback loop: adjust drive_duration for destinations (+2 min per "left too late", cap +15 min)
- **Files:** `src/lib/stats/stats-service.ts`, `src/screens/HistoryScreen.tsx`

### 5.2 Sound Library
- **Task:** Built-in sounds + custom audio import
- **Details:**
  - 5 built-in sounds per category (Commute, Routine, Errand)
  - Custom import: MP3, WAV, M4A (max 30 sec)
  - Transcode to normalized format
  - Fallback on corrupted/missing file
- **Files:** `src/lib/audio/sound-library.ts`, `src/lib/audio/audio-importer.ts`

### 5.3 Morning Routines & Standing Recurring
- **Task:** Routine template system
- **Details:**
  - User-defined routine with multiple anchor points
  - Daily/weekdays/custom recurrence
  - Streak tracking per routine
- **Files:** `src/screens/RoutineEditorScreen.tsx`, `src/lib/routines/routine-engine.ts`

---

## Priority 6: Quality & Documentation

### 6.1 Test Suite
- **Task:** Achieve full spec coverage per section 14
- **Details:** Every acceptance criterion must have a corresponding passing test
- **Files:** `src/__tests__/`, `harness/scenario_harness.py` (scenario validation)

### 6.2 Error Handling & Graceful Degradation
- **Task:** Ensure all external dependencies fail safely
- **Details:**
  - LLM failure → keyword extraction fallback
  - TTS failure → notification sound + text
  - Calendar failure → manual reminders still work
  - Location failure → reminder without location escalation
- **Files:** `src/lib/errors/fallback-handlers.ts`

### 6.3 README & Onboarding Docs
- **Task:** Document setup, configuration, API keys
- **Files:** `README.md`, `docs/ENVIRONMENT.md`

---

## Implementation Order (Dependency Graph)

```
1. Mobile App Scaffold (1.1)
   ↓
2. Data Persistence (1.2)
   ↓
3. Chain Engine Module (1.3)
   ↓
4. Reminder Parser (1.4)
   ↓
5. Quick Add UI (2.1)
   ↓
6. Voice Personality (2.2)
   ↓
7. TTS Service (2.3)
   ↓
8. Reminders List (2.4)
   ↓
9. Notification System (3.1)
   ↓
10. Background Scheduling (3.2)
   ↓
11. Snooze & Dismissal (3.3)
   ↓
12. Calendar Integration (4.1)
   ↓
13. Location Awareness (4.2)
   ↓
14. History & Stats (5.1)
   ↓
15. Sound Library (5.2)
   ↓
16. Routines (5.3)
   ↓
17. Test Suite (6.1)
   ↓
18. Error Handling (6.2)
   ↓
19. Documentation (6.3)
```

---

## Environment Variables Required

```bash
ELEVENLABS_API_KEY=          # ElevenLabs TTS
ANTHROPIC_API_KEY=           # Or MiniMax for LLM parsing
GOOGLE_CALENDAR_CLIENT_ID=   # Google Calendar OAuth
DATABASE_PATH=/path/to/.db   # SQLite location
```

---

## Verification Checklist

Before marking implementation complete, verify:

- [ ] `python3 -m pytest harness/` passes
- [ ] `python3 -m py_compile src/lib/*.py src/*.py` passes (if Python files)
- [ ] All 6 chain engine test scenarios pass (TC-01 through TC-06)
- [ ] Parser handles all 7 test scenarios (TC-01 through TC-07)
- [ ] Database migrations apply cleanly on fresh install
- [ ] TTS cache cleanup works on reminder deletion
- [ ] Snooze re-registration survives app restart
- [ ] Calendar permission denial shows explanation banner
