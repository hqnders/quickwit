"""Cog to manage persistent storage"""
import sqlite3
import os
from logging import getLogger
from datetime import datetime, timezone
from discord.ext import commands
import quickwit.cogs.storage as storage


class PersistentStorage(storage.Storage, name='Storage'):
    """Cog for persistent event storage"""
    _DATA_FOLDER_NAME = 'data'
    _DATABASE_NAME = 'events.db'
    _SCRIPTS_PATH = 'resources/sql'
    _CREATION_SCRIPT_NAME = 'create'
    _SET_TIMEZONE_SCRIPT_NAME = 'insert_or_update_user_timezones'
    _REGISTER_USER_SCRIPT_NAME = 'insert_or_update_registrations'
    _STORE_EVENT_SCRIPT_NAME = 'insert_or_update_events'

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self._connection = sqlite3.connect(os.path.join(
            self._DATA_FOLDER_NAME, self._DATABASE_NAME))
        self._scripts = {}  # type: dict[str, str]
        for file in os.listdir(self._SCRIPTS_PATH):
            self._scripts[file.split('.')[0]] = ''.join(open(
                f'{self._SCRIPTS_PATH}/{file}', 'r', encoding='utf-8').readlines())
        self._connection.execute('PRAGMA foreign_keys = ON')
        self._connection.executescript(
            self._scripts[self._CREATION_SCRIPT_NAME])
        self._connection.commit()

    def set_timezone(self, user_id: int, user_timezone: str):
        super().set_timezone(user_id, user_timezone)
        self._connection.execute(
            self._scripts[self._SET_TIMEZONE_SCRIPT_NAME], [user_id, user_timezone])
        self._connection.commit()

    def get_timezone(self, user_id: int) -> str:
        user_timezone = super().get_timezone(user_id)
        if user_timezone != 'UTC':
            return user_timezone
        result = self._connection.execute(
            'SELECT timezone FROM UserTimezones WHERE user_id=?', [user_id]).fetchone()
        if result is not None:
            user_timezone = result[0]
        super().set_timezone(user_id, user_timezone)
        return user_timezone

    def register_user(self, channel_id: int, registration: storage.Event.Registration):
        self._ensure_cached_event(channel_id)
        super().register_user(channel_id, registration)

        self._connection.execute(self._scripts[self._REGISTER_USER_SCRIPT_NAME],
                                 [channel_id, registration.user_id, registration.job, str(registration.status)])
        self._connection.commit()

    def unregister_user(self, channel_id: int, user_id: int):
        self._ensure_cached_event(channel_id)
        super().unregister_user(channel_id, user_id)
        self._connection.execute(
            'DELETE FROM Registrations WHERE channel_id=? AND user_id=?', [channel_id, user_id])
        self._connection.commit()

    def store_event(self, stored_event: storage.Event):
        super().store_event(stored_event)
        start = round(stored_event.utc_start.timestamp())
        end = round(stored_event.utc_end.timestamp())
        reminder = round(stored_event.reminder.timestamp())
        self._connection.execute(self._scripts[self._STORE_EVENT_SCRIPT_NAME], [
            stored_event.channel_id, stored_event.event_type, stored_event.name,
            stored_event.description, stored_event.scheduled_event_id,
            stored_event.organiser_id, start, end, stored_event.guild_id, reminder
        ])
        self._connection.commit()

    def delete_event(self, channel_id: int):
        super().delete_event(channel_id)
        self._connection.execute(
            'DELETE FROM Events WHERE channel_id=?', [channel_id])
        self._connection.commit()

    def get_event(self, channel_id: int) -> storage.Event | None:
        """The channel corresponding to channel_id must be within 
            the bot's channel cache to succeed"""
        # Attempt to get it from cache
        event = super().get_event(channel_id)
        if event is not None:
            return event

        # Attempt to get it from persistent storage
        result = self._connection.execute(
            'SELECT event_type, name, description, scheduled_event_id, organiser_id, utc_start, \
                utc_end, guild_id, reminder FROM Events WHERE channel_id=?',
            [channel_id]).fetchone()
        if result is None:
            getLogger(__name__).error(
                'Could not get event %i from database', channel_id)
            return None
        event_type = result[0]
        name = result[1]
        description = result[2]
        scheduled_event_id = result[3]
        organiser_id = result[4]
        utc_start = datetime.fromtimestamp(result[5], timezone.utc)
        utc_end = datetime.fromtimestamp(result[6], timezone.utc)
        guild_id = result[7]
        reminder = datetime.fromtimestamp(result[8], timezone.utc)

        # Create the event
        stored_event = storage.Event(channel_id, event_type, name, description,
                                     scheduled_event_id, organiser_id, utc_start,
                                     utc_end, guild_id, reminder)

        # Fetch registrations
        result = self._connection.execute(
            'SELECT user_id, status, job FROM Registrations WHERE channel_id=?',
            [channel_id]).fetchall()
        for row in result:
            stored_event.registrations.append(
                stored_event.Registration(row[0], row[1], row[2]))

        # Cache the event
        super().store_event(stored_event)
        return stored_event

    def get_past_events(self) -> list[int]:
        end = round(datetime.now().timestamp())
        result = self._connection.execute(
            'SELECT channel_id, scheduled_event_id, guild_id FROM Events WHERE utc_end<=?', [end])
        return [(row[0], row[1], row[2]) for row in result.fetchall()]

    def get_active_reminders(self) -> list[int]:
        now = round(datetime.now().timestamp())
        results = self._connection.execute(
            'SELECT channel_id FROM Events WHERE utc_start>? AND reminder<?', [now, now]).fetchall()
        return [result[0] for result in results]

    def _ensure_cached_event(self, channel_id: int):
        if super().get_event(channel_id) is None:
            event = self.get_event(channel_id)
            if event is None:
                raise ValueError('Event does not exist')
            super().store_event(event)
