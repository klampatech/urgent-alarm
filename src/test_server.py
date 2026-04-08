#!/usr/bin/env python3
"""
Urgent Alarm - Test Server for Harness Validation

A minimal HTTP server that exposes core app logic for scenario testing:
- Chain engine computation
- Reminder parsing (LLM mock + keyword fallback)
- Database operations (SQLite)
- Voice personality message generation
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os
import re
from datetime import datetime, timedelta
import uuid

DB_PATH = "/tmp/urgent-alarm.db"


def init_db():
    """Initialize SQLite database with schema from spec."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            destination TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            drive_duration INTEGER NOT NULL,
            reminder_type TEXT NOT NULL DEFAULT 'countdown_event',
            voice_personality TEXT NOT NULL DEFAULT 'assistant',
            sound_category TEXT,
            selected_sound TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchors (
            id TEXT PRIMARY KEY,
            reminder_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            urgency_tier TEXT NOT NULL,
            tts_clip_path TEXT,
            fired INTEGER DEFAULT 0,
            fire_count INTEGER DEFAULT 0,
            FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE,
            UNIQUE(reminder_id, timestamp)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            reminder_id TEXT,
            destination TEXT NOT NULL,
            scheduled_arrival TEXT NOT NULL,
            outcome TEXT NOT NULL,
            feedback_type TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destination_adjustments (
            destination TEXT PRIMARY KEY,
            adjustment_minutes INTEGER DEFAULT 0,
            hit_count INTEGER DEFAULT 0,
            miss_count INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


# Chain Engine - Core escalation logic
URGENCY_TIERS = {
    'calm': {'minutes_before': 30, 'order': 1},
    'casual': {'minutes_before': 25, 'order': 2},
    'pointed': {'minutes_before': 20, 'order': 3},
    'urgent': {'minutes_before': 15, 'order': 4},
    'pushing': {'minutes_before': 10, 'order': 5},
    'firm': {'minutes_before': 5, 'order': 6},
    'critical': {'minutes_before': 1, 'order': 7},
    'alarm': {'minutes_before': 0, 'order': 8},
}


def compute_escalation_chain(arrival_time: datetime, drive_duration: int) -> list[dict]:
    """
    Compute escalation chain anchors based on arrival time and drive duration.
    
    Rules from spec:
    - buffer >= 25 min: 8 anchors (full chain)
    - buffer 10-24 min: compressed (skip calm/casual)
    - buffer 5-9 min: shorter (start at pushing)
    - buffer <= 5 min: minimum (firm, critical, alarm only)
    """
    departure_time = arrival_time - timedelta(minutes=drive_duration)
    buffer_minutes = drive_duration
    
    anchors = []
    
    if buffer_minutes >= 25:
        # Full 8-anchor chain
        tiers = [
            ('calm', drive_duration),
            ('casual', drive_duration - 5),
            ('pointed', drive_duration - 10),
            ('urgent', drive_duration - 15),
            ('pushing', drive_duration - 20),
            ('firm', drive_duration - 25),
            ('critical', drive_duration - 29),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 20:
        # Skip calm, start at casual
        tiers = [
            ('casual', drive_duration - 5),
            ('pointed', drive_duration - 10),
            ('urgent', drive_duration - 15),
            ('pushing', drive_duration - 20),
            ('firm', drive_duration - 25),
            ('critical', drive_duration - 29),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 10:
        # Compressed: urgent, pushing, firm, critical, alarm
        tiers = [
            ('urgent', drive_duration - 5),
            ('pushing', drive_duration - 10),
            ('firm', drive_duration - 15),
            ('critical', drive_duration - (buffer_minutes - 1)),
            ('alarm', 0),
        ]
    elif buffer_minutes >= 5:
        # Short: firm, critical, alarm
        tiers = [
            ('firm', 5),
            ('critical', buffer_minutes - 1),
            ('alarm', 0),
        ]
    else:
        # Minimum: critical + alarm (or just alarm for very short)
        if buffer_minutes > 1:
            tiers = [
                ('firm', buffer_minutes - 1),
                ('alarm', 0),
            ]
        else:
            tiers = [
                ('alarm', 0),
            ]
    
    for tier_name, minutes_before in tiers:
        if minutes_before < 0:
            continue
        anchor_time = arrival_time - timedelta(minutes=minutes_before)
        anchors.append({
            'urgency_tier': tier_name,
            'timestamp': anchor_time.isoformat(),
            'minutes_before': minutes_before,
        })
    
    return anchors


def validate_chain(arrival_time: datetime, drive_duration: int) -> dict:
    """Validate that a chain can be created."""
    departure_time = arrival_time - timedelta(minutes=drive_duration)
    if departure_time <= datetime.now():
        return {'valid': False, 'error': 'departure_time_in_past'}
    if drive_duration <= 0:
        return {'valid': False, 'error': 'invalid_drive_duration'}
    return {'valid': True}


# Parser - Natural language parsing with keyword fallback
def parse_reminder_natural(input_text: str) -> dict:
    """
    Parse natural language input to extract reminder fields.
    Supports formats:
    - "30 minute drive to Parker Dr, check-in at 9am"
    - "dryer in 3 min"
    - "meeting tomorrow 2pm, 20 min drive"
    """
    result = {
        'destination': None,
        'arrival_time': None,
        'drive_duration': None,
        'reminder_type': 'countdown_event',
        'confidence': 0.0,
    }
    
    # Extract destination (everything after "to" or before "arrive" or before "check-in")
    dest_patterns = [
        r'to\s+([^,]+?)(?:,|arrive|check-in|$)',
        r'for\s+([^,]+?)(?:,|$)',
        r'([^,]+?)\s+at\s+\d',
    ]
    for pattern in dest_patterns:
        match = re.search(pattern, input_text, re.IGNORECASE)
        if match:
            result['destination'] = match.group(1).strip()
            break
    
    if not result['destination']:
        # Default: use the whole input as destination
        result['destination'] = input_text.strip()
    
    # Extract drive duration
    duration_patterns = [
        r'(\d+)\s*(?:minute|min)\s*drive',
        r'drive\s*(?:of\s*)?(\d+)\s*(?:minute|min)',
        r'(\d+)\s*(?:minute|min)\s*drive',
    ]
    for pattern in duration_patterns:
        match = re.search(pattern, input_text, re.IGNORECASE)
        if match:
            result['drive_duration'] = int(match.group(1))
            break
    
    if not result['drive_duration']:
        # Check for "in X minutes"
        match = re.search(r'in\s+(\d+)\s*(?:minute|min)', input_text, re.IGNORECASE)
        if match:
            result['drive_duration'] = 0  # Simple countdown, no drive
            result['reminder_type'] = 'simple_countdown'
    
    # Extract arrival time
    now = datetime.now()
    time_patterns = [
        # "at 9am", "at 9:30am"
        r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',
        # "in 3 min" (relative)
        r'in\s+(\d+)\s*(?:minute|min)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, input_text, re.IGNORECASE)
        if match:
            if 'in' in pattern and 'minute' in input_text.lower():
                # Relative time: "in X minutes"
                minutes = int(match.group(1))
                result['arrival_time'] = (now + timedelta(minutes=minutes)).isoformat()
                if result['drive_duration'] is None:
                    result['drive_duration'] = 0
                    result['reminder_type'] = 'simple_countdown'
            else:
                # Absolute time
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                ampm = match.group(3).lower() if match.group(3) else 'am'
                
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                
                arrival = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Handle "tomorrow"
                if 'tomorrow' in input_text.lower():
                    arrival += timedelta(days=1)
                
                # If time has passed today, assume it's for tomorrow
                if arrival <= now:
                    arrival += timedelta(days=1)
                
                result['arrival_time'] = arrival.isoformat()
            break
    
    # Calculate confidence
    fields_filled = sum([
        result['destination'] is not None,
        result['arrival_time'] is not None,
        result['drive_duration'] is not None,
    ])
    result['confidence'] = fields_filled / 3.0
    
    return result


# Voice personality message generation
VOICE_PERSONALITIES = {
    'coach': {
        'calm': "Alright, time to head out for {dest}. {dur} minute drive, you've got this!",
        'casual': "Hey, {dest} in {remaining} minutes. You should probably be in the car by now.",
        'pointed': "{dest}, {remaining} minutes. You leaving soon, right?",
        'urgent': "Let's GO! {remaining} minutes to {dest}! Time to move!",
        'pushing': "{remaining} minutes! {dest}! You need to leave NOW!",
        'firm': "OK, {remaining} minutes to {dest}. LEAVE NOW.",
        'critical': "{remaining} MINUTE{plural}! {dest}! MOVE!",
        'alarm': "BEEP BEEP BEEP — {dest} is RIGHT NOW!",
    },
    'assistant': {
        'calm': "Time to depart for {dest}. You have {dur} minutes for the drive.",
        'casual': "Reminder: {dest} in {remaining} minutes. I suggest heading out soon.",
        'pointed': "{dest} in {remaining} minutes. The drive takes {dur} minutes.",
        'urgent': "You have {remaining} minutes to reach {dest}. I'd recommend leaving now.",
        'pushing': "Urgent: {remaining} minutes until {dest}. Please depart immediately.",
        'firm': "Critical: {remaining} minutes. {dest}. Leave now.",
        'critical': "Final warning: {remaining} minute{plural} to {dest}. Move immediately.",
        'alarm': "ALARM: {dest} is now. Immediate action required.",
    },
    'best_friend': {
        'calm': "Omg okay so, time to head to {dest}! You've got {dur} minutes, let's do this!",
        'casual': "Heyyy so {dest} is in like {remaining} minutes? You should probably get going!",
        'pointed': "Okay so {dest} in {remaining} mins... you're leaving soon right??",
        'urgent': "Yo {dest} in {remaining} minutes! Like seriously, go go go!",
        'pushing': "{remaining} minutes to {dest}! I am literally begging you to leave!",
        'firm': "OKAY {remaining} minutes! {dest}! You gotta go RIGHT NOW!",
        'critical': "BRO {remaining} MINUTE{plural}! {dest}! GO GO GO!",
        'alarm': "ALARM ALARM {dest} IS NOW OMG!",
    },
    'no_nonsense': {
        'calm': "{dest}. {dur} min drive. Leave now.",
        'casual': "{dest}. {remaining} min. Go.",
        'pointed': "{dest}. {remaining} min. Move.",
        'urgent': "{remaining} min. {dest}. Leave.",
        'pushing': "{remaining} min. {dest}. Now.",
        'firm': "{remaining} min. {dest}. GO.",
        'critical': "{remaining} min{plural}. {dest}. LEAVE.",
        'alarm': "ALARM: {dest}. NOW.",
    },
    'calm': {
        'calm': "Time to leave for {dest}. Take your time, you have {dur} minutes.",
        'casual': "Gentle reminder: {dest} in {remaining} minutes.",
        'pointed': "{dest} in {remaining} minutes. Perhaps start heading out.",
        'urgent': "{remaining} minutes to {dest}.",
        'pushing': "{remaining} minutes. {dest}.",
        'firm': "{remaining} minutes. Please proceed to {dest}.",
        'critical': "{remaining} minutes. {dest}.",
        'alarm': "Reminder: {dest} is now.",
    },
}


def generate_voice_message(personality: str, urgency_tier: str, destination: str, 
                           drive_duration: int, minutes_remaining: int) -> str:
    """Generate a voice message for the given context."""
    templates = VOICE_PERSONALITIES.get(personality, VOICE_PERSONALITIES['assistant'])
    template = templates.get(urgency_tier, templates['calm'])
    
    plural = '' if minutes_remaining == 1 else 'S'
    
    return template.format(
        dest=destination,
        dur=drive_duration,
        remaining=minutes_remaining,
        plural=plural,
    )


# Stats calculations
def calculate_hit_rate(days: int = 7) -> float:
    """Calculate hit rate for trailing N days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute("""
        SELECT outcome, COUNT(*) FROM history 
        WHERE created_at >= ? AND outcome != 'pending'
        GROUP BY outcome
    """, (cutoff,))
    
    results = cursor.fetchall()
    conn.close()
    
    total = sum(r[1] for r in results)
    hits = sum(r[1] for r in results if r[0] == 'hit')
    
    return (hits / total * 100) if total > 0 else 0.0


class UrgentAlarmHandler(BaseHTTPRequestHandler):
    """HTTP handler for Urgent Alarm test endpoints."""
    
    def log_message(self, format, *args):
        import sys
        sys.stderr.write(f"[UrgentAlarm] {format % args}\n")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        if self.path == "/health":
            self.send_json({"status": "healthy", "service": "urgent-alarm"})
        
        elif self.path.startswith("/chain/"):
            # GET /chain?arrival=2026-04-08T09:00:00&duration=30
            params = {}
            if '?' in self.path:
                query = self.path.split('?')[1]
                for pair in query.split('&'):
                    k, v = pair.split('=')
                    params[k] = v.replace('%3A', ':')
            
            arrival_str = params.get('arrival')
            duration_str = params.get('duration')
            
            if not arrival_str or not duration_str:
                self.send_json({"error": "Missing arrival or duration param"}, 400)
                return
            
            try:
                arrival = datetime.fromisoformat(arrival_str.replace('%3A', ':'))
                duration = int(duration_str)
                
                validation = validate_chain(arrival, duration)
                if not validation['valid']:
                    self.send_json({"error": validation['error']}, 400)
                    return
                
                anchors = compute_escalation_chain(arrival, duration)
                self.send_json({"anchors": anchors, "count": len(anchors)})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        
        elif self.path.startswith("/reminders"):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, destination, arrival_time, drive_duration, status FROM reminders")
            rows = cursor.fetchall()
            conn.close()
            self.send_json({"reminders": [{"id": r[0], "destination": r[1], "arrival_time": r[2], "drive_duration": r[3], "status": r[4]} for r in rows]})
        
        elif self.path.startswith("/stats/hit-rate"):
            rate = calculate_hit_rate()
            self.send_json({"hit_rate": rate})
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
        except Exception as e:
            self.send_json({"error": f"Failed to read body: {e}"}, 400)
            return
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        
        # POST /reminders - Create a reminder with chain
        if self.path == "/reminders":
            destination = data.get("destination", "")
            arrival_time_str = data.get("arrival_time")
            drive_duration = data.get("drive_duration", 0)
            voice_personality = data.get("voice_personality", "assistant")
            reminder_type = data.get("reminder_type", "countdown_event")
            
            if not arrival_time_str:
                self.send_json({"error": "Missing arrival_time"}, 400)
                return
            
            try:
                arrival_time = datetime.fromisoformat(arrival_time_str)
            except:
                self.send_json({"error": "Invalid arrival_time format"}, 400)
                return
            
            # Validate
            validation = validate_chain(arrival_time, drive_duration)
            if not validation['valid']:
                self.send_json({"error": validation['error']}, 400)
                return
            
            # Create reminder
            reminder_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (id, destination, arrival_time, drive_duration, 
                reminder_type, voice_personality, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (reminder_id, destination, arrival_time_str, drive_duration, 
                  reminder_type, voice_personality, now, now))
            
            # Create anchors
            anchors = compute_escalation_chain(arrival_time, drive_duration)
            for anchor in anchors:
                anchor_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO anchors (id, reminder_id, timestamp, urgency_tier, fired)
                    VALUES (?, ?, ?, ?, 0)
                """, (anchor_id, reminder_id, anchor['timestamp'], anchor['urgency_tier']))
            
            conn.commit()
            conn.close()
            
            self.send_json({
                "id": reminder_id,
                "destination": destination,
                "arrival_time": arrival_time_str,
                "drive_duration": drive_duration,
                "anchors_created": len(anchors),
                "status": "pending"
            }, 201)
        
        # POST /parse - Parse natural language input
        elif self.path == "/parse":
            input_text = data.get("text", "")
            if not input_text:
                self.send_json({"error": "Missing text"}, 400)
                return
            
            parsed = parse_reminder_natural(input_text)
            self.send_json(parsed)
        
        # POST /voice/message - Generate voice message
        elif self.path == "/voice/message":
            personality = data.get("personality", "assistant")
            urgency_tier = data.get("urgency_tier", "calm")
            destination = data.get("destination", "")
            drive_duration = data.get("drive_duration", 0)
            minutes_remaining = data.get("minutes_remaining", 0)
            
            message = generate_voice_message(personality, urgency_tier, destination, 
                                            drive_duration, minutes_remaining)
            self.send_json({"message": message, "personality": personality, "tier": urgency_tier})
        
        # POST /history - Record outcome
        elif self.path == "/history":
            history_id = str(uuid.uuid4())
            reminder_id = data.get("reminder_id")
            destination = data.get("destination", "")
            scheduled_arrival = data.get("scheduled_arrival")
            outcome = data.get("outcome", "hit")
            feedback_type = data.get("feedback_type")
            
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (id, reminder_id, destination, scheduled_arrival, 
                outcome, feedback_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (history_id, reminder_id, destination, scheduled_arrival, 
                  outcome, feedback_type, now))
            
            # Update destination adjustments if missed
            if outcome == 'miss' and feedback_type == 'left_too_late':
                cursor.execute("""
                    INSERT INTO destination_adjustments (destination, adjustment_minutes, miss_count)
                    VALUES (?, 2, 1)
                    ON CONFLICT(destination) DO UPDATE SET
                        adjustment_minutes = adjustment_minutes + 2,
                        miss_count = miss_count + 1
                """, (destination,))
            elif outcome == 'hit':
                cursor.execute("""
                    INSERT INTO destination_adjustments (destination, hit_count)
                    VALUES (?, 1)
                    ON CONFLICT(destination) DO UPDATE SET
                        hit_count = hit_count + 1
                """, (destination,))
            
            conn.commit()
            conn.close()
            
            self.send_json({"id": history_id, "outcome": outcome}, 201)
        
        # POST /anchors/fire - Mark anchor as fired
        elif self.path == "/anchors/fire":
            anchor_id = data.get("anchor_id")
            if not anchor_id:
                self.send_json({"error": "Missing anchor_id"}, 400)
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE anchors SET fired = 1, fire_count = fire_count + 1 WHERE id = ?", (anchor_id,))
            conn.commit()
            conn.close()
            
            self.send_json({"anchor_id": anchor_id, "fired": True})
        
        else:
            self.send_json({"error": "Not found"}, 404)


def run_server(host="localhost", port=8090):
    """Run the Urgent Alarm test server."""
    init_db()
    server = HTTPServer((host, port), UrgentAlarmHandler)
    print(f"Urgent Alarm test server running on http://{host}:{port}")
    print("Endpoints:")
    print("  GET  /health                  -> 200 OK")
    print("  GET  /chain?arrival=X&duration=Y -> Chain anchors")
    print("  GET  /reminders               -> List reminders")
    print("  GET  /stats/hit-rate          -> Hit rate")
    print("  POST /reminders               -> Create reminder + anchors")
    print("  POST /parse                   -> Parse natural language")
    print("  POST /voice/message           -> Generate voice message")
    print("  POST /history                 -> Record outcome")
    print("  POST /anchors/fire            -> Mark anchor fired")
    print("\nPress Ctrl+C to stop...")
    server.serve_forever()


if __name__ == "__main__":
    run_server()