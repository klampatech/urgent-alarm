# Urgent Alarm - Implementation Plan

## Current State Assessment

The project has a working **test server** (`src/test_server.py`) with partial core functionality:
- Basic chain engine computation
- Keyword-based parser (no LLM adapter mock)
- 5 voice personality templates
- SQLite database with core tables

**Missing or incomplete** (per spec):

| Section | Status | Notes |
|---------|--------|-------|
| 2. Escalation Chain Engine | Partial | Missing compressed chain for 10-24 min, some validation gaps |
| 3. Reminder Parsing | Partial | Keyword extractor works; no LLM adapter mock interface |
| 4. Voice & TTS Generation | Missing | No ElevenLabs adapter, no TTS cache system |
| 5. Notification & Alarm Behavior | Missing | No DND handling, sound tier escalation, quiet hours |
| 6. Background Scheduling | Missing | No Notifee integration, no recovery scan |
| 7. Calendar Integration | Missing | No EventKit/Google Calendar adapters |
| 8. Location Awareness | Missing | No origin check, no 500m geofence logic |
| 9. Snooze & Dismissal Flow | Partial | No chain re-computation, no feedback prompts |
| 10. Voice Personality System | Partial | Templates exist; no custom prompt support, no variations |
| 11. History, Stats & Feedback Loop | Partial | Basic hit rate; no common miss window, no streak, no adjustment cap |
| 12. Sound Library | Missing | No built-in sounds, no custom import |
| 13. Data Persistence | Partial | Missing tables: `custom_sounds`, `calendar_sync`, `user_preferences` columns, schema versioning |

---

## Priority 1: Foundation & Core Engine

### Task 1.1: Complete Escalation Chain Engine
**Priority:** Critical  
**Dependencies:** None

**Gaps:**
- Compressed chain for 10-24 min buffer not working correctly (see TC-02 in spec)
- `get_next_unfired_anchor()` function missing
- Chain determinism testing needed
- Validation: departure_time_in_past not checked correctly

**Acceptance Criteria:**
- [ ] Full 8-anchor chain for ≥25 min buffer
- [ ] Compressed 5-anchor chain for 15-24 min buffer
- [ ] Short 4-anchor chain for 10-14 min buffer  
- [ ] Minimum 2-3 anchor chain for ≤9 min buffer
- [ ] `get_next_unfired_anchor(reminder_id)` works
- [ ] Chain determinism unit tests pass

---

### Task 1.2: Database Schema Alignment
**Priority:** Critical  
**Dependencies:** None

**Gaps:**
- Missing `custom_sounds` table
- Missing `calendar_sync` table
- Missing `origin_lat`, `origin_lng`, `origin_address` in reminders
- Missing `tts_fallback`, `snoozed_to` in anchors
- Missing `actual_arrival`, `missed_reason` in history
- No schema versioning

**Actions:**
- Add migration system
- Add missing columns/tables per spec schema
- Enable WAL mode and foreign keys

**Acceptance Criteria:**
- [ ] All spec tables exist with correct columns
- [ ] Foreign key cascade works
- [ ] Schema version tracked

---

### Task 1.3: LLM Adapter Interface (Mock)
**Priority:** High  
**Dependencies:** Task 1.2

**Gaps:**
- No `ILanguageModelAdapter` interface
- No mock implementation for tests
- Keyword extraction not fallback-only

**Actions:**
- Define `ILanguageModelAdapter` protocol
- Implement `MockLanguageModelAdapter` for tests
- Implement `KeywordExtractionAdapter` as fallback
- Implement `MiniMaxAdapter` (real API, configurable)

**Acceptance Criteria:**
- [ ] Interface exists and is mock-able
- [ ] Mock adapter returns fixture data without API call
- [ ] Keyword extraction handles all spec formats
- [ ] Confidence score returned on fallback

---

## Priority 2: Voice & TTS System

### Task 2.1: TTS Adapter Interface (Mock)
**Priority:** High  
**Dependencies:** Task 1.1

**Gaps:**
- No `ITTSAdapter` interface
- No local TTS cache system
- No ElevenLabs adapter

