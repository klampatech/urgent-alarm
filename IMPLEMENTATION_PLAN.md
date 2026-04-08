# Urgent Alarm — Implementation Plan

## Project Overview

A mobile alarm app that speaks escalating urgency messages adapting based on remaining time. The app creates departure chains from calm nudges to urgent alarms, with AI-generated contextual voice messages.

## Gap Analysis Summary

| Section | Spec Status | Implementation Status |
|---------|-------------|----------------------|
| 1. Overview | ✅ Complete | ✅ Aligned |
| 2. Escalation Chain Engine | ✅ Detailed | ⚠️ Partial (missing `get_next_unfired_anchor`, determinism tests) |
| 3. Reminder Parsing | ✅ Detailed | ⚠️ Partial (keyword only, no LLM adapter interface) |
| 4. Voice & TTS Generation | ✅ Detailed | ⚠️ Partial (templates only, no TTS adapter interface) |
| 5. Notification & Alarm | ✅ Detailed | ❌ Not implemented |
| 6. Background Scheduling | ✅ Detailed | ❌ Not implemented (Notifee stub only) |
| 7. Calendar Integration | ✅ Detailed | ❌ Not implemented |
| 8. Location Awareness | ✅ Detailed | ❌ Not implemented |
| 9. Snooze & Dismissal | ✅ Detailed | ⚠️ Partial (history recording only) |
| 10. Voice Personality | ✅ Detailed | ⚠️ Partial (1 template per tier, no variations) |
| 11. History, Stats & Feedback | ✅ Detailed | ⚠️ Partial (basic hit rate only) |
| 12. Sound Library | ✅ Detailed | ❌ Not implemented |
| 13. Data Persistence | ✅ Detailed | ⚠️ Partial (missing tables/columns) |
| 14. Definition of Done | ✅ Complete | ❌ No tests |

---

## Priority 1: Foundation (Must Implement First)

These are dependencies for all other features.

### 1.1 Complete SQLite Schema
**Spec:** Section 13 (Data Persistence)
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

**Tasks:**
- [ ] Add `schema_migrations` table for version tracking
- [ ] Add missing columns to `reminders`: `sound_category`, `selected_sound`, `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id`
- [ ] Add missing columns to `anchors`: `tts_clip_path`, `tts_fallback`, `snoozed_to`
- [ ] Add missing columns to `history`: `actual_arrival`, `missed_reason`
- [ ] Add `updated_at` to `destination_adjustments`, `user_preferences`
- [ ] Create `custom_sounds` table
- [ ] Create `calendar_sync` table
- [ ] Enable WAL mode and foreign keys
- [ ] Add migration system (sequential, versioned)
- [ ] Write migration tests

### 1.2 Adapter Interfaces
**Spec:** Sections 3, 4, 7, 8
**Files:** `src/lib/adapters/base.py`

**Tasks:**
- [ ] Create `ILanguageModelAdapter` abstract interface for parsing
- [ ] Create `ITTSAdapter` abstract interface for voice generation
- [ ] Create `ICalendarAdapter` abstract interface for calendar
- [ ] Create `ILocationAdapter` abstract interface for location
- [ ] Document adapter contract for each interface

### 1.3 Chain Engine Completion
**Spec:** Section 2
**Files:** `src/lib/chain_engine.py`, `tests/test_chain_engine.py`

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` function
- [ ] Add chain determinism guarantee (same inputs = same outputs)
- [ ] Fix buffer calculation edge cases in `compute_escalation_chain`:
  - TC-02: buffer 10-24 min → 5 anchors (urgent, pushing, firm, critical, alarm)
  - TC-03: buffer 3 min → 3 anchors (firm, critical, alarm)
- [ ] Implement `validate_chain` with proper error codes
- [ ] Write unit tests for all 6 test scenarios (TC-01 through TC-06)
- [ ] Add anchor ordering verification

---

## Priority 2: Core Features (LLM, TTS, Parser)

### 2.1 LLM Adapter Implementation
**Spec:** Section 3
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/mock_llm_adapter.py`

**Tasks:**
- [ ] Implement `MinimaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter`
- [ ] Implement `MockLLMAdapter` for testing with fixture responses
- [ ] Add system prompt for extraction schema
- [ ] Implement keyword extraction fallback (regex-based)
- [ ] Add confidence scoring to parse results
- [ ] Write tests: TC-01 through TC-07 from spec

