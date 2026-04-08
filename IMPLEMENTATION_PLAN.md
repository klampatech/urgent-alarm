# Urgent Alarm — Implementation Plan

## Project Overview

A mobile alarm app that speaks escalating urgency messages adapting based on remaining time. The app creates departure chains from calm nudges to urgent alarms, with AI-generated contextual voice messages.

## Codebase Analysis

### Current State

| Component | File | Status |
|-----------|------|--------|
| Chain Engine | `src/test_server.py` | ⚠️ Partial (compute_escalation_chain, validate_chain) |
| Parser | `src/test_server.py` | ⚠️ Partial (keyword extraction only, no LLM adapter) |
| Voice Personalities | `src/test_server.py` | ⚠️ Partial (5 personas, 1 template each, no variations) |
| Stats | `src/test_server.py` | ⚠️ Partial (calculate_hit_rate only) |
| Database CRUD | `src/test_server.py` | ⚠️ Basic (create/list reminders, record history) |
| Tests | `harness/` | ❌ Empty |

### What's Missing

| Spec Section | Missing Items |
|--------------|---------------|
| §2 Chain Engine | `get_next_unfired_anchor()`, determinism guarantee, anchor sorting |
| §3 Parser | LLM adapter interface, mock adapter, confidence scoring |
| §4 TTS | Adapter interface, ElevenLabs integration, caching, mock |
| §5 Notifications | Tier escalation, DND/quiet hours, chain overlap |
| §6 Scheduling | Notifee stub, recovery scan, late-fire logging |
| §9 Snooze | Chain re-computation, snooze persistence, custom duration picker |
| §10 Voice Personalities | 3+ variations per tier, custom prompt support |
| §11 Stats | Miss window, streak counter, adjustment formula |
| §12 Sound Library | Built-in sounds, import, per-reminder selection |
| §13 Data Persistence | Missing tables (custom_sounds, calendar_sync, schema_migrations), missing columns |
| §14 Tests | No test suite exists |

---

## Priority 1: Foundation (Must Implement First)

These are hard dependencies for all other features.

### 1.1 Complete SQLite Schema
**Spec:** §13 Data Persistence
**Files:** `src/lib/database.py`, `src/lib/migrations.py`

| Task | Description |
|------|-------------|
| Add schema_migrations table | Version tracking for sequential migrations |
| Add reminders columns | `sound_category`, `selected_sound`, `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id` |
| Add anchors columns | `tts_clip_path`, `tts_fallback`, `snoozed_to` |
| Add history columns | `actual_arrival`, `missed_reason` |
| Add updated_at columns | `destination_adjustments`, `user_preferences` |
| Create custom_sounds table | id, filename, original_name, category, file_path, duration_seconds, created_at |
| Create calendar_sync table | calendar_type, last_sync_at, sync_token, is_connected |
| Enable WAL mode + foreign keys | `PRAGMA journal_mode = WAL`, `PRAGMA foreign_keys = ON` |
| Migration system | Sequential, versioned migrations (never modify applied) |

### 1.2 Adapter Interfaces
**Spec:** §3, §4, §7, §8
**Files:** `src/lib/adapters/base.py`

```python
# Required interfaces
ILanguageModelAdapter  # Parse natural language → structured data
ITTSAdapter            # Generate TTS clips
ICalendarAdapter       # Fetch calendar events
ILocationAdapter       # Single-point location check
```

### 1.3 Chain Engine Completion
**Spec:** §2
**Files:** `src/lib/chain_engine.py`

| Task | Description |
|------|-------------|
| `get_next_unfired_anchor(reminder_id)` | Return earliest unfired anchor for recovery |
| Chain determinism | Same inputs → same anchor list (for unit testing) |
| Fix buffer edge cases | See test scenarios below |
| Anchor sorting | Ensure anchors sorted by timestamp ASC |

**Test Scenarios (TC-01 to TC-06):**
- TC-01: 30min buffer → 8 anchors (8:30 calm through 9:00 alarm)
- TC-02: 15min buffer → 5 anchors (urgent, pushing, firm, critical, alarm)
- TC-03: 3min buffer → 3 anchors (firm, critical, alarm)
- TC-04: Invalid chain rejected (drive_duration > time_to_arrival)
- TC-05: `get_next_unfired_anchor` returns correct anchor after partial fire
- TC-06: Determinism — identical inputs produce identical outputs

---

## Priority 2: Core Features (LLM, TTS, Parser)

