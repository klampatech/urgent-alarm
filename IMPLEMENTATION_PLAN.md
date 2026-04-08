# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Current State:** Python test server (`src/test_server.py`) implements ~20% of spec:
- ✅ Basic escalation chain engine (`compute_escalation_chain`)
- ✅ Keyword-based natural language parser (`parse_reminder_natural`)
- ✅ 5 voice personality message templates (`generate_voice_message`)
- ✅ Basic SQLite schema (4 tables: reminders, anchors, history, destination_adjustments)
- ✅ Hit rate calculation (`calculate_hit_rate`)
- ✅ HTTP API endpoints for testing

**Missing/Incomplete:**
- ❌ Full spec schema (missing origin_*, calendar_sync, custom_sounds, user_preferences table, migrations)
- ❌ LLM adapter interface (keyword fallback only, no real LLM integration)
- ❌ TTS adapter interface (no TTS generation, no caching)
- ❌ Snooze/recomputation, chain re-computation
- ❌ Background scheduling (Notifee)
- ❌ Calendar/location integration
- ❌ Sound library
- ❌ Full stats (streak, common miss window)
- ❌ Mobile app UI

**Spec Coverage:** ~20% — core chain logic and message templates exist, but all adapters, integrations, and mobile infrastructure are missing.

---

## Gap Analysis

### What's Implemented (src/test_server.py)
| Component | Status | Spec Section |
|-----------|--------|--------------|
| Chain engine basic | ✅ Implemented | §2 (partial) |
| Keyword parser | ✅ Implemented | §3 (partial) |
| 5 voice personalities | ✅ Implemented | §10 |
| Basic SQLite schema | ⚠️ Partial | §13 (partial) |
| Hit rate calculation | ✅ Implemented | §11 |
| HTTP test endpoints | ✅ Implemented | N/A |

### What's Missing
| Component | Priority | Spec Section |
|-----------|----------|--------------|
| Database schema alignment (full) | P0 | §13 |
| LLM adapter interface | P0 | §3 |
| TTS adapter interface | P0 | §4 |
| Chain engine enhancement (get_next_unfired, snooze recompute) | P1 | §2, §9 |
| Natural language parser (LLM integration) | P1 | §3 |
| Voice personality message variations | P1 | §10 |
| Notification/alarm behavior | P1 | §5 |
| Snooze & dismissal flow | P1 | §9 |
| Background scheduling | P2 | §6 |
| Location awareness | P2 | §8 |
| Calendar integration | P2 | §7 |
| Sound library | P2 | §12 |
| History & stats enhancement | P2 | §11 |
| Feedback loop enhancement | P2 | §11 |
| Mobile app UI | P3 | N/A |

---

## Phase 1: Foundation (Schema + Adapters)

### 1.1 [P0] Database Schema Alignment
**Spec:** Section 13.2-13.3

Align `src/test_server.py` init_db() with full spec schema:

**Current columns:**
```sql
reminders: id, destination, arrival_time, drive_duration, reminder_type, voice_personality, sound_category, selected_sound, status, created_at, updated_at
anchors: id, reminder_id, timestamp, urgency_tier, tts_clip_path, fired, fire_count
history: id, reminder_id, destination, scheduled_arrival, outcome, feedback_type, created_at
```

**Missing columns:**
- [ ] `reminders`: origin_lat, origin_lng, origin_address, custom_sound_path, calendar_event_id
- [ ] `anchors`: tts_fallback, snoozed_to
- [ ] `history`: actual_arrival, missed_reason
- [ ] `user_preferences`: key, value, updated_at
- [ ] `destination_adjustments`: updated_at
- [ ] `calendar_sync`: calendar_type, last_sync_at, sync_token, is_connected
- [ ] `custom_sounds`: id, filename, original_name, category, file_path, duration_seconds, created_at

**Tasks:**
- [ ] Add all missing columns to init_db()
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] Add migration system (version tracking, sequential migrations)
- [ ] Add schema_version table
- [ ] Add ON DELETE CASCADE for anchors→reminders

**Files:** `src/test_server.py`

---

### 1.2 [P0] LLM Adapter Interface
**Spec:** Section 3.3

Create mockable LLM adapter interface:

