# Implementation Plan: Urgent — AI Escalating Voice Alarm

## Gap Analysis Summary

The current codebase (`src/test_server.py`) is a **minimal Python HTTP test server** with basic chain computation, keyword parsing, and SQLite storage. The full spec requires a production React Native/Flutter mobile app with 13 major subsystems. This plan focuses on building out the **Python backend/service layer** as a foundation before mobile app development.

---

## Phase 1: Core Infrastructure (Foundation)

### 1.1 Complete SQLite Schema & Migrations
**Priority: P0 (Blocking all other work)**

| Task | Description |
|------|-------------|
| Add missing columns to `reminders` | `sound_category`, `selected_sound`, `custom_sound_path`, `origin_lat`, `origin_lng`, `origin_address`, `calendar_event_id` |
| Add missing columns to `anchors` | `tts_fallback`, `snoozed_to` |
| Add missing columns to `history` | `actual_arrival`, `missed_reason` |
| Create missing tables | `custom_sounds`, `calendar_sync` |
| Implement migration system | Sequential, versioned migrations with schema tracking |
| Enable WAL mode & FK enforcement | `PRAGMA journal_mode = WAL`, `PRAGMA foreign_keys = ON` |
| Implement cascade deletes | Reminders → Anchors cascade |

**Acceptance:** Fresh install applies all migrations; in-memory test DB works; cascade deletes verified.

---

### 1.2 Escalation Chain Engine — Complete
**Priority: P0 (Core app logic)**

| Task | Description |
|------|-------------|
| Implement `get_next_unfired_anchor(reminder_id)` | Returns earliest unfired anchor for recovery |
| Add anchor sorting | Ensure anchors are stored sorted by timestamp |
| Add deterministic unit tests | Same inputs → same outputs |
| Add validation for `drive_duration > time_to_arrival` | Reject invalid chains |

**Acceptance:** TC-01 through TC-06 from spec Section 2.5 all pass.

---

### 1.3 Reminder Parser — Complete with LLM Adapter Interface
**Priority: P0 (User-facing Quick Add feature)**

| Task | Description |
|------|-------------|
| Define `ILanguageModelAdapter` interface | Abstract base for mock and real adapters |
| Implement `MockLLMAdapter` | Returns predefined fixture responses for tests |
| Implement `AnthropicLLMAdapter` | Real API call to Anthropic/MiniMax |
| Implement keyword extraction fallback | Comprehensive regex for all specified formats |
| Add "tomorrow" date resolution | Correctly handles dates |
| Add `reminder_type` extraction | countdown_event, simple_countdown, morning_routine, standing_recurring |
| Add confidence scoring | Return confidence < 1.0 on fallback |
| Add field correction support | User can edit any parsed field |

**Acceptance:** TC-01 through TC-07 from spec Section 3.5 all pass.

---

## Phase 2: Voice & TTS System

### 2.1 TTS Adapter Interface
**Priority: P1**

| Task | Description |
|------|-------------|
| Define `ITTSAdapter` interface | Abstract base for mock and real adapters |
| Implement `MockTTSAdapter` | Writes silent audio file locally for tests |
| Implement `ElevenLabsTTSAdapter` | Real API integration with caching |
| Implement TTS cache directory | `/tts_cache/{reminder_id}/` structure |
| Implement cache invalidation | Delete TTS files when reminder deleted |
| Implement fallback on TTS failure | System sound + notification text |

**Acceptance:** TC-01 through TC-05 from spec Section 4.5 all pass.

---

### 2.2 Voice Personality System
**Priority: P1**

| Task | Description |
|------|-------------|
| Map personalities to ElevenLabs voice IDs | coach, assistant, best_friend, no_nonsense, calm, custom |
| Implement custom prompt support | User-written prompt appended to system prompt (max 200 chars) |
| Implement message variation generation | Minimum 3 variations per tier per personality |
| Store personality per reminder | Existing reminders retain personality at creation time |

