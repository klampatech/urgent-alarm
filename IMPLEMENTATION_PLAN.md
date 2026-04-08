# URGENT Alarm - Implementation Plan

## Executive Summary

**Current State Analysis:**
- `src/test_server.py` - Partial Python HTTP server with ~15% of spec implemented
- `harness/` - Empty directory, no harness exists
- `scenarios/` - 15 scenario YAMLs created and installed to `/var/otto-scenarios/urgent-alarm/`
- `IMPLEMENTATION_PLAN.md` - Exists but needs update to reflect current gaps

**Gaps Identified:**
1. No scenario harness (blocking validation of all features)
2. Chain engine has incorrect tier logic
3. Parser lacks LLM adapter interface
4. No TTS integration
5. Database schema incomplete
6. No voice message variations (3 per tier)
7. Many spec acceptance criteria untested

---

## Priority 1: Create the Scenario Harness (BLOCKING)

The harness is the validation gate — without it, we cannot verify any implementation.

### 1.1 Create Harness Directory Structure
**Status**: Empty `harness/` directory  
**Priority**: Critical

- [ ] Create `harness/scenario_harness.py` - Main executable
- [ ] Create `harness/requirements.txt` - Python dependencies
- [ ] Create `harness/adapters/` - Test adapter interfaces

### 1.2 Implement Core Harness Logic
**Spec**: Otto loop integration  
**Priority**: Critical

- [ ] Parse scenario YAML files from `/var/otto-scenarios/urgent-alarm/`
- [ ] `ApiSequenceTrigger` - Execute HTTP API calls in sequence
- [ ] Assertion types:
  - [ ] `http_status` - Validate response status
  - [ ] `db_record` - Validate database records
  - [ ] `llm_judge` - Use LLM to evaluate responses
- [ ] Write `{"pass": true}` or `{"pass": false}` to `/tmp/ralph-scenario-result.json`
- [ ] Handle connection to `http://localhost:8090`

### 1.3 Integrate with Otto Loop
**Spec**: OTTO_GUIDE.md  
**Priority**: Critical

- [ ] Ensure harness runs after `git push` via `sudo python3 harness/scenario_harness.py --project urgent-alarm`
- [ ] Harness reads from `/var/otto-scenarios/urgent-alarm/` (root-owned, secure)
- [ ] Write result to `/tmp/ralph-scenario-result.json` (world-readable)

---

## Priority 2: Fix & Test Chain Engine

### 2.1 Fix Chain Tier Logic
**Current Issue**: `test_server.py` has incorrect compressed chain logic  
**Spec**: Section 2  

**Required fix:**
- `≥25 min`: 8 anchors (calm, casual, pointed, urgent, pushing, firm, critical, alarm)
- `20-24 min`: 7 anchors (skip calm, start casual)
- `15-19 min`: 6 anchors (skip calm/casual, start pointed)  
- `10-14 min`: 5 anchors (urgent, pushing, firm, critical, alarm)
- `5-9 min`: 3 anchors (firm, critical, alarm)
- `<5 min`: 2 anchors (critical, alarm) - or just alarm

### 2.2 Add Missing Functions
**Spec**: Section 2.3

- [ ] `get_next_unfired_anchor(reminder_id)` - For scheduler recovery
- [ ] Chain validation: reject if `drive_duration > (arrival_time - now)`

### 2.3 Test Chain Engine
**Spec**: Section 2.5

- [ ] TC-01: Full chain (30 min) → 8 anchors
- [ ] TC-02: Compressed chain (15 min) → 5 anchors (urgent, pushing, firm, critical, alarm)
- [ ] TC-03: Minimum chain (3 min) → 2 anchors (critical, alarm)
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism (same inputs = same outputs)

---

## Priority 3: Complete Database Schema

### 3.1 Update Schema
**Spec**: Section 13.2  

**Add missing columns to `reminders`:**
- [ ] `origin_lat REAL`
- [ ] `origin_lng REAL`
- [ ] `origin_address TEXT`
- [ ] `custom_sound_path TEXT`
- [ ] `calendar_event_id TEXT`

**Add missing columns to `anchors`:**
- [ ] `tts_fallback BOOLEAN DEFAULT FALSE`
- [ ] `snoozed_to TEXT`

**Add missing columns to `history`:**
- [ ] `actual_arrival TEXT`
- [ ] `missed_reason TEXT`

**Add missing columns to `user_preferences`:**
- [ ] `updated_at TEXT NOT NULL`

**Add missing tables:**
- [ ] `schema_migrations` (for versioning)
- [ ] `calendar_sync` (calendar_type, last_sync_at, sync_token, is_connected)
- [ ] `custom_sounds` (id, filename, original_name, category, file_path, duration_seconds, created_at)
- [ ] `destination_adjustments` - Add `updated_at` column

### 3.2 Migration System
**Spec**: Section 13.3

- [ ] Sequential, versioned migrations
- [ ] `mode=memory` for tests (fresh in-memory DB)
- [ ] Enable foreign keys (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)

---

## Priority 4: LLM Parser & Adapter Interface

