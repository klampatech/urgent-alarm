# Implementation Plan — Urgent Voice Alarm App

## Overview

Analysis of `specs/*.md` vs current `src/*.py` codebase reveals significant gaps. The Python test server has partial implementations with critical bugs, the test harness is completely missing (blocking Otto loop), and most feature systems are not yet implemented.

**Gap Analysis Date:** 2026-04-08

**Analyzed By:** pi-coding-agent

---

## Executive Summary

| Category | Status | Gap Count |
|----------|--------|-----------|
| Core Logic | ⚠️ Partial + Buggy | 1 critical bug, 2 incomplete |
| Adapters (LLM/TTS) | ❌ Missing | 2 interfaces not implemented |
| Infrastructure | ⚠️ Partial | 2 incomplete |
| Mobile Features | ❌ Missing | 5 systems not implemented |
| Test Infrastructure | ❌ Missing | Blocking all validation |

**Critical Path:** Chain engine bugs → Test harness → Database schema → Remaining features

---

## Current State Assessment

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| HTTP Test Server | `src/test_server.py` | ⚠️ 627 lines | Partial - has bugs |
| Chain Engine | `src/test_server.py:101-180` | ❌ **BUGGY** | Wrong timestamps, duplicates |
| Keyword Parser | `src/test_server.py:183-270` | ⚠️ Partial | Limited regex |
| Voice Templates | `src/test_server.py:273-380` | ⚠️ Partial | 1 variation per tier |
| Stats Calculator | `src/test_server.py:383-400` | ⚠️ Partial | Basic hit rate only |
| DB Schema | `src/test_server.py:19-97` | ⚠️ Partial | Missing columns |
| Test Harness | `harness/` | ❌ **EMPTY** | BLOCKS validation |
| Lib Modules | `src/lib/` | ❌ **MISSING** | No module structure |
| Scenarios | `scenarios/` | 15 YAML files | Ready but cannot run |
| Tests | `tests/` | ❌ **MISSING** | None exist |

---

## ⚠️ CRITICAL ISSUES

### Critical Issue 1: Chain Engine Produces Wrong Timestamps

**Severity:** CRITICAL - Breaks core functionality

**Location:** `src/test_server.py`, function `compute_escalation_chain()`

**Issue:** The chain engine computes anchor timestamps incorrectly, producing wrong times, missing anchors, and duplicate timestamps.

**Spec Requirements (Section 2.3):**
| Buffer Size | Anchors | Tiers |
|-------------|---------|-------|
| ≥25 min | 8 | calm, casual, pointed, urgent, pushing, firm, critical, alarm |
| 20-24 min | 7 | casual, pointed, urgent, pushing, firm, critical, alarm |
| 10-19 min | 5 | urgent, pushing, firm, critical, alarm |
| 5-9 min | 3 | firm, critical, alarm |
| 1-4 min | 3 | firm, critical, alarm |
| 0 min | 1 | alarm |

**Current Bugs (verified via code analysis):**

1. **10-min buffer produces wrong timestamps:**
   - Expected: T-10=08:50, T-5=08:55, T-1=08:59, T-0=09:00
   - Actual: Uses `drive_duration - X` formula that doesn't align with absolute thresholds

2. **3-min buffer missing critical anchor:**
   - Expected: T-2=08:57, T-1=08:59, T-0=09:00
   - Actual: Only 2 anchors, missing critical at T-1

3. **6-min buffer produces duplicate timestamps:**
   - Expected: T-5=08:55, T-1=08:59, T-0=09:00
   - Actual: DUPLICATE T-5 timestamps (violates DB UNIQUE constraint)

**Root Cause:** The `minutes_before` calculation uses relative offsets from drive_duration instead of absolute thresholds from arrival time.

**Fix Required:** Rewrite anchor generation to use absolute `minutes_before` thresholds per spec.

---

### Critical Issue 2: Test Harness Missing (BLOCKING Otto Loop)

**Severity:** BLOCKING - No validation possible

**Location:** `harness/` directory is empty

**Issue:** Without `scenario_harness.py`, the Otto loop cannot:
- Execute the 15 validation scenarios in `scenarios/`
- Write results to `/tmp/ralph-scenario-result.json`
- Validate any work after git push