### 2.2 TTS Adapter Implementation
**Spec:** Section 4
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/mock_tts_adapter.py`

**Tasks:**
- [ ] Implement `ElevenLabsAdapter` with voice ID mapping
- [ ] Implement `MockTTSAdapter` that writes silent audio files
- [ ] Implement TTS caching system: `/tts_cache/{reminder_id}/`
- [ ] Add fallback behavior: on TTS failure, mark `tts_fallback = true`
- [ ] Implement cache invalidation on reminder deletion
- [ ] Map voice personalities to ElevenLabs voice IDs
- [ ] Write tests: TC-01 through TC-05 from spec

### 2.3 Voice Personality Message Variations
**Spec:** Section 10
**Files:** `src/lib/voice_personalities.py`

**Tasks:**
- [ ] Refactor `VOICE_PERSONALITIES` to support 3+ variations per tier
- [ ] Implement message selection (random or round-robin)
- [ ] Add "Calm" personality as 5th option (gentle-only mode)
- [ ] Add custom personality prompt support (max 200 chars)
- [ ] Write tests: TC-01 through TC-05 from spec

---

## Priority 3: Reminder Management

### 3.1 Quick Add Flow
**Spec:** Section 3
**Files:** `src/lib/reminder_service.py`

**Tasks:**
- [ ] Implement `QuickAddService.create_reminder(input_text, voice_personality)`
- [ ] Flow: parse → confirm (show parsed fields) → create chain → generate TTS
- [ ] Add manual field correction support
- [ ] Implement input validation (reject unintelligible: "blah blah")
- [ ] Write integration tests for full Quick Add flow

### 3.2 Reminder CRUD Operations
**Files:** `src/lib/reminder_service.py`, `src/lib/anchor_service.py`

**Tasks:**
- [ ] `create_reminder(parsed_data)` → reminder + anchors
- [ ] `get_reminder(reminder_id)` → full reminder with anchors
- [ ] `update_reminder(reminder_id, updates)` → update + recompute if needed
- [ ] `delete_reminder(reminder_id)` → cascade delete anchors + TTS cache
- [ ] `get_pending_reminders()` → all pending reminders
- [ ] `get_next_unfired_anchor(reminder_id)` → anchor service method

---

## Priority 4: Notification & Alarm System

### 4.1 Notification Tier System
**Spec:** Section 5
**Files:** `src/lib/notification_service.py`

**Tasks:**
- [ ] Implement notification tier escalation:
  - calm/casual → gentle chime
  - pointed/urgent → pointed beep
  - pushing/firm → urgent siren
  - critical/alarm → looping alarm
- [ ] Implement DND awareness (visual + vibration for final 5 min)
- [ ] Implement quiet hours suppression (configurable, default 10pm-7am)
- [ ] Implement overdue anchor queue (15-min rule: drop if >15 min late)
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] Write tests: TC-01 through TC-06 from spec

### 4.2 T-0 Alarm Behavior
**Spec:** Section 5.3
**Files:** `src/lib/alarm_service.py`

**Tasks:**
- [ ] Implement looping alarm until user action
- [ ] Alarm must NOT auto-dismiss
- [ ] Notification display: destination, time remaining, voice icon

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration (Stub for Testing)
**Spec:** Section 6
**Files:** `src/lib/scheduling/scheduler.py`, `src/lib/scheduling/recovery.py`

**Tasks:**
- [ ] Create `NotificationScheduler` interface (abstract for testing)
- [ ] Implement `schedule_anchor(anchor)` method
- [ ] Implement `cancel_anchor(anchor_id)` method
- [ ] Implement `re_register_pending_anchors()` for crash recovery
- [ ] Implement recovery scan on app launch:
  - Fire overdue anchors within 15-min grace window
  - Drop anchors >15 min overdue, log with `missed_reason`
  - Log late fires (>60s) with warning
- [ ] Write tests: TC-01 through TC-06 from spec

### 5.2 Snooze & Re-computation
**Spec:** Section 9
**Files:** `src/lib/snooze_service.py`

**Tasks:**
- [ ] Implement `snooze_1_min(anchor_id)` → tap snooze
- [ ] Implement `custom_snooze(anchor_id, minutes)` → tap-and-hold picker (1, 3, 5, 10, 15)
- [ ] Implement chain re-computation after snooze:
  - Shift remaining unfired anchors to `now + original_time_remaining`
  - Re-register with scheduler
- [ ] Persist snoozed state to SQLite (`snoozed_to` column)
- [ ] TTS confirmation: "Okay, snoozed [X] minutes"
- [ ] Write tests: TC-01, TC-02, TC-03, TC-06 from spec

### 5.3 Dismissal & Feedback
**Spec:** Section 9
**Files:** `src/lib/feedback_service.py`

**Tasks:**
- [ ] Implement feedback prompt: "You missed [destination] — was the timing right?"
- [ ] Handle "Yes — timing was right" → record as 'hit'
- [ ] Handle "No — timing was off" → sub-prompt: "What was wrong?"
  - "Left too early" → future reminders suggest earlier departure
  - "Left too late" → future reminders add +2 min to drive_duration
  - "Other" → log without adjustment
- [ ] Write tests: TC-04, TC-05 from spec

---

## Priority 6: History & Feedback Loop

### 6.1 Stats System
**Spec:** Section 11
**Files:** `src/lib/stats_service.py`

**Tasks:**
- [ ] Implement `calculate_hit_rate(days=7)` → hits / (total - pending) * 100
- [ ] Implement `get_common_miss_window(destination)` → most missed urgency tier
- [ ] Implement `get_streak_counter(reminder_id)` → consecutive hits
- [ ] Ensure all stats derived from history table (no separate store)
- [ ] Write tests: TC-01 through TC-07 from spec

### 6.2 Feedback Loop Adjustment
**Spec:** Section 11.3
**Files:** `src/lib/adjustment_service.py`

**Tasks:**
- [ ] `adjust_drive_duration(destination, base_duration)`:
  - Formula: `adjusted = base + (late_count * 2 min)`
  - Cap: `+15 minutes max`
- [ ] Implement `destination_adjustments` table updates
- [ ] Apply adjustment when creating new reminders to same destination
- [ ] Write tests: TC-02, TC-03 from spec

### 6.3 Data Retention
**Spec:** Section 11.3
**Files:** `src/lib/cleanup_service.py`

**Tasks:**
- [ ] Archive history entries older than 90 days
- [ ] Implement cleanup job (can be manual or scheduled)

---

## Priority 7: Calendar Integration

### 7.1 Calendar Adapters
**Spec:** Section 7
**Files:** `src/lib/adapters/calendar_adapter.py`, `src/lib/adapters/apple_calendar_adapter.py`, `src/lib/adapters/google_calendar_adapter.py`

**Tasks:**
- [ ] Implement `ICalendarAdapter` interface
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Sync on launch + every 15 minutes + background refresh
- [ ] Filter: only events with non-empty `location`
- [ ] Write tests: TC-01 through TC-06 from spec

### 7.2 Suggestion System
**Spec:** Section 7
**Files:** `src/lib/suggestion_service.py`

**Tasks:**
- [ ] Surface suggestion card: "Parker Dr check-in — 9:00 AM — add departure reminder?"
- [ ] "Add Reminder" → creates countdown_event reminder
- [ ] Mark calendar-sourced reminders with `calendar_event_id`
- [ ] Handle recurring events (generate reminder per occurrence)
- [ ] Handle permission denial: show explanation banner with "Open Settings"

---

## Priority 8: Location Awareness

### 8.1 Location Adapter
**Spec:** Section 8
**Files:** `src/lib/adapters/location_adapter.py`

**Tasks:**
- [ ] Implement `ILocationAdapter` interface
- [ ] Implement single-point location check (not continuous)
- [ ] 500m geofence radius for "at origin" comparison
- [ ] Request permission only at first location-aware reminder creation
- [ ] Handle denied permission gracefully

### 8.2 Departure Escalation
**Spec:** Section 8
**Files:** `src/lib/location_service.py`

**Tasks:**
- [ ] At departure anchor: compare current location to origin
- [ ] If within 500m (still at origin): fire firm/critical tier immediately
- [ ] If >500m (already left): proceed with normal chain
- [ ] No location history stored after comparison
- [ ] Write tests: TC-01 through TC-05 from spec

---

## Priority 9: Sound Library

### 9.1 Sound System
**Spec:** Section 12
**Files:** `src/lib/sound_service.py`

**Tasks:**
- [ ] Bundle 5 sounds per category: Commute, Routine, Errand
- [ ] Sound selection per reminder (not global)
- [ ] Custom sound import: MP3, WAV, M4A (max 30 seconds)
- [ ] Store in app sandbox with reference in `custom_sounds` table
- [ ] Fallback to category default if custom sound missing
- [ ] Write tests: TC-01 through TC-05 from spec

---

## Priority 10: Testing Suite

### 10.1 Unit Tests
**Files:** `tests/test_chain_engine.py`, `tests/test_parser.py`, `tests/test_tts_adapter.py`, `tests/test_llm_adapter.py`

**Tasks:**
- [ ] Chain engine: TC-01 through TC-06
- [ ] Parser: TC-01 through TC-07
- [ ] TTS adapter: TC-01 through TC-05
- [ ] LLM adapter: TC-01 through TC-07
- [ ] Stats: TC-01 through TC-07
- [ ] Database migrations: TC-01 through TC-05

### 10.2 Integration Tests
**Files:** `tests/test_reminder_flow.py`, `tests/test_snooze_recovery.py`, `tests/test_feedback_loop.py`

**Tasks:**
- [ ] Full reminder creation: parse → chain → TTS → persist
- [ ] Anchor firing: schedule → fire → mark fired
- [ ] Snooze recovery: snooze → recompute → re-register
- [ ] Feedback loop: dismiss → feedback → adjustment applied

### 10.3 Adapter Mock Tests
**Files:** `tests/test_adapters.py`

**Tasks:**
- [ ] All adapters have working mock implementations
- [ ] Tests use in-memory SQLite
- [ ] Tests are independent (fresh db per test)

---

## Dependency Graph

```
[1.1 Schema] → [1.2 Adapters] → [1.3 Chain Engine]
                                    ↓
