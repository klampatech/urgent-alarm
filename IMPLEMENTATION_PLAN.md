# Urgent Alarm - Implementation Plan

## Analysis Summary (2026-04-08)

### Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Chain Engine** | ⚠️ PARTIAL | Basic computation works; missing `get_next_unfired_anchor()`, snooze recomputation |
| **Keyword Parser** | ⚠️ PARTIAL | Works for basic cases; no LLM adapter, no confidence scoring fallback |
| **Voice Messages** | ✅ DONE | All 5 personalities + templates implemented |
| **Database Schema** | ⚠️ INCOMPLETE | Missing: `origin_lat/lng/address`, `calendar_event_id`, `custom_sound_path`, `snoozed_to`, `tts_clip_path`, `tts_fallback`, `actual_arrival`, `missed_reason`, `calendar_sync` table, `custom_sounds` table |
| **Stats** | ⚠️ PARTIAL | Basic hit rate works; missing streaks, common miss window, feedback loop cap |
| **LLM Adapter** | ❌ MISSING | No interface, no mock implementation |
| **TTS Adapter** | ❌ MISSING | No interface, no caching |
| **Calendar Adapter** | ❌ MISSING | No EventKit or Google Calendar integration |
| **Location Awareness** | ❌ MISSING | No single-point check |
| **Snooze/Dismissal** | ❌ MISSING | No tap snooze, no chain recomputation |
| **Background Scheduling** | ❌ MISSING | No Notifee integration |
| **Notification System** | ❌ MISSING | No DND awareness, no quiet hours |
| **Unit Tests** | ❌ MISSING | harness/ directory is empty |

---

## Phase 1: Complete Foundation (CRITICAL)

### 1.1 Expand Database Schema
**Priority: CRITICAL** | **Effort: 2 hours**

The current schema is missing columns required by the spec. All other features depend on a complete schema.

**Tasks:**
- [ ] Add `reminders.origin_lat`, `reminders.origin_lng`, `reminders.origin_address`
- [ ] Add `reminders.custom_sound_path`, `reminders.calendar_event_id`
- [ ] Add `anchors.tts_clip_path`, `anchors.tts_fallback`, `anchors.snoozed_to`
- [ ] Add `history.actual_arrival`, `history.missed_reason`
- [ ] Create `calendar_sync` table (apple/google sync state)
- [ ] Create `custom_sounds` table (imported audio files)
- [ ] Add cascade delete for reminders→anchors
- [ ] Enable foreign keys (`PRAGMA foreign_keys = ON`)
- [ ] Enable WAL mode (`PRAGMA journal_mode = WAL`)

**Spec Reference:** Section 13.2 Schema

---

### 1.2 Complete Chain Engine Functions
**Priority: CRITICAL** | **Effort: 3 hours**

Current chain engine works for basic computation but lacks recovery functions.

