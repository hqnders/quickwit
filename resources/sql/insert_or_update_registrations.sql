INSERT INTO Registrations (channel_id, user_id, job, status)
VALUES (?, ?, ?, ?)
ON CONFLICT(channel_id, user_id) DO UPDATE SET
    job = excluded.job,
    status = excluded.status;