### 4.1 Create Adapter Interface
**Spec**: Section 3.3

- [ ] `ILanguageModelAdapter` abstract class
- [ ] System prompt for extraction schema
- [ ] Return structured JSON: `{ destination, arrival_time, drive_duration, reminder_type, confidence }`

### 4.2 Implement Adapters
**Spec**: Section 3.1

- [ ] `MinimaxAdapter` - MinMax API (Anthropic-compatible)
- [ ] `AnthropicAdapter` - Anthropic Claude API
- [ ] `MockLanguageModelAdapter` - Returns predefined fixture responses

### 4.3 Improve Keyword Fallback
**Spec**: Section 3.2

**Patterns to handle:**
- `X min drive` → drive_duration = X
- `X-minute drive` → drive_duration = X
- `in X minutes` → arrival_time = now + X (simple countdown)
- `arrive at X` / `check-in at X` → arrival_time = X
- `tomorrow` → +1 day resolution

### 4.4 Test Parser
**Spec**: Section 3.5

- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am"
- [ ] TC-02: "dryer in 3 min" → simple_countdown
- [ ] TC-03: "meeting tomorrow 2pm, 20 min drive" → +1 day
- [ ] TC-04: LLM API failure → keyword fallback
- [ ] TC-05: Manual field correction (confirmation card UI - later)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter in tests

---

## Priority 5: Voice Personality System

### 5.1 Add Message Variations
**Spec**: Section 10.3  
**Current**: 1 template per tier per personality  
**Required**: Minimum 3 variations per tier per personality

- [ ] Coach: 3 variations × 8 tiers = 24 templates
- [ ] Assistant: 24 templates
- [ ] Best Friend: 24 templates
- [ ] No-nonsense: 24 templates
- [ ] Calm: 24 templates

### 5.2 Custom Personality Support
**Spec**: Section 10.2

- [ ] User prompt (max 200 chars) appended to message generation system prompt
- [ ] Route through ElevenLabs voice settings

### 5.3 ElevenLabs Integration
**Spec**: Section 4

- [ ] `ITTSAdapter` interface
- [ ] `ElevenLabsAdapter` - Environment variable config (`ELEVENLABS_API_KEY`)
- [ ] Voice ID mapping per personality
- [ ] Custom prompt → voice settings/style

### 5.4 TTS Cache Management
**Spec**: Section 4.3

- [ ] Cache directory: `/tts_cache/{reminder_id}/`
- [ ] Pre-generate all clips at reminder creation
- [ ] Fallback: system notification sound + text on failure
- [ ] Cache invalidation on reminder deletion

### 5.5 Test Voice System
**Spec**: Section 10.5

- [ ] TC-01: Coach personality at T-5 → motivational
- [ ] TC-02: No-nonsense at T-5 → brief, direct
- [ ] TC-03: Custom prompt tone
- [ ] TC-04: Personality immutability for existing reminders
- [ ] TC-05: Message variation (distinct phrasings)

---

## Priority 6: Expand HTTP API Endpoints

### 6.1 Missing Endpoints
**Current**: Basic CRUD + parse + voice

**Add:**
- [ ] `GET /reminders/{id}` - Get single reminder
- [ ] `DELETE /reminders/{id}` - Cascade delete anchors
- [ ] `PUT /reminders/{id}` - Update reminder
- [ ] `GET /anchors?reminder_id=X` - Get anchors for reminder
- [ ] `GET /anchors/next?reminder_id=X` - Get next unfired anchor
- [ ] `POST /anchors/snooze` - Snooze with duration
- [ ] `GET /stats/hit-rate?days=7` - Parameterized
- [ ] `GET /stats/streaks` - Streak counters
- [ ] `GET /stats/common-miss` - Common miss window
- [ ] `GET /adjustments?destination=X` - Destination adjustment
- [ ] `POST /preferences` - Set preference
- [ ] `GET /preferences/{key}` - Get preference

### 6.2 Session Management
**Priority**: Medium

- [ ] Connection pooling or thread-local sessions
- [ ] Foreign keys enabled per connection
- [ ] Handle concurrent requests

---

## Priority 7: Stats & Feedback Loop

### 7.1 Calculate Hit Rate
**Spec**: Section 11.1

Formula: `count(outcome='hit') / count(outcome!='pending') * 100` for trailing 7 days

### 7.2 Feedback Loop
**Spec**: Section 11.2

- [ ] On "Left too late" feedback: `adjustment_minutes += 2` for destination
- [ ] Cap adjustment at +15 minutes
- [ ] Apply adjustments when creating reminders for same destination

### 7.3 Common Miss Window
**Spec**: Section 11.3

- [ ] Identify most frequently missed urgency tier per destination
- [ ] Display: "You usually miss the T-5 warning"

### 7.4 Streak Counter
**Spec**: Section 11.4

- [ ] Increment on `outcome='hit'` for recurring reminders
- [ ] Reset to 0 on `outcome='miss'`

### 7.5 Test Stats
**Spec**: Section 11.5