**Acceptance:** TC-01 through TC-05 from spec Section 10.5 all pass.

---

## Phase 3: Snooze, Dismissal & Chain Recomputation

### 3.1 Snooze & Dismissal Flow
**Priority: P1**

| Task | Description |
|------|-------------|
| Implement 1-minute tap snooze | Pause current anchor, re-fire after 1 min |
| Implement custom snooze picker | 1, 3, 5, 10, 15 minute options |
| Implement chain re-computation on snooze | Shift remaining anchors by snooze duration |
| Implement snooze persistence | Survive app restart |
| Implement dismissal feedback prompt | "Was timing right?" Yes/No + "What was wrong?" flow |
| Implement TTS snooze confirmation | "Okay, snoozed X minutes" |

**Acceptance:** TC-01 through TC-06 from spec Section 9.5 all pass.

---

### 3.2 Feedback Loop & Destination Adjustments
**Priority: P1**

| Task | Description |
|------|-------------|
| Apply drive_duration adjustment on "Left too late" | +2 minutes per miss, capped at +15 min |
| Implement "Left too early" adjustment | -2 minutes per early arrival, floor at original |
| Apply adjustments to new reminders | Suggest adjusted drive_duration |

**Acceptance:** TC-02 and TC-03 from spec Section 11.5 pass.

---

## Phase 4: Notification & Alarm Behavior

### 4.1 Notification Layer
**Priority: P2**

| Task | Description |
|------|-------------|
| Implement urgency tier → sound mapping | gentle chime → pointed beep → urgent siren → looping alarm |
| Implement DND handling | Early anchors = silent; final 5 min = visual override + vibration |
| Implement quiet hours suppression | 10pm–7am default, configurable |
| Implement 15-minute overdue drop rule | Anchors > 15 min overdue are dropped |
| Implement chain overlap serialization | Queue new anchors until current chain completes |
| Implement T-0 alarm looping | Loop until user dismisses/snoozes |
| Implement post-DND/quiet-hours catch-up | Fire queued anchors when restriction ends |

**Acceptance:** TC-01 through TC-06 from spec Section 5.5 all pass.

---

## Phase 5: Background Scheduling

### 5.1 Background Task Integration
**Priority: P2**

| Task | Description |
|------|-------------|
| Define `ISchedulerAdapter` interface | Abstract for Notifee integration |
| Implement `NotifeeSchedulerAdapter` | Register anchors with Notifee |
| Implement recovery scan on launch | Fire overdue anchors within 15-min window |
| Implement late-fire warning | Log if anchor fires > 60s late |
| Implement pending anchor re-registration | After crash/force-kill recovery |
| Implement anchor logging | Log missed anchors with `missed_reason` |

**Acceptance:** TC-01 through TC-06 from spec Section 6.5 all pass.

---

## Phase 6: Calendar & Location Integration

### 6.1 Calendar Integration
**Priority: P2**

| Task | Description |
|------|-------------|
| Define `ICalendarAdapter` interface | Abstract for calendar integrations |
| Implement `AppleCalendarAdapter` | EventKit integration (iOS) |
| Implement `GoogleCalendarAdapter` | Google Calendar API integration |
| Implement calendar sync scheduler | On launch + every 15 min |
| Implement suggestion card generation | Surface events with locations |
| Implement calendar-sourced reminder creation | Create countdown_event from event data |
| Implement permission denial handling | Explanation banner + settings link |
| Implement graceful degradation | Manual reminders work even if calendar fails |

**Acceptance:** TC-01 through TC-06 from spec Section 7.5 all pass.

---

### 6.2 Location Awareness
**Priority: P3**