**Actions:**
- Define `ITTSAdapter` protocol
- Implement `MockTTSAdapter` for tests (writes silent audio file)
- Implement `ElevenLabsAdapter` (real API, configurable)
- Create `/tts_cache/{reminder_id}/` structure
- Implement cache invalidation on reminder delete

**Acceptance Criteria:**
- [ ] Interface exists and is mock-able
- [ ] Mock TTS creates local file and returns path
- [ ] Cache directory structure matches spec
- [ ] TTS generation respects voice personality

---

### Task 2.2: Voice Personality System Upgrade
**Priority:** Medium  
**Dependencies:** Task 2.1

**Gaps:**
- No custom prompt support (max 200 chars)
- No message variations (3 per tier per personality minimum)
- No "Calm" personality (gentle-only for non-aggressive users)

**Actions:**
- Add "Calm" personality templates
- Implement message variation rotation
- Implement custom prompt concatenation
- Add per-reminder voice override storage

**Acceptance Criteria:**
- [ ] All 6 personalities work (Coach, Assistant, Best Friend, No-nonsense, Calm, Custom)
- [ ] Message generation uses rotation for variety
- [ ] Custom prompt modifies message tone

---

## Priority 3: User Interaction

### Task 3.1: Notification & Alarm Behavior
**Priority:** High  
**Dependencies:** Task 2.1

**Gaps:**
- No sound tier escalation
- No DND handling
- No quiet hours suppression
- No chain overlap serialization
- T-0 alarm not looping

**Actions:**
- Implement notification tier escalation (gentle → beep → siren → alarm)
- Implement DND detection and override logic
- Implement quiet hours configuration and suppression
- Implement chain overlap queue
- Implement T-0 looping alarm

**Acceptance Criteria:**
- [ ] Sound tier matches urgency tier
- [ ] DND suppressed early anchors, visual+vibration for final 5 min
- [ ] Quiet hours skip and queue anchors
- [ ] Overdue 15+ min anchors dropped
- [ ] Chain serialization prevents overlap

---

### Task 3.2: Snooze & Dismissal Flow
**Priority:** High  
**Dependencies:** Task 3.1, Task 1.1

**Gaps:**
- No tap snooze (1 min)
- No tap-and-hold custom snooze picker
- No chain re-computation after snooze
- No feedback prompt UI
- No feedback data storage and adjustment

**Actions:**
- Implement tap snooze action
- Implement custom snooze picker UI (1, 3, 5, 10, 15 min)
- Implement chain re-computation shifting remaining anchors
- Implement re-registration with Notifee
- Implement feedback prompt and storage
- Implement feedback loop: adjust drive_duration for destination

**Acceptance Criteria:**
- [ ] Tap snooze pauses 1 min
- [ ] Custom snooze picker works
- [ ] Chain re-computation shifts correctly
- [ ] Feedback prompt appears on dismiss
- [ ] "Left too late" feedback adds 2 min (cap +15)

---

### Task 3.3: Sound Library
**Priority:** Medium  
**Dependencies:** Task 3.1

**Gaps:**
- No built-in sounds (5 per category)
- No custom audio import
- No per-reminder sound selection UI

**Actions:**
- Bundle 5 built-in sounds per category (Commute, Routine, Errand)
- Implement file picker for MP3/WAV/M4A import (max 30 sec)
- Implement per-reminder sound selection
- Implement corrupted file fallback

**Acceptance Criteria:**
- [ ] Built-in sounds play without network
- [ ] Custom import works for MP3/WAV/M4A
- [ ] Corrupted file fallback uses category default

---

## Priority 4: Background & Reliability

### Task 4.1: Background Scheduling
**Priority:** High  
**Dependencies:** Task 1.1, Task 3.1

**Note:** This is a React Native/Flutter feature in production, but for the Python test server we'll implement the scheduling logic as if Notifee were present.

**Gaps:**
- No anchor scheduling simulation
- No recovery scan on launch
- No late fire warning logging

**Actions:**
- Implement `Scheduler` class that holds pending anchors
- Implement `schedule_anchors()` for reminder creation
- Implement `recovery_scan()` on startup
- Implement `late_fire_warning` logging

