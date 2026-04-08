# Implementation Plan — Urgent AI Escalating Voice Alarm

## Project Status

**Last Updated:** 2026-04-08  
**Analysis Mode:** Gaps between `specs/*.md` and current `src/` codebase

---

## Executive Summary

The current codebase (`src/test_server.py`) implements ~40% of the specification. Core engine functions exist (chain computation, basic parsing, voice templates) but have critical bugs. Major features are missing entirely (snooze, calendar, location, background scheduling).

---

## Gap Analysis

### Implemented (~40%)

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| Escalation chain computation | ⚠️ Buggy | `compute_escalation_chain()` | 30min works, 3min broken |
| Basic parsing (keyword) | ⚠️ Buggy | `parse_reminder_natural()` | Crashes on simple countdown |
| Voice message templates | ⚠️ Partial | `VOICE_PERSONALITIES` | 1 template/tier, need 3+ |
| Database schema | ⚠️ Incomplete | `init_db()` | Missing columns/tables |
| Hit rate calculation | ✅ Works | `calculate_hit_rate()` | - |
| History recording | ✅ Works | `POST /history` | Partial |

### Missing (60%)

| Feature | Spec Section | Priority |
|---------|-------------|----------|
| Cascade delete | §13 | P0 |
| Next unfired anchor | §2 | P1 |
| Snooze & chain recomputation | §9 | P1 |
| Dismissal feedback | §9 | P1 |
| LLM adapter interface | §3 | P1 |
| TTS adapter interface | §4 | P1 |
| Calendar integration | §7 | P2 |
| Location awareness | §8 | P2 |
| Background scheduling | §6 | P2 |
| Sound library | §12 | P2 |
| Notification tiers & DND | §5 | P2 |
| Streak counter | §11 | P2 |
| Common miss window | §11 | P2 |

---

## Critical Bugs (Must Fix First)

### Bug 1: Parser Crash — Simple Countdown

**File:** `src/test_server.py`, line ~175-190  
**Spec:** Section 3.5, TC-02  
**Failure:** `"dryer in 3 min"` causes `IndexError: no such group`

**Root Cause:**
```python
for pattern in time_patterns:
    match = re.search(pattern, input_text, re.IGNORECASE)
    if match:
        if 'in' in pattern and 'minute' in input_text.lower():
            minutes = int(match.group(1))
            result['arrival_time'] = (now + timedelta(minutes=minutes)).isoformat()
            if result['drive_duration'] is None:
                result['drive_duration'] = 0
                result['reminder_type'] = 'simple_countdown'
        else:
            # Absolute time - tries to access group(2) for minute
            minute = int(match.group(2)) if match.group(2) else 0  # BUG
```

**Fix:**
```python
# Better handling for "in X minutes" - separate from absolute time patterns
relative_pattern = r'in\s+(\d+)\s*(?:minute|min)'
match = re.search(relative_pattern, input_text, re.IGNORECASE)
if match:
    minutes = int(match.group(1))
    result['arrival_time'] = (now + timedelta(minutes=minutes)).isoformat()
    if result['drive_duration'] is None:
        result['drive_duration'] = 0
        result['reminder_type'] = 'simple_countdown'
```

---

### Bug 2: Parser Fails — Time Without "at"

**File:** `src/test_server.py`, line ~180  
**Spec:** Section 3.5, TC-01, TC-03  
**Failure:** `"Parker Dr 9am, 30 min drive"` and `"meeting tomorrow 2pm"` fail to parse time

**Root Cause:** Regex requires "at" keyword:
```python
r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)'  # Requires "at"
```

**Fix:** Add patterns for bare time:
```python
time_patterns = [
    r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # "at 9am"
    r'(\d{1,2}):?(\d{2})?\s*(am|pm)',        # "9am", "9:30am"
    r'tomorrow\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # "tomorrow 2pm"
]
```

---

### Bug 3: Chain Validation — Past Departure Not Rejected

**File:** `src/test_server.py`, line ~110  
**Spec:** Section 2.3, Req #8, TC-04  
**Failure:** `drive_duration=120, arrival=9am` should return 400 but doesn't

**Root Cause:** `validate_chain()` only checks:
```python
def validate_chain(arrival_time: datetime, drive_duration: int) -> dict:
    departure_time = arrival_time - timedelta(minutes=drive_duration)
    if departure_time <= datetime.now():
        return {'valid': False, 'error': 'departure_time_in_past'}  # ✓ This is there
    if drive_duration <= 0:
        return {'valid': False, 'error': 'invalid_drive_duration'}
    return {'valid': True}  # ✓ validation exists
```

Wait, this is actually implemented. Let me re-check the actual code flow...

Actually the validation exists but may not be called in `do_POST /reminders`. Let me verify:

Looking at `do_POST /reminders`:
```python
validation = validate_chain(arrival_time, drive_duration)
if not validation['valid']:
    self.send_json({"error": validation['error']}, 400)
    return
```

This is present. So validation works. The scenario may be failing for another reason - need to test.

