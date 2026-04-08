# Urgent Alarm - Implementation Plan

## Executive Summary

This document maps the specification (`specs/*.md`) to the current codebase and identifies gaps requiring implementation.

**Status:** Partial implementation exists in `src/test_server.py`. Core chain engine and parser are working but have bugs. Major features (notifications, background scheduling, calendar, location) are not implemented.

---

## Gap Analysis

### ✅ Working Components

| Component | File | Notes |
|-----------|------|-------|
| Chain engine (partial) | `src/test_server.py:compute_escalation_chain()` | Logic mostly correct, has bugs |
| Keyword parser (partial) | `src/test_server.py:parse_reminder_natural()` | Has bugs with "in X min" |
| Voice messages | `src/test_server.py:VOICE_PERSONALITIES` | 5 personalities, single template each |
| Database schema (partial) | `src/test_server.py:init_db()` | Missing columns per spec |
| Hit rate calc | `src/test_server.py:calculate_hit_rate()` | Works correctly |

### ❌ Critical Bugs (Must Fix First)

| ID | Bug | Impact | Fix |
|----|-----|--------|-----|
| B1 | Anchors not sorted by timestamp | Chain fires wrong order | Sort before return |
| B2 | 3min buffer produces 2 anchors | Missing critical tier | Fix tier calculation logic |
| B3 | No validation for drive > arrival | Invalid data persists | Add `drive_duration > time_to_arrival` check |
| B4 | Regex crash on "in X min" | Parser crashes | Fix optional group handling |
| B5 | reminder_type not set for countdown | Wrong type classification | Set type when "in X min" detected |

### ❌ Missing Schema (Per Spec Section 13)

| Table | Missing Columns |
|-------|-----------------|
| `reminders` | `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id` |
| `anchors` | `tts_fallback`, `snoozed_to` |
| `history` | `actual_arrival`, `missed_reason` |
| `user_preferences` | `updated_at` |
| `destination_adjustments` | `updated_at` |
| *(new)* | `custom_sounds` table |
| *(new)* | `calendar_sync` table |
| *(new)* | `schema_version` table |

### ❌ Missing Interfaces & Adapters (Per Spec Sections)

| ID | Interface | Spec Section | Purpose |
|----|-----------|--------------|---------|
| I1 | `ILanguageModelAdapter` | 3.3 | LLM parsing with mock for tests |
| I2 | `ITTSAdapter` | 4.3 | TTS generation with mock for tests |
| I3 | `ICalendarAdapter` | 7.3 | Calendar sync with mock |

### ❌ Missing Features by Priority

#### P1 - Core Chain & Parsing (Section 2, 3)
- [ ] `get_next_unfired_anchor(reminder_id)` function
- [ ] Chain determinism verification (same inputs = same output)
- [ ] Keyword extraction as LLM fallback
- [ ] LLM adapter (MiniMax/Anthropic) integration

#### P2 - Voice & TTS (Section 4, 10)
- [ ] TTS cache system (`/tts_cache/{reminder_id}/{anchor_id}.mp3`)
- [ ] ElevenLabs adapter integration
- [ ] Message variations (3+ per tier per personality)
- [ ] Custom voice prompt support (max 200 chars)

#### P3 - Notifications & Alarms (Section 5)
- [ ] Sound tier escalation (gentle → beep → siren → alarm)
- [ ] DND handling (silent early, visual+vibration final 5min)
- [ ] Quiet hours suppression (10pm-7am configurable)
- [ ] Chain overlap serialization
- [ ] T-0 looping alarm until user action

#### P4 - Background Scheduling (Section 6)
- [ ] Notifee-style anchor scheduling
- [ ] Recovery scan on app launch (within 15-min grace)
- [ ] Late fire warning (>60s delay logged)

#### P5 - Snooze & Dismissal (Section 9)
- [ ] Tap snooze (1 min)
- [ ] Custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Feedback prompt on dismiss
- [ ] Snooze persistence after restart

#### P6 - Location Awareness (Section 8)
- [ ] Origin storage at creation
- [ ] Single location check at departure
- [ ] 500m geofence comparison
- [ ] Immediate escalation if at origin

#### P7 - Calendar Integration (Section 7)
- [ ] Apple Calendar adapter (EventKit)
- [ ] Google Calendar adapter
- [ ] Sync scheduling (every 15 min)
- [ ] Suggestion cards for events with locations

#### P8 - Sound Library (Section 12)
- [ ] Built-in sounds (5 per category)
- [ ] Custom audio import (MP3, WAV, M4A, max 30s)
- [ ] Per-reminder sound selection
- [ ] Corrupted file fallback

#### P9 - Stats & History (Section 11)
- [ ] Common miss window calculation
- [ ] Streak counter for recurring reminders
- [ ] 90-day data retention/archive
- [ ] Adjustment cap (+15 min max)

---

## Prioritized Implementation Tasks

### Phase 1: Bug Fixes (Day 1)
**Prerequisite:** None

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Sort anchors by timestamp in `compute_escalation_chain()` | `src/test_server.py` |
| 1.2 | Fix 3min buffer: add critical tier (T-1) | `src/test_server.py` |
| 1.3 | Add validation: `drive_duration > time_to_arrival` → 400 error | `src/test_server.py` |
| 1.4 | Fix regex crash on "in X min" pattern | `src/test_server.py` |
| 1.5 | Set `reminder_type = "simple_countdown"` when "in X min" detected | `src/test_server.py` |

