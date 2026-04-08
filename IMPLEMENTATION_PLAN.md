# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Last Updated:** 2026-04-08

**Current State:** Python test server (`src/test_server.py`) implements core engine ~35% of spec. Needs significant work on bugs, schema completeness, and adapter interfaces.

---

## Gap Analysis Summary

### Spec Coverage by Section

| Section | Topic | Implementation Status | Notes |
|---------|-------|----------------------|-------|
| §2 | Escalation Chain Engine | ⚠️ Partial | 8 anchors work, 3min buffer broken, validation incomplete |
| §3 | Reminder Parsing & Creation | ❌ Broken | Parser crashes on simple countdown, fails on multiple formats |
| §4 | Voice & TTS Generation | ⚠️ Partial | Templates exist, but only 1 per tier (need 3+), no TTS adapter |
| §5 | Notification & Alarm Behavior | ❌ Missing | Not implemented |
| §6 | Background Scheduling | ❌ Missing | Not implemented |
| §7 | Calendar Integration | ❌ Missing | Not implemented |
| §8 | Location Awareness | ❌ Missing | Not implemented |
| §9 | Snooze & Dismissal Flow | ❌ Missing | Snooze not implemented |
| §10 | Voice Personality System | ⚠️ Partial | 5 personalities, but no variations, no custom prompts |
| §11 | History, Stats & Feedback Loop | ⚠️ Partial | Hit rate works, streak/miss-window missing, feedback loop partial |
| §12 | Sound Library | ❌ Missing | Not implemented |
| §13 | Data Persistence | ⚠️ Partial | Schema incomplete, no migrations, no cascade delete |

---

## Critical Bugs (P0)

### Bug 1: Parser Crash on Simple Countdown
**Spec:** Section 3.5, TC-02  
**File:** `src/test_server.py`  
**Issue:** `"dryer in 3 min"` causes `IndexError: no such group`  
**Root Cause:** Line ~266 in `parse_reminder_natural`:
```python
minute = int(match.group(2)) if match.group(2) else 0
```
The regex `r'in\s+(\d+)\s*(?:minute|min)'` only has one capture group, but code tries to access `group(2)`.

**Fix Required:** Separate handling for relative time pattern with single capture group.

---

### Bug 2: Parser Fails Time Extraction Without "at"
**Spec:** Section 3.5, TC-01, TC-03  
**File:** `src/test_server.py`  
**Issue:** `"Parker Dr 9am, 30 min drive"` and `"meeting tomorrow 2pm, 20 min drive"` fail to parse time  
**Root Cause:** The regex `r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)'` requires "at" keyword.

**Fix Required:** Update regex patterns to handle:
- `"Xam"` / `"Xpm"` without "at"
- `"tomorrow Xpm"` with "tomorrow" prefix

---

### Bug 3: Chain Validation Incomplete
**Spec:** Section 2.3, TC-04, Req #8  
**File:** `src/test_server.py`  
**Issue:** `drive_duration=120, arrival=9am` should be rejected but isn't  
**Spec Requirement:** "arrival_time > departure_time + minimum_drive_time"

**Fix Required:** Add validation that departure_time > now in `validate_chain()`:
```python
departure_time = arrival_time - timedelta(minutes=drive_duration)
if departure_time <= datetime.now():
    return {'valid': False, 'error': 'departure_time_in_past'}
```

---

### Bug 4: 3-Minute Buffer Produces Wrong Anchor Count
**Spec:** Section 2.5, TC-03  
**File:** `src/test_server.py`  
**Issue:** 3min buffer produces 2 anchors instead of required 3  
**Spec TC-03:** "3 anchors are created: T-3 (firm), T-1 (critical), T-0 (alarm)"

**Current Output:** `[{'firm': T-2}, {'alarm': T-0}]`  
**Required Output:** `[{'firm': T-3}, {'critical': T-1}, {'alarm': T-0}]`

**Fix Required:** Update `compute_escalation_chain()` logic for buffer <= 5.

---

## Schema Completeness (P0)

### Missing Columns in `reminders` Table
| Column | Type | Notes |
|--------|------|-------|
| `origin_lat` | REAL | Location origin latitude |
| `origin_lng` | REAL | Location origin longitude |
| `origin_address` | TEXT | User-specified origin address |
| `custom_sound_path` | TEXT | Path to custom audio file |
| `calendar_event_id` | TEXT | Reference to calendar event if calendar-sourced |
| `reminder_type` | TEXT | Already exists, verify enum values |

