INSERT INTO Events (channel_id, event_type, name, description, scheduled_event_id, organiser_id, utc_start, utc_end, guild_id, reminder)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(channel_id) DO UPDATE SET
    name = excluded.name,
    description = excluded.description,
    utc_start = excluded.utc_start,
    utc_end = excluded.utc_end,
    scheduled_event_id = excluded.scheduled_event_id,
    reminder = excluded.reminder;
