# Schema Migration V1 - Initial Schema
# Creates the base tables for Urgent Alarm application
--
-- Migration: 001_initial_schema
-- Description: Create base tables for reminders, anchors, history, and preferences
-- Applied: Automatic on first run
--

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrent performance
PRAGMA journal_mode = WAL;

-- Reminders table - core reminder data
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
    updated_at TEXT NOT NULL,
    -- Extended fields from spec Section 13.2
    origin_lat REAL,
    origin_lng REAL,
    origin_address TEXT,
    calendar_event_id TEXT,
    custom_sound_path TEXT
);

-- Anchors table - escalation chain timestamps
CREATE TABLE IF NOT EXISTS anchors (
    id TEXT PRIMARY KEY,
    reminder_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    urgency_tier TEXT NOT NULL,
    tts_clip_path TEXT,
    fired INTEGER DEFAULT 0,
    fire_count INTEGER DEFAULT 0,
    snoozed_to TEXT,
    tts_fallback INTEGER DEFAULT 0,
    FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE,
    UNIQUE(reminder_id, timestamp)
);

-- History table - reminder outcomes
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    reminder_id TEXT,
    destination TEXT NOT NULL,
    scheduled_arrival TEXT NOT NULL,
    outcome TEXT NOT NULL,
    feedback_type TEXT,
    missed_reason TEXT,
    actual_arrival TEXT,
    created_at TEXT NOT NULL
);

-- Destination adjustments table - feedback loop data
CREATE TABLE IF NOT EXISTS destination_adjustments (
    destination TEXT PRIMARY KEY,
    adjustment_minutes INTEGER DEFAULT 0,
    hit_count INTEGER DEFAULT 0,
    miss_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Custom sounds table - user-imported audio
CREATE TABLE IF NOT EXISTS custom_sounds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration_seconds REAL,
    category TEXT,
    created_at TEXT NOT NULL
);

-- Calendar sync table
CREATE TABLE IF NOT EXISTS calendar_sync (
    id TEXT PRIMARY KEY,
    calendar_type TEXT NOT NULL,
    calendar_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_title TEXT NOT NULL,
    event_location TEXT,
    event_start TEXT NOT NULL,
    event_end TEXT,
    sync_status TEXT NOT NULL DEFAULT 'pending',
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(calendar_type, event_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_anchors_reminder_id ON anchors(reminder_id);
CREATE INDEX IF NOT EXISTS idx_anchors_timestamp ON anchors(timestamp);
CREATE INDEX IF NOT EXISTS idx_anchors_fired ON anchors(fired);
CREATE INDEX IF NOT EXISTS idx_history_reminder_id ON history(reminder_id);
CREATE INDEX IF NOT EXISTS idx_history_outcome ON history(outcome);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
CREATE INDEX IF NOT EXISTS idx_reminders_arrival ON reminders(arrival_time);