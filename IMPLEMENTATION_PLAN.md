# URGENT — AI Escalating Voice Alarm: Implementation Plan

## Gap Analysis Summary

| Component | Spec Section | Implementation Status | Gap Severity |
|-----------|-------------|----------------------|--------------|
| Chain Engine | 2 | Partial — missing compression logic for 20-24 min, missing T-10 for 10-19 min | HIGH |
| Reminder Parsing | 3 | Partial — keyword extraction works, but no LLM adapter, no fallback confidence | MEDIUM |
| Voice Personality | 4, 10 | Partial — templates exist, but missing variations (only 1 per tier) | MEDIUM |
| TTS Generation | 4 | Missing — no ElevenLabs adapter, no TTS caching service | HIGH |
| Notifications | 5 | Missing — no notification service, no DND/quiet hours handling | HIGH |
| Background Scheduling | 6 | Missing — no Notifee integration, no recovery scan, no BG task registration | HIGH |
| Calendar Integration | 7 | Missing — no EventKit/Google Calendar adapters | HIGH |
| Location Awareness | 8 | Missing — no geofence check at departure trigger | HIGH |
| Snooze/Dismissal | 9 | Missing — no chain re-computation, no feedback flow | HIGH |
| Feedback Loop | 11 | Partial — adjustment exists but not capped at +15 min | MEDIUM |
| History/Stats | 11 | Partial — hit rate works, missing streak, miss window, 90-day retention | MEDIUM |
| Sound Library | 12 | Missing — no per-reminder sound selection, no custom import | MEDIUM |
| Database Schema | 13 | Partial — missing columns (origin_lat/lng, snoozed_to, missed_reason, etc.) | HIGH |
| Database Migrations | 13 | Missing — no versioned migration system | HIGH |
| Adapter Interfaces | - | Missing — no ILanguageModelAdapter, ITTSAdapter, ICalendarAdapter, ILocationAdapter | HIGH |
| Repository Layer | - | Missing — no repository abstractions | HIGH |
| Scenario Harness | - | Missing — harness/scenario_harness.py doesn't exist | CRITICAL |

---

## Priority 1: CRITICAL - Test Infrastructure (Blocker)

### 1.1 Create scenario_harness.py
**Status:** Missing (BLOCKS all validation)
**Files:** `harness/scenario_harness.py`
**Impact:** Cannot run 16 scenario tests without this

**Required Features:**
- YAML scenario loading from `/var/otto-scenarios/{project}/`
- HTTP client for API calls (POST /reminders, /parse, /voice/message, etc.)
- SQLite database inspection for `db_record` assertions
- LLM judge integration for `llm_judge` assertions
- Scenario runner with pass/fail reporting
- CLI with `--project` argument

**Acceptance Criteria:**
- [ ] Loads scenarios from `/var/otto-scenarios/{project}/`
- [ ] Executes `api_sequence` trigger steps
- [ ] Validates `http_status` assertions
- [ ] Validates `db_record` assertions (query SQLite)
- [ ] Validates `llm_judge` assertions (call LLM with prompt)
- [ ] Reports PASS/FAIL per scenario with summary

---

## Priority 2: Database Foundation

### 2.1 Full Schema (per Spec Section 13)
**Status:** Partial — missing columns and tables
**Files:** `src/lib/database.py`

**Current Schema Gaps:**
| Table | Missing Columns |
|-------|-----------------|
| reminders | `origin_lat`, `origin_lng`, `origin_address`, `custom_sound_path`, `calendar_event_id` |
| anchors | `tts_clip_path`, `tts_fallback`, `snoozed_to` |
| history | `actual_arrival`, `missed_reason` |
| destination_adjustments | `updated_at` |

**Missing Tables:**
- `calendar_sync` — calendar_type, last_sync_at, sync_token, is_connected
- `custom_sounds` — id, filename, original_name, category, file_path, duration_seconds, created_at

**Tasks:**
- [ ] Add missing columns to `reminders` table
- [ ] Add missing columns to `anchors` table
- [ ] Add missing columns to `history` table
- [ ] Add missing columns to `destination_adjustments` table
- [ ] Create `calendar_sync` table
- [ ] Create `custom_sounds` table