**Tasks:**
- [ ] Create `src/lib/adapters/llm_adapter.py`
- [ ] Define `ILanguageModelAdapter` abstract class with `parse(input_text: str) -> dict`
- [ ] Implement `MockLLMAdapter` for testing (returns predefined fixtures)
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` (Claude API)
- [ ] Environment variable: `LLM_ADAPTER=minimax|anthropic|mock`
- [ ] Integrate into parser flow with fallback to keyword extraction

**Files:** `src/lib/adapters/llm_adapter.py`, `tests/adapters/test_llm_adapter.py`

---

### 1.3 [P0] TTS Adapter Interface
**Spec:** Section 4.3

Create mockable TTS adapter interface:

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py`
- [ ] Define `ITTSAdapter` abstract class with `generate(clip_id: str, text: str, voice_id: str) -> bytes`
- [ ] Implement `MockTTSAdapter` for testing (writes silent 1-sec file)
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Create `src/lib/tts_cache.py` for file storage under `/tts_cache/{reminder_id}/`
- [ ] Implement cache invalidation on reminder deletion
- [ ] Environment variable: `TTS_ADAPTER=elevenlabs|mock`
- [ ] Fallback behavior: skip clip, mark `tts_fallback = true`

**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/tts_cache.py`, `tests/adapters/test_tts_adapter.py`

---

## Phase 2: Core Engine Enhancements

### 2.1 [P1] Chain Engine Enhancement
**Spec:** Section 2.3

Enhance chain engine to match spec exactly:

**Tasks:**
- [ ] Add `get_next_unfired_anchor(reminder_id)` function
- [ ] Validate `arrival_time > departure_time + minimum_drive_time` (reject if not)
- [ ] Add chain determinism tests (same inputs → same anchors)
- [ ] Implement snooze chain recomputation (`shift_remaining_anchors(reminder_id, snooze_minutes)`)
- [ ] Add anchor state fields: `snoozed_to`, `tts_fallback`

**Files:** `src/test_server.py`, `tests/test_chain_engine.py`

---

### 2.2 [P1] Natural Language Parser Enhancement
**Spec:** Section 3.4-3.5

Enhance parser to handle all spec test cases:

**Tasks:**
- [ ] Integrate LLM adapter into parser flow
- [ ] Handle all test case formats:
  - [ ] "30 minute drive to Parker Dr, check-in at 9am" → destination, arrival_time, drive_duration=30
  - [ ] "dryer in 3 min" → simple_countdown with arrival_time=now+3min
  - [ ] "meeting tomorrow 2pm, 20 min drive" → tomorrow's date
- [ ] Return `confidence` score in parsed result
- [ ] Handle empty/unintelligible input with error response
- [ ] Extract `reminder_type` enum: countdown_event, simple_countdown, morning_routine, standing_recurring

**Files:** `src/test_server.py`, `tests/test_parser.py`

---

### 2.3 [P1] Voice Personality Message Variations
**Spec:** Section 10.3

Generate message variations to avoid repetition:

**Tasks:**
- [ ] Each personality generates minimum 3 message variations per urgency tier
- [ ] Random selection or round-robin from variations
- [ ] Add variation tests (3 calls → at least 2 distinct messages)

**Files:** `src/test_server.py`, `tests/test_voice.py`

---

## Phase 3: User Interaction

### 3.1 [P1] Notification & Alarm Behavior
**Spec:** Section 5.3

Implement notification escalation and DND/quiet hours:

**Tasks:**
- [ ] 4-tier notification sounds: gentle chime, pointed beep, urgent siren, looping alarm
- [ ] DND awareness: silent for early anchors, visual override for final 5 min
- [ ] Quiet hours suppression (default 10pm–7am)
- [ ] Queue overdue anchors; drop if >15 minutes overdue
- [ ] Chain overlap serialization (queue new anchors)
- [ ] T-0 alarm loops until user action

**Files:** `src/lib/notifications.py`, `tests/test_notifications.py`

---

### 3.2 [P1] Snooze & Dismissal Flow
**Spec:** Section 9.3

Implement snooze and feedback:

**Tasks:**
- [ ] Tap snooze (1 minute default)
- [ ] Custom snooze (1, 3, 5, 10, 15 min)
- [ ] Chain re-computation after snooze
- [ ] Re-register snoozed anchors with new timestamps
- [ ] Dismissal feedback prompt
- [ ] TTS confirmation: "Okay, snoozed [X] minutes"
- [ ] Persist snoozed timestamps across restart

**Files:** `src/lib/snooze.py`, `src/lib/dismissal.py`, `tests/test_snooze.py`

---

## Phase 4: System Integration

### 4.1 [P2] Background Scheduling
**Spec:** Section 6.3

Note: Requires React Native; marked as P2 for Python layer preparation.

**Tasks:**
- [ ] Prepare Python layer for Notifee integration (anchor state management)
- [ ] Document expected Notifee API surface
- [ ] Implement recovery scan logic in Python

**Files:** `src/lib/scheduler.py`

---

### 4.2 [P2] Calendar Integration
**Spec:** Section 7.3

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py`
- [ ] Define `ICalendarAdapter` interface
- [ ] Document expected EventKit/Google Calendar API surface
- [ ] Implement suggestion card generation logic

