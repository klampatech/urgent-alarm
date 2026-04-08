# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Last Updated:** 2026-04-08

**Current State:** Python test server (`src/test_server.py`) implements ~30% of spec.

### ✅ Implemented
- Basic escalation chain engine (`compute_escalation_chain`) — working correctly for 30min (8 anchors)
- Keyword-based natural language parser (`parse_reminder_natural`) — partial, has bugs
- 5 voice personality message templates (`generate_voice_message`) — all 5 personalities
- Basic SQLite schema (4 tables: reminders, anchors, history, destination_adjustments)
- Hit rate calculation (`calculate_hit_rate`)
- HTTP API endpoints for testing

### ❌ Bugs / Issues Found
1. **Parser crash:** `"dryer in 3 min"` causes `IndexError: no such group`
2. **Parser partial failure:** `"meeting tomorrow 2pm, 20 min drive"` fails to parse time (arrival_time=None)
3. **Parser partial failure:** `"Parker Dr 9am, 30 min drive"` fails to parse time (arrival_time=None)
4. **Validation incomplete:** `validate_chain` doesn't reject `drive_duration > time_to_arrival` (spec TC-04)
5. **Anchor ordering issue:** For 15min buffer, critical (T-1) appears before alarm (T-0) in sorted output (though functionally okay)
6. **Missing DELETE endpoint:** No `/reminders/{id}` or `/reminders/{id}/anchors` endpoint for cascade delete test
7. **Missing origin columns:** Schema lacks `origin_lat`, `origin_lng`, `origin_address` columns
8. **Missing `snoozed_to` column:** Anchors don't have snooze timestamp tracking
9. **Missing schema versioning:** No migration system or schema_version table

---

## Gap Analysis

### Implemented Components

| Component | Status | Spec Section | Notes |
|-----------|--------|--------------|-------|
| Chain engine basic | ✅ Working | §2 | 30min buffer: 8 anchors correct |
| Chain 15min | ⚠️ Buggy | §2 | 5 anchors but order issue (minor) |
| Chain 3min | ⚠️ Buggy | §2 | 2 anchors instead of 3 |
| Chain validation | ❌ Missing | §2 | Doesn't reject drive > arrival |
| Keyword parser | ⚠️ Partial | §3 | Crashes on simple countdown |
| 5 voice personalities | ✅ Working | §10 | All templates exist |
| SQLite schema basic | ⚠️ Partial | §13 | Missing columns |
| Hit rate | ✅ Working | §11 | Correct calculation |
| History record | ✅ Working | §11 | Partial |
| Feedback loop | ⚠️ Partial | §11 | Records but not applied |
| Cascade delete | ❌ Missing | §13 | No DELETE endpoint |

### Missing Components (Full Spec)

| Component | Priority | Spec Section |
|-----------|----------|--------------|
| Database schema full alignment | P0 | §13 |
| LLM adapter interface | P0 | §3 |
| TTS adapter interface | P0 | §4 |
| Fix parser bugs | P0 | §3 |
| Fix chain validation | P0 | §2 |
| DELETE endpoint + cascade | P0 | §13 |
| `get_next_unfired_anchor` | P1 | §2 |
| Snooze chain recomputation | P1 | §9 |
| Message variations (3+ per tier) | P1 | §10 |
| Notification/alarm behavior | P1 | §5 |
| Background scheduling (Notifee) | P2 | §6 |
| Calendar integration | P2 | §7 |
| Location awareness | P2 | §8 |
| Sound library | P2 | §12 |
| Streak counter | P2 | §11 |
| Common miss window | P2 | §11 |
| Quiet hours / DND | P2 | §5 |
| Chain overlap queue | P2 | §5 |

---

## Phase 1: Critical Fixes (P0)

### 1.1 Fix Parser Bug
**Spec:** Section 3.5, TC-02

**Issue:** `"dryer in 3 min"` causes IndexError.

**Root Cause:** Line 266 in `parse_reminder_natural`:
```python
minute = int(match.group(2)) if match.group(2) else 0
```
The regex `r'in\s+(\d+)\s*(?:minute|min)'` only has one capture group, but code tries to access `group(2)`.

