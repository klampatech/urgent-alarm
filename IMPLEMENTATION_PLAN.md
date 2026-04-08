# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Project Status Summary

The **specs** define a comprehensive mobile alarm application with:
- Escalation chain engine for time-based urgency nudges
- Natural language reminder parsing (LLM + keyword fallback)
- Pre-generated TTS voice messages with 5+ personality styles
- Background scheduling, calendar integration, location awareness
- Snooze/dismissal flows, history tracking, and feedback loops
- SQLite persistence with migrations

The **current codebase** (`src/test_server.py`) is a Python HTTP server prototype that implements:
- Basic escalation chain computation (core algorithm)
- Keyword-based natural language parser (regex patterns)
- Voice personality message templates (5 personalities)
- Simple SQLite database with 5 tables
- Basic HTTP endpoints for testing

**Gap Analysis:** The codebase is ~15% of the spec. It provides foundational algorithms but lacks all mobile app infrastructure, platform integrations, and most feature implementations.

---

## Priority 1: Foundation & Architecture

These tasks must be completed first as all other features depend on them.

### 1.1 Mobile App Scaffold
**Status:** Not Started | **Effort:** High | **Priority:** P0

- [ ] Choose platform: React Native or Flutter (per spec options)
- [ ] Set up project with TypeScript/Flow
- [ ] Configure project structure following clean architecture
- [ ] Set up CI/CD pipeline

### 1.2 Database Migration System
**Status:** Not Started | **Effort:** Medium | **Priority:** P0

- [ ] Design versioned migration system (schema_v1, schema_v2, etc.)
- [ ] Implement migration runner
- [ ] Add all tables from spec (Section 13.2):
  - [ ] `reminders` — add missing columns: `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`, `updated_at`, `custom_sound_path`
  - [ ] `anchors` — add: `tts_fallback`, `snoozed_to`
  - [ ] `history` — add: `actual_arrival`, `missed_reason`
  - [ ] `calendar_sync` table (apple/google sync state)
  - [ ] `custom_sounds` table (imported audio files)
- [ ] Enable foreign key enforcement and WAL mode
- [ ] Add in-memory SQLite mode for tests

### 1.3 LLM Adapter Interface & Mock
**Status:** Not Started | **Effort:** Medium | **Priority:** P0

- [ ] Define `ILanguageModelAdapter` interface
- [ ] Implement mock adapter for testing (returns predefined fixtures)
- [ ] Implement MiniMax adapter (Anthropic-compatible endpoint)
- [ ] Implement Anthropic adapter (fallback)
- [ ] Add environment-based adapter selection

---

## Priority 2: Core Feature Implementation

### 2.1 Enhanced Reminder Parsing
**Status:** Partial (basic regex exists) | **Effort:** Medium | **Priority:** P1

- [ ] Integrate LLM adapter for full natural language parsing
- [ ] Add confirmation card UI component
- [ ] Implement manual field correction flow
- [ ] Add reminder type enum extraction (countdown_event, simple_countdown, morning_routine, standing_recurring)
- [ ] Improve keyword extraction fallback confidence scoring
- [ ] Handle edge cases: "tomorrow", relative dates, ambiguous times

### 2.2 TTS Adapter Interface & Mock
**Status:** Not Started | **Effort:** Medium | **Priority:** P1

- [ ] Define `ITTSAdapter` interface
- [ ] Implement mock TTS adapter for testing
- [ ] Implement ElevenLabs adapter:
  - [ ] Voice ID mapping per personality
  - [ ] Custom prompt passing as style parameters
  - [ ] Async generation with polling (30s timeout)
- [ ] Implement TTS cache manager:
  - [ ] File storage at `/tts_cache/{reminder_id}/{anchor_id}.mp3`
  - [ ] Cache invalidation on reminder deletion
  - [ ] Fallback to notification text on TTS failure

### 2.3 Voice Personality System Expansion
**Status:** Partial (5 templates exist) | **Effort:** Medium | **Priority:** P1

