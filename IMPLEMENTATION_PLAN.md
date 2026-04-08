# URGENT Alarm — Implementation Plan

## Current State Analysis

### What Exists (Proof of Concept)
| Component | Status | Location |
|-----------|--------|----------|
| Chain Engine | ✅ Basic | `src/test_server.py:compute_escalation_chain()` |
| Natural Language Parser | ✅ Basic | `src/test_server.py:parse_reminder_natural()` |
| Voice Message Generation | ✅ Basic | `src/test_server.py:generate_voice_message()` |
| SQLite Schema | ⚠️ Partial | `src/test_server.py:init_db()` |
| HTTP Endpoints | ⚠️ Partial | `src/test_server.py:UrgentAlarmHandler` |
| Scenarios | ⚠️ YAML only | `scenarios/*.yaml` |
| Harness | ❌ Missing | `harness/` is empty |

### What the Spec Requires But is Missing

#### 1. Database Schema Gaps (Critical)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Migration system | 13 | No schema versioning |
| `custom_sounds` table | 13 | Can't store custom audio |
| `calendar_sync` table | 13 | Can't track calendar sync state |
| `origin_lat/lng/address` columns | 13 | Can't store origin for location |
| `custom_sound_path` column | 13 | Can't reference custom sounds |
| `snoozed_to` column | 9 | Can't track snooze state |
| `missed_reason` column | 11 | Can't log missed anchor reasons |
| `actual_arrival` column | 11 | Can't track true arrival time |
| Schema version table | 13 | No migration tracking |
| In-memory test mode | 13 | No isolated test DB |
| Cascade delete test | 13 | No cascade delete scenario |

#### 2. Chain Engine Gaps (Critical)
| Missing | Spec Section | Test Scenario |
|---------|--------------|--------------|
| `get_next_unfired_anchor()` | 2.3 | TC-05 |
| `shift_anchors()` for snooze | 9.3 | TC-03 |
| Unit tests (not HTTP) | 14 | TC-01 through TC-06 |
| Determinism verification | 2.3 | TC-06 |

#### 3. Voice Personality Gaps (High)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Message variations (3+ per tier) | 10.3 | Repetitive messages |
| Custom prompt support | 10.3 | Can't customize tone |
| ElevenLabs voice ID mapping | 10.3 | No actual TTS |
| Message rotation/randomization | 10.4 | Static messages |

#### 4. TTS System Gaps (High)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| ElevenLabs adapter | 4 | No real voice output |
| TTS cache manager | 4.2 | No clip caching |
| Audio file playback | 4 | No sound played |
| TTS fallback on failure | 4.3 | No graceful degradation |

#### 5. Background & Notification Gaps (Critical)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Notifee adapter | 6 | No background scheduling |
| Recovery scan | 6.3 | Missed anchors not recovered |
| DND detection/handling | 5.3 | Ignores system DND |
| Quiet hours | 5.3 | No sleep mode |
| Chain overlap serialization | 5.3 | Concurrent chains possible |
| T-0 alarm looping | 5.3 | No persistent alarm |

#### 6. Snooze/Dismissal Gaps (High)
| Missing | Spec Section | Test Scenario |
|---------|--------------|--------------|
| Tap snooze (1 min) | 9.3 | TC-01 |
| Custom snooze picker | 9.3 | TC-02 |
| Chain re-computation | 9.3 | TC-03 |
| Snooze re-registration | 9.3 | TC-06 |
| Dismissal feedback | 9.3 | TC-04, TC-05 |
| TTS snooze confirmation | 9.3 | - |

#### 7. Calendar Integration Gaps (Medium)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Apple Calendar adapter | 7 | No calendar events |
| Google Calendar adapter | 7 | No calendar events |
| Calendar sync scheduler | 7 | No periodic sync |
| Suggestion cards | 7 | No auto-suggestions |

#### 8. Location Gaps (Medium)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Location adapter | 8 | No origin check |
| 500m geofence check | 8.4 | No "still at origin" detection |
| Immediate escalation | 8.3 | Can't skip to firm tier |