**Tasks:**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` — returns earliest unfired anchor
- [ ] Implement `get_unfired_anchors(reminder_id)` — returns all unfired for recovery scan
- [ ] Implement `recompute_chain_after_snooze(reminder_id, snooze_duration)` — shifts remaining anchors
- [ ] Implement reminder status transitions: pending → active → completed/cancelled
- [ ] Add chain determinism tests (same inputs → same outputs)
- [ ] Add validation: `arrival_time > departure_time + minimum_drive_time`

**Spec Reference:** Section 2.3 (Functional Requirements 1-7)

---

### 1.3 Create Unit Test Suite
**Priority: CRITICAL** | **Effort: 4 hours**

No tests exist. The harness/ directory is empty.

**Tasks:**
- [ ] Create `src/lib/test_database.py` — in-memory DB fixture with all migrations
- [ ] Create `src/lib/test_chain_engine.py` — TC-01 through TC-06
- [ ] Create `src/lib/test_parser.py` — TC-01 through TC-07 (LLM mock + keyword fallback)
- [ ] Create `src/lib/test_voice_messages.py` — all personalities, message variations
- [ ] Create `src/lib/test_stats.py` — hit rate, streaks, adjustments, cap logic
- [ ] Create `src/lib/test_snooze.py` — chain recomputation, snooze persistence

**Test Coverage Target:** All spec acceptance criteria mapped to tests

**Spec Reference:** Section 14 Definition of Done

---

## Phase 2: AI Integration (HIGH)

### 2.1 LLM Adapter Interface
**Priority: HIGH** | **Effort: 4 hours**

**Tasks:**
- [ ] Create `src/lib/adapters/llm_adapter.py` with `ILanguageModelAdapter` interface
- [ ] Implement `MiniMaxAdapter` (MiniMax API, Anthropic-compatible)
- [ ] Implement `AnthropicAdapter` (Anthropic API)
- [ ] Create `MockLLMAdapter` for tests (returns fixture, no API call)
- [ ] Implement keyword fallback when LLM fails (confidence < 1.0)
- [ ] Add prompt templates for extraction schema

**Spec Reference:** Section 3.3 (Functional Requirements 1-8)

---

### 2.2 TTS Adapter Interface
**Priority: HIGH** | **Effort: 4 hours**

**Tasks:**
- [ ] Create `src/lib/adapters/tts_adapter.py` with `ITTSAdapter` interface
- [ ] Implement `ElevenLabsAdapter` (ElevenLabs API)
- [ ] Create `MockTTSAdapter` for tests (writes silent file)
- [ ] Implement cache management (`/tts_cache/{reminder_id}/`)
- [ ] Implement cache invalidation on reminder deletion
- [ ] Implement fallback: system sound + notification text on failure

**Spec Reference:** Section 4.3 (Functional Requirements 1-9)

---

### 2.3 Message Variation System
**Priority: MEDIUM** | **Effort: 2 hours**

**Tasks:**
- [ ] Create 3+ message variations per tier per personality
- [ ] Implement random/rotating selection
- [ ] Add custom prompt support (max 200 chars)
- [ ] Add destination interpolation with context

**Spec Reference:** Section 10.3 (FR 1-8)

---

## Phase 3: Persistence & Recovery (HIGH)

### 3.1 Background Scheduling
**Priority: HIGH** | **Effort: 6 hours**

**Tasks:**
- [ ] Create `src/lib/scheduler.py` — scheduler abstraction layer
- [ ] Implement anchor registration with Notifee (iOS BGTaskScheduler + Android WorkManager)
- [ ] Implement recovery scan on app launch (fire ≤15 min overdue)
- [ ] Implement pending anchor re-registration after crash
- [ ] Add late firing warning (>60s after scheduled time)

**Spec Reference:** Section 6.3 (FR 1-8)

---

### 3.2 Snooze & Dismissal System
**Priority: HIGH** | **Effort: 4 hours**

**Tasks:**
- [ ] Implement tap snooze (1 minute)
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement chain re-computation on snooze (shift remaining anchors)
- [ ] Implement re-registration with Notifee
- [ ] Implement dismissal feedback prompt ("Was timing right?")
- [ ] Store feedback in history table
- [ ] TTS confirmation: "Okay, snoozed X minutes"

**Spec Reference:** Section 9.3 (FR 1-9)

---

## Phase 4: System Integration (MEDIUM)

### 4.1 Notification & Alarm Behavior
**Priority: MEDIUM** | **Effort: 6 hours**

**Tasks:**
- [ ] Implement notification tier escalation: gentle → beep → siren → alarm
- [ ] Implement DND awareness (silent notifications during DND)
- [ ] Implement quiet hours suppression (10pm-7am default)
- [ ] Implement overdue anchor handling (drop >15 min overdue)
- [ ] Implement chain overlap serialization (queue new anchors)
- [ ] Implement T-0 alarm looping until user action

**Spec Reference:** Section 5.3 (FR 1-8)

---

### 4.2 Calendar Integration
**Priority: MEDIUM** | **Effort: 10 hours**

**Tasks:**
- [ ] Create `src/lib/adapters/calendar_adapter.py` with `ICalendarAdapter`
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement sync scheduler (on launch, every 15 min, background refresh)
- [ ] Implement suggestion cards for events with locations
- [ ] Implement recurring event handling
- [ ] Handle permission denial with explanation banner

**Spec Reference:** Section 7.3 (FR 1-9)

---

### 4.3 Location Awareness
**Priority: LOW** | **Effort: 4 hours**

**Tasks:**
- [ ] Capture origin (user-specified or current location at creation)
- [ ] Implement single location check at departure anchor fire
- [ ] Implement geofence comparison (500m radius)
- [ ] Implement escalation: fire firm/critical if at origin
- [ ] Request permission at first location-aware reminder

**Spec Reference:** Section 8.3 (FR 1-8)

---

## Phase 5: History & Stats (MEDIUM)

### 5.1 Complete Feedback Loop
**Priority: MEDIUM** | **Effort: 4 hours**

**Tasks:**
- [ ] Implement streak tracking (increment on hit, reset on miss)
- [ ] Implement common miss window (most frequently missed tier)
- [ ] Implement feedback loop adjustment (+2 min per late, cap +15)
- [ ] Implement 90-day retention with archiving

**Spec Reference:** Section 11.3 (FR 1-7)

---

### 5.2 Sound Library
**Priority: LOW** | **Effort: 4 hours**

**Tasks:**
- [ ] Bundle built-in sounds (5 per category: commute, routine, errand)
- [ ] Implement custom audio import (MP3, WAV, M4A, max 30 sec)
- [ ] Implement sound picker UI (per-reminder selection)
- [ ] Implement fallback behavior (category default if corrupted)

**Spec Reference:** Section 12.3 (FR 1-8)

---

## Phase 6: Scenario Validation (HIGH)

### 6.1 Run All Scenarios
**Priority: HIGH** | **Effort: 4 hours**

**Tasks:**
- [ ] Run chain scenarios (5): full, compressed, minimum, invalid
- [ ] Run parse scenarios (3): natural language, simple countdown, tomorrow
- [ ] Run voice scenarios (3): coach, no-nonsense, all personalities
- [ ] Run history scenarios (2): record outcome, miss feedback
- [ ] Run reminder scenarios (2): CRUD, cascade delete
- [ ] Run stats scenarios (1): hit rate

**Scenario Files:** `scenarios/*.yaml`

---

## Quick Wins (First Week)

1. **Complete database schema** — Enables all other work
2. **Add chain engine recovery functions** — Core business logic
3. **Create unit test suite** — Ensures correctness during development
4. **Implement LLM adapter interface** — Key differentiator feature

---

## Out of Scope (v1)

- Password reset / account management
- Smart home integration (Hue lights)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Automatic calendar adjustment
- Sound recording in app
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations

---

## Priority Order Summary

| Phase | Tasks | Dependencies |
|-------|-------|--------------|
| **1. Foundation** | Schema, Chain Engine, Unit Tests | All other work |
| **2. AI Integration** | LLM Adapter, TTS Adapter, Message Variations | Foundation |
| **3. Persistence** | Scheduling, Snooze/Dismissal | Foundation |
| **4. System Integration** | Notifications, Calendar, Location | AI Integration |
| **5. History & Stats** | Feedback Loop, Sound Library | Foundation |
| **6. E2E Tests** | Scenario Validation | All previous phases |