---

### Bug 4: 3-Minute Chain — Wrong Anchor Count

**File:** `src/test_server.py`, line ~150  
**Spec:** Section 2.5, TC-03  
**Failure:** 3min buffer produces 2 anchors, needs 3

**Spec Requirement:**
> "3 anchors are created: T-3 (firm), T-1 (critical), T-0 (alarm)"

**Current Logic:**
```python
else:
    # Minimum: critical + alarm (or just alarm for very short)
    if buffer_minutes > 1:
        tiers = [
            ('firm', buffer_minutes - 1),  # T-2, not T-3!
            ('alarm', 0),
        ]
    else:
        tiers = [
            ('alarm', 0),
        ]
```

**Fix:**
```python
elif buffer_minutes <= 5:
    # Minimum chain: firm at T-buffer, critical at T-1, alarm at T-0
    if buffer_minutes > 2:
        tiers = [
            ('firm', buffer_minutes),  # T-3 for 3min buffer
            ('critical', 1),
            ('alarm', 0),
        ]
    elif buffer_minutes > 1:
        tiers = [
            ('critical', 1),
            ('alarm', 0),
        ]
    else:
        tiers = [
            ('alarm', 0),
        ]
```

---

## Database Schema Gaps

### Missing Columns in `reminders`

| Column | Type | Added By |
|--------|------|----------|
| `origin_lat` | REAL | P0 |
| `origin_lng` | REAL | P0 |
| `origin_address` | TEXT | P0 |
| `custom_sound_path` | TEXT | P2 |
| `calendar_event_id` | TEXT | P2 |
| `reminder_type` | TEXT | Already exists |

### Missing Columns in `anchors`

| Column | Type | Added By |
|--------|------|----------|
| `tts_fallback` | BOOLEAN | P0 |
| `snoozed_to` | TEXT | P1 |

### Missing Columns in `history`

| Column | Type | Added By |
|--------|------|----------|
| `actual_arrival` | TEXT | P0 |
| `missed_reason` | TEXT | P0 |

### Missing Tables

| Table | Purpose | Added By |
|-------|---------|----------|
| `user_preferences` (add `updated_at`) | Settings | P0 |
| `destination_adjustments` (add `updated_at`) | Feedback loop | P0 |
| `calendar_sync` | Calendar connection state | P2 |
| `custom_sounds` | Imported audio files | P2 |
| `schema_version` | Migration tracking | P1 |

### Missing Settings

```sql
PRAGMA foreign_keys = ON;  -- Not enabled
PRAGMA journal_mode = WAL;  -- Not enabled
```

---

## Missing HTTP Endpoints

| Endpoint | Method | Spec Section | Priority |
|----------|--------|--------------|----------|
| `/reminders/{id}` | DELETE | §13, TC-03 | P0 |
| `/reminders/{id}/next-anchor` | GET | §2, Req #6 | P1 |
| `/anchors/{id}/snooze` | POST | §9 | P1 |
| `/adjustments/{destination}` | GET | §11 | P2 |

---

## Task Prioritization

### Priority 0 — Critical Bugs (Blocking Tests)

| # | Task | Test Scenario | Files |
|---|------|--------------|-------|
| P0-1 | Fix parser crash on simple countdown | `parse-simple-countdown.yaml` | `src/test_server.py` |
| P0-2 | Fix parser time extraction (bare "9am", "tomorrow 2pm") | `parse-tomorrow.yaml` | `src/test_server.py` |
| P0-3 | Fix 3-minute chain (needs 3 anchors, not 2) | `chain-minimum-3min.yaml` | `src/test_server.py` |
| P0-4 | Add DELETE endpoint with cascade | `reminder-creation-cascade-delete.yaml` | `src/test_server.py` |
| P0-5 | Complete database schema (missing columns) | - | `src/test_server.py` |
| P0-6 | Enable foreign keys pragma | - | `src/test_server.py` |

**Dependencies:** None — start here.

---

### Priority 1 — Core Features (High Value)

| # | Task | Spec Section | Dependencies |
|---|------|--------------|--------------|
| P1-1 | Add `get_next_unfired_anchor` endpoint | §2, Req #6 | P0-5 |
| P1-2 | Implement snooze + chain recomputation | §9 | P0-4, P0-5 |
| P1-3 | Implement dismissal feedback flow | §9 | P0-5 |
| P1-4 | LLM adapter interface (mock-able) | §3 | - |
| P1-5 | TTS adapter interface (mock-able) | §4 | - |
| P1-6 | Expand voice message variations (3+ per tier) | §10 | - |
| P1-7 | Implement streak counter | §11 | P0-5 |
| P1-8 | Implement common miss window | §11 | P0-5 |
| P1-9 | Schema version table + migrations | §13 | P0-5 |

---

### Priority 2 — Integrations (Medium Value)