**Fix:**
```python
# For relative time "in X minutes", use the first group
minutes = int(match.group(1))
```

**Files:** `src/test_server.py`

---

### 1.2 Fix Time Parsing for Shortened Input
**Spec:** Section 3.5, TC-01, TC-03

**Issue:** `"Parker Dr 9am, 30 min drive"` and `"meeting tomorrow 2pm, 20 min drive"` fail to parse time.

**Root Cause:** The regex `r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)'` requires "at" keyword. These inputs don't have "at".

**Fix:** Update regex patterns to handle:
- `"Xam"` / `"Xpm"` without "at"
- `"tomorrow Xpm"` with "tomorrow" prefix

**Files:** `src/test_server.py`

---

### 1.3 Fix Chain Validation
**Spec:** Section 2.3, TC-04

**Issue:** `drive_duration=120, arrival=9am` should be rejected but isn't.

**Spec Requirement:** "arrival_time > departure_time + minimum_drive_time" validation.

**Fix:** Add validation in `validate_chain`:
```python
# departure_time must be in the future
departure_time = arrival_time - timedelta(minutes=drive_duration)
if departure_time <= datetime.now():
    return {'valid': False, 'error': 'departure_time_in_past'}

# Actually, the spec says: arrival_time > departure_time + minimum_drive_time
# This is tautological since minimum_drive_time >= 0
# The real check: departure_time > now (not arrival)
```

Wait, re-reading TC-04: "Given arrival_time = 9:00 AM and drive_duration = 120 minutes"
- Departure would be 7:00 AM (in the past!)
- So `departure_time <= now` should reject it.

**Files:** `src/test_server.py`

---

### 1.4 Add DELETE Endpoint for Cascade Delete
**Spec:** Section 13.5, TC-03

**Issue:** No way to delete reminders to test cascade.

**Tasks:**
- [ ] Add `DELETE /reminders/{id}` endpoint
- [ ] Enable `PRAGMA foreign_keys = ON` in `init_db()`
- [ ] Verify cascade delete works

**Files:** `src/test_server.py`

---

### 1.5 Complete Database Schema
**Spec:** Section 13.2

**Current Missing Columns:**
- [ ] `reminders`: origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id
- [ ] `anchors`: tts_fallback, snoozed_to
- [ ] `history`: actual_arrival, missed_reason
- [ ] `user_preferences`: updated_at
- [ ] `destination_adjustments`: updated_at
- [ ] Add `calendar_sync` table
- [ ] Add `custom_sounds` table
- [ ] Add `schema_version` table

**Files:** `src/test_server.py`

---

## Phase 2: Core Engine Enhancements (P1)

### 2.1 Chain Engine Full Spec Compliance
**Spec:** Section 2.3, TC-03

**Issue:** 3min buffer produces 2 anchors instead of 3.

**Spec TC-03:** "3 anchors are created: T-3 (firm), T-1 (critical), T-0 (alarm)"

**Current:** `[{'firm': T-2}, {'alarm': T-0}]`

**Fix:** For buffer <= 5, include T-1 (critical) before alarm.

**Files:** `src/test_server.py`

---

### 2.2 Add `get_next_unfired_anchor`
**Spec:** Section 2.3, Req #6

**Tasks:**
- [ ] Add `GET /reminders/{id}/next-anchor` endpoint
- [ ] Return earliest unfired anchor for scheduler recovery

**Files:** `src/test_server.py`

---

### 2.3 Add `get_next_unfired_anchor`
**Spec:** Section 2.3, Req #6

**Tasks:**
- [ ] Add `GET /reminders/{id}/next-anchor` endpoint
- [ ] Return earliest unfired anchor for scheduler recovery
- [ ] Handle case where all anchors fired (return null)

**Files:** `src/test_server.py`

---

### 2.4 Snooze Chain Recomputation
**Spec:** Section 9.3, TC-03