**Acceptance Criteria:**
- [ ] Anchors scheduled with timestamps
- [ ] Recovery scan fires overdue anchors within 15 min
- [ ] Overdue 15+ min anchors dropped and logged

---

### Task 4.2: Location Awareness
**Priority:** Medium  
**Dependencies:** Task 4.1

**Note:** In production this uses CoreLocation/FusedLocationProvider. For test server, we'll mock the location check.

**Gaps:**
- No origin address storage
- No single location check at departure
- No 500m geofence comparison
- No immediate escalation if at origin

**Actions:**
- Add origin storage to reminder
- Implement `LocationAdapter` interface with mock
- Implement `check_if_at_origin()` function
- Implement immediate escalation to firm/critical if at origin

**Acceptance Criteria:**
- [ ] Origin stored at reminder creation
- [ ] Single location check at departure anchor
- [ ] At-origin triggers immediate escalation

---

## Priority 5: External Integrations

### Task 5.1: Calendar Integration
**Priority:** Medium  
**Dependencies:** Task 1.2

**Gaps:**
- No Apple Calendar adapter
- No Google Calendar adapter
- No `ICalendarAdapter` interface
- No sync scheduling

**Actions:**
- Define `ICalendarAdapter` interface
- Implement `AppleCalendarAdapter` (EventKit mock for testing)
- Implement `GoogleCalendarAdapter` (Google Calendar API mock for testing)
- Implement sync scheduler (every 15 min)
- Implement suggestion cards for events with locations

**Acceptance Criteria:**
- [ ] Interface exists with mock implementation
- [ ] Events with locations surface as suggestions
- [ ] Calendar permission denial shows explanation banner

---

## Priority 6: Stats & History

### Task 6.1: History, Stats & Feedback Loop
**Priority:** Medium  
**Dependencies:** Task 1.2, Task 3.2

**Gaps:**
- No common miss window calculation
- No streak counter for recurring reminders
- No 90-day archive logic
- No adjustment cap enforcement

**Actions:**
- Implement `get_common_miss_window()` function
- Implement streak increment/reset logic
- Implement 90-day archive query
- Ensure adjustment cap at +15 minutes

**Acceptance Criteria:**
- [ ] Common miss window identifies most-missed tier
- [ ] Streak increments on hit, resets on miss
- [ ] Adjustment capped at +15 minutes
- [ ] Stats computable from history table alone

---

## Implementation Order

```
Phase 1: Foundation
├── 1.1 Complete Chain Engine
├── 1.2 Database Schema Alignment  
└── 1.3 LLM Adapter Interface (Mock)

Phase 2: Voice System
├── 2.1 TTS Adapter Interface (Mock)
└── 2.2 Voice Personality System Upgrade

Phase 3: User Interaction
├── 3.1 Notification & Alarm Behavior
├── 3.2 Snooze & Dismissal Flow
└── 3.3 Sound Library

Phase 4: Background & Reliability
├── 4.1 Background Scheduling
└── 4.2 Location Awareness

Phase 5: External Integrations
└── 5.1 Calendar Integration

Phase 6: Stats & History
└── 6.1 History, Stats & Feedback Loop
```

---

## Testing Strategy

Per spec section 14, all acceptance criteria require corresponding tests:

### Unit Tests Needed
- Chain engine determinism
- Parser fixtures (mock adapter)
- TTS adapter mock
- Keyword extraction
- Schema validation
- Message generation variations

### Integration Tests Needed
- Full reminder creation flow (parse → chain → TTS → persist)
- Anchor firing (schedule → fire → mark fired)
- Snooze recovery (snooze → recompute → re-register)
- Feedback loop (dismiss → feedback → adjustment applied)

### End-to-End Tests (Manual/Detox)
- Quick Add flow
- Reminder confirmation
- Anchor firing sequence
- Snooze interaction
- Dismissal feedback
- Settings navigation
- Sound library browsing

---

## Notes

- The Python test server is a **harness for validation**, not the actual mobile app
- Real TTS (ElevenLabs) and LLM (MiniMax) adapters are configurable via environment variable
- All external dependencies should fail gracefully with sensible fallbacks
- The project uses NLSpec format for specifications