**Required by Otto Loop:**
```bash
sudo python3 harness/scenario_harness.py --project $(basename "$(git rev-parse --show-toplevel)")`
```

---

## Priority 1: Foundation (Must Complete First)

### 1.1 Fix Chain Engine Bugs
**Files to modify:** `src/test_server.py`

**Spec Reference:** Section 2 — Escalation Chain Engine

**Tasks:**
- [ ] Rewrite `compute_escalation_chain()` to use absolute `minutes_before` thresholds
- [ ] Ensure no duplicate timestamps (critical for DB UNIQUE constraint)
- [ ] Ensure minimum chain (≤5 min) produces 3 anchors: T-(buffer-1), T-1, T-0
- [ ] Validate all buffer sizes produce correct anchor counts and timestamps
- [ ] Add unit tests verifying determinism (same inputs = same outputs)
- [ ] Ensure anchors sorted by timestamp ascending

**Acceptance Criteria (Spec Section 2.4):**
- [ ] 30 min buffer → 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] 10 min buffer → 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] 3 min buffer → 3 anchors: 8:57, 8:59, 9:00
- [ ] Invalid chain rejected with validation error
- [ ] `get_next_unfired_anchor()` correctly returns earliest unfired anchor

**Test Scenarios (Spec Section 2.5):**
- [ ] TC-01: Full chain generation (≥25 min buffer)
- [ ] TC-02: Compressed chain (10-24 min buffer)
- [ ] TC-03: Minimum chain (≤5 min buffer)
- [ ] TC-04: Invalid chain rejection
- [ ] TC-05: Next unfired anchor recovery
- [ ] TC-06: Chain determinism

---

### 1.2 Create Test Harness Infrastructure
**Files to create:** `harness/scenario_harness.py`, `harness/__init__.py`

**Spec Reference:** Section 14 — Definition of Done

**Tasks:**
- [ ] Create `ScenarioHarness` class that loads YAML scenarios from `/var/otto-scenarios/[project]/`
- [ ] Implement scenario step executor (HTTP API calls to test_server.py)
- [ ] Implement assertion validators:
  - `http_status` - validate HTTP status codes
  - `db_record` - validate database records exist with conditions
  - `llm_judge` - call LLM to evaluate output quality
- [ ] Create `MockLanguageModelAdapter` for test fixtures
- [ ] Create `MockTTSAdapter` for test fixtures
- [ ] Create `getInMemoryDatabase()` helper
- [ ] Write result to `/tmp/ralph-scenario-result.json` after run
- [ ] Support running single scenario or all scenarios
- [ ] Report pass/fail per assertion and overall scenario

**Verification:**
- [ ] `python3 -m py_compile harness/scenario_harness.py src/test_server.py` passes
- [ ] All 15 scenarios in `scenarios/` execute without error
- [ ] `/tmp/ralph-scenario-result.json` contains valid JSON with pass/fail

---

### 1.3 Complete Database Schema Migration System
**Files to create:** `src/lib/db/`, migration files

**Spec Reference:** Section 13 — Data Persistence

**Current Schema Gaps:**
| Table | Column | Status |
|-------|--------|--------|
| reminders | origin_lat, origin_lng, origin_address | ❌ Missing |
| reminders | calendar_event_id, custom_sound_path | ❌ Missing |
| reminders | tts_cache_dir | ❌ Missing |
| anchors | tts_fallback, snoozed_to | ❌ Missing |
| history | actual_arrival, missed_reason | ❌ Missing |
| user_preferences | updated_at | ❌ Missing |
| destination_adjustments | updated_at | ❌ Missing |
| **calendar_sync** | table | ❌ Missing |
| **custom_sounds** | table | ❌ Missing |
| All | WAL mode, FK enforcement | ❌ Not enabled |
| **schema_version** | tracking table | ❌ Missing |

**Tasks:**
- [ ] Create `schema_version` tracking table
- [ ] Create migration runner with sequential versioned migrations (v1, v2, etc.)
- [ ] Create all spec-compliant tables in migration order
- [ ] Enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`
- [ ] Ensure cascade deletes work correctly
- [ ] Create `DatabaseConnection` class with `getInMemoryInstance()` for tests
- [ ] All timestamps in ISO 8601 format
- [ ] UUID v4 for all primary keys

**Verification:**
- [ ] Fresh install applies all migrations in order
- [ ] In-memory test database starts empty with all migrations applied
- [ ] Deleting a reminder cascades to delete its anchors
- [ ] Foreign key violation returns error without crashing

---

### 1.4 Refactor Monolithic test_server.py
**Files to create:** `src/lib/` modules