### 2.1 LLM Adapter Implementation
**Spec:** §3
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/mock_llm_adapter.py`

| Task | Description |
|------|-------------|
| `MinimaxAdapter` | Anthropic-compatible API |
| `AnthropicAdapter` | Direct Anthropic API |
| `MockLLMAdapter` | Fixture responses for testing |
| System prompt | Extraction schema definition |
| Keyword fallback | Regex-based extraction on API failure |
| Confidence scoring | 0.0-1.0 based on fields extracted |

**Test Scenarios (TC-01 to TC-07):**
- TC-01: "30 minute drive to Parker Dr, check-in at 9am" → proper fields
- TC-02: "dryer in 3 min" → simple_countdown with arrival = now+3min
- TC-03: "meeting tomorrow 2pm, 20 min drive" → correct tomorrow date
- TC-04: LLM API failure → keyword fallback with confidence < 1.0
- TC-05: Manual field correction → confirmed reminder uses edited values
- TC-06: Unintelligible input ("asdfgh") → user-facing error
- TC-07: Mock adapter returns fixture without real API call

### 2.2 TTS Adapter Implementation
**Spec:** §4
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/mock_tts_adapter.py`

| Task | Description |
|------|-------------|
| `ElevenLabsAdapter` | Voice ID mapping, async generation |
| `MockTTSAdapter` | Write silent audio files |
| Cache system | `/tts_cache/{reminder_id}/{anchor_id}.mp3` |
| Fallback behavior | On failure, mark `tts_fallback=true` |
| Cache invalidation | Delete on reminder deletion |

**Test Scenarios (TC-01 to TC-05):**
- TC-01: 8 MP3 files created per reminder
- TC-02: Anchor plays from local cache (no network)
- TC-03: TTS failure → fallback + `tts_fallback=true`
- TC-04: Reminder deletion → TTS files removed
- TC-05: Mock adapter writes silent file without API call

### 2.3 Voice Personality Message Variations
**Spec:** §10.5
**Files:** `src/lib/voice_personalities.py`

| Task | Description |
|------|-------------|
| 3+ variations per tier | Avoid robotic repetition |
| Selection mechanism | Random or round-robin |
| "Calm" personality | 5th option (gentle-only) |
| Custom prompt | Max 200 chars, appended to system prompt |

---

## Priority 3: Reminder Management

### 3.1 Quick Add Flow
**Spec:** §3.3
**Files:** `src/lib/reminder_service.py`

| Task | Description |
|------|-------------|
| Parse → Confirm → Create | Full flow: input → LLM parse → user confirm → chain create |
| Manual correction | User can edit any parsed field |
| Validation | Reject unintelligible input |

### 3.2 Reminder CRUD
**Files:** `src/lib/reminder_service.py`, `src/lib/anchor_service.py`

| Method | Description |
|--------|-------------|
| `create_reminder()` | Parsed data → reminder + anchors |
| `get_reminder()` | Full reminder with anchors |
| `update_reminder()` | Update + recompute if needed |
| `delete_reminder()` | Cascade delete + TTS cache |
| `get_pending_reminders()` | All pending reminders |
| `get_next_unfired_anchor()` | For scheduler recovery |

---

## Priority 4: Notification & Alarm System

### 4.1 Notification Tier System
**Spec:** §5
**Files:** `src/lib/notification_service.py`

| Task | Description |
|------|-------------|
| Tier escalation | gentle chime → pointed beep → urgent siren → looping alarm |
| DND awareness | Silent early anchors; visual+vibration for final 5min |
| Quiet hours | Configurable suppress (default 10pm-7am) |
| Overdue queue | 15-min rule: drop if >15 min late |
| Chain overlap | Queue new anchors until current chain completes |

### 4.2 T-0 Alarm Behavior
**Spec:** §5.3
**Files:** `src/lib/alarm_service.py`

| Task | Description |
|------|-------------|
| Looping alarm | Until user dismisses or snoozes |
| No auto-dismiss | Must be user action |
| Display | Destination, time remaining, voice icon |

---

## Priority 5: Background Scheduling

### 5.1 Notifee Integration (Stub)
**Spec:** §6
**Files:** `src/lib/scheduling/scheduler.py`, `src/lib/scheduling/recovery.py`

| Task | Description |
|------|-------------|
| `schedule_anchor()` | Register individual background task |
| `cancel_anchor()` | Cancel pending anchor |
| `re_register_pending_anchors()` | Crash recovery |
| Recovery scan | Fire within 15-min grace; drop >15 min overdue |
| Late fire logging | Warning if >60s after scheduled time |

### 5.2 Snooze & Re-computation
**Spec:** §9
**Files:** `src/lib/snooze_service.py`

| Task | Description |
|------|-------------|
| `snooze_1_min()` | Tap snooze |
| `custom_snooze()` | Tap-and-hold picker (1, 3, 5, 10, 15 min) |
| Chain re-computation | Shift remaining anchors: `now + original_time_remaining` |
| Persist snooze | SQLite `snoozed_to` column |
| TTS confirmation | "Okay, snoozed [X] minutes" |