- [ ] Add "Calm" personality (gentle-only for non-aggressive users)
- [ ] Add "Custom" personality with user prompt (max 200 chars)
- [ ] Implement per-tier message variations (minimum 3 per tier per personality)
- [ ] Lock personality at reminder creation (don't retroactively change)
- [ ] Store personality selection in user preferences

### 2.4 Enhanced Escalation Chain Engine
**Status:** Partial (algorithm exists) | **Effort:** Low | **Priority:** P1

- [ ] Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Add deterministic chain computation for unit testing
- [ ] Validate `arrival_time > departure_time + minimum_drive_time`
- [ ] Add chain sorting by timestamp

### 2.5 Snooze & Dismissal Flow
**Status:** Not Started | **Effort:** Medium | **Priority:** P1

- [ ] Implement tap snooze (1 minute default)
- [ ] Implement tap-and-hold custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation after snooze:
  - [ ] Shift remaining anchors by snooze duration
  - [ ] Re-register with Notifee
- [ ] Implement swipe-to-dismiss feedback prompt:
  - [ ] "You missed [destination] — was the timing right?"
  - [ ] Yes/No response flow
  - [ ] "What was wrong?" sub-prompt if "No"
- [ ] Add TTS snooze confirmation: "Okay, snoozed [X] minutes"
- [ ] Persist snooze state across app restarts

---

## Priority 3: Platform Integration

### 3.1 Notification & Alarm System
**Status:** Not Started | **Effort:** High | **Priority:** P1

- [ ] Implement notification tier escalation:
  - [ ] Gentle chime: calm/casual
  - [ ] Pointed beep: pointed/urgent
  - [ ] Urgent siren: pushing/firm
  - [ ] Looping alarm: critical/alarm (T-0)
- [ ] Implement DND awareness:
  - [ ] Early anchors: silent notification only
  - [ ] Final 5 minutes: visual + vibration override
- [ ] Implement quiet hours suppression:
  - [ ] User-configurable start/end (default 10pm–7am)
  - [ ] Queue suppressed anchors
  - [ ] Drop anchors >15 minutes overdue
- [ ] Implement chain overlap serialization
- [ ] Implement T-0 alarm looping until user action

### 3.2 Background Scheduling
**Status:** Not Started | **Effort:** High | **Priority:** P1

- [ ] Integrate Notifee (iOS + Android)
- [ ] Register each anchor as individual background task
- [ ] Implement iOS BGTaskScheduler:
  - [ ] `BGAppRefreshTask` for near-accurate timing
  - [ ] `BGProcessingTask` for TTS clip pre-warming
- [ ] Implement recovery scan on app launch:
  - [ ] Fire overdue anchors within 15-minute grace window
  - [ ] Drop and log anchors >15 minutes overdue
- [ ] Re-register pending anchors on crash recovery
- [ ] Add late fire warning (>60s delay triggers log)

### 3.3 Calendar Integration
**Status:** Not Started | **Effort:** High | **Priority:** P2

- [ ] Define `ICalendarAdapter` interface
- [ ] Implement Apple Calendar adapter (EventKit):
  - [ ] Event sync with location extraction
  - [ ] Permission handling with explanation banner
- [ ] Implement Google Calendar adapter:
  - [ ] OAuth flow
  - [ ] Event sync with location extraction
- [ ] Implement sync scheduler (launch + every 15 minutes + background)
- [ ] Implement suggestion card UI:
  - [ ] "Parker Dr check-in at 9am — add departure reminder?"
  - [ ] Calendar icon distinction
- [ ] Handle recurring events
- [ ] Graceful degradation on sync failure

### 3.4 Location Awareness
**Status:** Not Started | **Effort:** Medium | **Priority:** P2

- [ ] Implement single-point location check at departure anchor
- [ ] Store origin: user-specified address OR device location at creation
- [ ] Implement geofence comparison (500m radius)
- [ ] Implement escalation if user still at origin:
  - [ ] Fire firm/critical tier immediately instead of calm departure
- [ ] Request location permission at first location-aware reminder
- [ ] Handle permission denial gracefully
- [ ] Ensure no location history storage (single comparison only)

---

## Priority 4: Data & Analytics

### 4.1 History & Feedback Loop
**Status:** Partial (basic hit rate exists) | **Effort:** Medium | **Priority:** P2

- [ ] Implement hit rate calculation:
  - `count(outcome = 'hit') / count(outcome != 'pending') * 100`
- [ ] Implement feedback loop adjustment:
  - [ ] Track late_count per destination
  - [ ] `adjusted_drive_duration = stored + (late_count * 2_min)`
  - [ ] Cap adjustment at +15 minutes
- [ ] Implement "common miss window" identification
- [ ] Implement streak counter for recurring reminders:
  - [ ] Increment on hit
  - [ ] Reset on miss
- [ ] Implement 90-day data retention with archive

### 4.2 Sound Library
**Status:** Not Started | **Effort:** Medium | **Priority:** P3

- [ ] Bundle built-in sounds by category (5 per: commute, routine, errand)
- [ ] Implement custom audio import:
  - [ ] Support MP3, WAV, M4A (max 30 seconds)
  - [ ] File picker integration
  - [ ] Transcode to normalized format
- [ ] Implement per-reminder sound selection
- [ ] Implement sound picker UI
- [ ] Implement corrupted file fallback to category default
- [ ] Persist sound selection on reminder edit

---

## Priority 5: User Experience

### 5.1 Quick Add UI
**Status:** Not Started | **Effort:** Medium | **Priority:** P2

- [ ] Single text/speech input
- [ ] Parsed interpretation preview before confirm
- [ ] Manual field correction interface
- [ ] Natural language examples

### 5.2 History & Stats UI
**Status:** Not Started | **Effort:** Low | **Priority:** P3

- [ ] Weekly hit rate display
- [ ] Streak counter for routines
- [ ] Common miss window visualization
- [ ] History list with outcomes

### 5.3 Settings & Preferences
**Status:** Not Started | **Effort:** Low | **Priority:** P3

- [ ] Voice personality selection
- [ ] Quiet hours configuration
- [ ] Default drive duration
- [ ] Sound library access
- [ ] Calendar connection management

### 5.4 Morning Routine Templates
**Status:** Not Started | **Effort:** Medium | **Priority:** P3

- [ ] Routine template creation UI
- [ ] Anchor point definition (wake up → clothes → leave)
- [ ] Reusable routine scheduling
- [ ] Standing/recurring reminder support

---

## Testing Strategy

### Unit Tests Required
- [ ] Chain engine determinism tests (TC-06, Section 2.5)
- [ ] Parser tests: natural language, countdown, tomorrow resolution (Section 3.5)
- [ ] Keyword extraction fallback (TC-04, Section 3.5)
- [ ] TTS cache cleanup (TC-04, Section 4.5)
- [ ] Database migrations (TC-01-TC-05, Section 13.5)
- [ ] Hit rate calculation (TC-01, Section 11.5)
- [ ] Feedback loop adjustment with cap (TC-02, TC-03, Section 11.5)

### Integration Tests Required
- [ ] Reminder creation → chain → anchor firing flow
- [ ] Calendar sync → suggestion → reminder creation
- [ ] Snooze → chain re-computation → adjusted fire times
- [ ] Background kill → recovery → overdue anchor handling

---

## Implementation Order (Dependency Graph)

```
[1.1 Mobile Scaffold] ──┬──> [1.2 Database Migrations] ──> [1.3 LLM Adapter]
                        │                                       │
                        └───────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        [2.1 Reminder Parsing] [2.2 TTS Adapter] [2.4 Chain Engine]
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        [2.3 Voice Personalities] [2.5 Snooze/Dismiss] [3.1 Notifications]
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        [3.2 Background Sched] [3.3 Calendar] [3.4 Location]
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                [4.1 History/Stats]      [4.2 Sound Library]
                        │                       │
                        └───────────────────────┘
                                    │
                                    ▼
                            [5.x UI/UX Features]
```

---

## Estimated Complexity

| Component | Spec Lines | Test Cases | Complexity |
|-----------|------------|------------|------------|
| Chain Engine | 82 | 6 | Low |
| Reminder Parsing | 85 | 7 | Medium |
| Voice & TTS | 65 | 5 | Medium |
| Notifications | 75 | 6 | High |
| Background Sched | 70 | 6 | High |
| Calendar Integration | 80 | 6 | High |
| Location Awareness | 60 | 5 | Medium |
| Snooze & Dismissal | 65 | 6 | Medium |
| Voice Personalities | 55 | 5 | Medium |
| History & Stats | 70 | 7 | Medium |
| Sound Library | 55 | 5 | Medium |
| Data Persistence | 80 | 5 | Medium |

**Total:** ~842 spec lines, 69 test cases

---

## Notes

- The current `test_server.py` serves as a Python prototype for validating core algorithms (chain computation, message generation). Mobile implementation should maintain API compatibility with its HTTP endpoints for scenario harness testing.
- Voice/TTS integration requires API keys (ElevenLabs, OpenAI/Anthropic) — use environment variables.
- Calendar and location integrations require user permissions — implement graceful degradation if denied.
- The spec mentions React Native or Flutter; this decision should be made before Priority 1 tasks begin.