[2.1 LLM Adapter] ← [2.2 TTS Adapter] ← [2.3 Voice Personalities]
        ↓               ↓                    ↓
[3.1 Quick Add] ← [3.2 Reminder CRUD] → [4.1 Notifications] → [5.1 Scheduler] → [5.2 Snooze] → [5.3 Dismissal]
                                                                            ↓
[6.1 Stats] ← [6.2 Feedback Loop] ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
        ↓
[6.3 Cleanup]

[7.1 Calendar Adapters] → [7.2 Suggestion System] → [3.2 Reminder CRUD]

[8.1 Location Adapter] → [8.2 Departure Escalation] → [4.1 Notifications]

[9.1 Sound Library] → [3.2 Reminder CRUD]

[10.1-10.3 Tests] ← All features
```

---

## Estimated Effort (Story Points)

| Priority | Feature | Points | Notes |
|----------|---------|--------|-------|
| P1 | Complete SQLite Schema | 5 | Migrations, foreign keys |
| P1 | Adapter Interfaces | 3 | Abstract classes |
| P1 | Chain Engine Completion | 5 | Tests included |
| P2 | LLM Adapter | 8 | API integration + mock |
| P2 | TTS Adapter | 8 | ElevenLabs + caching |
| P2 | Voice Personality Variations | 3 | Template expansion |
| P3 | Quick Add Flow | 5 | Parse → confirm → create |
| P3 | Reminder CRUD | 5 | Full service layer |
| P4 | Notification System | 8 | Tier escalation + DND |
| P4 | T-0 Alarm | 3 | Looping until action |
| P5 | Background Scheduling | 8 | Notifee stub + recovery |
| P5 | Snooze & Re-computation | 5 | Chain shifting |
| P5 | Dismissal & Feedback | 3 | Feedback prompt |
| P6 | Stats System | 5 | Hit rate, streak, miss window |
| P6 | Feedback Loop Adjustment | 3 | Drive duration +2 min |
| P6 | Data Retention | 2 | 90-day archive |
| P7 | Calendar Adapters | 8 | EventKit + Google API |
| P7 | Suggestion System | 5 | Suggestion cards |
| P8 | Location Adapter | 5 | Single-point check |
| P8 | Departure Escalation | 3 | Immediate hard escalation |
| P9 | Sound Library | 5 | Import + playback |
| P10 | Unit Tests | 8 | All test scenarios |
| P10 | Integration Tests | 8 | Full flows |
| **TOTAL** | | **117** | |

---

## Next Steps

1. **Immediate**: Implement Priority 1 (Foundation) — schema, interfaces, chain engine
2. **Short-term**: Priority 2-3 (LLM/TTS, Quick Add)
3. **Medium-term**: Priority 4-6 (Notifications, Scheduling, Stats)
4. **Long-term**: Priority 7-9 (Calendar, Location, Sound)
5. **Continuous**: Priority 10 (Tests) throughout

**Validation Commands:**
```bash
# Start server
python3 src/test_server.py &

# Run basic validation
python3 -m pytest tests/  # Once tests exist

# Manual validation
curl http://localhost:8090/health
curl "http://localhost:8090/chain?arrival=2026-04-09T09:00:00&duration=30"
curl -X POST http://localhost:8090/parse -d '{"text":"Parker Dr 9am, 30 min drive"}'
```