### 2.2 Migration System
**Status:** Missing
**Tasks:**
- [ ] Create `schema_migrations` table to track applied versions
- [ ] Implement sequential migration runner (v1 → vN)
- [ ] Add PRAGMA settings: WAL mode, foreign keys ON
- [ ] Support in-memory mode for tests (`?mode=memory`)

---

## Priority 3: Adapter Interfaces (Mock-able for Testing)

### 3.1 Abstract Interfaces
**Status:** Missing
**Files:** `src/lib/adapters/base.py`

**Required Interfaces:**
- `ILanguageModelAdapter` — `parse(text) -> ParsedReminder`
- `ITTSAdapter` — `generate(text, voice_id) -> audio_path`
- `ICalendarAdapter` — `get_events() -> list[CalendarEvent]`
- `ILocationAdapter` — `get_current_location() -> (lat, lng)`

### 3.2 Concrete Implementations
**Status:** Partial
**Files:** `src/lib/adapters/llm_adapter.py`, `tts_adapter.py`, etc.

**Current State:**
- Keyword parsing exists in test_server.py (not adapter pattern)
- No LLM adapter (MiniMax or Anthropic)
- No TTS adapter (ElevenLabs)
- No calendar adapter (EventKit, Google Calendar)
- No location adapter (CoreLocation)

**Tasks:**
- [ ] Create `MockLLMAdapter` for testing
- [ ] Create `MiniMaxAdapter` / `AnthropicAdapter` for production
- [ ] Create `MockTTSAdapter` for testing
- [ ] Create `ElevenLabsAdapter` for production
- [ ] Create `MockCalendarAdapter` for testing
- [ ] Create `AppleCalendarAdapter`, `GoogleCalendarAdapter` for production
- [ ] Create `MockLocationAdapter` for testing
- [ ] Create `CoreLocationAdapter` for production

---

## Priority 4: Chain Engine (Spec Section 2)

### 4.1 Compression Logic Fix
**Status:** Partial — incorrect for some buffer sizes
**File:** `src/lib/services/chain_engine.py`

**Current Issues:**
- Spec says: buffer ≥ 25 min → 8 anchors (departure, T-25, T-20, T-15, T-10, T-5, T-1, T-0)
- Current code: `buffer >= 25` gives 8 anchors but timestamps may be off
- Spec says: buffer 10-24 min → compressed, skip calm/casual, start at T-10
- Current code: `buffer >= 10` starts at T-5, not T-10

**Required Fixes:**
- For 20-24 min buffer: Start at T-15 (urgent), not T-5
- For 15-19 min buffer: Start at T-10 (pushing), not T-5
- For 10-14 min buffer: Start at T-5 (firm), existing is close

**Acceptance Criteria:**
- [ ] TC-01: 30 min → 8 anchors: 8:30 (calm), 8:35 (casual), 8:40 (pointed), 8:45 (urgent), 8:50 (pushing), 8:55 (firm), 8:59 (critical), 9:00 (alarm)
- [ ] TC-02: 15 min → 5 anchors: 8:45 (urgent), 8:50 (pushing), 8:55 (firm), 8:59 (critical), 9:00 (alarm)
- [ ] TC-03: 3 min → 3 anchors: 8:57 (firm), 8:59 (critical), 9:00 (alarm)
- [ ] TC-04: drive_duration > arrival_time → reject with validation error
- [ ] TC-05: `get_next_unfired_anchor()` returns earliest unfired
- [ ] TC-06: Chain computation is deterministic (same inputs = same output)

---

## Priority 5: Voice Personality Service (Spec Section 10)

### 5.1 Message Variations
**Status:** Partial — only 1 template per tier per personality
**File:** `src/lib/services/voice_personality_service.py`

**Current State:**
- Each personality has 1 template per urgency tier
- Spec requires minimum 3 variations per tier per personality

**Tasks:**
- [ ] Add 2 more templates per tier per personality (Coach, Assistant, Best Friend, No-nonsense, Calm)
- [ ] Implement rotation logic (round-robin or random)
- [ ] Support custom prompt modifier (max 200 chars)

**Acceptance Criteria:**
- [ ] TC-01: "Coach" at T-5 → motivational message with exclamation
- [ ] TC-02: "No-nonsense" at T-5 → brief, direct, no filler
- [ ] TC-03: Custom prompt modifies tone appropriately
- [ ] TC-04: Changing default personality doesn't affect existing reminders
- [ ] TC-05: Each personality generates at least 3 distinct message variations