- [ ] TC-01: Hit rate calculation (4 hits, 1 miss = 80%)
- [ ] TC-02: Feedback loop adjustment (+6 min after 3 late)
- [ ] TC-03: Adjustment cap (+15 min max)
- [ ] TC-04: Common miss window identification
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table only

---

## Priority 8: Background Scheduling (Future)

**Note**: Requires React Native app. Skip for backend-only phase.

### 8.1 Notifee Integration
**Spec**: Section 6

- [ ] Register anchors as Notifee tasks
- [ ] iOS: BGAppRefreshTask + BGProcessingTask
- [ ] Recovery scan on launch
- [ ] Re-register after crash

### 8.2 Notification Behavior
**Spec**: Section 5

- [ ] Tier escalation (gentle → beep → siren → alarm)
- [ ] DND awareness
- [ ] Quiet hours suppression
- [ ] Chain overlap serialization

### 8.3 Snooze & Dismissal
**Spec**: Section 9

- [ ] Tap snooze (1 min) + TTS confirmation
- [ ] Custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Swipe dismiss → feedback prompt

---

## Priority 9: External Integrations (Future)

### 9.1 Calendar Integration
**Spec**: Section 7

- [ ] `ICalendarAdapter` interface
- [ ] `AppleCalendarAdapter` (EventKit)
- [ ] `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Sync scheduler
- [ ] Suggestion cards

### 9.2 Location Awareness
**Spec**: Section 8

- [ ] Single location check at departure anchor
- [ ] 500m geofence radius
- [ ] Immediate escalation if at origin
- [ ] No continuous tracking

### 9.3 Sound Library
**Spec**: Section 12

- [ ] Built-in sounds (5 per category)
- [ ] Custom audio import (MP3, WAV, M4A)
- [ ] Corrupted file fallback

---

## Implementation Order

### Phase 1: Harness + Validation (This Week)
1. Create `harness/scenario_harness.py` - Core harness
2. Implement `ApiSequenceTrigger` and assertions
3. Test against existing scenarios
4. Commit and verify Otto integration

### Phase 2: Fix Core Backend (Week 1)
5. Fix chain engine tier logic
6. Add `get_next_unfired_anchor()` 
7. Complete database schema + migrations
8. Test all chain scenarios (TC-01 to TC-06)

### Phase 3: LLM + Voice (Week 2)
9. Implement `ILanguageModelAdapter` interface
10. Implement mock adapters for testing
11. Improve keyword fallback
12. Add message variations to voice personalities
13. Implement `ITTSAdapter` interface + mock

### Phase 4: API Expansion + Stats (Week 3)
14. Add missing HTTP endpoints
15. Implement stats calculations
16. Implement feedback loop
17. Test all stats scenarios

### Phase 5: Integration Testing (Week 4)
18. Full workflow tests (create → chain → fire → record → stats)
19. Stress test with concurrent requests
20. Performance optimization

### Phase 6: Mobile + Background (Future)
21. React Native project setup
22. Notifee integration
23. Calendar + Location
24. UI implementation

---

## Scenario Coverage

| Scenario | Spec Section | Status |
|----------|--------------|--------|
| `chain-full-30min.yaml` | 2, TC-01 | Needs fix |
| `chain-compressed-15min.yaml` | 2, TC-02 | Needs fix |
| `chain-minimum-3min.yaml` | 2, TC-03 | Needs fix |
| `chain-invalid-rejected.yaml` | 2, TC-04 | Needs fix |
| `parse-natural-language.yaml` | 3, TC-01 | Partial |
| `parse-simple-countdown.yaml` | 3, TC-02 | Partial |
| `parse-tomorrow.yaml` | 3, TC-03 | Partial |
| `voice-coach-personality.yaml` | 10, TC-01 | Working |
| `voice-no-nonsense.yaml` | 10, TC-02 | Working |
| `voice-all-personalities.yaml` | 10 | Working |
| `history-record-hit.yaml` | 11, TC-04 | Working |
| `history-record-miss-feedback.yaml` | 11, TC-05 | Working |
| `stats-hit-rate.yaml` | 11, TC-01 | Working |
| `reminder-creation-crud.yaml` | 13 | Partial |
| `reminder-creation-cascade-delete.yaml` | 13, TC-03 | Needs schema |

---

## Validation Commands

After implementation, run:

```bash
# Start server
python3 src/test_server.py &

# Run harness
sudo python3 harness/scenario_harness.py --project urgent-alarm

# Or with custom scenario dir
OTTO_SCENARIO_DIR=./scenarios python3 harness/scenario_harness.py --project urgent-alarm
```

---

## Notes

- **Chain engine bug**: Current implementation uses `drive_duration - X` for tier minutes, but spec says tiers are based on `minutes_before_arrival` relative to arrival time. Fixed version should compute anchors directly from departure time.

- **Scenario validation is hard gate**: Otto loop will not proceed if harness writes `{"pass": false}`. Must get harness passing first.

- **Database schema mismatches**: Current schema missing many columns from spec. Will need migration system.

- **No mobile yet**: Backend-only implementation for now. React Native is future work.