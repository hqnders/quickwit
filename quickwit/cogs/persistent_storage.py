"""Cog to manage persistent storage"""
import sqlite3
import os
from logging import getLogger
from datetime import datetime, timedelta, timezone
from inspect import getmembers, isclass
from discord.ext import commands
from quickwit import events
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

    def register_user(self, channel_id: int, user_id: int, registration: events.Event.Registration):
        self._ensure_cached_event(channel_id)
        super().register_user(channel_id, user_id, registration)

        # Fetch the user's job if we're registering for a jobevent
        job = None
        if isinstance(registration, events.JobEvent.Registration):
            job = registration.job.value[0]

        self._connection.execute(self._scripts[self._REGISTER_USER_SCRIPT_NAME],
                                 [channel_id, user_id, job, registration.status.value[0]])
        self._connection.commit()

    def unregister_user(self, channel_id: int, user_id: int):
        self._ensure_cached_event(channel_id)
        super().unregister_user(channel_id, user_id)
        self._connection.execute(
            'DELETE FROM Registrations WHERE channel_id=? AND user_id=?', [channel_id, user_id])
        self._connection.commit()

    def store_event(self, stored_event: storage.StoredEvent):
        super().store_event(stored_event)
        event = stored_event.event
        event_type = type(event).__name__
        start = round(event.start.timestamp())
        end = round(
            (event.start + timedelta(minutes=event.duration)).timestamp())
        reminder = round(stored_event.reminder.timestamp())
        self._connection.execute(self._scripts[self._STORE_EVENT_SCRIPT_NAME], [
            stored_event.channel_id, event_type, event.name, event.description,
            stored_event.scheduled_event_id, event.organiser_id, start,
            end, stored_event.guild_id, reminder
        ])
        self._connection.commit()

    def delete_event(self, channel_id: int):
        super().delete_event(channel_id)
        self._connection.execute(
            'DELETE FROM Events WHERE channel_id=?', [channel_id])
        self._connection.commit()

    def get_event(self, channel_id: int) -> storage.StoredEvent | None:
        """The channel corresponding to channel_id must be within the bot's channel cache to succeed"""
        # Attempt to get it from cache
        event = super().get_event(channel_id)
        if event is not None:
            return event

        # Attempt to get it from persistent storage
        result = self._connection.execute(
            'SELECT event_type, name, description, scheduled_event_id, organiser_id, utc_start, utc_end, guild_id, reminder FROM Events WHERE channel_id=?', [channel_id]).fetchone()
        if result is None:
            getLogger(__name__).error(
                'Could not get event %i from database', channel_id)
            return None
        event_type = result[0]
        name = result[1]
        description = result[2]
        scheduled_event_id = result[3]
        organiser_id = result[4]
        start = datetime.fromtimestamp(result[5], timezone.utc)
        duration = (datetime.fromtimestamp(
            result[6], timezone.utc) - start).total_seconds() / 60
        guild_id = result[7]
        reminder = datetime.fromtimestamp(result[8], timezone.utc)

        # Create the event
        event_class = events.Event
        for event_class_name, _event_class in getmembers(events, lambda x: isclass(x) and issubclass(x, events.Event)):
            if event_class_name == event_type:
                event_class = _event_class
                break
        event = event_class(name=name, description=description,
                            start=start, duration=duration, organiser_id=organiser_id)

        # Fetch registrations
        result = self._connection.execute(
            'SELECT user_id, status, job FROM Registrations WHERE channel_id=?', [channel_id]).fetchall()
        for row in result:
            if issubclass(event_class, events.JobEvent):
                event.registrations[row[0]] = event_class.Registration(
                    status=row[1], job=row[2])
            else:
                getLogger(__name__).warning(
                    'Assuming default registrationg type after unable to find registration type for %s', event_class.__name__)
                event.registrations[row[0]] = event_class.Registration(
                    status=row[1])

        stored_event = storage.StoredEvent(
            event, channel_id, scheduled_event_id, guild_id, reminder)
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