---

## Priority 6: Parser Service (Spec Section 3)

### 6.1 Keyword Extraction Fix
**Status:** Partial — needs improvement
**File:** `src/lib/services/parser_service.py`

**Current Issues:**
- "30 minute drive to Parker Dr, check-in at 9am" — works
- "dryer in 3 min" — drive_duration becomes 0, but arrival_time calculation needs fixing
- "meeting tomorrow 2pm, 20 min drive" — tomorrow resolution works

**Tasks:**
- [ ] Improve destination extraction regex patterns
- [ ] Better handle "in X minutes" for simple countdowns
- [ ] Add confidence scoring (0.0-1.0)
- [ ] Add fallback behavior when LLM unavailable

**Acceptance Criteria:**
- [ ] TC-01: "30 minute drive to Parker Dr, check-in at 9am" → destination="Parker Dr check-in", arrival_time ~ today's 9:00, drive_duration=30
- [ ] TC-02: "dryer in 3 min" → reminder_type="simple_countdown", drive_duration=0, arrival_time ~ now+3min
- [ ] TC-03: "meeting tomorrow 2pm, 20 min drive" → arrival_time = tomorrow 2:00 PM
- [ ] TC-04: LLM failure → keyword extraction runs with confidence < 1.0
- [ ] TC-05: User can edit parsed fields before confirming
- [ ] TC-06: Unintelligible input → error "Couldn't understand that — try again"
- [ ] TC-07: Mock adapter returns fixture without API call

---

## Priority 7: TTS Cache Service (Spec Section 4)

### 7.1 TTS Generation & Caching
**Status:** Missing
**File:** `src/lib/services/tts_cache_service.py`

**Required Features:**
- Generate TTS clips at reminder creation (not at runtime)
- Cache in `/tts_cache/{reminder_id}/`
- Map clip paths to anchor records
- Fallback to system notification sound on failure
- Invalidate cache on reminder deletion

**Acceptance Criteria:**
- [ ] TC-01: 8 MP3 clips generated at creation, stored in `/tts_cache/{reminder_id}/`
- [ ] TC-02: Playing anchor fires from local cache (no network call)
- [ ] TC-03: ElevenLabs failure → fallback to system sound
- [ ] TC-04: Reminder deletion → all cached TTS files removed
- [ ] TC-05: Mock TTS writes silent file in tests

---

## Priority 8: Notification Service (Spec Section 5)

### 8.1 Notification Tier Escalation
**Status:** Missing
**File:** `src/lib/services/notification_service.py`

**Required Features:**
- Sound tiers: gentle chime (calm/casual), pointed beep (pointed/urgent), urgent siren (pushing/firm), looping alarm (critical/alarm)
- DND handling: silent notifications (early), visual override + vibration (final 5 min)
- Quiet hours: suppress 10pm-7am, queue for post-quiet-hours, drop >15 min overdue
- Chain overlap: serialize, queue new anchors until current chain completes
- T-0 alarm: loop until user dismisses/snoozes

**Acceptance Criteria:**
- [ ] TC-01: DND early anchor → silent notification, no TTS
- [ ] TC-02: DND T-5 anchor → visual + vibration + TTS
- [ ] TC-03: Quiet hours → suppress and queue
- [ ] TC-04: 15 min overdue → drop and log
- [ ] TC-05: Chain overlap → queue and fire after current completes
- [ ] TC-06: T-0 alarm loops until action

---

## Priority 9: Background Scheduler (Spec Section 6)

### 9.1 Notifee Integration
**Status:** Missing
**File:** `src/lib/services/scheduler_service.py`

**Required Features:**
- Register each anchor with Notifee as individual background task
- iOS: BGAppRefreshTask + BGProcessingTask
- Recovery scan on app launch (within 15-min grace window)
- Drop and log >15 min overdue anchors
- Re-register pending anchors on crash recovery
- Late firing warning (>60s after scheduled)

**Acceptance Criteria:**
- [ ] TC-01: All 8 anchors registered with correct timestamps
- [ ] TC-02: App closed → anchors fire via notification
- [ ] TC-03: Launch after force-kill → recovery scan fires grace-window anchors
- [ ] TC-04: 20 min overdue → dropped and logged
- [ ] TC-05: Pending anchors re-registered on restart
- [ ] TC-06: 90s late → warning log entry