| Task | Description |
|------|-------------|
| Define `ILocationAdapter` interface | Abstract for location integrations |
| Implement `CoreLocationAdapter` (iOS) | Single location check at departure |
| Implement `FusedLocationAdapter` (Android) | Single location check at departure |
| Implement 500m geofence check | At origin if within 500m |
| Implement location-based escalation | Fire firm/critical immediately if still at origin |
| Implement on-demand permission request | Request at first location-aware reminder creation |
| Implement location data cleanup | No location history retained |

**Acceptance:** TC-01 through TC-05 from spec Section 8.5 all pass.

---

## Phase 7: Sound Library

### 7.1 Sound Library
**Priority: P3**

| Task | Description |
|------|-------------|
| Bundle built-in sounds | 5 per category (Commute, Routine, Errand) |
| Implement custom sound import | MP3, WAV, M4A up to 30 seconds |
| Implement sound transcoding | Normalize to app format |
| Implement per-reminder sound selection | Override category default |
| Implement corrupted sound fallback | Category default + error log |

**Acceptance:** TC-01 through TC-05 from spec Section 12.5 all pass.

---

## Phase 8: History & Stats

### 8.1 Complete Stats System
**Priority: P2**

| Task | Description |
|------|-------------|
| Implement hit rate calculation | trailing 7 days, formula from spec |
| Implement common miss window | Identify most frequently missed tier |
| Implement streak counter | Increment on hit, reset on miss |
| Implement 90-day retention policy | Archive old data |
| Implement stats derivation from history | No separate stats table |

**Acceptance:** TC-01 through TC-07 from spec Section 11.5 all pass.

---

## Phase 9: Mobile App Shell

### 9.1 React Native/Flutter Project Setup
**Priority: P2 (Can parallelize with Phase 1-5)**

| Task | Description |
|------|-------------|
| Initialize React Native project | iOS + Android targets |
| Set up navigation | Tab-based: Home, Calendar, History, Settings |
| Implement Quick Add UI | Text/speech input → confirmation card |
| Implement reminder list view | Active reminders with status |
| Implement settings screen | Voice personality, quiet hours, sounds |
| Implement notification handlers | React to Notifee/FCM events |

---

## Task Ordering (Dependency Graph)

```
[1.1] Complete Schema & Migrations
        ↓
[1.2] Complete Chain Engine ─────────→ [3.1] Snooze & Dismissal
        ↓                               ↓
[1.3] Complete Parser ──────────────→ [3.2] Feedback Loop
        ↓                               ↓
[2.1] TTS Adapter ─────────────────→ [4.1] Notification Layer
        ↓                               ↓
[2.2] Voice Personality ────────────→ [5.1] Background Scheduling
        ↓                               ↓
[6.1] Calendar Integration ◄─────────┤
        │                              ↓
[6.2] Location Awareness ───────────→ [7.1] Sound Library
                                            ↓
                                      [8.1] Complete Stats
                                            ↓
                                      [9.1] Mobile App Shell
```

---

## Immediate Next Steps

1. **Migrate `test_server.py` to proper module structure** (`src/lib/`)
2. **Implement migration system** with `schema_version` tracking
3. **Add missing columns and tables** to match spec schema
4. **Write unit tests** for chain engine determinism
5. **Create adapter interfaces** (`ILanguageModelAdapter`, `ITTSAdapter`, `ISchedulerAdapter`, `ICalendarAdapter`, `ILocationAdapter`)
6. **Commit: "Foundation: schema migrations + core chain engine"**

---

## Notes

- **Spec vs. Implementation Gap:** The current `test_server.py` demonstrates concept feasibility but is not production-ready. Full spec requires 13 subsystems, most of which are unimplemented.
- **Mobile vs. Backend:** This plan treats the Python service layer as the implementation target (matching `test_server.py` pattern). Mobile app (React Native/Flutter) should be a separate phase.
- **LLM/TTS APIs:** Real API integration (Anthropic, ElevenLabs) should be configurable via environment variables with mocks used in tests.
- **Scope exclusions (per spec):** No auth, no smart home, no voice reply, no multi-device sync, no Bluetooth routing in v1.
