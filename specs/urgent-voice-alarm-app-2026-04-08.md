# URGENT — AI Escalating Voice Alarm

## Concept

A mobile alarm app that speaks to you — not just beeps, but *talks* — with escalating urgency messages that adapt based on remaining time and context. Set a reminder like "leave for Parker Dr appointment in 30 minutes" and the app progressively nags you: "25 minutes... 15 minutes... 10 minutes to leave, you're 30 minutes away... 2 minutes, MOVE." It knows when to escalate from calm to urgent, and speaks like a real person who cares whether you make it.

## Target Users

- **Commuters and field workers** — people with back-to-back off-site appointments who need aggressive departure nudges
- **People with ADHD** — external executive function support; a voice in your ear keeping you on track
- **Logistics / delivery** — "30 second countdown" style but contextual ("you have 3 packages to drop, 2 minutes left on stop 1")
- **Caregivers / parents** — morning routines for kids ("10 minutes, brush teeth... 5 minutes, shoes on... 1 minute, GO")

## Core Experience

### Setting a Reminder (the "Ask")

User opens app → taps "+" → speaks or types:

> "30 minute drive to Parker Dr, check-in at 9am"

App parses this:
- **Destination / label:** Parker Dr check-in
- **Arrival time:** 9:00 AM
- **Drive time:** 30 minutes
- **Departure needed:** 8:30 AM

App then creates an **escalation chain** from departure cue through arrival deadline, voiced by AI.

### The Escalation Chain

For the example above, the app would speak at:

| Time | Message | Tone |
|------|---------|-------|
| 8:30 AM | "Alright, time to head out for your Parker Dr check-in. 30 minute drive, you've got this." | Calm, encouraging |
| 8:35 AM | "Hey, Parker Dr check-in in 25 minutes. You should probably be in the car by now." | Casual nudge |
| 8:40 AM | "Parker Dr, 20 minutes. You leaving soon, right?" | Getting pointed |
| 8:45 AM | "20 minute mark — Parker Dr check-in in 15 minutes. 30 minute drive. Time to go. Now." | Urgent |
| 8:50 AM | "10 minutes. Parker Dr. You're cutting it close. 30 minute drive, departure was 8:30." | Pushing |
| 8:55 AM | "5 minutes. Parker Dr. 30 minute drive. LEAVE NOW." | Firm |
| 8:59 AM | "One minute to Parker Dr. You are late. Move." | Critical |
| 9:00 AM | "BEEP BEEP BEEP — Parker Dr check-in was right now." | Alarm escalation |

The chain is **adaptive**: shorter buffers trigger shorter chains. If the user sets "20 min drive, 10 min buffer", the app skips the calm 25/20-min nudges and goes straight to 5-minute urgency.

### Voice Personalities

User picks a voice style at onboarding (can be changed later):

- **"Coach"** — motivating, pep-talk energy. "Let's GO, you've got 5 minutes!"
- **"Assistant"** — calm, clear, slightly British. "You have three minutes. I'd suggest moving now."
- **"Best Friend"** — casual, warm. "Omg okay so Parker Dr is in like... 2 minutes? You should probably be worried."
- **"No-nonsense"** — clipped, direct. "5 minutes. Parker Dr. Leave."
- **Custom** — user writes a short prompt: "speak like a disappointed but caring parent who doesn't yell but is firm"

Voice is generated via TTS (e.g., ElevenLabs) and cached per reminder after generation.

### Types of Reminders

**1. Countdown Event** (most common)
"30 min drive to Parker Dr, arrive 9am" — triggers departure chain + arrival alarm

**2. Simple Countdown**
"Just in 3 minutes: put clothes in dryer" — single escalating sequence at T-3, T-2, T-1, T-0

**3. Morning Routine**
User defines a reusable routine template: "Morning routine, 7am wake up, 7:10 clothes in dryer, 7:30 leave for work"
App builds a chain that fires each anchor point.

**4. Standing / Recurring**
Same as above but repeats daily/weekdays/custom. App learns from past behavior (e.g., "you always run 7 minutes late to this one").

### Notification / Alarm Behavior