**Spec Requirement:** After snooze, shift remaining anchors by snooze duration.

**Example:** Snooze at 8:45 with 3-min snooze → remaining anchors: 8:48, 8:53, 8:59, 9:00

**Tasks:**
- [ ] Add `POST /anchors/{id}/snooze` with duration parameter
- [ ] Compute new timestamps for all unfired anchors
- [ ] Update anchor records with `snoozed_to`
- [ ] TTS confirmation: "Okay, snoozed 3 minutes"

**Files:** `src/test_server.py`, `src/lib/snooze.py`

---

### 2.5 Voice Personality Message Variations
**Spec:** Section 10.3, TC-05

**Spec Requirement:** Minimum 3 message variations per tier per personality.

**Tasks:**
- [ ] Expand each personality's templates to 3+ variations
- [ ] Add random or round-robin selection
- [ ] Test: 3 calls → at least 2 distinct messages

**Files:** `src/test_server.py`, `tests/test_voice.py`

---

## Phase 3: Adapter Interfaces (P0)

### 3.1 LLM Adapter Interface
**Spec:** Section 3.3

**Tasks:**
- [ ] Create `src/lib/adapters/llm_adapter.py`
- [ ] Define `ILanguageModelAdapter` abstract class
- [ ] Implement `MockLLMAdapter` for testing
- [ ] Implement `MiniMaxAdapter`
- [ ] Implement `AnthropicAdapter`
- [ ] Environment variable: `LLM_ADAPTER=minimax|anthropic|mock`
- [ ] Integrate with fallback to keyword extraction

**Files:** `src/lib/adapters/llm_adapter.py`

---

### 3.2 TTS Adapter Interface
**Spec:** Section 4.3

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py`
- [ ] Define `ITTSAdapter` abstract class
- [ ] Implement `MockTTSAdapter`
- [ ] Implement `ElevenLabsAdapter`
- [ ] Create `src/lib/tts_cache.py`
- [ ] Environment variable: `TTS_ADAPTER=elevenlabs|mock`
- [ ] Fallback: mark `tts_fallback=true`

**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/tts_cache.py`

---

## Phase 4: User Interaction (P1)

### 4.1 Notification & Alarm Behavior
**Spec:** Section 5.3

**Tasks:**
- [ ] 4-tier notification sounds
- [ ] DND awareness
- [ ] Quiet hours (default 10pm–7am)
- [ ] Queue overdue anchors, drop if >15min
- [ ] Chain overlap serialization
- [ ] T-0 alarm loop

**Files:** `src/lib/notifications.py`

---

### 4.2 Dismissal Feedback
**Spec:** Section 9.3

**Tasks:**
- [ ] Add `feedback_type` options: timing_right, left_too_early, left_too_late, other
- [ ] Apply adjustments on reminder creation
- [ ] TTS: "You missed {destination} — was timing right?"

**Files:** `src/lib/dismissal.py`

---

## Phase 5: System Integration (P2)

### 5.1 Background Scheduling
**Spec:** Section 6.3

**Note:** Requires React Native; prepare Python layer.

**Tasks:**
- [ ] Document Notifee API surface
- [ ] Implement recovery scan logic

**Files:** `src/lib/scheduler.py`

---

