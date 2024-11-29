INSERT INTO UserTimezones (user_id, timezone)
VALUES (?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    timezone = excluded.timezone;