---

## Priority 10: Location Awareness (Spec Section 8)

### 10.1 Geofence Check at Departure
**Status:** Missing
**File:** `src/lib/services/location_check_service.py`

**Required Features:**
- Single location check at departure anchor (T-drive_duration)
- 500m geofence radius
- If at origin → fire urgent/firm tier immediately
- If left → normal chain proceeds
- No location history retention
- Request permission at first location-aware reminder

**Acceptance Criteria:**
- [ ] TC-01: At origin at departure → firm tier fires instead of calm
- [ ] TC-02: Already left at departure → normal calm nudge
- [ ] TC-03: Permission requested at first location-aware reminder
- [ ] TC-04: Permission denied → reminder created without location escalation
- [ ] TC-05: Only one location API call made

---

## Priority 11: Snooze & Dismissal (Spec Section 9)

### 11.1 Snooze Service
**Status:** Missing
**File:** `src/lib/services/snooze_service.py`

**Required Features:**
- Tap → 1-min snooze
- Tap-and-hold → custom picker (1, 3, 5, 10, 15 min)
- Chain re-computation: shift remaining anchors by snooze duration
- Re-register with Notifee
- TTS: "Okay, snoozed [X] minutes"
- Persist snoozed timestamps for restart recovery

### 11.2 Dismissal & Feedback Service
**Status:** Missing
**File:** `src/lib/services/dismissal_service.py`

**Required Features:**
- Swipe-to-dismiss → feedback prompt
- "Yes — timing was right" → store feedback, no adjustment
- "No — timing was off" → prompt for "Left too early", "Left too late", "Other"
- "Left too late" → +2 min adjustment for destination

**Acceptance Criteria:**
- [ ] TC-01: Tap snooze → 1-min pause + TTS confirmation
- [ ] TC-02: Custom snooze → 5-min shift + TTS
- [ ] TC-03: Chain re-computation shifts all remaining anchors
- [ ] TC-04: Dismiss with "timing right" → stored, no adjustment
- [ ] TC-05: Dismiss with "left too late" → +2 min adjustment (cap +15)
- [ ] TC-06: After snooze + restart → remaining anchors fire at adjusted times

---

## Priority 12: Calendar Integration (Spec Section 7)

### 12.1 Calendar Sync Service
**Status:** Missing
**File:** `src/lib/services/calendar_sync_service.py`

**Required Features:**
- EventKit (Apple Calendar) adapter
- Google Calendar API adapter
- Sync on launch, every 15 min, background refresh
- Filter events with location
- Suggestion cards for departure reminders
- Recurring event handling
- Permission denial handling with explanation

**Acceptance Criteria:**
- [ ] TC-01: Apple Calendar events with locations → suggestion card
- [ ] TC-02: Google Calendar events with locations → suggestion card
- [ ] TC-03: Suggestion → countdown_event reminder created
- [ ] TC-04: Permission denied → explanation banner with Open Settings
- [ ] TC-05: Sync failure → manual reminders still work
- [ ] TC-06: Recurring daily event → reminder for each occurrence

---

## Priority 13: Feedback Loop (Spec Section 11)

### 13.1 Destination Adjustment
**Status:** Partial — needs cap enforcement
**File:** `src/lib/services/feedback_loop_service.py`

**Current State:**
- Basic +2 min adjustment on "left too late" feedback
- No cap at +15 minutes

**Tasks:**
- [ ] Implement adjustment cap at +15 minutes
- [ ] Formula: `adjusted_drive_duration = stored_drive_duration + min(late_count * 2, 15)`

**Acceptance Criteria:**
- [ ] TC-02: 3 "left too late" → +6 min adjustment
- [ ] TC-03: 10 "left too late" → +15 min adjustment (capped)

---

## Priority 14: Sound Library (Spec Section 12)

### 14.1 Sound Library Service
**Status:** Missing
**File:** `src/lib/services/sound_library_service.py`

**Required Features:**
- 5 built-in sounds per category (Commute, Routine, Errand)
- Custom audio import (MP3, WAV, M4A, max 30 sec)
- Per-reminder sound selection
- Corrupted sound fallback to category default
- Sound selection persistence