### 5.3 Dismissal & Feedback
**Spec:** §9.4
**Files:** `src/lib/feedback_service.py`

| Task | Description |
|------|-------------|
| Feedback prompt | "You missed [dest] — was timing right?" |
| "Yes" response | Record as 'hit' |
| "No" response | Sub-prompt: "Left too early", "Left too late", "Other" |
| Feedback loop | "Left too late" → +2 min drive_duration for destination |

---

## Priority 6: History & Feedback Loop

### 6.1 Stats System
**Spec:** §11
**Files:** `src/lib/stats_service.py`

| Task | Formula | Test |
|------|---------|------|
| Hit rate | hits / (total - pending) * 100, trailing 7 days | TC-01 |
| Common miss window | Most frequently missed urgency tier | TC-04 |
| Streak counter | Consecutive hits for recurring reminders | TC-05, TC-06 |

### 6.2 Feedback Loop Adjustment
**Spec:** §11.3
**Files:** `src/lib/adjustment_service.py`

| Task | Formula |
|------|---------|
| `adjust_drive_duration()` | `adjusted = base + (late_count * 2 min)` |
| Cap | Maximum +15 minutes |

### 6.3 Data Retention
**Spec:** §11.3
**Files:** `src/lib/cleanup_service.py`

Archive history >90 days old.

---

## Priority 7: Calendar Integration

### 7.1 Calendar Adapters
**Spec:** §7
**Files:** `src/lib/adapters/calendar_adapter.py`, `apple_calendar_adapter.py`, `google_calendar_adapter.py`

| Task | Description |
|------|-------------|
| `ICalendarAdapter` | Common interface |
| `AppleCalendarAdapter` | EventKit (iOS) |
| `GoogleCalendarAdapter` | Google Calendar API |
| Sync schedule | Launch + every 15 min + background refresh |
| Filter | Events with non-empty `location` only |

### 7.2 Suggestion System
**Spec:** §7.3
**Files:** `src/lib/suggestion_service.py`

| Task | Description |
|------|-------------|
| Suggestion card | "Parker Dr check-in — 9:00 AM — add departure reminder?" |
| "Add Reminder" → countdown_event | With `calendar_event_id` reference |
| Recurring events | Generate reminder per occurrence |
| Permission denial | Explanation banner + "Open Settings" |

---

## Priority 8: Location Awareness

### 8.1 Location Adapter
**Spec:** §8
**Files:** `src/lib/adapters/location_adapter.py`

| Task | Description |
|------|-------------|
| Single-point check | One API call at departure trigger |
| 500m geofence | "At origin" if within 500m |
| Permission request | At first location-aware reminder, not app launch |
| Graceful denial | Reminder created without location escalation |

### 8.2 Departure Escalation
**Spec:** §8
**Files:** `src/lib/location_service.py`

| Task | Description |
|------|-------------|
| At departure anchor | Compare current location to origin |
| Within 500m | Fire firm/critical tier immediately |
| >500m away | Proceed with normal chain |
| No history | Location data not retained after comparison |

---

## Priority 9: Sound Library

### 9.1 Sound System
**Spec:** §12
**Files:** `src/lib/sound_service.py`

| Task | Description |
|------|-------------|
| Built-in sounds | 5 per category: Commute, Routine, Errand |
| Per-reminder selection | Not global |
| Custom import | MP3, WAV, M4A (max 30 seconds) |
| File storage | App sandbox + reference in `custom_sounds` table |
| Fallback | Category default if custom sound missing |

---

## Priority 10: Testing Suite

### 10.1 Unit Tests
**Files:** `tests/test_chain_engine.py`, `tests/test_parser.py`, `tests/test_tts_adapter.py`, `tests/test_llm_adapter.py`, `tests/test_stats.py`, `tests/test_database.py`

### 10.2 Integration Tests
**Files:** `tests/test_reminder_flow.py`, `tests/test_snooze_recovery.py`, `tests/test_feedback_loop.py`

### 10.3 Adapter Mock Tests
**Files:** `tests/test_adapters.py`

