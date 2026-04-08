# Urgent Alarm - Implementation Plan

## Analysis Summary

**Current State:** The codebase has a minimal test server (`src/test_server.py`) with basic chain engine computation, keyword-based parsing, and voice message templates. The spec defines 14 comprehensive sections covering the full application.

**Gaps Identified:** Major gaps in database schema, LLM/TTS integration, notification system, background scheduling, calendar integration, location awareness, snooze/dismissal flow, history/stats, and sound library.

---

## Phase 1: Foundation (Schema, Core Engine, Tests)

### 1.1 Complete Database Schema
**Priority: CRITICAL** (all other features depend on this)
**Estimated Time: 2-4 hours**

| Task | Description |
|------|-------------|
| Add missing columns to `reminders` | `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id` |
| Add missing columns to `anchors` | `snoozed_to`, `tts_fallback`, `tts_clip_path` |
| Add missing columns to `history` | `actual_arrival`, `missed_reason`, `created_at` |
| Create `calendar_sync` table | `calendar_type`, `last_sync_at`, `sync_token`, `is_connected` |
| Create `custom_sounds` table | `id`, `filename`, `original_name`, `category`, `file_path`, `duration_seconds`, `created_at` |
| Create schema migrations | Versioned migration system (`schema_v1`, `schema_v2`, etc.) |
| Enable WAL mode | `PRAGMA journal_mode = WAL` |
| Enable foreign keys | `PRAGMA foreign_keys = ON` |

**Acceptance Criteria:**
- [ ] All spec tables and columns exist
- [ ] Cascade delete works for reminders → anchors
- [ ] In-memory test database works

---

### 1.2 Chain Engine Completeness
**Priority: CRITICAL**
**Estimated Time: 2-3 hours**

| Task | Description |
|------|-------------|
| Implement `get_next_unfired_anchor(reminder_id)` | Returns earliest unfired anchor after restart |
| Implement reminder status transitions | pending → active → completed/cancelled |
| Add `recompute_chain_after_snooze()` | Recompute remaining anchors after snooze |
| Add `get_unfired_anchors()` | Get all unfired anchors for recovery |
| Add chain determinism tests | Same inputs → same outputs |

**Acceptance Criteria:**
- [ ] `get_next_unfired_anchor` returns correct anchor
- [ ] All chain test scenarios (TC-01 through TC-06) pass

---

### 1.3 Unit Test Suite
**Priority: HIGH**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Create `src/lib/test_database.py` | Fresh in-memory DB for each test |
| Create `src/lib/test_chain_engine.py` | All chain engine test cases |
| Create `src/lib/test_parser.py` | Parser test cases (LLM mock + keyword) |
| Create `src/lib/test_voice_messages.py` | Voice personality message tests |
| Create `src/lib/test_stats.py` | Hit rate, streak, adjustments |

**Test Scenarios to Cover:**
- TC-01 through TC-06 (chain engine)
- TC-01 through TC-07 (parser)
- TC-01 through TC-06 (voice messages)
- TC-01 through TC-07 (stats)

---

## Phase 2: AI Integration (Parser & TTS)

### 2.1 LLM Adapter Interface
**Priority: HIGH**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Create `src/lib/adapters/llm_adapter.py` | `ILanguageModelAdapter` interface |
| Implement `MiniMaxAdapter` | MiniMax API (Anthropic-compatible) |
| Implement `AnthropicAdapter` | Anthropic API |
| Create `MockLLMAdapter` | Returns predefined fixture responses |
| Implement keyword fallback | When LLM API fails |
| Add prompt templates | System prompts for extraction schema |

**Acceptance Criteria:**
- [ ] All parser test scenarios pass
- [ ] Mock adapter returns fixture without API call
- [ ] Fallback produces confidence_score < 1.0

---

### 2.2 TTS Adapter Interface
**Priority: HIGH**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Create `src/lib/adapters/tts_adapter.py` | `ITTSAdapter` interface |
| Implement `ElevenLabsAdapter` | ElevenLabs API integration |
| Create `MockTTSAdapter` | Writes 1-second silent file |
| Implement cache management | `/tts_cache/{reminder_id}/` directory |
| Implement cache invalidation | Delete on reminder deletion |
| Implement fallback behavior | System sound + notification text on failure |

**Acceptance Criteria:**
- [ ] TTS clips cached per reminder
- [ ] Mock adapter works in tests
- [ ] Cache cleanup on reminder delete

---

### 2.3 Voice Personality Message Generator
**Priority: MEDIUM**
**Estimated Time: 2-3 hours**

| Task | Description |
|------|-------------|
| Implement message templates | 3 variations per tier per personality |
| Implement custom prompt support | User-written prompts (max 200 chars) |
| Implement destination interpolation | Context-aware messages |

**Acceptance Criteria:**
- [ ] 5 built-in personalities work correctly
- [ ] Custom prompt modifies message tone
- [ ] Message variation avoids repetition

---

## Phase 3: Persistence & Recovery

### 3.1 Background Scheduling Preparation
**Priority: MEDIUM**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Create `src/lib/scheduler.py` | Scheduler abstraction layer |
| Implement anchor registration | Register each anchor as pending task |
| Implement recovery scan | Fire overdue unfired anchors (≤15 min) |
| Implement pending re-registration | On app launch after crash |

**Acceptance Criteria:**
- [ ] Recovery scan drops anchors > 15 min overdue
- [ ] Late firing (>60s) triggers warning log

---

