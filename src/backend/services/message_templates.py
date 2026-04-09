"""
Message Templates for Voice Personality System

Per spec Section 10: 5 personalities × 8 tiers × 3+ variations each.
Extracted from test_server.py for modularity and testability.
"""

# Voice personality message generation - 3+ variations per tier
VOICE_PERSONALITIES = {
    'coach': {
        'calm': [
            "Alright, time to head out for {dest}. {dur} minute drive, you've got this!",
            "Time to start getting ready for {dest}. You've got {dur} minutes before you need to leave.",
            "Heads up: {dest} is coming up. You've got {dur} minutes to prepare.",
        ],
        'casual': [
            "Hey, {dest} in {remaining} minutes. You should probably be in the car by now.",
            "Quick note: {dest} in about {remaining} minutes. Time to think about heading out.",
            "FYI: {remaining} minutes until {dest}. The drive takes {dur} minutes.",
        ],
        'pointed': [
            "{dest}, {remaining} minutes. You leaving soon, right?",
            "{remaining} minutes to {dest}. You should probably get moving.",
            "Hey! {dest} in {remaining}. Time to head out.",
        ],
        'urgent': [
            "Let's GO! {remaining} minutes to {dest}! Time to move!",
            "Okay, {remaining} minutes to {dest}. Let's get moving!",
            "Move it! {remaining} minutes to {dest}!",
        ],
        'pushing': [
            "{remaining} minutes! {dest}! You need to leave NOW!",
            "Time to go! {remaining} minutes to {dest}!",
            "Leave NOW! {remaining} minutes to {dest}!",
        ],
        'firm': [
            "OK, {remaining} minutes to {dest}. LEAVE NOW.",
            "{remaining} minutes. {dest}. Go now.",
            "Final call: {remaining} min to {dest}. GO.",
        ],
        'critical': [
            "{remaining} MINUTE{plural}! {dest}! MOVE!",
            "CRITICAL: {remaining} minutes to {dest}! GO NOW!",
            "LAST CHANCE: {remaining} min{plural} to {dest}! MOVE!",
        ],
        'alarm': [
            "BEEP BEEP BEEP — {dest} is RIGHT NOW!",
            "ALARM: {dest} is happening NOW!",
            "WAKE UP! {dest} is RIGHT NOW!",
        ],
    },
    'assistant': {
        'calm': [
            "Time to depart for {dest}. You have {dur} minutes for the drive.",
            "Reminder: {dest} departure in {dur} minutes.",
            "You have {dur} minutes before you need to leave for {dest}.",
        ],
        'casual': [
            "Reminder: {dest} in {remaining} minutes. I suggest heading out soon.",
            "FYI: {dest} in {remaining} minutes. You may want to start preparing.",
            "Heads up: {remaining} minutes until {dest}.",
        ],
        'pointed': [
            "{dest} in {remaining} minutes. The drive takes {dur} minutes.",
            "{remaining} minutes until {dest}. You should consider departing.",
            "Reminder: {dest} in {remaining} minutes. Time to leave soon.",
        ],
        'urgent': [
            "You have {remaining} minutes to reach {dest}. I'd recommend leaving now.",
            "Urgent: {remaining} minutes to {dest}. Please depart immediately.",
            "Time sensitive: {remaining} minutes until {dest}. Leave now.",
        ],
        'pushing': [
            "Urgent: {remaining} minutes until {dest}. Please depart immediately.",
            "Important: {remaining} minutes to {dest}. You must leave now.",
            "Critical: {remaining} min. {dest}. Depart immediately.",
        ],
        'firm': [
            "Critical: {remaining} minutes. {dest}. Leave now.",
            "{remaining} minutes to {dest}. Immediate departure required.",
            "Final notice: {remaining} minutes. {dest}. Leave now.",
        ],
        'critical': [
            "Final warning: {remaining} minute{plural} to {dest}. Move immediately.",
            "CRITICAL: {remaining} minutes to {dest}. GO NOW!",
            "URGENT: {remaining} minute{plural} until {dest}. Depart immediately!",
        ],
        'alarm': [
            "ALARM: {dest} is now. Immediate action required.",
            "ALARM: {dest} is happening RIGHT NOW!",
            "CRITICAL ALARM: {dest} is current. Move now!",
        ],
    },
    'best_friend': {
        'calm': [
            "Omg okay so, time to head to {dest}! You've got {dur} minutes, let's do this!",
            "Hey! So {dest} is coming up! You have {dur} minutes to get ready.",
            "Okay so, {dest} in {dur} minutes! No rush, you've got this!",
        ],
        'casual': [
            "Heyyy so {dest} is in like {remaining} minutes? You should probably get going!",
            "So {dest} in {remaining} mins... maybe start thinking about leaving?",
            "Quick heads up: {dest} in {remaining} minutes!",
        ],
        'pointed': [
            "Okay so {dest} in {remaining} mins... you're leaving soon right??",
            "{dest} in {remaining}! You need to go like NOW?",
            "Yo {dest} in {remaining}... are you leaving yet??",
        ],
        'urgent': [
            "Yo {dest} in {remaining} minutes! Like seriously, go go go!",
            "OK OK OK {remaining} minutes to {dest}! MOVE!",
            "GURL {dest} in {remaining}! GO GO GO!",
        ],
        'pushing': [
            "{remaining} minutes to {dest}! I am literally begging you to leave!",
            "PLEASEEEE {remaining} min to {dest}! Like right now!",
            "I'm begging you! {remaining} minutes to {dest}! LEAVE!",
        ],
        'firm': [
            "OKAY {remaining} minutes! {dest}! You gotta go RIGHT NOW!",
            "{remaining} min to {dest}! No more waiting! GO!",
            "FINAL WARNING {remaining}! {dest}! MOVE IT!",
        ],
        'critical': [
            "BRO {remaining} MINUTE{plural}! {dest}! GO GO GO!",
            "OMG {remaining} MINUTE{plural} TO {dest}!!! RUN!",
            "DUDE {remaining} min{plural}! {dest}!!! LEAVE NOW!!!",
        ],
        'alarm': [
            "ALARM ALARM {dest} IS NOW OMG!",
            "WAKE UP!!! {dest} IS HAPPENING RN!!!",
            "OMG OMG {dest} IS RIGHT NOW!!! GO!!!",
        ],
    },
    'no_nonsense': {
        'calm': [
            "{dest}. {dur} min drive. Leave now.",
            "Departure to {dest} in {dur} min. Start moving.",
            "Drive to {dest}: {dur} min. Leave when ready.",
        ],
        'casual': [
            "{dest}. {remaining} min. Go.",
            "{dest} in {remaining} min. Time to go.",
            "{remaining} min to {dest}. Go.",
        ],
        'pointed': [
            "{dest}. {remaining} min. Move.",
            "{remaining} min. {dest}. Go now.",
            "{dest}: {remaining} min. Move.",
        ],
        'urgent': [
            "{remaining} min. {dest}. Leave.",
            "Go now. {remaining} to {dest}.",
            "{remaining} min. {dest}. GO.",
        ],
        'pushing': [
            "{remaining} min. {dest}. Now.",
            "{dest} in {remaining}. Leave now.",
            "Go. {remaining} to {dest}.",
        ],
        'firm': [
            "{remaining} min. {dest}. GO.",
            "Leave now. {remaining} min.",
            "{dest}. {remaining}. GO.",
        ],
        'critical': [
            "{remaining} min{plural}. {dest}. LEAVE.",
            "GO. {remaining} min{plural} to {dest}.",
            "{remaining}. {dest}. MOVE.",
        ],
        'alarm': [
            "ALARM: {dest}. NOW.",
            "GO. {dest} NOW.",
            "ALARM: {dest}. MOVE.",
        ],
    },
    'calm': {
        'calm': [
            "Time to leave for {dest}. Take your time, you have {dur} minutes.",
            "Gentle reminder: {dest} in {dur} minutes. No rush.",
            "You have {dur} minutes before departing for {dest}.",
        ],
        'casual': [
            "Gentle reminder: {dest} in {remaining} minutes.",
            "Just a heads up: {dest} in {remaining} minutes.",
            "Reminder: {remaining} minutes until {dest}.",
        ],
        'pointed': [
            "{dest} in {remaining} minutes. Perhaps start heading out.",
            "You might want to begin heading to {dest} now. {remaining} minutes.",
            "Consider leaving for {dest} in the next few minutes.",
        ],
        'urgent': [
            "{remaining} minutes to {dest}.",
            "Reminder: {remaining} minutes until {dest}.",
            "You have {remaining} minutes to reach {dest}.",
        ],
        'pushing': [
            "{remaining} minutes. {dest}.",
            "{remaining} min until {dest}. Time to go.",
            "Consider departing for {dest} now.",
        ],
        'firm': [
            "{remaining} minutes. Please proceed to {dest}.",
            "{remaining} min: {dest}. Go now.",
            "Please leave now for {dest}. {remaining} minutes.",
        ],
        'critical': [
            "{remaining} minutes. {dest}.",
            "Urgent: {remaining} min to {dest}.",
            "Please move now. {remaining} min to {dest}.",
        ],
        'alarm': [
            "Reminder: {dest} is now.",
            "Now: {dest}.",
            "{dest} is happening now.",
        ],
    },
}


# Valid personality keys
VALID_PERSONALITIES = list(VOICE_PERSONALITIES.keys())

# Valid urgency tiers
VALID_TIERS = ['calm', 'casual', 'pointed', 'urgent', 'pushing', 'firm', 'critical', 'alarm']


def get_available_personalities() -> list[str]:
    """Return list of available personality names."""
    return VALID_PERSONALITIES.copy()


def get_tiers_for_personality(personality: str) -> list[str]:
    """Return list of tiers available for a personality."""
    if personality not in VOICE_PERSONALITIES:
        return VALID_TIERS
    return list(VOICE_PERSONALITIES[personality].keys())


def get_message_count(personality: str, tier: str) -> int:
    """Return number of message variations for a personality/tier combination."""
    if personality not in VOICE_PERSONALITIES:
        return 0
    if tier not in VOICE_PERSONALITIES[personality]:
        return 0
    return len(VOICE_PERSONALITIES[personality][tier])