#### 9. Sound Library Gaps (Low)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Built-in sounds | 12 | No bundled audio |
| Custom import | 12.3 | No MP3/WAV import |
| Sound picker | 12 | No UI for selection |

#### 10. History/Stats Gaps (Medium)
| Missing | Spec Section | Test Scenario |
|---------|--------------|--------------|
| Streak counter | 11.3 | TC-05, TC-06 |
| Common miss window | 11.3 | TC-04 |
| Auto-adjustment on create | 11.2 | TC-02, TC-03 |
| 90-day retention | 11.3 | No data cleanup |

#### 11. LLM Parser Gaps (High)
| Missing | Spec Section | Impact |
|---------|--------------|--------|
| Mock adapter interface | 3.3 | Can't test without real API |
| MiniMax adapter | 3.1 | No real LLM parsing |
| Anthropic adapter | 3.1 | No real LLM parsing |
| Keyword fallback confidence | 3.5 | TC-04 |
| Unintelligible rejection | 3.5 | TC-06 |

#### 12. Test Infrastructure Gaps (Critical)
| Missing | Impact |
|---------|--------|
| `harness/scenario_harness.py` | No harness to run scenarios |
| In-memory test DB | Tests pollute production DB |
| Unit test suite | No isolated business logic tests |
| Integration tests | No end-to-end flow tests |

---

## Phase 1: Test Infrastructure & Foundation (Week 1)

### 1.1 Create Harness
**Priority:** Critical — need to validate everything else

**Tasks:**
- [ ] Create `harness/scenario_harness.py` 
- [ ] Parse YAML scenario files
- [ ] Execute API sequences
- [ ] Validate assertions (HTTP status, DB records, LLM judge)
- [ ] Report pass/fail results

**Validation:** `python3 -m pytest harness/` passes

---

### 1.2 Enhance Database Schema
**Priority:** Critical — all data depends on this

**Tasks:**
- [ ] Add schema version table
- [ ] Add migration system (sequential, versioned)
- [ ] Create full schema migration from spec Section 13
- [ ] Add in-memory mode (`?mode=memory`) for tests
- [ ] Add cascade delete tests
- [ ] Enable foreign keys + WAL mode

**Schema additions:**
```sql
-- New columns in reminders:
origin_lat REAL,
origin_lng REAL, 
origin_address TEXT,
custom_sound_path TEXT,
status TEXT DEFAULT 'pending'

-- New columns in anchors:
snoozed_to TEXT,
tts_fallback BOOLEAN DEFAULT FALSE

-- New columns in history:
actual_arrival TEXT,
missed_reason TEXT

-- New tables:
destination_adjustments,
calendar_sync,
custom_sounds,
schema_version
```

**Tests:**
- [ ] `chain-invalid-rejected.yaml` passes (400 error)
- [ ] `reminder-creation-cascade-delete.yaml` passes
- [ ] In-memory DB is isolated per test

---

## Phase 2: Chain Engine Unit Tests (Week 1)

### 2.1 Chain Engine Test Suite
**Priority:** Critical — core algorithm must be correct

**Tasks:**
- [ ] Create `tests/test_chain_engine.py`
- [ ] Add TC-01: Full 8-anchor chain for ≥25 min buffer
- [ ] Add TC-02: Compressed 5-anchor chain for 10-24 min buffer
- [ ] Add TC-03: Minimum 3-anchor chain for ≤5 min buffer
- [ ] Add TC-04: Invalid chain rejection (drive > arrival)
- [ ] Add TC-05: `get_next_unfired_anchor()` recovery
- [ ] Add TC-06: Chain determinism (same input = same output)