### 3.2 Snooze & Dismissal System
**Priority: HIGH**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Implement tap snooze (1 min) | Pause + re-fire after 1 minute |
| Implement custom snooze picker | 1, 3, 5, 10, 15 minute options |
| Implement chain re-computation | Shift remaining anchors by snooze duration |
| Implement re-registration | Re-register snoozed anchors with Notifee |
| Implement dismissal feedback | Prompt: "Was timing right?" |
| Implement feedback storage | Store in history table |

**Acceptance Criteria:**
- [ ] Tap snooze works
- [ ] Custom snooze re-computes chain
- [ ] Feedback adjusts drive_duration (+2 min per late)

---

## Phase 4: System Integration

### 4.1 Notification & Alarm Behavior
**Priority: MEDIUM**
**Estimated Time: 6-8 hours**

| Task | Description |
|------|-------------|
| Implement notification tiers | gentle → beep → siren → alarm |
| Implement DND awareness | Silent notifications during DND |
| Implement quiet hours | Suppress between user-configured times |
| Implement overdue anchor handling | Drop > 15 min overdue |
| Implement chain overlap serialization | Queue new anchors |
| Implement T-0 alarm looping | Loop until user action |

**Acceptance Criteria:**
- [ ] DND suppresses early anchors
- [ ] Final 5 minutes override DND
- [ ] T-0 loops until dismiss/snooze

---

### 4.2 Calendar Integration
**Priority: MEDIUM**
**Estimated Time: 8-12 hours**

| Task | Description |
|------|-------------|
| Create `src/lib/adapters/calendar_adapter.py` | `ICalendarAdapter` interface |
| Implement `AppleCalendarAdapter` | EventKit integration |
| Implement `GoogleCalendarAdapter` | Google Calendar API |
| Implement sync scheduler | On launch, every 15 min, background refresh |
| Implement suggestion cards | "Add departure reminder?" for events with location |
| Implement recurring event handling | Generate reminder for each occurrence |

**Acceptance Criteria:**
- [ ] Apple Calendar events with locations appear as suggestions
- [ ] Google Calendar events appear as suggestions
- [ ] Calendar permission denial shows explanation banner

---

### 4.3 Location Awareness
**Priority: LOW**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Implement origin capture | User-specified or current location |
| Implement single location check | At departure anchor fire |
| Implement geofence comparison | 500m radius |
| Implement escalation on presence | Fire firm/critical if at origin |
| Implement permission handling | Request at first location-aware reminder |

**Acceptance Criteria:**
- [ ] Single location check at departure anchor
- [ ] Within 500m triggers escalation
- [ ] No location history stored

---

## Phase 5: History & Stats

### 5.1 Complete History System
**Priority: MEDIUM**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Implement hit rate calculation | hits / (total - pending) for trailing 7 days |
| Implement streak tracking | Increment on hit, reset on miss |
| Implement common miss window | Most frequently missed urgency tier |
| Implement feedback loop | +2 min adjustment per late feedback (cap +15) |
| Implement 90-day retention | Archive old data |

**Acceptance Criteria:**
- [ ] Hit rate displays correctly (4 hits, 1 miss = 80%)
- [ ] Streak increments/resets correctly
- [ ] Feedback loop caps at +15 minutes

---

### 5.2 Sound Library
**Priority: LOW**
**Estimated Time: 4-6 hours**

| Task | Description |
|------|-------------|
| Implement built-in sounds | 5 sounds per category (commute, routine, errand) |
| Implement custom audio import | MP3, WAV, M4A (max 30 sec) |
| Implement sound picker UI | Per-reminder selection |
| Implement fallback behavior | Category default if custom sound missing |

**Acceptance Criteria:**
- [ ] Built-in sounds play without network
- [ ] Custom import appears in picker
- [ ] Corrupted sound falls back to default

---

## Phase 6: End-to-End Tests

### 6.1 Integration Tests
**Priority: HIGH**
**Estimated Time: 6-8 hours**

| Test | Description |
|------|-------------|
| Full reminder creation flow | parse → chain → TTS → persist |
| Anchor firing sequence | schedule → fire → mark fired |
| Snooze recovery | snooze → recompute → re-register |
| Feedback loop | dismiss → feedback → adjustment applied |

---

### 6.2 Scenario Validation
**Priority: HIGH**
**Estimated Time: 4-6 hours**

Run all scenario YAML files:
- `scenarios/chain-*.yaml` - 5 scenarios
- `scenarios/parse-*.yaml` - 4 scenarios
- `scenarios/voice-*.yaml` - 4 scenarios
- `scenarios/history-*.yaml` - 2 scenarios
- `scenarios/reminder-*.yaml` - 2 scenarios

---

## Priority Order Summary

| Phase | Tasks | Dependencies |
|-------|-------|--------------|
| **1. Foundation** | Schema, Chain Engine, Unit Tests | All other work |
| **2. AI Integration** | LLM Adapter, TTS Adapter, Message Generator | Foundation |
| **3. Persistence** | Scheduling, Snooze/Dismissal | Foundation |
| **4. System Integration** | Notifications, Calendar, Location | AI Integration |
| **5. History & Stats** | History System, Sound Library | Foundation |
| **6. E2E Tests** | Integration Tests, Scenario Validation | All previous phases |

---

## Quick Wins (First Week)

1. **Complete database schema** - Enables all other work
2. **Add missing chain engine functions** - Core business logic
3. **Create unit test suite** - Ensures correctness during development
4. **Implement LLM adapter interface** - Key differentiator feature

---

## Out of Scope (v1)

- Password reset / account management
- Smart home integration (Hue lights)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Automatic calendar adjustment based on feedback
- Sound recording in app
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
