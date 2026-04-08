# URGENT Alarm - Implementation Plan

> **Generated:** 2026-04-08  
> **Updated:** 2026-04-08  
> **Purpose:** Bridge gaps between `specs/urgent-voice-alarm-app-2026-04-08.spec.md` and current codebase

---

## Quick Status

| Component | Status | Notes |
|-----------|--------|-------|
| `src/test_server.py` | ⚠️ Partial | HTTP server with partial logic (~400 lines) |
| `harness/` | ❌ **EMPTY** | **CRITICAL** — Otto cannot run without this |
| `src/lib/` | ❌ Missing | Must be created for structured library |
| `scenarios/` | ✅ Ready | 16 YAML scenarios defined, not yet executable |

---

## Critical First Step: Otto Cannot Run

**The `harness/` directory is empty.** Otto needs `harness/scenario_harness.py` to execute scenarios.

### Why This Blocks Everything
1. Otto validates code by running scenarios from `/var/otto-scenarios/{project}/*.yaml`
2. No harness = no validation = Otto cannot assess implementation quality
3. Cannot measure progress or identify regressions

### The Fix (Priority 1)
Create `harness/scenario_harness.py` that:
- Parses `--project` and `--verbose` CLI args
- Reads scenarios from `/var/otto-scenarios/{project}/` (or env `OTTO_SCENARIO_DIR`)
- Starts `src/test_server.py` (the actual HTTP server, NOT `src/web.py` which doesn't exist)
- Executes each scenario's API sequences
- Validates assertions (HTTP status, DB records, llm_judge)
- Writes results to `/tmp/ralph-scenario-result.json`

**See `scenarios/README.md` for expected behavior and existing scenario definitions.**

---

## Current Codebase Analysis

### What Exists (`src/test_server.py`)

| Feature | Implemented | Spec Gap |
|---------|-------------|----------|
| Chain engine | ⚠️ Partial | Missing 20-24 min compression, `get_next_unfired_anchor()` |
| Parser | ⚠️ Keyword only | No LLM adapter interface, no mock, confidence scoring |
| Voice personalities | ⚠️ 1 template/tier | Spec requires 3 min variations per tier |
| Hit rate calculation | ✅ Basic | Missing "common miss window" |
| Database schema | ⚠️ Incomplete | Missing 12+ columns per spec §13 |
| HTTP endpoints | ⚠️ Partial | Missing `/anchors/next-unfired`, `/stats/*` |
| Cascade delete | ❌ Missing | No FK cascade configured |

### What Needs Creating (`harness/`)

```
harness/
├── __init__.py
├── scenario_harness.py     # Main entry point
├── conftest.py            # Pytest fixtures
├── runner.py              # Scenario execution engine
├── assertions/
│   ├── __init__.py
│   ├── http_assertions.py  # HTTP status/body assertions
│   ├── db_assertions.py    # DB record assertions
│   └── llm_judge.py        # LLM-based validation
└── fixtures/
    ├── __init__.py
    └── server.py           # Test server lifecycle
```

---

## Gaps by Spec Section

| § | Section | Severity | Gap Details |
|---|---------|----------|-------------|
| — | **Otto Harness** | 🔴 Critical | `harness/` is empty — Otto cannot run |
| 2 | Escalation Chain Engine | 🟡 Medium | Missing 20-24 min compression, `get_next_unfired_anchor()` |
| 3 | Reminder Parsing | 🔴 High | No LLM adapter interface, no mock, no confirmation flow |
| 4 | Voice & TTS Generation | 🔴 High | No ElevenLabs adapter, no TTS caching, no clip storage |
| 5 | Notification Behavior | ❌ Missing | No DND/quiet hours, no tier escalation sounds, no serialization |
| 6 | Background Scheduling | ❌ Missing | No Notifee/BGTaskScheduler, no recovery scan |
| 7 | Calendar Integration | ❌ Missing | No EventKit/Google Calendar |
| 8 | Location Awareness | ❌ Missing | No CoreLocation/FusedLocationProvider |
| 9 | Snooze & Dismissal | ❌ Missing | No snooze, no chain recompute, no feedback prompt |
| 10 | Voice Personality | 🟡 Medium | 1 template/tier (spec: 3 min variations) |
| 11 | History & Stats | 🟡 Medium | Missing common miss window, streak incomplete |
| 12 | Sound Library | ❌ Missing | No categories, no import |
| 13 | Data Persistence | 🟡 Medium | Schema incomplete (12+ columns missing) |

---

## Scenario → Implementation Mapping

| Scenario File | Tests | Requires |
|--------------|-------|----------|
| `chain-full-30min.yaml` | TC-01 (8 anchors) | `compute_escalation_chain()` |
| `chain-compressed-15min.yaml` | TC-02 (compressed) | Chain compression logic |
| `chain-minimum-3min.yaml` | TC-03 (minimum) | Minimum chain logic |
| `chain-invalid-rejected.yaml` | TC-04 (validation) | `validate_chain()` |
| `parse-natural-language.yaml` | TC-01 (§3) | `parse_reminder_natural()` |
| `parse-simple-countdown.yaml` | TC-02 (§3) | Simple countdown detection |
| `parse-tomorrow.yaml` | TC-03 (§3) | Tomorrow date resolution |
| `voice-coach-personality.yaml` | TC-01 (§10) | `VOICE_PERSONALITIES['coach']` |
| `voice-no-nonsense.yaml` | TC-02 (§10) | `VOICE_PERSONALITIES['no_nonsense']` |
| `voice-all-personalities.yaml` | §10 all | All 5 personalities |
| `history-record-outcome.yaml` | TC-04 (§11) | `POST /history` |
| `history-record-miss-feedback.yaml` | TC-05 (§11) | Feedback processing |
| `stats-hit-rate.yaml` | TC-01 (§11) | `calculate_hit_rate()` |
| `reminder-creation-crud.yaml` | §13 CRUD | Full reminder lifecycle |
| `reminder-creation-cascade-delete.yaml` | TC-03 (§13) | FK cascade |

---

## Implementation Tasks

### P0 — Otto Harness (Blocking Otto Loop)

#### 1.1 Create Scenario Harness
**Files:** `harness/scenario_harness.py`, `harness/conftest.py`, `harness/runner.py`

```python
# harness/scenario_harness.py (skeleton)
import argparse
import json
import os
import subprocess
import time
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    
    # Read scenarios from /var/otto-scenarios/{project}/
    scenario_dir = os.environ.get(
        'OTTO_SCENARIO_DIR',
        f'/var/otto-scenarios/{args.project}'
    )
    
    # Start test server
    server = subprocess.Popen(['python3', 'src/test_server.py'])
    time.sleep(2)  # Wait for server startup
    
    try:
        # Load and execute scenarios
        results = run_all_scenarios(scenario_dir, args.verbose)
        
        # Write results
        with open('/tmp/ralph-scenario-result.json', 'w') as f:
            json.dump({'pass': all(r['pass'] for r in results)}, f)
    finally:
        server.terminate()

if __name__ == '__main__':
    main()
```

**Acceptance Criteria:**
```bash
# Copy scenarios (requires sudo for /var/otto-scenarios/)
sudo mkdir -p /var/otto-scenarios/urgent-alarm
sudo cp scenarios/*.yaml /var/otto-scenarios/urgent-alarm/

# Run harness
sudo python3 harness/scenario_harness.py --project urgent-alarm
# Should write {"pass": true} or {"pass": false} to /tmp/ralph-scenario-result.json
```

---

### P1 — Database Schema Completion

#### 1.2 Complete Schema (Spec §13)
**File:** `src/test_server.py` (update `init_db()`)

**Missing columns per spec:**
```sql
-- reminders table missing:
origin_lat REAL,
origin_lng REAL,
origin_address TEXT,
custom_sound_path TEXT,
calendar_event_id TEXT

-- anchors table missing:
tts_fallback BOOLEAN DEFAULT FALSE,
snoozed_to TEXT

-- history table missing:
actual_arrival TEXT,
missed_reason TEXT

-- NEW tables needed:
calendar_sync (...)
custom_sounds (...)
```

**Tasks:**
- [ ] Add all missing columns
- [ ] Enable `PRAGMA foreign_keys = ON`
- [ ] Enable `PRAGMA journal_mode = WAL`
- [ ] Add cascade delete: `reminders → anchors`
- [ ] Add `Database.getInMemoryInstance()` for tests

---

### P1 — Chain Engine Enhancement

#### 1.3 Complete Chain Engine (Spec §2)
**File:** `src/test_server.py` (update `compute_escalation_chain()`)

**Missing logic:**
1. 20-24 min buffer compression (currently only 10-24 covered)
2. `get_next_unfired_anchor(reminder_id)` function
3. `fire_count` tracking
4. Validation: `arrival > departure + minimum_drive_time`

**Current test scenarios that must pass:**
| Input | Expected Anchors |
|-------|-----------------|
| 30 min drive | 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00 |
| 15 min drive | Compressed (skip calm/casual) |
| 3 min drive | 3 anchors: T-3, T-1, T-0 |

---

### P2 — Adapter Interfaces

#### 2.1 LLM Adapter (Spec §3)
**Files:** `src/lib/adapters/llm_adapter.py`, `src/lib/adapters/llm_mock.py`

**Interface needed:**
```python
class ILanguageModelAdapter:
    def parse(self, text: str) -> ParsedReminder: ...
    def is_mock() -> bool: ...

class MockLLMAdapter(ILanguageModelAdapter):
    fixtures: dict[str, ParsedReminder]
    
class KeywordFallbackAdapter(ILanguageModelAdapter):
    # Regex-based, confidence < 1.0
```

**Supported formats:**
- "X min drive", "X-minute drive"
- "in X minutes"
- "arrive at X", "check-in at X"

#### 2.2 TTS Adapter (Spec §4)
**Files:** `src/lib/adapters/tts_adapter.py`, `src/lib/adapters/tts_mock.py`

**Interface needed:**
```python
class ITTSAdapter:
    def generate(text: str, voice_id: str) -> bytes: ...
    def cache_clip(reminder_id: str, anchor_id: str, audio: bytes): ...

class MockTTSAdapter(ITTSAdapter):
    # Writes 1-second silent file for tests
```

**Cache structure:** `/tts_cache/{reminder_id}/{anchor_id}.mp3`

---

### P3 — Voice Personalities (Spec §10)

#### 3.1 Expand Message Templates
**File:** `src/test_server.py` (update `VOICE_PERSONALITIES`)

**Current state:** 1 template per tier per personality  
**Required:** 3 message variations per tier per personality (5 × 8 × 3 = 120 messages)

**Example for Coach at T-5:**
```python
'urgent': [
    "Let's GO! You've got {remaining} minutes to {dest}!",
    "Time to move! {dest} in {remaining} minutes!",
    "Chop chop! {remaining} minutes — {dest}!",
]
```

---

### P3 — History & Stats (Spec §11)

#### 3.2 Complete Stats
**File:** `src/test_server.py` (update/add endpoints)

**Missing:**
1. "Common miss window" identification
2. Streak counter for recurring reminders
3. Drive duration adjustment cap (+15 min max)
4. 90-day retention with archive

**New endpoints needed:**
```
GET  /stats/common-miss-window
GET  /stats/streaks
POST /stats/adjustment
```

---

## Validation Commands

```bash
# 1. Start test server
python3 src/test_server.py &
sleep 2

# 2. Run pytest (when harness is created)
python3 -m pytest harness/

# 3. Run harness manually (requires sudo)
sudo python3 harness/scenario_harness.py --project urgent-alarm

# 4. Lint check
python3 -m py_compile src/test_server.py
```

---

## Dependencies Map

```
harness/scenario_harness.py (P0) ───────────────────────┐
                                                        │
src/test_server.py (P1) ────────────────────────────────┤
    │                                                  │
    ├── init_db() — Database schema                   │
    ├── compute_escalation_chain() — Chain engine     │
    ├── parse_reminder_natural() — Parser              │
    └── VOICE_PERSONALITIES — Voice templates         │
                                                        │
src/lib/adapters/ (P2)                                 │
    ├── llm_adapter.py                                 │
    └── tts_adapter.py                                 │
                                                        │
All scenarios pass ◄────────────────────────────────────┘
```

---

## Out of Scope (Per Spec)

- Password reset / account management (v1: local-only)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min")
- Multi-device sync
- Bluetooth audio routing preference
- Database encryption
- Full-text search on destinations

---

## File Path Corrections

| AGENTS.md says | Actual file |
|----------------|-------------|
| `src/web.py` | `src/test_server.py` (does not exist as web.py) |
| `python3 src/web.py &` | `python3 src/test_server.py &` |

**Note:** The actual server file is `src/test_server.py`. Update AGENTS.md if needed.

---

*Last Updated: 2026-04-08*