- **Tone escalation:** First nudges use gentle notification sounds. Final 5 minutes and T-0 use actual alarm sounds (user-selectable: beep, siren, chime, custom audio)
- **Snooze:** Tap to snooze 1 min; tap-and-hold or swipe to set custom snooze with optional text ("snooze 5 min, I'll be ready"). App speaks the snooze confirmation and resets chain from current time.
- **Do Not Disturb aware:** Respects system DND. Fires visual notification instead during DND, and bumps to post-DND if within 15 min of trigger.
- **No chain overlap:** If a chain is mid-escalation, new reminders queue and fire after current chain completes or user dismisses.

## Features

### 1. Quick Add
- Single text/speech input; parses time, label, duration automatically via LLM
- Shows parsed interpretation before confirming
- Natural language: "Parker Dr 9am, 30 min drive" / "dryer in 3 min" / "meeting tomorrow 2pm"

### 2. Calendar Integration (Optional, opt-in)
- Reads Google Calendar / Apple Calendar events
- Auto-suggests departure reminders for events with a location
- Maps event times to escalation chains automatically

### 3. Location Awareness (Optional, opt-in)
- Single location check when departure-time arrives: is user still at origin?
- If still at origin at T-minus-drive-time, escalate harder (fire the "LEAVE NOW" tier immediately)
- No continuous tracking — only checked on reminder trigger

### 4. Sound Library
- Per-reminder-type sound selection (commute, routine, errand, custom)
- Built-in sounds + import custom audio

### 5. Missed Reminder Feedback
- On missed reminder (alarm dismissed without snooze): "You missed Parker Dr — was the timing right?"
- Stores feedback; adjusts future departure estimates for that destination

### 6. History / Stats
- Weekly hit rate: "You hit 94% of your reminders this week"
- Streak counter for routine reminders
- Common miss window: "You usually miss the 5-min warning"

### 7. Sleep / Wind-Down Mode
- Quiet hours: no nudges between set times (e.g., 10pm–7am)
- Morning routines can be pre-scheduled night before

## Differentiation from Existing Apps

| Feature | Native Alarm | Google/Apple Reminders | Dewy / AI Alarms | This App |
|---------|-------------|------------------------|-------------------|----------|
| Countdown urgency escalation | ✗ | ✗ | ✗ | ✓ |
| AI-generated contextual messages | ✗ | ✗ | Partial | ✓ |
| Voice-based reminder setting | ✗ | ✗ | ✓ | ✓ |
| Contextual departure timing | ✗ | ✓ (location) | ✗ | ✓ |
| Adaptive chain (shorter buffer = shorter chain) | ✗ | ✗ | ✗ | ✓ |
| Beep escalation + voice combo | ✗ | ✗ | ✓ | ✓ |
| Calendar auto-import + departure nudge | ✗ | ✓ | ✗ | ✓ |

## Technical Approach

### Stack
- **Platform:** React Native or Flutter (iOS + Android)
- **AI Voice:** ElevenLabs API (custom voice profiles, TTS caching)
- **LLM Parsing:** OpenAI or Claude API for natural language reminder parsing
- **Local DB:** SQLite (reminder storage, user preferences, history)
- **Push Notifications:** Firebase Cloud Messaging (cross-platform background alerts)
- **Calendar:** Google Calendar API + Apple EventKit
- **Location:** CoreLocation (iOS) + FusedLocationProvider (Android) — single check on trigger

### Key Architecture Decisions

1. **Voice caching:** TTS generated upfront at reminder creation and cached locally. Zero runtime TTS latency.
2. **Chain pre-computation:** Full escalation chain computed at creation (timestamps + pre-generated clips). No LLM at runtime.
3. **Background execution:** iOS BGTaskScheduler + Android WorkManager to ensure reminders fire with app closed.
4. **Graceful degradation:** Failed AI parsing falls back to keyword extraction. Failed TTS falls back to system beep + notification text.

## Name Candidates

- **Urgent** — on-brand
- **Nudge** — simple, action-oriented
- **Wake Call** — clear purpose
- **GetOut** — casual, memorable
- **Bolt** — implies urgency

## Monetization

- Free tier: 5 active reminders, 2 voice styles
- Premium ($4.99/mo): unlimited reminders, all voice styles, calendar integration
- Family tier: shared routine templates, household morning routines

## Open Questions

- Speaker vs. Bluetooth: should nudges play through phone speaker or auto-connect to last-used Bluetooth audio?
- Voice reply: can user respond to nudges ("snooze 5 min" spoken back)?
- Gentle mode: calm-only nudges for users who don't want aggression?
- Smart home integration: Hue lights pulse red in final minute?