| # | Task | Spec Section | Dependencies |
|---|------|--------------|--------------|
| P2-1 | Calendar adapter interface | §7 | P1-4 |
| P2-2 | Apple Calendar adapter (EventKit) | §7 | P2-1 |
| P2-3 | Google Calendar adapter (API) | §7 | P2-1 |
| P2-4 | Location awareness (single check) | §8 | P0-5 |
| P2-5 | Notification tiers & DND awareness | §5 | P2-1 |
| P2-6 | Background scheduling (Notifee) | §6 | P2-5 |
| P2-7 | Sound library (built-in + import) | §12 | P0-5 |
| P2-8 | Quiet hours suppression | §5 | P0-5 |

---

### Priority 3 — Polish (Lower Value)

| # | Task | Spec Section | Dependencies |
|---|------|--------------|--------------|
| P3-1 | Custom voice prompt mode | §10 | P1-4 |
| P3-2 | Chain overlap queue | §5 | P1-2 |
| P3-3 | 90-day data retention | §11 | - |
| P3-4 | TTS cache cleanup on delete | §4 | P0-4 |

---

## Files to Create/Modify

### Modify

```
src/test_server.py
  - Fix Bug 1: parse_reminder_natural() crash on "in X min"
  - Fix Bug 2: time extraction for bare "9am", "tomorrow 2pm"
  - Fix Bug 4: 3-minute chain needs 3 anchors
  - Add DELETE /reminders/{id}
  - Add GET /reminders/{id}/next-anchor
  - Add POST /anchors/{id}/snooze
  - Complete schema in init_db()
  - Enable foreign keys
  - Expand VOICE_PERSONALITIES with 3+ variations
```

### Create

```
src/lib/
src/lib/__init__.py
src/lib/adapters/
src/lib/adapters/__init__.py
src/lib/adapters/llm_adapter.py      # ILanguageModelAdapter
src/lib/adapters/tts_adapter.py      # ITTSAdapter
src/lib/adapters/calendar_adapter.py # ICalendarAdapter
src/lib/tts_cache.py
src/lib/location.py
src/lib/notifications.py
src/lib/scheduler.py
src/lib/sound_library.py
src/lib/stats.py
src/lib/feedback_loop.py
src/lib/dismissal.py
```

---

## Scenario Coverage

| Scenario | Current | Required | Priority |
|----------|----------|----------|----------|
| `chain-full-30min.yaml` | ✅ PASS | - | - |
| `chain-compressed-15min.yaml` | ⚠️ Review | Verify 5 anchors | P0 |
| `chain-minimum-3min.yaml` | ❌ FAIL | Fix bug 4 | P0-3 |
| `chain-invalid-rejected.yaml` | ⚠️ Review | May pass | - |
| `parse-natural-language.yaml` | ⚠️ Partial | Fix bugs 1,2 | P0-1, P0-2 |
| `parse-simple-countdown.yaml` | ❌ FAIL | Fix bug 1 | P0-1 |
| `parse-tomorrow.yaml` | ❌ FAIL | Fix bug 2 | P0-2 |
| `voice-coach-personality.yaml` | ✅ PASS | - | - |
| `voice-no-nonsense.yaml` | ✅ PASS | - | - |
| `voice-all-personalities.yaml` | ⚠️ Partial | 3+ variations | P1-6 |
| `history-record-outcome.yaml` | ✅ PASS | - | - |
| `history-record-miss-feedback.yaml` | ⚠️ Partial | Feedback applied | P1-3 |
| `stats-hit-rate.yaml` | ✅ PASS | - | - |
| `reminder-creation-cascade-delete.yaml` | ❌ FAIL | Add DELETE | P0-4 |

---

## Validation Commands

```bash
# Syntax check
python3 -m py_compile src/test_server.py

# Start server
python3 src/test_server.py &
sleep 2

# Test 30min chain (should pass)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Test","arrival_time":"2026-04-10T09:00:00","drive_duration":30}' | jq

# Test 3min chain (should return 3 anchors)
curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Quick","arrival_time":"2026-04-10T09:00:00","drive_duration":3}' | jq '.anchors_created'

# Test parser (should not crash)
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"dryer in 3 min"}' | jq

# Test tomorrow parsing
curl -s -X POST http://localhost:8090/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"meeting tomorrow 2pm, 20 min drive"}' | jq '.arrival_time'

# Test cascade delete
ID=$(curl -s -X POST http://localhost:8090/reminders \
  -H "Content-Type: application/json" \
  -d '{"destination":"Cascade","arrival_time":"2026-04-10T15:00:00","drive_duration":30}' | jq -r '.id')
curl -s -X DELETE http://localhost:8090/reminders/$ID | jq

# Run pytest
python3 -m pytest harness/ 2>/dev/null || echo "No harness tests yet"
```

---

## Definition of Done

- [ ] All Priority 0 bugs fixed and scenarios pass
- [ ] Database schema complete and validated
- [ ] DELETE endpoint implemented with cascade
- [ ] Code compiles without errors
- [ ] No regressions in existing passing tests

---

*Last updated: 2026-04-08*