**Tasks:**
- [ ] Create `src/lib/__init__.py`
- [ ] Create `src/lib/chain/__init__.py`, `src/lib/chain/engine.py`
- [ ] Create `src/lib/parser/__init__.py`, `src/lib/parser/nl_parser.py`, `src/lib/parser/keyword_extractor.py`
- [ ] Create `src/lib/voice/__init__.py`, `src/lib/voice/personalities.py`
- [ ] Create `src/lib/stats/__init__.py`, `src/lib/stats/calculator.py`
- [ ] Create `src/lib/db/__init__.py`, `src/lib/db/connection.py`, `src/lib/db/migrations.py`
- [ ] Refactor `test_server.py` to import from `src/lib/`
- [ ] Ensure backward compatibility with existing API endpoints

**Verification:**
- [ ] `python3 -m py_compile src/lib/**/*.py` passes
- [ ] Server starts and serves existing endpoints after refactoring

---

## Priority 2: Core Domain Logic

### 2.1 LLM Adapter + Parser Enhancement
**Files to create/modify:** `src/lib/parser/`

**Spec Reference:** Section 3 — Reminder Parsing & Creation

**Current Gaps:**
| Feature | Status |
|---------|--------|
| ILanguageModelAdapter interface | ❌ Missing |
| MiniMax/Anthropic API adapter | ❌ Missing |
| MockLanguageModelAdapter | ❌ Missing |
| All keyword extraction formats | ⚠️ Partial |
| Confidence scoring | ⚠️ Partial |
| reminder_type enum detection | ❌ Missing |
| User confirmation flow | ❌ Missing |

**Tasks:**
- [ ] Create `ILanguageModelAdapter` abstract interface
- [ ] Create `MiniMaxAdapter` and `AnthropicAdapter` implementations
- [ ] Create `MockLanguageModelAdapter` for tests
- [ ] Improve keyword extractor for all spec formats
- [ ] Implement confidence scoring and LLM fallback
- [ ] Implement `parse_and_confirm()` for UI review
- [ ] Handle "tomorrow" date resolution
- [ ] Detect reminder_type enum (countdown_event, simple_countdown, etc.)

**Acceptance Criteria (Spec Section 3.4):**
- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses correctly
- [ ] "dryer in 3 min" parses as simple_countdown
- [ ] "meeting tomorrow 2pm, 20 min drive" parses with correct date
- [ ] LLM failure falls back to keyword extraction with confidence < 1.0
- [ ] User can edit any parsed field and confirm
- [ ] Empty input returns user-facing error

---

### 2.2 Chain Engine Completeness (post-bug-fix)
**Files to modify:** `src/lib/chain/engine.py`

**Tasks (after 1.1):**
- [ ] Implement `get_next_unfired_anchor(reminder_id)` query
- [ ] Add TTS clip path tracking per anchor
- [ ] Add fire_count increment on retry
- [ ] Add chain validation per spec
- [ ] Make chain computation pure (accept `now` parameter)

---

## Priority 3: Voice & TTS System

### 3.1 TTS Adapter Interface + Cache
**Files to create:** `src/lib/tts/`

**Spec Reference:** Section 4 — Voice & TTS Generation

**Tasks:**
- [ ] Create `ITTSAdapter` interface
- [ ] Create `ElevenLabsAdapter` implementation
- [ ] Create `MockTTSAdapter` for tests
- [ ] Create cache manager with `/tts_cache/{reminder_id}/` structure
- [ ] Implement `generate_tts_for_anchors()`
- [ ] Implement fallback when API unavailable
- [ ] Implement cache invalidation on reminder delete
- [ ] TTS generation within 30 seconds

**Acceptance Criteria (Spec Section 4.4):**
- [ ] New reminder generates MP3 clips in `/tts_cache/{reminder_id}/`
- [ ] Playing anchor fires correct pre-generated clip from cache
- [ ] ElevenLabs failure falls back to system sound
- [ ] Reminder deletion removes all cached TTS files

---

### 3.2 Voice Personality Message Variations
**Files to modify:** `src/lib/voice/personalities.py`

**Spec Reference:** Section 10 — Voice Personality System

**Current:** 1 template per tier per personality
**Required:** 3+ templates per tier per personality

**Tasks:**
- [ ] Expand each personality to 3+ templates per urgency tier
- [ ] Add random selection for variation
- [ ] Implement custom prompt mode (max 200 chars)
- [ ] Ensure existing reminders retain personality at creation

**Acceptance Criteria (Spec Section 10.4):**
- [ ] Coach at T-5 produces motivating message with exclamation
- [ ] No-nonsense at T-5 produces brief, direct message
- [ ] Custom prompt modifies message tone appropriately
- [ ] 3+ message variations per urgency tier per personality

---

## Priority 4: Notification & Alarm Behavior

### 4.1 Notification Tier System
**Files to create:** `src/lib/notifications/`