**Validation:**
```bash
python3 -m pytest harness/  # Run scenario tests
python3 -m py_compile src/test_server.py  # Syntax check
```

---

### Phase 2: Schema & Core Functions (Day 2)
**Prerequisite:** Phase 1 complete

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Add missing columns to existing tables | `src/test_server.py` |
| 2.2 | Create `custom_sounds`, `calendar_sync`, `schema_version` tables | `src/test_server.py` |
| 2.3 | Implement `get_next_unfired_anchor(reminder_id)` | `src/test_server.py` |
| 2.4 | Add `ILanguageModelAdapter` interface + mock | `src/test_server.py` |
| 2.5 | Add `ITTSAdapter` interface + mock | `src/test_server.py` |

---

### Phase 3: Voice System (Day 3)
**Prerequisite:** Phase 2 complete

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Add 3+ message variations per tier per personality | `src/test_server.py` |
| 3.2 | Implement `generate_voice_message()` rotation | `src/test_server.py` |
| 3.3 | Add custom voice prompt support | `src/test_server.py` |
| 3.4 | Implement TTS cache directory structure | `src/test_server.py` |

---

### Phase 4: Snooze & Dismissal (Day 4)
**Prerequisite:** Phase 2 complete

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Implement `POST /snooze` endpoint | `src/test_server.py` |
| 4.2 | Implement chain re-computation after snooze | `src/test_server.py` |
| 4.3 | Add feedback prompt endpoints | `src/test_server.py` |
| 4.4 | Implement feedback loop (adjust drive_duration) | `src/test_server.py` |

---

### Phase 5: Stats & History (Day 5)
**Prerequisite:** Phase 4 complete

| Task | Description | Files |
|------|-------------|-------|
| 5.1 | Implement common miss window calculation | `src/test_server.py` |
| 5.2 | Add streak counter for recurring reminders | `src/test_server.py` |
| 5.3 | Implement adjustment cap (+15 min max) | `src/test_server.py` |
| 5.4 | Add `GET /stats/streak` endpoint | `src/test_server.py` |

---

### Phase 6: Notifications & Scheduling (Day 6-7)
**Prerequisite:** Phase 3 complete

| Task | Description | Files |
|------|-------------|-------|
| 6.1 | Implement notification tier escalation | `src/test_server.py` |
| 6.2 | Add DND handling simulation | `src/test_server.py` |
| 6.3 | Add quiet hours logic | `src/test_server.py` |
| 6.4 | Implement chain overlap serialization | `src/test_server.py` |
| 6.5 | Implement recovery scan on launch | `src/test_server.py` |

---

### Phase 7: Integrations (Day 8-9)
**Prerequisite:** Phase 2 complete

| Task | Description | Files |
|------|-------------|-------|
| 7.1 | Implement `ICalendarAdapter` interface | `src/test_server.py` |
| 7.2 | Add Apple Calendar mock adapter | `src/test_server.py` |
| 7.3 | Add Google Calendar mock adapter | `src/test_server.py` |
| 7.4 | Implement location awareness | `src/test_server.py` |
| 7.5 | Implement sound library | `src/test_server.py` |

---

## Scenario Coverage

| Scenario File | Status | Spec Ref |
|---------------|--------|----------|
| `chain-full-30min.yaml` | Needs bug fix | Section 2 TC-01 |
| `chain-compressed-15min.yaml` | Needs bug fix | Section 2 TC-02 |
| `chain-minimum-3min.yaml` | Needs bug fix | Section 2 TC-03 |
| `chain-invalid-rejected.yaml` | Needs validation fix | Section 2 TC-04 |
| `parse-natural-language.yaml` | Needs bug fix | Section 3 TC-01 |
| `parse-simple-countdown.yaml` | Needs bug fix | Section 3 TC-02 |
| `parse-tomorrow.yaml` | Needs bug fix | Section 3 TC-03 |
| `voice-coach-personality.yaml` | Working | Section 10 TC-01 |
| `voice-no-nonsense.yaml` | Working | Section 10 TC-02 |
| `voice-all-personalities.yaml` | Working | Section 10 |
| `history-record-outcome.yaml` | Working | Section 11 |
| `history-record-miss-feedback.yaml` | Working | Section 11 TC-05 |
| `stats-hit-rate.yaml` | Working | Section 11 TC-01 |
| `reminder-creation-cascade-delete.yaml` | Needs schema update | Section 13 |
| `reminder-creation-crud.yaml` | Working | Section 13 |

---

## Notes

1. **Test Server Scope:** `src/test_server.py` is a validation harness, not the mobile app. It exposes HTTP endpoints that test scenarios can validate against.

2. **External APIs:** ElevenLabs and MiniMax adapters should be configurable via environment variables and fail gracefully when unavailable.

3. **Mobile App:** React Native/Flutter implementation is out of scope for the test server but documented in the spec for future phases.

4. **Dependencies:** Each phase depends on the previous phase completing successfully.

---

## Quick Start

```bash
# Start the test server
python3 src/test_server.py &

# Run scenario tests
python3 -m pytest harness/

# Run single scenario
python3 harness/scenario_harness.py --project otto-matic
```