### Missing Columns in `anchors` Table
| Column | Type | Notes |
|--------|------|-------|
| `tts_fallback` | BOOLEAN | True if TTS failed, using fallback |
| `snoozed_to` | TEXT | New timestamp if snoozed |

### Missing Columns in `history` Table
| Column | Type | Notes |
|--------|------|-------|
| `actual_arrival` | TEXT | Nullable, set when resolved |
| `missed_reason` | TEXT | background_task_killed, dnd_suppressed, user_dismissed |

### Missing Tables
- [ ] `user_preferences` needs `updated_at` column
- [ ] `destination_adjustments` needs `updated_at` column
- [ ] `calendar_sync` table (apple, google sync state)
- [ ] `custom_sounds` table (imported audio files)
- [ ] `schema_version` table (for migrations)

### Database Settings Missing
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`

---

## Missing HTTP Endpoints (P0)

| Endpoint | Method | Purpose | Spec Section |
|----------|--------|---------|-------------|
| `/reminders/{id}` | DELETE | Delete reminder + cascade anchors | §13, TC-03 |
| `/reminders/{id}/next-anchor` | GET | Get next unfired anchor for recovery | §2, Req #6 |
| `/anchors/{id}/snooze` | POST | Snooze anchor with duration | §9 |
| `/adjustments/{destination}` | GET | Get destination adjustment | §11 |

---

## Adapter Interfaces (P0)

### LLM Adapter Interface
**Spec:** Section 3.3  
**Purpose:** Mock-able natural language parsing adapter

**Required Files:**
- `src/lib/adapters/__init__.py`
- `src/lib/adapters/llm_adapter.py` — `ILanguageModelAdapter` abstract class

**Implementations:**
- `MockLLMAdapter` — returns predefined fixture responses
- `MiniMaxAdapter` — MiniMax API endpoint
- `AnthropicAdapter` — Anthropic API endpoint

**Environment:** `LLM_ADAPTER=minimax|anthropic|mock`

**Fallback:** Keyword extraction when LLM fails

---

### TTS Adapter Interface
**Spec:** Section 4.3  
**Purpose:** Mock-able text-to-speech adapter

**Required Files:**
- `src/lib/adapters/tts_adapter.py` — `ITTSAdapter` abstract class
- `src/lib/tts_cache.py` — cache management

**Implementations:**
- `MockTTSAdapter` — writes silent audio file
- `ElevenLabsAdapter` — ElevenLabs API

**Environment:** `TTS_ADAPTER=elevenlabs|mock`

**Cache Path:** `/tts_cache/{reminder_id}/{anchor_id}.mp3`

---

## Phase 1: Core Engine Fixes

### 1.1 Fix Parser Bug — Simple Countdown
- [ ] Separate relative time pattern handling (single capture group)
- [ ] Test: `"dryer in 3 min"` parses without crash
- [ ] Test: `reminder_type = "simple_countdown"`, `drive_duration = 0`

### 1.2 Fix Parser Bug — Time Without "at"
- [ ] Add regex patterns for: `Xam`, `Xpm`, `X:XXam`, `X:XXpm`
- [ ] Handle "tomorrow" prefix without "at"
- [ ] Test: `"Parker Dr 9am, 30 min drive"` parses correctly
- [ ] Test: `"meeting tomorrow 2pm, 20 min drive"` parses correctly

### 1.3 Fix Chain Validation
- [ ] Add `departure_time <= datetime.now()` check
- [ ] Test: `drive_duration=120, arrival=9am` returns 400

### 1.4 Fix 3-Minute Chain
- [ ] Update `compute_escalation_chain()` for buffer <= 5
- [ ] Test: 3 anchors for 3min buffer: T-3, T-1, T-0

---

## Phase 2: Database & Schema

### 2.1 Complete Database Schema
- [ ] Add missing `reminders` columns
- [ ] Add missing `anchors` columns
- [ ] Add missing `history` columns
- [ ] Add `user_preferences.updated_at`
- [ ] Add `destination_adjustments.updated_at`
- [ ] Create `calendar_sync` table
- [ ] Create `custom_sounds` table
- [ ] Create `schema_version` table

### 2.2 Enable Foreign Keys & WAL
- [ ] Add `PRAGMA foreign_keys = ON` in `init_db()`
- [ ] Add `PRAGMA journal_mode = WAL`

### 2.3 Add DELETE Endpoint
- [ ] Add `DELETE /reminders/{id}`
- [ ] Test cascade delete: deleting reminder deletes anchors

### 2.4 Add Next-Anchor Endpoint
- [ ] Add `GET /reminders/{id}/next-anchor`
- [ ] Return earliest unfired anchor
- [ ] Handle: all fired → return null

---

## Phase 3: Voice & Message System

### 3.1 Expand Message Variations
**Spec:** Section 10.3, TC-05  
**Requirement:** Minimum 3 message variations per tier per personality

**Current:** 1 template per tier  
**Required:** 3+ templates per tier

**Tasks:**
- [ ] Expand `VOICE_PERSONALITIES` dict with 3 variations per tier
- [ ] Add random or round-robin selection logic
- [ ] Test: 3 calls → at least 2 distinct messages

### 3.2 Custom Voice Prompts
**Spec:** Section 10.3, Req #3  
**Requirement:** Custom mode accepts user-written prompt (max 200 chars)

**Tasks:**
- [ ] Add "custom" personality mode
- [ ] Append custom prompt to message generation system prompt
- [ ] Test: Custom prompt modifies message tone

---

## Phase 4: Snooze & Dismissal

### 4.1 Snooze Chain Recomputation
**Spec:** Section 9.3, TC-03  
**Requirement:** After snooze, shift remaining anchors by snooze duration

**Tasks:**
- [ ] Add `POST /anchors/{id}/snooze` endpoint
- [ ] Compute new timestamps for unfired anchors
- [ ] Update anchor records with `snoozed_to`
- [ ] Return TTS confirmation text

**Example:** Snooze at 8:45 with 3-min → 8:48, 8:53, 8:59, 9:00

### 4.2 Snooze Duration Picker
**Spec:** Section 9.3, Req #2  
**Options:** 1, 3, 5, 10, 15 minutes

### 4.3 Dismissal Feedback
**Spec:** Section 9.4  
**Requirement:** Feedback prompt on dismissal

**Tasks:**
- [ ] Add `feedback_type` options: timing_right, left_too_early, left_too_late, other
- [ ] Store feedback in history
- [ ] Return adjustment applied via TTS

---

## Phase 5: Stats & Feedback Loop

### 5.1 Streak Counter
**Spec:** Section 11.3, Req #4  
**Requirement:** Increment on hit, reset on miss for recurring reminders

**Tasks:**
- [ ] Add `streak_count` to reminder or compute from history
- [ ] Increment on outcome='hit' for recurring
- [ ] Reset on outcome='miss'

### 5.2 Common Miss Window
**Spec:** Section 11.3, Req #3  
**Requirement:** Identify most frequently missed urgency tier

**Tasks:**
- [ ] Query history for missed anchors by tier
- [ ] Return most common missed tier

### 5.3 Feedback Loop Adjustment
**Spec:** Section 11.3, Req #2  
**Requirement:** `adjusted_drive_duration = stored + (late_count * 2)`, capped at +15

**Tasks:**
- [ ] Apply adjustment on reminder creation for known destinations
- [ ] Add `GET /adjustments/{destination}` endpoint
- [ ] Add `GET /adjustments/{destination}` PUT endpoint for updates

---

## Phase 6: Notification & Alarm Behavior

### 6.1 Notification Tiers
**Spec:** Section 5.3, Req #1  
**Tiers:** gentle chime → pointed beep → urgent siren → looping alarm

### 6.2 DND Awareness
**Spec:** Section 5.3, Req #2  
**Behavior:**
- Early anchors during DND: silent notification
- Final 5 minutes during DND: visual override + vibration

### 6.3 Quiet Hours
**Spec:** Section 5.3, Req #3  
**Default:** 10pm–7am  
**Behavior:** Suppress nudges, queue for post-quiet-hours

### 6.4 Overdue Anchor Drop
**Spec:** Section 5.3, Req #5  
**Rule:** Drop anchors >15 minutes overdue

### 6.5 Chain Overlap Serialization
**Spec:** Section 5.3, Req #6  
**Behavior:** Queue new anchors if chain is mid-escalation

### 6.6 T-0 Alarm Loop
**Spec:** Section 5.3, Req #7  
**Behavior:** Loop until user dismisses or snoozes

---

## Phase 7: Background Scheduling

### 7.1 Recovery Scan Logic
**Spec:** Section 6.3, Req #3  
**Behavior:** On app launch, fire overdue unfired anchors within 15-min grace window

### 7.2 Pending Anchors Re-registration
**Spec:** Section 6.3, Req #7  
**Behavior:** Re-register unfired anchors on crash recovery

### 7.3 Late Fire Warning
**Spec:** Section 6.3, Req #8  
**Rule:** Log warning if anchor fires >60 seconds after scheduled time

---

## Phase 8: Calendar Integration

### 8.1 Calendar Adapter Interface
**Spec:** Section 7.3  
**Interface:** `ICalendarAdapter`

**Implementations:**
- `AppleCalendarAdapter` — EventKit
- `GoogleCalendarAdapter` — Google Calendar API

### 8.2 Calendar Sync Logic
**Spec:** Section 7.3, Req #3  
**Schedule:** On launch, every 15 minutes, via background refresh

### 8.3 Event Suggestion Cards
**Spec:** Section 7.3, Req #4  
**Rule:** Only events with non-empty `location` field

---

## Phase 9: Location Awareness

### 9.1 Single Location Check
**Spec:** Section 8.3, Req #1, #3  
**Trigger:** At departure anchor only  
**API:** CoreLocation / FusedLocationProvider (single call)

### 9.2 Geofence Comparison
**Spec:** Section 8.3, Req #4  
**Rule:** Within 500m = "at origin"

### 9.3 Immediate Escalation
**Spec:** Section 8.3, Req #5  
**Behavior:** Fire firm/critical anchor if still at origin

---

## Phase 10: Sound Library

### 10.1 Built-in Sounds
**Spec:** Section 12.3, Req #1  
**Categories:** Commute (5), Routine (5), Errand (5), Custom

### 10.2 Custom Import
**Spec:** Section 12.3, Req #3  
**Formats:** MP3, WAV, M4A, max 30 seconds

### 10.3 Corrupted Sound Fallback
**Spec:** Section 12.3, Req #8  
**Behavior:** Fall back to category default, surface error

---

## Scenario Coverage Matrix

| Scenario File | Test | Current Status | Required Fix |
|---------------|------|----------------|--------------|
| `chain-full-30min.yaml` | TC-01 | ✅ PASS | None |
| `chain-compressed-15min.yaml` | TC-02 | ⚠️ Partial | Verify anchor count |
| `chain-minimum-3min.yaml` | TC-03 | ❌ FAIL | Bug 4: Wrong anchor count |
| `chain-invalid-rejected.yaml` | TC-04 | ❌ FAIL | Bug 3: Validation incomplete |
| `parse-natural-language.yaml` | TC-01 | ⚠️ Partial | Verify parsing |
| `parse-simple-countdown.yaml` | TC-02 | ❌ FAIL | Bug 1: Parser crash |
| `parse-tomorrow.yaml` | TC-03 | ❌ FAIL | Bug 2: Time not parsed |
| `voice-coach-personality.yaml` | TC-01 | ✅ PASS | None |
| `voice-no-nonsense.yaml` | TC-02 | ✅ PASS | None |
| `voice-all-personalities.yaml` | TC-05 | ⚠️ Partial | Need 3+ variations |
| `history-record-outcome.yaml` | - | ✅ PASS | None |
| `history-record-miss-feedback.yaml` | TC-05 | ⚠️ Partial | Need adjustment applied |
| `stats-hit-rate.yaml` | TC-01 | ✅ PASS | None |
| `reminder-creation-cascade-delete.yaml` | TC-03 | ❌ FAIL | Missing DELETE endpoint |

---

## Task Prioritization

### Priority 0 (Critical — Blocking Tests)

| # | Task | Dependencies | Files |
|---|------|--------------|-------|
| P0-1 | Fix parser crash (simple countdown) | None | `src/test_server.py` |
| P0-2 | Fix parser time extraction (no "at") | None | `src/test_server.py` |
| P0-3 | Fix chain validation (departure in past) | None | `src/test_server.py` |
| P0-4 | Fix 3-minute chain (3 anchors) | None | `src/test_server.py` |
| P0-5 | Complete database schema | None | `src/test_server.py` |
| P0-6 | Add DELETE endpoint (cascade) | Schema | `src/test_server.py` |
| P0-7 | Enable foreign keys | Schema | `src/test_server.py` |

### Priority 1 (High — Core Features)

| # | Task | Dependencies | Files |
|---|------|--------------|-------|
| P1-1 | Add `get_next_unfired_anchor` endpoint | Schema | `src/test_server.py` |
| P1-2 | Expand message variations (3+ per tier) | None | `src/test_server.py` |
| P1-3 | Add snooze endpoint + recomputation | Schema, P0-5 | `src/test_server.py` |
| P1-4 | Add dismissal feedback | Schema, P0-5 | `src/test_server.py` |
| P1-5 | Implement streak counter | History | `src/test_server.py` |
| P1-6 | Implement common miss window | History | `src/test_server.py` |
| P1-7 | Implement feedback loop adjustment | Schema | `src/test_server.py` |

### Priority 2 (Medium — Integrations)

| # | Task | Dependencies | Files |
|---|------|--------------|-------|
| P2-1 | LLM adapter interface | None | `src/lib/adapters/llm_adapter.py` |
| P2-2 | TTS adapter interface | None | `src/lib/adapters/tts_adapter.py` |
| P2-3 | Calendar adapter interface | P2-1 | `src/lib/adapters/calendar_adapter.py` |
| P2-4 | Location awareness | P0-5 | `src/lib/location.py` |
| P2-5 | Notification behavior | P2-1 | `src/lib/notifications.py` |
| P2-6 | Background scheduling | P0-5, P2-5 | `src/lib/scheduler.py` |
| P2-7 | Sound library | P0-5 | `src/lib/sound_library.py` |

### Priority 3 (Lower — Nice to Have)

| # | Task | Dependencies | Files |
|---|------|--------------|-------|
| P3-1 | Custom voice prompts | P2-1 | `src/lib/adapters/llm_adapter.py` |
| P3-2 | Quiet hours | P0-5 | `src/lib/notifications.py` |
| P3-3 | Chain overlap queue | P1-3 | `src/lib/notifications.py` |
| P3-4 | 90-day data retention | History | `src/lib/stats.py` |

---

## Validation Commands

After implementing fixes, run:

```bash
# Syntax check
python3 -m py_compile src/test_server.py