**Spec Reference:** Section 5 — Notification & Alarm Behavior

**Tasks:**
- [ ] Create notification tier definitions (gentle chime → alarm escalation)
- [ ] Create `SoundPlayer` for sound under TTS
- [ ] Add DND check (silent early, visual+vibration for final 5 min)
- [ ] Add quiet hours suppression (default 10pm-7am)
- [ ] Queue anchors if another chain is firing
- [ ] Loop T-0 alarm until user acts

**Acceptance Criteria (Spec Section 5.4):**
- [ ] Notification tier escalates with urgency
- [ ] DND respected
- [ ] Quiet hours suppress nudges
- [ ] Anchors >15 min overdue dropped
- [ ] Chain overlap serialized
- [ ] T-0 alarm loops until action

---

## Priority 5: Background Scheduling

### 5.1 Scheduling Service (Stub for Python Server)
**Files to create:** `src/lib/scheduling/`

**Spec Reference:** Section 6 — Background Scheduling & Reliability

**Tasks:**
- [ ] Create `SchedulingService` interface
- [ ] Create `schedule_anchor()`, `cancel_anchor()` functions
- [ ] Create recovery scan with 15-min grace window
- [ ] Drop overdue anchors and log missed_reason
- [ ] Re-register pending anchors on restart
- [ ] Log warning for late firing (>60 seconds)

**Acceptance Criteria (Spec Section 6.4):**
- [ ] All anchors scheduled correctly in Notifee
- [ ] App closed doesn't prevent anchors from firing
- [ ] Recovery scan fires only anchors within grace window
- [ ] Late firing (>60s) triggers warning log

---

## Priority 6-10: Additional Systems

| Priority | System | Status | Key Gaps |
|----------|--------|--------|----------|
| 6 | Calendar Integration | ❌ Missing | EventKit, Google Calendar adapters |
| 7 | Location Awareness | ❌ Missing | 500m geofence check at departure |
| 8 | Snooze & Dismissal | ⚠️ Partial | No snooze picker, no chain recompute |
| 9 | History & Stats | ⚠️ Partial | Missing feedback loop, streaks |
| 10 | Sound Library | ❌ Missing | No built-in sounds, no import |

---

## 🚨 Critical Path

```
IMMEDIATE:
├── 1.1 Fix Chain Engine Bugs ← CRITICAL (wrong timestamps)
└── 1.2 Create Test Harness ← BLOCKING (Otto loop)
        ↓
THEN:
└── 1.3 Database Schema + Migrations
        ↓
NEXT:
└── 1.4 Refactor test_server.py → src/lib/
        ↓
CONTINUE:
├── 2.1 LLM Adapter + Parser
├── 3.2 Voice Personality Variations
└── Remaining priorities...
```

---

## Verification Commands

After implementing Priority 1:
```bash
# Lint
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Typecheck (if added)
python3 -m mypy src/ --ignore-missing-imports

# Run tests (when harness complete)
python3 -m pytest harness/
```

---

## Status Summary

| Priority | Task | Status | Dependencies |
|----------|------|--------|--------------|
| **1.1** | **Fix Chain Engine Bugs** | ❌ CRITICAL | None |
| **1.2** | **Create Test Harness** | ❌ BLOCKING | None |
| 1.3 | Database Schema + Migrations | ⚠️ Partial | 1.2 |
| 1.4 | Refactor test_server.py | ⚠️ Single file | 1.3 |
| 2.1 | LLM Adapter + Parser | ⚠️ Partial | 1.4 |
| 2.2 | Chain Engine Completeness | ⚠️ Partial | 1.1 |
| 3.1 | TTS Adapter + Cache | ❌ Missing | 1.4 |
| 3.2 | Voice Personality Variations | ⚠️ 1 template | 1.4 |
| 4.1 | Notification Tier System | ❌ Missing | 3.1 |
| 5.1 | Background Scheduling | ❌ Missing | 1.3 |
| 6 | Calendar Integration | ❌ Missing | 1.4 |
| 7 | Location Awareness | ❌ Missing | 1.4 |
| 8 | Snooze & Dismissal | ⚠️ Partial | 1.4 |
| 9 | History & Stats | ⚠️ Partial | 1.3 |
| 10 | Sound Library | ❌ Missing | 1.4 |

---

## Quick Wins (Can Start Immediately)

1. Expand voice personality templates to 3+ variations per tier
2. Improve keyword extractor regex patterns
3. Add `get_next_unfired_anchor()` query to chain engine
4. Improve hit rate calculation with trailing 7-day window