**Files:** `src/lib/adapters/calendar_adapter.py`

---

### 4.3 [P2] Location Awareness
**Spec:** Section 8.3

**Tasks:**
- [ ] Create `src/lib/location.py` with single-check logic
- [ ] Geofence comparison: within 500m = "at origin"
- [ ] Fire firm/critical tier if still at origin

**Files:** `src/lib/location.py`

---

## Phase 5: Analytics Enhancement

### 5.1 [P2] History & Stats Enhancement
**Spec:** Section 11.3

**Tasks:**
- [ ] Implement "common miss window" identification
- [ ] Implement streak counter (increment on hit, reset on miss)
- [ ] 90-day retention with archive logic

**Files:** `src/lib/stats.py`, `tests/test_stats.py`

---

### 5.2 [P2] Feedback Loop
**Spec:** Section 11.3

**Tasks:**
- [ ] On "left too late" feedback: `adjustment_minutes += 2`
- [ ] Cap adjustment at +15 minutes
- [ ] Apply adjustments on reminder creation

**Files:** `src/lib/feedback_loop.py`, `tests/test_feedback.py`

---

## Phase 6: Sound Library

### 6.1 [P2] Sound Library
**Spec:** Section 12.3

**Tasks:**
- [ ] Create `src/lib/sound_library.py`
- [ ] Bundle 5 built-in sounds per category
- [ ] Custom audio import support (MP3, WAV, M4A)
- [ ] Transcoding to normalized format
- [ ] Corrupted file fallback

**Files:** `src/lib/sound_library.py`, `tests/test_sound_library.py`

---

## Task Prioritization Summary

| Priority | Task | Dependencies | Spec Section |
|----------|------|--------------|--------------|
| P0 | Database schema alignment | None | §13 |
| P0 | LLM adapter interface | None | §3 |
| P0 | TTS adapter interface | None | §4 |
| P1 | Chain engine enhancement | None | §2 |
| P1 | Natural language parser | LLM adapter | §3 |
| P1 | Voice personality variations | None | §10 |
| P1 | Notification behavior | None | §5 |
| P1 | Snooze & dismissal | Chain engine | §9 |
| P2 | Background scheduling | Database | §6 |
| P2 | Calendar integration | Database | §7 |
| P2 | Location awareness | Database | §8 |
| P2 | Sound library | Database | §12 |
| P2 | History & stats | Database | §11 |
| P2 | Feedback loop | History | §11 |

---

## Scenario Coverage

The following scenarios define acceptance criteria that must pass:

| Scenario | Component | Status |
|----------|-----------|--------|
| chain-full-30min | Chain engine | ✅ Implemented |
| chain-compressed-15min | Chain engine | ⚠️ Partial |
| chain-minimum-3min | Chain engine | ⚠️ Partial |
| chain-invalid-rejected | Chain engine | ⚠️ Partial |
| parse-natural-language | Parser | ✅ Implemented |
| parse-simple-countdown | Parser | ⚠️ Partial |
| parse-tomorrow | Parser | ⚠️ Partial |
| voice-coach-personality | Voice | ✅ Implemented |
| voice-no-nonsense | Voice | ✅ Implemented |
| voice-all-personalities | Voice | ✅ Implemented |
| stats-hit-rate | Stats | ✅ Implemented |
| history-record-outcome | History | ✅ Implemented |
| history-record-miss-feedback | Feedback | ⚠️ Partial |
| reminder-creation-crud | Database | ⚠️ Partial |
| reminder-creation-cascade-delete | Database | ❌ Missing |

---

## Definition of Done

Every task must have:
1. Implementation matching acceptance criteria in spec
2. Corresponding scenario passing
3. No regressions in existing tests

Run validation:
```bash
python3 -m pytest harness/
python3 -m py_compile src/test_server.py
```