# Start server
python3 src/test_server.py &
sleep 1

# Test chain 30min (should pass)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Test","arrival_time":"2026-04-09T09:00:00","drive_duration":30}' | jq

# Test chain 3min (should pass with 3 anchors)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Quick","arrival_time":"2026-04-09T09:00:00","drive_duration":3}' | jq

# Test chain validation (should return 400)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Test","arrival_time":"2026-04-09T09:00:00","drive_duration":120}' | jq

# Test parser (should not crash)
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"dryer in 3 min"}' | jq

# Test parser tomorrow (should parse time)
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"meeting tomorrow 2pm, 20 min drive"}' | jq

# Test cascade delete
REMINDER_ID=$(curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Cascade Test","arrival_time":"2026-04-10T15:00:00","drive_duration":30}' | jq -r '.id')
curl -s -X DELETE http://localhost:8090/reminders/$REMINDER_ID | jq
```

---

## Definition of Done

Every task must have:
1. ✅ Implementation matching acceptance criteria in spec
2. ✅ Corresponding scenario passing
3. ✅ No regressions in existing tests
4. ✅ Code compiles without errors

---

## Files to Create/Modify

### New Files
```
src/lib/
src/lib/__init__.py
src/lib/adapters/
src/lib/adapters/__init__.py
src/lib/adapters/llm_adapter.py
src/lib/adapters/tts_adapter.py
src/lib/adapters/calendar_adapter.py
src/lib/tts_cache.py
src/lib/location.py
src/lib/notifications.py
src/lib/scheduler.py
src/lib/sound_library.py
src/lib/stats.py
src/lib/feedback_loop.py
src/lib/dismissal.py
```

### Modified Files
```
src/test_server.py  (multiple changes)
```

---

*Last generated: 2026-04-08*
