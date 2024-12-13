-- Create the UserTimezones to store user-specific timezone information
CREATE TABLE IF NOT EXISTS UserTimezones (
    user_id INTEGER PRIMARY KEY, -- Discord User ID
    timezone TEXT DEFAULT 'UTC' -- User-specific timezone
);

CREATE TABLE IF NOT EXISTS Events (
    channel_id INTEGER PRIMARY KEY, -- Discord Channel ID
    event_type TEXT NOT NULL, -- Event type
    name TEXT NOT NULL, -- Name of the event
    description TEXT NOT NULL, -- Description of the event
    scheduled_event_id INTEGER, -- Discord Scheduled Event ID
    organiser_id INTEGER NOT NULL, -- Discord User ID of the event organiser
    utc_start INTEGER NOT NULL, -- Seconds since epoch until event start in UTC
    utc_end INTEGER NOT NULL, -- Seconds since epoch until event end in UTC
    guild_id INTEGER NOT NULL, -- Discord Guild ID
    reminder INTEGER NOT NULL -- Seconds sinds epoch when the reminder needs to be sent
);

-- Create the Registrations table to store event registrations
CREATE TABLE IF NOT EXISTS Registrations (
    channel_id INTEGER NOT NULL, -- Discord Channel ID for event
    user_id INTEGER NOT NULL, -- Discord User ID
    job TEXT, -- Registered job
    status TEXT, -- User's attendance status
    UNIQUE (channel_id, user_id), -- Ensure a user can only register once per event
    FOREIGN KEY (channel_id) REFERENCES Events(channel_id) ON DELETE CASCADE
);