### 5.2 Calendar Integration
**Spec:** Section 7.3

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py`
- [ ] Define `ICalendarAdapter` interface
- [ ] Document EventKit/Google Calendar API surface

**Files:** `src/lib/adapters/calendar_adapter.py`

---

### 5.3 Location Awareness
**Spec:** Section 8.3

**Tasks:**
- [ ] Create `src/lib/location.py`
- [ ] 500m geofence comparison
- [ ] Fire firm/critical if at origin

**Files:** `src/lib/location.py`

---

## Phase 6: Analytics (P2)

### 6.1 Stats Enhancement
**Spec:** Section 11.3

**Tasks:**
- [ ] Implement streak counter
- [ ] Implement common miss window
- [ ] 90-day retention

**Files:** `src/lib/stats.py`

---

### 6.2 Feedback Loop
**Spec:** Section 11.3

**Tasks:**
- [ ] Apply `adjustment_minutes` on reminder creation
- [ ] Cap at +15 minutes
- [ ] Add `GET /adjustments/{destination}` endpoint

**Files:** `src/lib/feedback_loop.py`

---

## Phase 7: Sound Library (P2)

### 7.1 Sound Library
**Spec:** Section 12.3

**Tasks:**
- [ ] Create `src/lib/sound_library.py`
- [ ] Bundle 5 built-in sounds per category
- [ ] Custom import (MP3, WAV, M4A, max 30s)
- [ ] Corrupted file fallback

**Files:** `src/lib/sound_library.py`

---

## Scenario Coverage

| Scenario | Component | Status |
|----------|-----------|--------|
| chain-full-30min | Chain engine | ✅ PASS |
| chain-compressed-15min | Chain engine | ⚠️ Partial (no anchor count check) |
| chain-minimum-3min | Chain engine | ❌ FAIL (2 anchors not 3) |
| chain-invalid-rejected | Validation | ❌ FAIL (not rejected) |
| parse-natural-language | Parser | ✅ PASS |
| parse-simple-countdown | Parser | ❌ FAIL (crash) |
| parse-tomorrow | Parser | ⚠️ Partial (time not parsed) |
| voice-coach-personality | Voice | ✅ PASS |
| voice-no-nonsense | Voice | ✅ PASS |
| voice-all-personalities | Voice | ✅ PASS |
| stats-hit-rate | Stats | ✅ PASS |
| history-record-outcome | History | ✅ PASS |
| history-record-miss-feedback | Feedback | ⚠️ Partial |
| reminder-creation-crud | Database | ✅ PASS |
| reminder-creation-cascade-delete | Cascade | ❌ FAIL (no DELETE) |

---

## Task Prioritization Summary

| Priority | Task | Dependencies | Spec Section |
|----------|------|--------------|--------------|
| P0 | Fix parser crash | None | §3 |
| P0 | Fix time parsing | None | §3 |
| P0 | Fix chain validation | None | §2 |
| P0 | Add DELETE endpoint | None | §13 |
| P0 | Complete database schema | None | §13 |
| P0 | LLM adapter interface | None | §3 |
| P0 | TTS adapter interface | None | §4 |
| P1 | Fix 3min chain (3 anchors) | None | §2 |
| P1 | get_next_unfired_anchor | None | §2 |
| P1 | Snooze chain recompute | None | §9 |
| P1 | Message variations (3+) | None | §10 |
| P1 | Notification behavior | None | §5 |
| P1 | Dismissal feedback | None | §9 |
| P2 | Background scheduling | Database | §6 |
| P2 | Calendar integration | Database | §7 |
| P2 | Location awareness | Database | §8 |
| P2 | Sound library | Database | §12 |
| P2 | Streak counter | Database | §11 |
| P2 | Common miss window | Database | §11 |
| P2 | Quiet hours/DND | None | §5 |
| P2 | Chain overlap queue | None | §5 |

---

## Validation Commands

After implementing fixes, run:

```bash
# Start server
python3 src/test_server.py &

# Test chain 30min
curl -X POST http://localhost:8090/reminders -d '{"destination":"Test","arrival_time":"2026-04-09T09:00:00","drive_duration":30}' -H "Content-Type: application/json"

# Test parser (should not crash)
curl -X POST http://localhost:8090/parse -d '{"text":"dryer in 3 min"}' -H "Content-Type: application/json"

# Test validation (should return 400)
curl -X POST http://localhost:8090/reminders -d '{"destination":"Test","arrival_time":"2026-04-09T09:00:00","drive_duration":120}' -H "Content-Type: application/json"

# Test cascade delete (need DELETE endpoint)
curl -X DELETE http://localhost:8090/reminders/{id}

# Validation
python3 -m py_compile src/test_server.py
```

---

## Definition of Done

Every task must have:
1. Implementation matching acceptance criteria in spec
2. Corresponding scenario passing
3. No regressions in existing tests