**Tests must cover:**
```python
# Example test structure
def test_full_chain_30min():
    """TC-01: 30 min drive → 8 anchors"""
    arrival = datetime(2026, 4, 9, 9, 0, 0)
    anchors = compute_escalation_chain(arrival, 30)
    assert len(anchors) == 8
    assert anchors[0]['urgency_tier'] == 'calm'
    assert anchors[-1]['urgency_tier'] == 'alarm'

def test_compressed_chain_15min():
    """TC-02: 15 min drive → 5 anchors, starts at urgent"""
    ...

def test_minimum_chain_3min():
    """TC-03: 3 min drive → 3 anchors (firm, critical, alarm)"""
    ...

def test_invalid_chain_rejected():
    """TC-04: 120 min drive to 9am → error"""
    ...

def test_get_next_unfired_anchor():
    """TC-05: Returns earliest unfired after restart"""
    ...

def test_chain_determinism():
    """TC-06: Same input always produces same anchors"""
    ...
```

**Validation:** All 6 test scenarios pass

---

## Phase 3: Core Adapters (Week 1-2)

### 3.1 Adapter Interfaces
**Priority:** Critical — enables mocking

**Files to create:**
```
src/lib/adapters/
├── __init__.py
├── base.py                    # Abstract base classes
├── ilanguage_model.py         # LLM parsing
├── itts_adapter.py            # TTS generation
├── icalendar_adapter.py       # Calendar integration
├── ilocation_adapter.py       # Location check
├── inotification_adapter.py   # Notifications
├── ischeduler_adapter.py      # Background scheduling
└── iaudio_player.py           # Audio playback
```

**Tasks:**
- [ ] Define `ILanguageModelAdapter.parse(input_text) -> ParsedReminder`
- [ ] Define `ITTSAdapter.generate(text, voice_id) -> audio_path`
- [ ] Define `ICalendarAdapter.sync_events() -> List[CalendarEvent]`
- [ ] Define `ILocationAdapter.check_location(origin) -> bool`
- [ ] Define `INotificationAdapter.show(tier, content)`, `play_sound()`, `vibrate()`
- [ ] Define `ISchedulerAdapter.schedule(anchor, timestamp)`, `cancel()`, `recover()`
- [ ] Define `IAudioPlayer.play(path)`, `loop()`, `stop()`

---

### 3.2 Mock Adapters
**Priority:** Critical — enables testing without external services

**Files to create:**
```
src/lib/adapters/mock/
├── __init__.py
├── mock_llm.py                # Returns fixture responses
├── mock_tts.py                # Writes silent 1-sec files
├── mock_calendar.py          # Returns synthetic events
├── mock_location.py           # Returns configurable coords
├── mock_notification.py       # Logs calls
├── mock_scheduler.py          # In-memory scheduling
└── mock_audio.py             # Logs play requests
```

**Tasks:**
- [ ] `MockLLMAdapter` with configurable fixtures
- [ ] `MockTTSAdapter` writes to `/tmp/tts_cache/`
- [ ] `MockCalendarAdapter` returns empty list or synthetic events
- [ ] `MockLocationAdapter` with `at_origin` flag
- [ ] `MockSchedulerAdapter` tracks pending tasks in-memory
- [ ] All mocks are instantiable without external dependencies

---

### 3.3 LLM Adapter Implementation
**Priority:** High — enables natural language parsing

**Tasks:**
- [ ] Implement `MiniMaxAdapter` (Anthropic-compatible API)
- [ ] Implement `AnthropicAdapter` (direct Claude API)
- [ ] Implement `KeywordParser` fallback
- [ ] Implement `ReminderParser` orchestrator (LLM → keywords → error)
- [ ] Add confidence scoring (0.0-1.0)

**Tests:**
- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am"
- [ ] TC-02: "dryer in 3 min" → simple_countdown
- [ ] TC-03: "meeting tomorrow 2pm, 20 min drive"
- [ ] TC-04: LLM failure falls back to keyword extraction
- [ ] TC-05: Manual correction (parser output editable)
- [ ] TC-06: Unintelligible input rejection
- [ ] TC-07: Mock adapter used in tests

---

## Phase 4: Voice Personality System (Week 2)

### 4.1 Message Variations
**Priority:** High — avoid repetitive messages

