# URGENT — AI Escalating Voice Alarm Specification

## Table of Contents

1. [Overview and Goals](#1-overview-and-goals)
2. [Escalation Chain Engine](#2-escalation-chain-engine)
3. [Reminder Parsing & Creation](#3-reminder-parsing--creation)
4. [Voice & TTS Generation](#4-voice--tts-generation)
5. [Notification & Alarm Behavior](#5-notification--alarm-behavior)
6. [Background Scheduling & Reliability](#6-background-scheduling--reliability)
7. [Calendar Integration](#7-calendar-integration)
8. [Location Awareness](#8-location-awareness)
9. [Snooze & Dismissal Flow](#9-snooze--dismissal-flow)
10. [Voice Personality System](#10-voice-personality-system)
11. [History, Stats & Feedback Loop](#11-history-stats--feedback-loop)
12. [Sound Library](#12-sound-library)
13. [Data Persistence](#13-data-persistence)
14. [Definition of Done](#14-definition-of-done)

---

## 1. Overview and Goals

### 1.1 Problem Statement

People miss time-sensitive appointments because they underestimate drive times or become absorbed in tasks. Existing alarms are one-shot — they fire once and hope the user acts. They don't track the actual departure window, adapt urgency based on remaining time, or nag with escalating pressure as the deadline approaches. The result is missed appointments, rushed arrivals, and constant anxiety about whether you've left "early enough."

### 1.2 Goals

- **On-time arrivals** — Users consistently make appointments because departure reminders match actual travel needs, not arbitrary countdowns
- **Adaptive escalation** — Shorter buffers produce compressed urgency chains; longer buffers produce full calm-to-critical progressions
- **Reliable firing** — Reminders execute in the background even when the app is closed, phone is locked, or device is in power-saving mode
- **Graceful degradation** — Every external dependency (LLM, TTS, calendar, location) fails safely with a sensible fallback
- **Feedback learning** — System adjusts future departure estimates based on missed-reminder data

### 1.3 Scope

**In scope:**
- Natural language reminder creation (text + speech input)
- Adaptive escalation chain generation with configurable anchor points
- Five voice personality styles + custom prompt option
- Pre-generated TTS clips cached per reminder (zero runtime TTS latency)
- Local SQLite storage for reminders, preferences, history, and feedback
- Background scheduling via Notifee (iOS BGTaskScheduler + Android WorkManager)
- Apple Calendar and Google Calendar integration with departure nudge mapping
- Single-point location check at departure trigger (not continuous tracking)
- Snooze (1-min tap, custom duration) and dismissal with feedback prompt
- Quiet hours / sleep mode with post-DND catch-up firing
- Chain overlap queue — nudges serialize, never overlap
- History: hit rate, streak counter, common miss window
- Sound library: per-reminder-type sounds + custom audio import
- Missed reminder feedback loop that adjusts departure estimates

**Out of scope:**
- Password reset / account management (no auth in v1 — local-only data)
- Smart home integration (Hue lights, etc.)
- Voice reply / spoken snooze ("snooze 5 min")
- Multi-device sync (future consideration)
- Bluetooth audio routing preference (speaker-only in v1)

---

## 2. Escalation Chain Engine

### 2.1 Description

The escalation chain engine is the core of the app. Given a reminder's target arrival time and drive duration, it computes a precise timeline of nudge timestamps — from the departure cue through the arrival alarm — and maps each timestamp to a pre-generated TTS clip. The chain adapts dynamically: a 30-minute buffer gets a full 8-step progression; a 10-minute buffer gets a compressed 4-step progression.

### 2.2 User Journey

1. User creates a reminder via Quick Add (text or speech)
2. LLM parser extracts: destination, arrival time, drive duration
3. Chain engine computes anchor points and assigns urgency tiers to each
4. Chain is persisted to SQLite with all timestamps pre-computed
5. Background scheduler registers each anchor as an individual pending task
6. At each anchor time, the scheduler fires the corresponding TTS clip
7. Chain completes at arrival time with full alarm escalation

### 2.3 Functional Requirements

1. The chain engine SHALL compute departure time as `arrival_time - drive_duration`.
2. The chain engine SHALL generate anchor points at: departure, T-25, T-20, T-15, T-10, T-5, T-1, and T-0 (arrival) for buffers ≥ 25 minutes.
3. The chain engine SHALL compress the chain for buffers < 25 minutes, skipping calm-tier anchors and starting at T-5 or T-10.
4. The chain engine SHALL assign urgency tiers (calm, casual, pointed, urgent, pushing, firm, critical, alarm) based on time-remaining thresholds.
5. Each anchor SHALL store: `timestamp`, `urgency_tier`, `tts_clip_path`, `fired` (boolean), `fire_count` (retry counter).
6. The chain engine SHALL expose a `get_next_unfired_anchor(reminder_id)` function for scheduler recovery after app restart.
7. Chain computation SHALL be deterministic — same inputs always produce the same anchor list — to support unit testing.
8. The chain engine SHALL validate that `arrival_time > departure_time + minimum_drive_time` before persisting.

### 2.4 Acceptance Criteria

- [ ] Chain for "30 min drive, arrive 9am" produces 8 anchors: 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "10 min drive, arrive 9am" produces 4 anchors: 8:50, 8:55, 8:59, 9:00
- [ ] Chain for "3 min drive, arrive 9am" produces 3 anchors: 8:57, 8:59, 9:00
- [ ] Chain with `drive_duration > arrival_time` is rejected with validation error
- [ ] `get_next_unfired_anchor` correctly returns the earliest unfired anchor after app restart
- [ ] Anchors are sorted by timestamp ascending in the database

### 2.5 Test Scenarios

**TC-01: Full chain generation (≥25 min buffer)**
Given a reminder with arrival_time = 9:00 AM and drive_duration = 30 minutes
When the chain engine computes the escalation chain
Then 8 anchors are created with timestamps: 8:30 AM (calm), 8:35 AM (casual), 8:40 AM (pointed), 8:45 AM (urgent), 8:50 AM (pushing), 8:55 AM (firm), 8:59 AM (critical), 9:00 AM (alarm)

**TC-02: Compressed chain (10-24 min buffer)**
Given a reminder with arrival_time = 9:00 AM and drive_duration = 15 minutes
When the chain engine computes the escalation chain
Then 5 anchors are created skipping calm and casual tiers, starting at T-10 (urgent)

**TC-03: Minimum chain (≤5 min buffer)**
Given a reminder with arrival_time = 9:00 AM and drive_duration = 3 minutes
When the chain engine computes the escalation chain
Then 3 anchors are created: T-3 (firm), T-1 (critical), T-0 (alarm)

**TC-04: Invalid chain rejection**
Given a reminder with arrival_time = 9:00 AM and drive_duration = 120 minutes
When the chain engine validates the chain
Then a validation error is returned: "drive_duration exceeds time_to_arrival"

**TC-05: Next unfired anchor recovery**
Given a reminder with 5 anchors where the first 2 have `fired = true` and the remaining 3 have `fired = false`
When `get_next_unfired_anchor(reminder_id)` is called
Then the third anchor (earliest unfired) is returned

**TC-06: Chain determinism**
Given identical arrival_time and drive_duration inputs
When chain engine is called twice
Then both calls produce anchor lists with identical timestamps and tiers (set comparison passes)

### 2.6 Out of Scope

- TTS clip generation (separate topic: Voice & TTS Generation)
- Background scheduling and actual firing (separate topic: Background Scheduling & Reliability)
- LLM parsing input validation (separate topic: Reminder Parsing & Creation)

---

## 3. Reminder Parsing & Creation

### 3.1 Description

The Quick Add interface accepts natural language input via text or speech. A unified LLM adapter (MiniMax or Anthropic) parses the input and extracts structured reminder data: destination/label, arrival time, and drive duration. The adapter is mock-able so parsing behavior can be tested without real API calls. Failed parsing falls back to keyword extraction.

### 3.2 User Journey

1. User taps "+" and speaks or types: "30 minute drive to Parker Dr, check-in at 9am"
2. App sends raw input to LLM adapter
3. Adapter returns structured object: `{ destination: "Parker Dr check-in", arrival_time: "09:00", drive_duration: 30, unit: "minutes" }`
4. App displays parsed interpretation for user confirmation
5. On confirm, chain engine computes anchors and TTS generation begins
6. Reminder is persisted to SQLite with status "pending"

### 3.3 Functional Requirements

1. The LLM adapter SHALL support MiniMax API endpoint (Anthropic-compatible) and Anthropic API, configurable via environment variable.
2. The adapter SHALL accept a system prompt defining the extraction schema and return a structured JSON object.
3. The adapter SHALL be fully mock-able via an `ILanguageModelAdapter` interface — a test implementation returns predefined fixture responses.
4. On LLM API failure, the adapter SHALL fall back to keyword extraction using regex patterns for time and duration.
5. Keyword extraction SHALL handle formats: "X min drive", "X-minute drive", "in X minutes", "arrive at X", "check-in at X".
6. The parsed result SHALL be displayed to the user as a confirmation card before chain creation.
7. User SHALL be able to manually correct any parsed field before confirming.
8. The parser SHALL extract the following fields: `destination` (string), `arrival_time` (ISO 8601 datetime), `drive_duration` (integer minutes), `reminder_type` (enum: countdown_event, simple_countdown, morning_routine, standing_recurring).

### 3.4 Acceptance Criteria

- [ ] "30 minute drive to Parker Dr, check-in at 9am" parses to destination = "Parker Dr check-in", arrival_time = today's 9:00 AM, drive_duration = 30
- [ ] "dryer in 3 min" parses as simple_countdown with drive_duration = 0 and arrival_time = now + 3 minutes
- [ ] "meeting tomorrow 2pm, 20 min drive" parses with arrival_time = next day's 2:00 PM
- [ ] On API failure, keyword extraction produces a best-effort parsed object with confidence score
- [ ] User can edit any parsed field and confirm — edited values are used for chain creation
- [ ] Empty or unintelligible input ("blah blah") returns a user-facing error and prompts retry

### 3.5 Test Scenarios

**TC-01: Full natural language parse**
Given user input: "30 minute drive to Parker Dr, check-in at 9am"
When the LLM adapter parses the input
Then the returned object contains: destination = "Parker Dr check-in", arrival_time within 1 minute of today's 9:00 AM, drive_duration = 30

**TC-02: Simple countdown parse**
Given user input: "dryer in 3 min"
When the LLM adapter parses the input
Then the returned object contains: destination = "dryer", arrival_time within 1 minute of now + 3 minutes, drive_duration = 0, reminder_type = "simple_countdown"

**TC-03: Tomorrow date resolution**
Given user input: "meeting tomorrow 2pm, 20 min drive" and today is April 8, 2026
When the LLM adapter parses the input
Then arrival_time is April 9, 2026 at 2:00 PM

**TC-04: LLM API failure fallback**
Given user input: "Parker Dr 9am, 30 min drive" and the LLM API returns an error
When the adapter processes the input
Then keyword extraction runs and returns a best-effort parsed object with confidence_score < 1.0

**TC-05: Manual field correction**
Given the parsed result: destination = "Parker Dr check-in", arrival_time = "09:00 AM"
When the user changes arrival_time to "09:15 AM" in the confirmation card
Then the confirmed reminder is created with arrival_time = "09:15 AM"

**TC-06: Unintelligible input rejection**
Given user input: "asdfgh jkl qwerty"
When the LLM adapter and keyword extractor both fail to extract valid fields
Then a user-facing error "Couldn't understand that — try again" is displayed

**TC-07: Mock adapter in tests**
Given a mock LLM adapter configured with fixture: `{ destination: "Test", arrival_time: "2026-04-09T10:00:00", drive_duration: 15 }`
When the parser processes any input in test mode
Then the mock response is returned without any real API call

### 3.6 Out of Scope

- Chain computation (separate topic: Escalation Chain Engine)
- TTS generation (separate topic: Voice & TTS Generation)
- Calendar event parsing (separate topic: Calendar Integration)

---

## 4. Voice & TTS Generation

### 4.1 Description

All voice output is pre-generated at reminder creation time and cached locally. This eliminates runtime TTS latency — when an anchor fires, the app plays a local file, never calls an API. Each reminder stores its TTS clips keyed by anchor ID. The ElevenLabs adapter is fully mock-able for testing.

### 4.2 User Journey

1. User confirms parsed reminder
2. Chain engine produces anchor list
3. For each anchor, TTS generation service calls ElevenLabs with: voice personality prompt, urgency-tier message text, and destination context
4. Generated audio file is saved to local cache (`/tts_cache/{reminder_id}/{anchor_id}.mp3`)
5. Anchor record is updated with `tts_clip_path`
6. On chain fire, audio player reads from local cache — no network call

### 4.3 Functional Requirements

1. The TTS adapter SHALL support ElevenLabs API and be configurable via environment variable.
2. The TTS adapter SHALL be fully mock-able via an `ITTSAdapter` interface.
3. TTS generation SHALL run at reminder creation only — not at runtime.
4. Generated clips SHALL be cached in the app's local file system under `/tts_cache/{reminder_id}/`.
5. If TTS generation fails, the system SHALL fall back to system notification sounds with the text rendered as notification body.
6. Each voice personality SHALL map to a distinct ElevenLabs voice ID.
7. Custom voice prompts SHALL be passed as ElevenLabs voice settings/style parameters.
8. The TTS cache SHALL be invalidated when a reminder is deleted.
9. Total TTS generation for a single reminder SHALL complete within 30 seconds (ElevenLabs async API with polling).

### 4.4 Acceptance Criteria

- [ ] A new reminder generates 8 MP3 clips (one per anchor) stored in `/tts_cache/{reminder_id}/`
- [ ] Playing an anchor fires the correct pre-generated clip from local cache
- [ ] When ElevenLabs API is unavailable, fallback to system sound + notification text fires without error
- [ ] Reminder deletion removes all cached TTS files for that reminder
- [ ] TTS generation uses the correct voice ID for the selected voice personality

### 4.5 Test Scenarios

**TC-01: TTS clip generation at creation**
Given a confirmed reminder with 8 anchors and voice personality "Coach"
When TTS generation completes
Then 8 MP3 files exist in `/tts_cache/{reminder_id}/` and each anchor record has a non-null `tts_clip_path`

**TC-02: Anchor fires from cache**
Given a reminder with all TTS clips pre-generated
When the scheduler fires anchor 3
Then the audio player plays the local file at `tts_clip_path` with no network call

**TC-03: TTS fallback on API failure**
Given ElevenLabs API returns a 503 error
When TTS generation attempts to create a clip
Then the clip is skipped and the anchor is marked with `tts_fallback = true`

**TC-04: TTS cache cleanup on delete**
Given a reminder with 5 cached TTS files
When the reminder is deleted
Then all 5 files are removed from `/tts_cache/{reminder_id}/`

**TC-05: Mock TTS in tests**
Given a mock TTS adapter that writes a 1-second silent file
When TTS generation is called in test mode
Then a file is written locally and the path is returned without any real API call

### 4.6 Out of Scope

- Runtime TTS streaming (not used — all pre-generated)
- Voice recording import (custom voice audio import is separate topic: Sound Library)

---

## 5. Notification & Alarm Behavior

### 5.1 Description

The notification and alarm behavior layer handles how nudges are presented to the user: gentle notification sounds for early anchors, full alarm sounds for final 5 minutes and T-0, DND awareness, quiet hours, and chain overlap serialization.

### 5.2 User Journey

1. Scheduler fires anchor at pre-computed timestamp
2. If phone is in DND and anchor is pre-5-minute: skip, queue for post-DND
3. If phone is in DND and anchor is in final 5 minutes: fire visual notification (no sound)
4. If phone is in quiet hours and anchor is before 7am/after 10pm: skip, queue for post-quiet-hours
5. If another chain is currently firing: queue this anchor, fire after current chain completes
6. Play TTS clip + appropriate notification sound tier
7. On final anchor (T-0): play alarm sound in a loop until user acts

### 5.3 Functional Requirements

1. The notification tier SHALL escalate with urgency: gentle chime (calm/casual), pointed beep (pointed/urgent), urgent siren (pushing/firm), looping alarm (critical/alarm).
2. The app SHALL respect system Do Not Disturb — early anchors fire as silent notifications during DND; final 5 minutes fire with visual override and vibration.
3. Quiet hours SHALL suppress all nudges between a user-configurable start and end time (default: 10pm–7am).
4. Anchors skipped due to DND or quiet hours SHALL be queued and fired at the next available moment after the restriction ends, unless they are more than 15 minutes overdue.
5. Anchors more than 15 minutes overdue due to DND/quiet hours SHALL be silently dropped.
6. The app SHALL serialize chain execution — if a chain is mid-escalation when a new reminder's anchor fires, the new anchor is queued and fires after the current chain completes.
7. T-0 alarm SHALL continue looping until the user dismisses or snoozes — it SHALL NOT auto-dismiss.
8. The notification SHALL display: destination label, time remaining ("5 minutes"), and voice personality icon.

### 5.5 Test Scenarios

**TC-01: DND — early anchor suppressed**
Given a reminder fires at 8:30 AM and the phone is in DND mode
When the anchor fires
Then a silent notification is posted and the TTS clip is not played

**TC-02: DND — final 5-minute override**
Given a reminder fires at 8:55 AM (T-5) and the phone is in DND mode
When the anchor fires
Then a visual notification with vibration is posted and TTS clip plays

**TC-03: Quiet hours suppression**
Given quiet hours are set to 10pm–7am and an anchor is scheduled for 6:30am
When the anchor fires
Then it is suppressed and queued

**TC-04: Overdue anchor drop (15 min rule)**
Given an anchor was scheduled for 8:55 AM but was suppressed by quiet hours until 9:10 AM
When the system evaluates the queued anchor at 9:10 AM
Then the anchor is dropped and the chain continues from the next anchor

**TC-05: Chain overlap serialization**
Given Chain A is mid-escalation (anchor 4 of 8 firing)
When an anchor from Chain B arrives
Then Chain B's anchor is queued and fires after Chain A completes

**TC-06: T-0 alarm loops until action**
Given the T-0 alarm anchor fires
When the alarm fires
Then it loops continuously until the user taps dismiss or snooze

### 5.6 Out of Scope

- Background scheduling (separate topic: Background Scheduling & Reliability)
- Snooze behavior (separate topic: Snooze & Dismissal Flow)
- Sound library selection (separate topic: Sound Library)

---

## 6. Background Scheduling & Reliability

### 6.1 Description

Reminders must fire accurately even when the app is closed, the phone is locked, or iOS has suspended background tasks. Notifee (backed by BGTaskScheduler on iOS and WorkManager on Android) provides reliable background scheduling. The system also implements device-state awareness and recovery for missed triggers.

### 6.2 User Journey

1. User creates reminder → chain anchors registered with Notifee
2. App can be closed; Notifee holds the scheduled tasks in the OS scheduler
3. At anchor time, OS wakes the app (or starts it from terminated state)
4. App loads reminder from SQLite, checks anchor hasn't already fired
5. Anchor fires via notification + TTS
6. If device was offline or app was killed, recovery scan runs on next app open

### 6.3 Functional Requirements

1. Each anchor SHALL be registered with Notifee as an individual background task with a precise trigger timestamp.
2. On iOS, the app SHALL use `BGAppRefreshTask` for near-accurate timing and `BGProcessingTask` for TTS clip pre-warming.
3. If a background task fails to fire (OS kill, battery saver), a recovery scan SHALL run on app launch and fire any overdue unfired anchors within the 15-minute grace window.
4. The recovery scan SHALL NOT fire anchors more than 15 minutes overdue.
5. Anchors that were missed and dropped SHALL be logged to history with `missed_reason = "background_task_killed"`.
6. The app SHALL persist all anchor state (fired/unfired) to SQLite so state survives app termination.
7. The scheduler SHALL re-register all pending (unfired) anchors on app launch after crash/termination.
8. Battery optimization MAY cause delays — the system SHALL log a warning if an anchor fires more than 60 seconds after its scheduled time.

### 6.4 Acceptance Criteria

- [ ] A reminder created with the app in foreground schedules all anchors correctly in Notifee
- [ ] Closing the app (swipe-to-dismiss) does not prevent anchors from firing within 5 minutes of their scheduled time
- [ ] After a simulated crash/force-kill, pending anchors are re-registered on next launch
- [ ] Recovery scan on launch fires only anchors within the 15-minute grace window
- [ ] Missed anchors more than 15 minutes overdue are dropped and logged with reason
- [ ] Late firing (>60s after scheduled time) triggers a warning log entry

### 6.5 Test Scenarios

**TC-01: Anchor scheduling with Notifee**
Given a reminder with 8 anchors
When the reminder is confirmed
Then 8 Notifee tasks are registered with correct trigger timestamps

**TC-02: Background fire with app closed**
Given the app is in the background (or not running) and Notifee has a pending anchor
When the trigger timestamp arrives
Then the anchor fires via notification

**TC-03: Recovery scan on launch**
Given the app launches after being force-killed with 3 unfired anchors that are within the grace window
When the recovery scan runs
Then those 3 anchors fire in timestamp order

**TC-04: Overdue anchor drop**
Given an anchor is 20 minutes overdue (app was killed at 8:50, now 9:10)
When the recovery scan runs
Then the anchor is dropped and logged with `missed_reason = "background_task_killed"`

**TC-05: Pending anchors re-registered on crash recovery**
Given a crash occurs with 5 unfired anchors
When the app restarts
Then those 5 anchors are re-registered with Notifee

**TC-06: Late fire warning**
Given an anchor fires 90 seconds after its scheduled time
When the anchor completes firing
Then a warning log entry is written with `late_fire_seconds = 90`

### 6.6 Out of Scope

- Exact wake-time guarantee (OS-controlled; iOS bg tasks have ±1 minute accuracy)
- Battery saver mode interaction (handled by OS; app logs but cannot override)

---

## 7. Calendar Integration

### 7.1 Description

The app integrates with Apple Calendar (EventKit) and Google Calendar (Google Calendar API) to automatically suggest departure reminders for calendar events that have a location. Events with locations are mapped to escalation chains using the event's start time as the arrival time and a user-configured default drive duration.

### 7.2 User Journey

1. User opts in to calendar access and selects which calendars to monitor
2. App syncs events from Apple Calendar and/or Google Calendar on launch and every 15 minutes
3. For each event with a location, the app surfaces a suggestion card: "Parker Dr check-in at 9am — add departure reminder?"
4. User confirms → a countdown_event reminder is created with parsed event data
5. Standing/recurring events auto-create reminders based on user preference (opt-in per calendar or per event type)

### 7.3 Functional Requirements

1. The calendar adapter SHALL support Apple Calendar via EventKit (iOS) and Google Calendar via Google Calendar API.
2. Both adapters SHALL implement a common `ICalendarAdapter` interface.
3. Calendar sync SHALL run on app launch, every 15 minutes while app is open, and via background refresh.
4. Only events with a non-empty `location` field SHALL be considered for departure nudge suggestions.
5. Suggested reminders from calendar events SHALL use a user-configured default drive duration, overridable per-event.
6. Calendar-sourced reminders SHALL be visually distinguished from manually-created reminders (calendar icon).
7. Recurring events SHALL generate a reminder for each occurrence, with the ability to snooze/disable a recurring series.
8. If calendar sync fails, the app SHALL continue functioning with locally-created reminders and surface an error banner.
9. Calendar permission denial SHALL surface a prompt explaining why calendar access is beneficial with a link to settings.

### 7.4 Acceptance Criteria

- [ ] Apple Calendar events with locations appear as suggestion cards within 2 minutes of sync
- [ ] Google Calendar events with locations appear as suggestion cards within 2 minutes of sync
- [ ] Confirming a calendar suggestion creates a countdown_event reminder
- [ ] Calendar permission denial shows explanation banner with "Open Settings" action
- [ ] Calendar sync failure does not prevent manual reminder creation
- [ ] Recurring daily event generates a reminder for each occurrence

### 7.5 Test Scenarios

**TC-01: Apple Calendar event suggestion**
Given the user has granted Apple Calendar permission and an event "Parker Dr check-in" at 9am with location "123 Parker Dr" exists
When the calendar sync runs
Then a suggestion card appears: "Parker Dr check-in — 9:00 AM — add departure reminder?"

**TC-02: Google Calendar event suggestion**
Given the user has connected Google Calendar and an event with location exists
When the calendar sync runs
Then a suggestion card appears for that event

**TC-03: Suggestion → reminder creation**
Given a calendar suggestion card for "Parker Dr check-in at 9am"
When the user taps "Add Reminder"
Then a countdown_event reminder is created with destination = "Parker Dr check-in", arrival_time = 9:00 AM

**TC-04: Permission denial handling**
Given Apple Calendar permission is denied
When the user opens the calendar tab
Then an explanation banner is shown: "Calendar access helps us suggest departure reminders. [Open Settings]"

**TC-05: Sync failure graceful degradation**
Given a Google Calendar API error occurs during sync
When the sync completes with error
Then manual reminders still work and an error banner is shown in the calendar tab

**TC-06: Recurring event handling**
Given a recurring event "Team Standup" at 9am every weekday with location "Zoom"
When the current day's sync runs
Then a reminder suggestion appears for today's occurrence

### 7.6 Out of Scope

- Calendar write operations (creating/editing events)
- Two-way calendar sync (reminders do not appear as calendar events)
- Event RSVP status filtering

---

## 8. Location Awareness

### 8.1 Description

At the moment a departure anchor fires, the app performs a single location check: is the user still at their origin? This is not continuous tracking — one API call at trigger time. If the user is still at origin at departure time, the app escalates to the "LEAVE NOW" urgency tier immediately rather than waiting for the next anchor.

### 8.2 User Journey

1. User creates a reminder — optionally sets an origin address or uses current location as origin
2. At departure time anchor (T-drive_duration), the app checks current location against origin
3. If still at origin: the "LEAVE NOW" (firm/critical) tier fires immediately instead of the scheduled calm nudge
4. If already left (not at origin): normal chain proceeds
5. Location data is not stored long-term — only used for this single comparison

### 8.3 Functional Requirements

1. Location check SHALL occur only at the departure anchor (T-drive_duration) — never continuously.
2. The origin location SHALL be resolved from: user-specified address, or current device location at reminder creation time.
3. The current location SHALL be obtained via a single CoreLocation (iOS) / FusedLocationProvider (Android) call at departure trigger.
4. Location comparison SHALL use a geofence radius of 500 meters — "at origin" if within 500m.
5. If the user is within 500m of origin at departure time, the system SHALL immediately fire the firm (T-5) or critical (T-1) anchor instead of the scheduled departure anchor.
6. Location permission SHALL be requested at the time of the first location-aware reminder creation, not at app launch.
7. If location permission is denied, the reminder SHALL be created without location awareness and a note shown: "Location-based escalation disabled."
8. Location data SHALL NOT be stored beyond the single comparison — no location history is retained.

### 8.4 Acceptance Criteria

- [ ] Departure anchor fires at scheduled time and performs one location check
- [ ] If user is within 500m of origin, the critical/urgent tier fires immediately instead of the calm departure nudge
- [ ] If user has left ( > 500m from origin), the normal chain proceeds from the departure anchor
- [ ] Location permission is requested only when first creating a location-aware reminder
- [ ] Denied location permission results in reminder creation without location escalation
- [ ] No location history is stored after the comparison completes

### 8.5 Test Scenarios

**TC-01: User still at origin at departure**
Given a reminder with origin set to 123 Main St and the user is within 500m of 123 Main St at departure time
When the departure anchor fires
Then the T-5 (firm) anchor fires immediately instead of the T-0 departure nudge

**TC-02: User already left at departure**
Given a reminder with origin set to 123 Main St and the user is 2km away from 123 Main St at departure time
When the departure anchor fires
Then the normal calm departure nudge fires as scheduled

**TC-03: Location permission request**
Given no location-aware reminders exist
When the user creates a reminder with "use current location as origin"
Then the system requests location permission at that moment (not on app launch)

**TC-04: Location permission denied**
Given location permission is "Denied" in system settings
When the user creates a reminder with location awareness
Then the reminder is created successfully with a note: "Location-based escalation disabled"

**TC-05: Single location check only**
Given a reminder is created with location awareness
When the app monitors the reminder over its lifetime
Then only one location API call is made (at departure anchor fire)

### 8.6 Out of Scope

- Continuous location tracking (explicitly excluded)
- Origin address autocomplete (future consideration)
- ETA-based dynamic drive duration (future consideration)

---

## 9. Snooze & Dismissal Flow

### 9.1 Description

The user interacts with nudges via tap (snooze 1 min), tap-and-hold (custom snooze), and swipe-to-dismiss. Each action has distinct behavior. Snooze resets the chain from the current time — it re-computes the remaining anchors and re-registers them. Dismissal triggers the missed-reminder feedback prompt.

### 9.2 User Journey

1. Anchor fires with notification
2. **Tap** → snooze 1 minute, TTS confirmation "Snoozed 1 minute", chain pauses
3. **Tap-and-hold** → custom snooze picker appears (1, 3, 5, 10, 15 min), TTS confirmation, chain resets
4. **Swipe dismiss** → feedback prompt: "You missed [destination] — was the timing right?" with Yes/No options
5. On snooze: chain re-computes from current time, re-registers remaining anchors with new timestamps
6. On feedback: response stored, departure estimate for this destination is adjusted

### 9.3 Functional Requirements

1. Tap snooze SHALL snooze the current anchor for 1 minute.
2. Tap-and-hold SHALL present a snooze duration picker (1, 3, 5, 10, 15 minutes).
3. On snooze, the chain SHALL re-compute: all remaining unfired anchors have their timestamps shifted to `now + original_time_remaining`.
4. Snoozed anchors SHALL be re-registered with Notifee with new timestamps.
5. Swipe-to-dismiss SHALL display a feedback prompt: "You missed [destination] — was the timing right? [Yes — timing was right] [No — timing was off]"
6. "No" response SHALL trigger a prompt: "What was wrong? [Left too early] [Left too late] [Other]"
7. Feedback data SHALL be stored in SQLite and used to adjust future departure estimates for that destination.
8. TTS SHALL speak the snooze confirmation: "Okay, snoozed [X] minutes."
9. If a chain is snoozed and the app is subsequently killed, the re-registration on next launch SHALL use the snoozed timestamps.

### 9.4 Acceptance Criteria

- [ ] Tap snooze pauses current anchor and re-fires after 1 minute
- [ ] Custom snooze picker allows 1, 3, 5, 10, 15 minute selection
- [ ] Chain re-computation after snooze shifts all remaining anchors by the snooze duration
- [ ] Feedback prompt appears on swipe-dismiss with destination label
- [ ] "No — timing was off" with "Left too late" feedback increases the drive_duration estimate for this destination by 2 minutes on next reminder
- [ ] TTS confirms snooze: "Okay, snoozed 3 minutes"
- [ ] After custom snooze and app restart, remaining anchors fire at adjusted times

### 9.5 Test Scenarios

**TC-01: Tap snooze**
Given anchor 4 (T-10, urgent) fires
When the user taps the notification
Then the current anchor is snoozed for 1 minute and TTS says "Okay, snoozed 1 minute"

**TC-02: Custom snooze**
Given anchor 3 (T-15, pointed) fires
When the user tap-and-holds and selects 5 minutes
Then the remaining anchors are shifted by 5 minutes and TTS says "Okay, snoozed 5 minutes"

**TC-03: Chain re-computation after snooze**
Given a reminder has anchors at 8:30, 8:35, 8:40, 8:45, 8:50, 8:55, 8:59, 9:00 and the user snoozes at 8:45
When the chain is re-computed with a 3-minute snooze
Then the remaining anchors are re-centered around 8:48 (8:48, 8:53, 8:59, 9:00)

**TC-04: Dismissal feedback — timing correct**
Given a reminder fires and the user swipes to dismiss
When the feedback prompt appears and user taps "Yes — timing was right"
Then feedback is stored and no adjustment is made to future departure estimates

**TC-05: Dismissal feedback — timing off (left too late)**
Given a reminder fires and user swipes to dismiss, then selects "No — timing was off" and "Left too late"
When feedback is processed
Then the drive_duration estimate for this destination is increased by 2 minutes for future reminders

**TC-06: Snooze persistence after restart**
Given a user applies a 5-minute snooze and the app is then killed
When the app restarts
Then the remaining anchors are re-registered with the 5-minute snooze offset applied

### 9.6 Out of Scope

- Voice reply snooze ("snooze 5 min" spoken) — future consideration
- Snooze stacking (multiple consecutive snoozes) — only the most recent snooze is active

---

## 10. Voice Personality System

### 10.1 Description

The voice personality defines the tone, vocabulary, and urgency delivery style of all TTS messages. Five built-in personalities are available, plus a custom mode where the user writes a short style prompt. Each personality maps to an ElevenLabs voice ID and a set of pre-written message templates per urgency tier.

### 10.2 User Journey

1. User completes onboarding → selects a voice personality from 5 options + custom
2. User can change personality at any time in Settings
3. At reminder creation, the selected personality determines: ElevenLabs voice ID, system prompt for message generation, and template overrides per urgency tier
4. TTS generation uses personality settings to produce clips that match the selected tone

### 10.3 Functional Requirements

1. Five built-in personalities SHALL be available: "Coach", "Assistant", "Best Friend", "No-nonsense", and "Calm" (gentle-only for users who don't want aggression).
2. Each personality SHALL define: `voice_id` (ElevenLabs), `system_prompt` fragment for message generation, and tier-specific message templates.
3. "Custom" mode SHALL accept a user-written prompt (max 200 characters) that is appended to the message generation system prompt.
4. The selected personality SHALL be stored in user preferences (SQLite) and applied to all new reminders.
5. Existing reminders SHALL NOT change personality when user changes their default — they retain the personality active at creation time.
6. Each personality tier SHALL produce distinct message variations (minimum 3 per tier per personality) to avoid robotic repetition.

### 10.4 Acceptance Criteria

- [ ] "Coach" personality at T-5 produces: "Let's GO! You've got 5 minutes to Parker Dr!"
- [ ] "No-nonsense" personality at T-5 produces: "5 minutes. Parker Dr. Leave."
- [ ] "Assistant" personality at T-5 produces: "You have 5 minutes. I'd suggest moving now for Parker Dr."
- [ ] Custom prompt "speak like a disappointed but caring parent" modifies message tone appropriately
- [ ] Changing default personality in settings does not affect existing reminders
- [ ] Each personality generates at least 3 message variations per urgency tier

### 10.5 Test Scenarios

**TC-01: Coach personality messages**
Given personality = "Coach" and urgency_tier = "urgent"
When message generation is called for "Parker Dr" at T-5
Then the generated message contains motivational language and an exclamation mark

**TC-02: No-nonsense personality messages**
Given personality = "No-nonsense" and urgency_tier = "firm"
When message generation is called for "Parker Dr" at T-5
Then the generated message is brief, direct, and contains no filler words

**TC-03: Custom personality**
Given custom_prompt = "speak like a disappointed but caring parent who doesn't yell but is firm"
When message generation is called for T-3
Then the message reflects a firm-but-caring tone without aggressive shouting

**TC-04: Personality immutability for existing reminders**
Given a reminder was created with "Coach" personality
When the user changes their default personality to "Assistant" and the existing reminder's chain fires
Then the existing reminder still uses "Coach" messages

**TC-05: Message variation**
Given personality = "Best Friend" and urgency_tier = "casual"
When message generation is called 3 times for the same context
Then at least 2 distinct message phrasings are produced

### 10.6 Out of Scope

- Voice recording import (custom audio files — separate topic: Sound Library)
- Prosody control (speed/pitch adjustment) beyond ElevenLabs voice settings
- Per-reminder personality override — all anchors in a reminder use the same personality

---

## 11. History, Stats & Feedback Loop

### 11.1 Description

The history and stats system tracks every reminder outcome: hit (user left on time), missed (user dismissed without snooze), or snoozed (user snoozed at least once). Over time, the system learns from missed reminders to adjust departure estimates for specific destinations.

### 11.2 User Journey

1. User opens History tab → sees weekly hit rate, current streak, and common miss patterns
2. Each reminder completion is recorded with: destination, scheduled departure, actual departure (inferred), and outcome
3. On dismissal feedback ("Left too late"), future reminders to the same destination automatically add 2 minutes to the drive_duration estimate
4. "Common miss window" shows users that they typically miss the 5-minute warning — encouraging them to leave earlier
5. Streak counter increments for consecutive on-time completions of standing/recurring reminders

### 11.3 Functional Requirements

1. Hit rate SHALL be calculated as: `count(outcome = 'hit') / count(outcome != 'pending') * 100` for the trailing 7 days.
2. The feedback loop SHALL adjust `drive_duration` for a destination: `adjusted_drive_duration = stored_drive_duration + (late_count * 2_minutes)`, capped at +15 minutes.
3. "Common miss window" SHALL display the urgency tier that is most frequently missed (e.g., "You usually miss the T-5 warning").
4. Streak counter SHALL increment when a standing/recurring reminder completes with outcome = 'hit' and reset to 0 on a 'miss'.
5. History entries SHALL store: `reminder_id`, `destination`, `scheduled_arrival`, `actual_arrival` (nullable), `outcome` (hit, miss, snoozed), `feedback_type` (nullable), `created_at`.
6. All stats SHALL be computable from the history table — no separate stats table (single source of truth).
7. History data SHALL be retained for 90 days; data older than 90 days SHALL be archived but accessible.

### 11.4 Acceptance Criteria

- [ ] Weekly hit rate displays correctly: 4 hits and 1 miss in 7 days = 80% hit rate
- [ ] After 3 "Left too late" feedback events for "Parker Dr", the next "Parker Dr" reminder adds 6 minutes to drive_duration estimate
- [ ] "Common miss window" correctly identifies the most frequently missed urgency tier
- [ ] Streak increments on hit and resets on miss for the same recurring reminder
- [ ] Stats are computable from the history table alone (no separate stats store)

### 11.5 Test Scenarios

**TC-01: Hit rate calculation**
Given 7 days of history: 4 hits, 1 miss, 2 pending (not yet fired)
When the hit rate is computed
Then the result is 80% (4 / 5 * 100)

**TC-02: Feedback loop — drive duration adjustment**
Given "Parker Dr" has 3 late feedback entries stored
When a new reminder to Parker Dr is created
Then the suggested drive_duration is original_duration + 6 minutes

**TC-03: Feedback loop cap**
Given "Parker Dr" has 10 late feedback entries stored (each +2 min)
When a new reminder to Parker Dr is created
Then the suggested drive_duration is original_duration + 15 minutes (capped)

**TC-04: Common miss window identification**
Given history shows anchors at T-5 were missed 4 times while T-10 was missed 1 time for the same destination
When "common miss window" is queried
Then "T-5" is returned

**TC-05: Streak increment on hit**
Given a recurring morning routine reminder has a current streak of 5
When the reminder completes with outcome = 'hit'
Then the streak becomes 6

**TC-06: Streak reset on miss**
Given a recurring morning routine reminder has a current streak of 5
When the reminder completes with outcome = 'miss'
Then the streak becomes 0

**TC-07: Stats derived from history table**
Given a fresh database with history entries
When stats are computed
Then the results match a direct SQL aggregation of the history table

### 11.6 Out of Scope

- Export/history sharing (future consideration)
- Multi-user/household aggregate stats (future consideration — family tier)
- Automatic calendar adjustment based on feedback (future consideration)

---

## 12. Sound Library

### 12.1 Description

Each reminder type (commute, routine, errand, custom) has an associated sound profile. The app ships with 5 built-in sounds per profile and supports importing custom audio files (MP3, WAV, M4A). Sound selection is per-reminder, not global.

### 12.2 User Journey

1. User creates a reminder → expands "Sound" section
2. User selects a sound category (commute, routine, errand, custom)
3. User picks a sound from the category's library or taps "Import Custom"
4. Custom import opens file picker — user selects MP3/WAV/M4A
5. Selected sound is copied to app storage and associated with the reminder
6. At anchor fire, the selected sound plays under the TTS message

### 12.3 Functional Requirements

1. Built-in sounds SHALL be bundled with the app and never require a network call.
2. Sound categories: "Commute" (5 sounds), "Routine" (5 sounds), "Errand" (5 sounds), "Custom" (imported).
3. Custom audio imports SHALL support MP3, WAV, and M4A formats, maximum 30 seconds duration.
4. Imported sounds SHALL be transcoded to a normalized format and stored in app sandbox.
5. Per-reminder sound selection SHALL override the category default.
6. Sound selection SHALL be stored in the reminder record in SQLite.
7. Custom sounds SHALL be associated with the user account and persist across app reinstalls (via SQLite reference, not raw file).
8. If a custom sound file is deleted/corrupted, the system SHALL fall back to the category default and surface an error.

### 12.4 Acceptance Criteria

- [ ] Built-in sounds play without network access
- [ ] Custom MP3 import appears in the sound picker for the reminder
- [ ] Imported sound plays correctly under TTS at anchor fire
- [ ] Corrupted custom sound fallback shows error and uses category default
- [ ] Sound selection persists when reminder is edited

### 12.5 Test Scenarios

**TC-01: Built-in sound playback**
Given a reminder with sound_category = "Commute" and selected_sound = default
When anchor fires
Then the built-in "commute_default" sound plays under TTS

**TC-02: Custom sound import**
Given the user imports "my_alarm.mp3" via the file picker
When the reminder's sound picker is opened
Then "my_alarm.mp3" appears as an option in the Custom category

**TC-03: Custom sound playback**
Given a reminder with a selected custom sound "my_alarm.mp3"
When anchor fires
Then "my_alarm.mp3" plays under TTS

**TC-04: Corrupted sound fallback**
Given a reminder references a custom sound that no longer exists on disk
When anchor fires
Then the category default sound plays and an error is logged

**TC-05: Sound persistence on edit**
Given a reminder with a non-default sound selected
When the user edits the reminder's destination
Then the sound selection is retained

### 12.6 Out of Scope

- Sound recording (user cannot record a sound within the app)
- Sound trimming/editing (imported sounds play as-is)
- Cloud sound library / sound purchases (future consideration)

---

## 13. Data Persistence

### 13.1 Description

All app data lives in a local SQLite database. The schema supports reminders, anchors, history, user preferences, calendar sync state, and sound library references. Migrations are versioned and applied sequentially. In-memory SQLite mode is used for tests.

### 13.2 Schema

```sql
-- Core tables
reminders (
  id TEXT PRIMARY KEY,
  destination TEXT NOT NULL,
  arrival_time TEXT NOT NULL,        -- ISO 8601
  drive_duration INTEGER NOT NULL,    -- minutes
  reminder_type TEXT NOT NULL,        -- countdown_event | simple_countdown | morning_routine | standing_recurring
  voice_personality TEXT NOT NULL,    -- coach | assistant | best_friend | no_nonsense | calm | custom
  sound_category TEXT,               -- commute | routine | errand | custom
  selected_sound TEXT,
  custom_sound_path TEXT,
  origin_lat REAL,
  origin_lng REAL,
  origin_address TEXT,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | active | completed | cancelled
  calendar_event_id TEXT,             -- references calendar event if calendar-sourced
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)

anchors (
  id TEXT PRIMARY KEY,
  reminder_id TEXT NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
  timestamp TEXT NOT NULL,            -- ISO 8601
  urgency_tier TEXT NOT NULL,         -- calm | casual | pointed | urgent | pushing | firm | critical | alarm
  tts_clip_path TEXT,                 -- local file path, null if fallback
  tts_fallback BOOLEAN DEFAULT FALSE,
  fired BOOLEAN DEFAULT FALSE,
  fire_count INTEGER DEFAULT 0,       -- retry counter
  snoozed_to TEXT,                    -- new timestamp if snoozed
  UNIQUE(reminder_id, timestamp)
)

history (
  id TEXT PRIMARY KEY,
  reminder_id TEXT REFERENCES reminders(id),
  destination TEXT NOT NULL,
  scheduled_arrival TEXT NOT NULL,
  actual_arrival TEXT,                -- null until resolved
  outcome TEXT NOT NULL,               -- hit | miss | snoozed
  feedback_type TEXT,                  -- timing_right | left_too_early | left_too_late | other
  missed_reason TEXT,                  -- background_task_killed | dnd_suppressed | user_dismissed | null
  created_at TEXT NOT NULL
)

user_preferences (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
)

-- Drive duration adjustment per destination (for feedback loop)
destination_adjustments (
  destination TEXT PRIMARY KEY,
  adjustment_minutes INTEGER DEFAULT 0,
  hit_count INTEGER DEFAULT 0,
  miss_count INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL
)

-- Calendar sync state
calendar_sync (
  calendar_type TEXT PRIMARY KEY,     -- apple | google
  last_sync_at TEXT,
  sync_token TEXT,                    -- for incremental sync
  is_connected BOOLEAN DEFAULT FALSE
)

-- Sound library
custom_sounds (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  category TEXT NOT NULL,
  file_path TEXT NOT NULL,            -- app sandbox path
  duration_seconds REAL,
  created_at TEXT NOT NULL
)
```

### 13.3 Functional Requirements

1. All migrations SHALL be sequential and versioned (starting at schema_v1).
2. No existing migration SHALL be modified after being applied — only new migrations added.
3. In-memory SQLite mode SHALL be available for tests via a `?mode=memory` connection string.
4. Each test suite SHALL use a fresh in-memory database with schema migrations applied.
5. All timestamps SHALL be stored in ISO 8601 format (UTC internally, displayed in local time).
6. `reminders.id` SHALL be a UUID v4 generated at creation time.
7. Foreign key enforcement SHALL be enabled (`PRAGMA foreign_keys = ON`).
8. The database SHALL be opened with WAL mode for performance (`PRAGMA journal_mode = WAL`).

### 13.4 Acceptance Criteria

- [ ] Fresh install applies all migrations in order, schema is current
- [ ] In-memory test database starts empty and migrations apply cleanly
- [ ] `reminders.id` is always a valid UUID v4
- [ ] Deleting a reminder cascades to delete its anchors
- [ ] Foreign key violation returns error without crashing

### 13.5 Test Scenarios

**TC-01: Migration sequence**
Given schema version 0 (fresh install)
When migrations run
Then all tables are created in order and schema_version = N (current)

**TC-02: In-memory test database**
Given a test requests `Database.getInMemoryInstance()`
When the database is used
Then it is a fresh in-memory instance with all migrations applied and no persisted data

**TC-03: Cascade delete**
Given a reminder with 8 anchors exists
When the reminder is deleted
Then all 8 anchor rows are also deleted

**TC-04: Foreign key enforcement**
Given an anchor exists with reminder_id = "reminder-uuid"
When a DELETE attempt is made on the reminders table without CASCADE
Then an FK violation error is returned

**TC-05: UUID generation**
Given a new reminder is created
When the reminder is persisted
Then `reminders.id` is a valid UUID v4 string

### 13.6 Out of Scope

- Multi-device sync (future — requires server-side storage)
- Database encryption (future consideration)
- Full-text search on destination names (future consideration)

---

## 14. Definition of Done

All acceptance criteria have corresponding passing tests.

Every criterion in Sections 2–13 maps to at least one test scenario (Given/When/Then). The test suite must achieve:

- **Unit tests** — Chain engine determinism, parser fixtures, TTS adapter mock, LLM adapter mock, keyword extraction, schema validation
- **Integration tests** — Full reminder creation flow (parse → chain → TTS → persist), anchor firing (schedule → fire → mark fired), snooze recovery (snooze → recompute → re-register), feedback loop (dismiss → feedback → adjustment applied)
- **E2E tests** (Detox) — Quick Add flow, reminder confirmation, anchor firing sequence, snooze interaction, dismissal feedback, settings navigation, sound library browsing

All tests run in CI on every push. A failing test blocks merge.

---

## Derived From

- Product Requirements: `specs/urgent-voice-alarm-app-2026-04-08.md`
- Interview sessions: Q1–Q7 (problem statement, users, success definition, failure modes, tech stack, scope, edge cases)
- Ralph Wiggum Technique — Geoffrey Huntley (github.com/ghuntley/how-to-ralph-wiggum)
- NLSpec format — StrongDM Attractor (github.com/strongdm/attractor)