All adapters must have working mock implementations. Tests use in-memory SQLite.

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY 1: FOUNDATION                                                │
├─────────────────────────────────────────────────────────────────────────┤
│ [1.1 Schema] ─→ [1.2 Adapters] ─→ [1.3 Chain Engine]                  │
│                    ↓                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY 2: CORE FEATURES                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ [2.1 LLM Adapter] ← [2.2 TTS Adapter] ← [2.3 Voice Personalities]      │
│        ↓               ↓                    ↓                           │
│ [3.1 Quick Add] ← [3.2 Reminder CRUD]                                 │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY 3-5: NOTIFICATIONS, SCHEDULING, SNOOZE                        │
├─────────────────────────────────────────────────────────────────────────┤
│ [4.1 Notifications] ─→ [5.1 Scheduler] ─→ [5.2 Snooze] ─→ [5.3 Dismiss]│
│                                                        ↓               │
│ [6.1 Stats] ← [6.2 Feedback Loop] ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←│
│      ↓                                                                  │
│ [6.3 Cleanup]                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY 7-9: OPTIONAL FEATURES                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ [7.1 Calendar Adapters] ─→ [7.2 Suggestion System]                       │
│ [8.1 Location Adapter] ─→ [8.2 Departure Escalation]                    │
│ [9.1 Sound Library]                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ PRIORITY 10: TESTING                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ [10.1 Unit Tests] ─ [10.2 Integration Tests] ─ [10.3 Adapter Mocks]   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Estimated Effort (Story Points)

| Priority | Feature | Points | Files |
|----------|---------|--------|-------|
| P1 | Complete SQLite Schema | 5 | `src/lib/database.py`, `src/lib/migrations.py` |
| P1 | Adapter Interfaces | 3 | `src/lib/adapters/base.py` |
| P1 | Chain Engine Completion | 5 | `src/lib/chain_engine.py` |
| P2 | LLM Adapter | 8 | `src/lib/adapters/llm_adapter.py`, `mock_llm_adapter.py` |
| P2 | TTS Adapter | 8 | `src/lib/adapters/tts_adapter.py`, `mock_tts_adapter.py` |
| P2 | Voice Personality Variations | 3 | `src/lib/voice_personalities.py` |
| P3 | Quick Add Flow | 5 | `src/lib/reminder_service.py` |
| P3 | Reminder CRUD | 5 | `src/lib/reminder_service.py`, `src/lib/anchor_service.py` |
| P4 | Notification System | 8 | `src/lib/notification_service.py` |
| P4 | T-0 Alarm | 3 | `src/lib/alarm_service.py` |
| P5 | Background Scheduling | 8 | `src/lib/scheduling/scheduler.py`, `recovery.py` |
| P5 | Snooze & Re-computation | 5 | `src/lib/snooze_service.py` |
| P5 | Dismissal & Feedback | 3 | `src/lib/feedback_service.py` |
| P6 | Stats System | 5 | `src/lib/stats_service.py` |
| P6 | Feedback Loop Adjustment | 3 | `src/lib/adjustment_service.py` |
| P6 | Data Retention | 2 | `src/lib/cleanup_service.py` |
| P7 | Calendar Adapters | 8 | `src/lib/adapters/calendar_adapter.py` |
| P7 | Suggestion System | 5 | `src/lib/suggestion_service.py` |
| P8 | Location Adapter | 5 | `src/lib/adapters/location_adapter.py` |
| P8 | Departure Escalation | 3 | `src/lib/location_service.py` |
| P9 | Sound Library | 5 | `src/lib/sound_service.py` |
| P10 | Unit Tests | 8 | `tests/` |
| P10 | Integration Tests | 8 | `tests/` |
| **TOTAL** | | **117** | |

---

## Next Steps

1. **Immediate**: Implement Priority 1 (Foundation) — schema, interfaces, chain engine
2. **Short-term**: Priority 2-3 (LLM/TTS, Quick Add)
3. **Medium-term**: Priority 4-6 (Notifications, Scheduling, Stats)
4. **Long-term**: Priority 7-9 (Calendar, Location, Sound)
5. **Continuous**: Priority 10 (Tests) throughout

---

## Validation Commands

```bash
# Start server
python3 src/test_server.py &

# Health check
curl http://localhost:8090/health

# Chain computation
curl "http://localhost:8090/chain?arrival=2026-04-09T09:00:00&duration=30"

# Parse natural language
curl -X POST http://localhost:8090/parse -H "Content-Type: application/json" -d '{"text":"Parker Dr 9am, 30 min drive"}'

# Create reminder
curl -X POST http://localhost:8090/reminders -H "Content-Type: application/json" -d '{"destination":"Parker Dr check-in","arrival_time":"2026-04-09T09:00:00","drive_duration":30}'

# Generate voice message
curl -X POST http://localhost:8090/voice/message -H "Content-Type: application/json" -d '{"personality":"coach","urgency_tier":"urgent","destination":"Parker Dr","drive_duration":30,"minutes_remaining":15}'

# Hit rate
curl http://localhost:8090/stats/hit-rate

# Run tests
python3 -m pytest tests/
```