**Tasks:**
- [ ] Expand each personality/tier to 3+ message templates
- [ ] Add message rotation (round-robin or random)
- [ ] Ensure variety in vocabulary and structure

**Example expansion for "Coach" personality, "urgent" tier:**
```python
'coach': {
    'urgent': [
        "Let's GO! You've got {remaining} minutes to {dest}!",
        "Time to move! {dest} in {remaining} minutes, come on!",
        "You need to leave NOW! {remaining} minutes to {dest}!",
    ],
}
```

---

### 4.2 Custom Prompt Support
**Priority:** Medium — enables personalization

**Tasks:**
- [ ] Accept custom prompt (max 200 chars) in settings
- [ ] Append custom prompt to message generation system prompt
- [ ] Store custom prompt in user_preferences

---

### 4.3 ElevenLabs Integration
**Priority:** High — enables actual voice output

**Tasks:**
- [ ] Implement `ElevenLabsAdapter`
- [ ] Map personalities to voice IDs
- [ ] Implement async generation with polling
- [ ] Implement audio caching
- [ ] Implement fallback on failure

---

## Phase 5: Scheduling & Notifications (Week 2-3)

### 5.1 Background Scheduler
**Priority:** Critical — app must fire in background

**Tasks:**
- [ ] Implement `NotifeeSchedulerAdapter` (or stub for testing)
- [ ] Register each anchor as individual task
- [ ] Implement recovery scan on launch
- [ ] Drop anchors >15 min overdue
- [ ] Log late fires (>60 sec)

---

### 5.2 Notification Behavior
**Priority:** Critical — user must be alerted

**Tasks:**
- [ ] Map urgency tiers to notification sounds
- [ ] Implement DND detection and handling
- [ ] Implement DND override for final 5 min
- [ ] Implement quiet hours suppression
- [ ] Implement quiet hours end queue
- [ ] Implement T-0 alarm looping

**Tests:**
- [ ] TC-01: DND early anchor suppressed
- [ ] TC-02: DND final 5-min override
- [ ] TC-03: Quiet hours suppression
- [ ] TC-04: Overdue anchor drop (15 min)
- [ ] TC-05: Chain overlap serialization
- [ ] TC-06: T-0 loops until action

---

### 5.3 Snooze & Dismissal
**Priority:** High — core user interaction

**Tasks:**
- [ ] Implement tap snooze (1 min)
- [ ] Implement custom snooze picker (1, 3, 5, 10, 15 min)
- [ ] Implement `shift_anchors()` for snooze re-computation
- [ ] Re-register snoozed anchors
- [ ] Implement dismissal feedback prompt
- [ ] TTS snooze confirmation: "Okay, snoozed {X} minutes"

**Tests:**
- [ ] TC-01: Tap snooze
- [ ] TC-02: Custom snooze
- [ ] TC-03: Chain re-computation after snooze
- [ ] TC-04: Dismissal feedback — timing correct
- [ ] TC-05: Dismissal feedback — timing off
- [ ] TC-06: Snooze persistence after restart

---

## Phase 6: History & Feedback Loop (Week 3)

### 6.1 Stats Service
**Priority:** Medium — user-facing feature

**Tasks:**
- [ ] Implement hit rate calculation (trailing 7 days)
- [ ] Implement streak counter (increment on hit, reset on miss)
- [ ] Implement common miss window identification
- [ ] Derive all stats from history table

**Tests:**
- [ ] TC-01: Hit rate calculation (4 hits / 5 resolved = 80%)
- [ ] TC-04: Common miss window (T-5 most frequently missed)
- [ ] TC-05: Streak increment on hit
- [ ] TC-06: Streak reset on miss
- [ ] TC-07: Stats derived from history table alone

---

### 6.2 Feedback Loop
**Priority:** Medium — intelligent learning

**Tasks:**
- [ ] Track destination adjustments in `destination_adjustments` table
- [ ] Apply +2 min adjustment per "left_too_late" feedback
- [ ] Cap adjustments at +15 min
- [ ] Pre-populate drive_duration with adjustment on reminder creation