**Acceptance Criteria:**
- [ ] TC-01: Built-in sounds play without network access
- [ ] TC-02: Custom MP3 import appears in picker
- [ ] TC-03: Custom sound plays under TTS
- [ ] TC-04: Corrupted sound → fallback + error log
- [ ] TC-05: Sound selection persists on edit

---

## Priority 15: Stats Service (Spec Section 11)

### 15.1 Enhanced Stats
**Status:** Partial — basic hit rate exists
**File:** `src/lib/services/stats_service.py`

**Required Features:**
- Hit rate: `count(outcome='hit') / count(outcome!='pending') * 100` (trailing 7 days)
- Common miss window: most frequently missed urgency tier
- Streak counter: increment on hit, reset on miss
- 90-day retention with archive

**Acceptance Criteria:**
- [ ] TC-01: Hit rate calculation (4 hits, 1 miss in 7 days = 80%)
- [ ] TC-04: Streak increments on hit, resets on miss
- [ ] TC-07: Stats derived from history table (no separate stats store)

---

## Implementation Order

### Phase 1: Critical Infrastructure (Start here)
1. ✅ **scenario_harness.py** — Unblock all validation
2. **database.py** — Full schema + migrations
3. **adapter interfaces** — Abstract bases + mock adapters

### Phase 2: Core Logic
4. **chain_engine.py** — Fix compression logic, add get_next_unfired_anchor
5. **parser_service.py** — Improve keyword extraction, add confidence
6. **voice_personality_service.py** — Add 2 more templates per tier

### Phase 3: External Services
7. **tts_cache_service.py** — TTS generation + caching
8. **notification_service.py** — DND, quiet hours, tier escalation
9. **scheduler_service.py** — Notifee, recovery scan

### Phase 4: User Interactions
10. **location_check_service.py** — Geofence at departure
11. **snooze_service.py** — Tap, custom snooze, chain re-compute
12. **dismissal_service.py** — Feedback flow + adjustment
13. **feedback_loop_service.py** — Cap at +15 min

### Phase 5: External Integrations
14. **calendar_sync_service.py** — EventKit + Google Calendar
15. **sound_library_service.py** — Built-in + custom import

### Phase 6: Analytics & Polish
16. **stats_service.py** — Hit rate, streaks, retention

---

## Files to Create

```
src/lib/
├── __init__.py
├── database.py                 # Connection, migrations, WAL, FK
├── adapters/
│   ├── __init__.py
│   ├── base.py                 # Abstract interfaces
│   ├── llm_adapter.py          # MiniMax, Anthropic, Mock
│   ├── tts_adapter.py          # ElevenLabs, Mock
│   ├── calendar_adapter.py     # Apple, Google, Mock
│   └── location_adapter.py     # CoreLocation, Mock
├── repositories/
│   ├── __init__.py
│   ├── base.py
│   ├── reminder_repository.py
│   ├── anchor_repository.py
│   ├── history_repository.py
│   ├── preferences_repository.py
│   ├── adjustments_repository.py
│   ├── calendar_sync_repository.py
│   └── custom_sounds_repository.py
└── services/
    ├── __init__.py
    ├── chain_engine.py
    ├── parser_service.py
    ├── voice_personality_service.py
    ├── tts_cache_service.py
    ├── notification_service.py
    ├── scheduler_service.py
    ├── location_check_service.py
    ├── snooze_service.py
    ├── dismissal_service.py
    ├── feedback_loop_service.py
    ├── calendar_sync_service.py
    ├── sound_library_service.py
    └── stats_service.py

harness/
├── __init__.py
└── scenario_harness.py

src/test_server.py              # Refactor to use lib/
```

---

## Validation Commands

```bash
# Start test server
python3 src/test_server.py &

# Run all scenarios (requires sudo for /var/otto-scenarios)
sudo python3 harness/scenario_harness.py --project otto-matic

# Syntax check
python3 -m py_compile harness/scenario_harness.py src/test_server.py

# Run unit tests
python3 -m pytest harness/
```

---

## Out of Scope (Per Spec)

- Password reset / account management (local-only v1)
- Smart home integration (Hue lights)
- Voice reply / spoken snooze
- Multi-device sync
- Bluetooth audio routing
- Calendar write operations
- Two-way calendar sync
- Voice recording import
- Prosody control beyond voice settings
- Per-reminder personality override
- Export/history sharing
- Database encryption
- Full-text search on destinations