**Tests:**
- [ ] TC-02: 3 late feedbacks → +6 min on next reminder
- [ ] TC-03: 10 late feedbacks → +15 min cap

---

## Phase 7: Integrations (Week 3-4)

### 7.1 Calendar Integration
**Priority:** Medium — calendar events → reminders

**Tasks:**
- [ ] Implement `AppleCalendarAdapter` (EventKit)
- [ ] Implement `GoogleCalendarAdapter` (Google Calendar API)
- [ ] Implement 15-min sync scheduler
- [ ] Generate suggestion cards for events with locations
- [ ] Handle recurring events
- [ ] Handle permission denial gracefully

**Tests:**
- [ ] TC-01: Apple Calendar event suggestion
- [ ] TC-02: Google Calendar event suggestion
- [ ] TC-03: Suggestion → reminder creation
- [ ] TC-04: Permission denial handling
- [ ] TC-05: Sync failure graceful degradation
- [ ] TC-06: Recurring event handling

---

### 7.2 Location Awareness
**Priority:** Medium — adaptive escalation

**Tasks:**
- [ ] Implement `LocationAdapter` (CoreLocation on iOS)
- [ ] Store origin at reminder creation
- [ ] Single location check at departure anchor
- [ ] 500m geofence comparison
- [ ] Immediate escalation if user at origin
- [ ] Request permission at reminder creation time

**Tests:**
- [ ] TC-01: User at origin → skip to firm/critical tier
- [ ] TC-02: User left → normal chain proceeds
- [ ] TC-03: Permission request at creation
- [ ] TC-04: Permission denied → reminder without location
- [ ] TC-05: Single location check only

---

### 7.3 Sound Library
**Priority:** Low-Medium — personalization

**Tasks:**
- [ ] Bundle built-in sounds (5 per category)
- [ ] Implement custom import (MP3, WAV, M4A, max 30 sec)
- [ ] Implement sound picker UI
- [ ] Handle corrupted sound fallback

**Tests:**
- [ ] TC-01: Built-in sound playback
- [ ] TC-02: Custom sound import
- [ ] TC-03: Custom sound playback
- [ ] TC-04: Corrupted sound fallback
- [ ] TC-05: Sound persistence on edit

---

## Phase 8: Mobile App UI (Week 4-6)

### 8.1 Project Setup
**Priority:** Critical — need running app

**Tasks:**
- [ ] Initialize React Native project (or Flutter)
- [ ] Set up project structure
- [ ] Configure navigation
- [ ] Set up state management
- [ ] Set up SQLite

---

### 8.2 Core Screens
- [ ] Quick Add screen with confirmation card
- [ ] Home screen with active reminders
- [ ] History screen with stats
- [ ] Settings screen

---

## Dependency Graph

```
Phase 1: Test Infrastructure
    │
    ├─► Phase 2: Chain Engine Tests
    │
    └─► Phase 3: Adapter Interfaces + Mocks
            │
            ├─► Phase 4: Voice Personality (TTS)
            │
            ├─► Phase 5: Scheduling + Notifications + Snooze
            │       │
            │       └─► Phase 6: History + Feedback
            │
            └─► Phase 7: Calendar + Location + Sound
                    │
                    └─► Phase 8: Mobile App UI
```

---

## Quick Wins (Days 1-3)

1. **Create harness/scenario_harness.py** — enables validation
2. **Add database schema gaps** — full spec schema
3. **Add chain engine unit tests** — validates core algorithm
4. **Create adapter interfaces** — enables mocking

---

## Out of Scope (v1)

- Password/auth (local-only data)
- Smart home integration
- Voice reply ("snooze 5 min")
- Multi-device sync
- Bluetooth audio routing
- Per-reminder personality override
- Voice recording import
- Sound trimming/editing
- Cloud sound library
- Database encryption
- Full-text search on destinations
