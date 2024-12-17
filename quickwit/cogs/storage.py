"""Cog to manage persistent storage"""
import sqlite3
import os
from enum import StrEnum
from logging import getLogger
from datetime import datetime, timezone
from discord.ext import commands
from quickwit.models import Event, Registration, EventType

DATA_FOLDER_NAME = 'data'
DATABASE_NAME = 'events.db'
SCRIPTS_PATH = 'resources/sql'


class Cache:
    """Cog for caching event storage"""

    def __init__(self):
        self._events_cache = dict[int, Event]()

    def cache_event(self, stored_event: Event):
        """Stores an event, also used to overwrite an existing event"""
        self._events_cache[stored_event.channel_id] = stored_event

    def uncache_event(self, channel_id: int):
        """Delete an existing event from cache"""
        self._events_cache.pop(channel_id, None)

    def get_event(self, channel_id: int) -> Event | None:
        """Fetch an event based on channel ID from cache"""
        return self._events_cache.get(channel_id, None)

    def register(self, channel_id: int, registration: Registration):
        """Ensures new registrations are added to cache"""
        if channel_id not in self._events_cache.keys():
            return

        for i, existing_registration in enumerate(self._events_cache[channel_id].registrations):
            if existing_registration.user_id == registration.user_id:
                self._events_cache[channel_id].registrations[i] = registration
                return
        self._events_cache[channel_id].registrations.append(registration)

    def unregister(self, channel_id: int, user_id: int):
        """Ensures registrations are removed from cache"""
        if channel_id not in self._events_cache.keys():
            return
        for i, existing_registration in enumerate(self._events_cache[channel_id].registrations):
            if existing_registration.user_id == user_id:
                self._events_cache[channel_id].registrations.pop(i)
                return


class NecessaryScripts(StrEnum):
    """Map all necessary scripts to filenames"""
    CREATION = 'create'
    SET_TIMEZONE = 'insert_or_update_user_timezones'
    REGISTER_USER = 'insert_or_update_registrations'
    STORE_EVENT = 'insert_or_update_events'


class Storage(commands.Cog):
    """Cog for persistent event storage"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache = Cache()
        self.conn = sqlite3.connect(os.path.join(
            DATA_FOLDER_NAME, DATABASE_NAME))

        # Populate the scripts container with all necessary scripts
        self.scripts = dict[NecessaryScripts, str]()
        for file in os.listdir(SCRIPTS_PATH):
            filename = file.split('.')[0]
            if filename in NecessaryScripts:
                with open(f'{SCRIPTS_PATH}/{file}', 'r', encoding='utf-8') as script:
                    self.scripts[filename] = script.read()

        # Turn on foreign key constraints and run the creation script
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.executescript(
            self.scripts[NecessaryScripts.CREATION])
        self.conn.commit()

        self._modernize()

    def get_timezone(self, user_id: int) -> str:
        """Fetch the timezone of a user, returning UTC on default"""
        result = self.conn.execute(
            'SELECT timezone FROM UserTimezones WHERE user_id=?', [user_id]).fetchone()
        if result is None:
            return 'UTC'
        return result[0]

    def store_event(self, event: Event):
        """Store an event in persistent storage"""
        # Convert times to timestamps
        start = round(event.utc_start.timestamp())
        end = round(event.utc_end.timestamp())
        reminder = round(event.reminder.timestamp())

        # Store event in database
        self.conn.execute(self.scripts[NecessaryScripts.STORE_EVENT], [
            event.channel_id, event.event_type, event.name,
            event.description, event.scheduled_event_id,
            event.organiser_id, start, end, event.guild_id, reminder
        ])
        self.conn.commit()

        # Update cache
        if self.cache is not None:
            self.cache.cache_event(event)

    def delete_event(self, channel_id: int):
        """Deletes the event from persistent storage"""
        # Delete from database
        self.conn.execute(
            'DELETE FROM Events WHERE channel_id=?', [channel_id])
        self.conn.commit()

        # Delete from cache
        if self.cache is not None:
            self.cache.uncache_event(channel_id)

    def get_event(self, channel_id: int) -> Event | None:
        """Retrieves an event from storage, getting it from cache first if possible"""
        # Attempt to retrieve the event from cache
        cached_event = None
        if self.cache is not None:
            cached_event = self.cache.get_event(channel_id)
            if cached_event is not None:
                return cached_event

        # Attempt to retrieve the event from database
        result = self.conn.execute(
            'SELECT event_type, name, description, scheduled_event_id, organiser_id, utc_start, \
                utc_end, guild_id, reminder FROM Events WHERE channel_id=?',
            [channel_id]).fetchone()
        if result is None:
            getLogger(__name__).error(
                'Could not get event %i from database', channel_id)
            return None

        # Map results to proper variables and typing
        event_type = result[0]
        name = result[1]
        description = result[2]
        scheduled_event_id = result[3]
        organiser_id = result[4]
        utc_start = datetime.fromtimestamp(result[5], timezone.utc)
        utc_end = datetime.fromtimestamp(result[6], timezone.utc)
        guild_id = result[7]
        reminder = datetime.fromtimestamp(result[8], timezone.utc)
        registrations = []

        # Fetch registrations
        result = self.conn.execute(
            'SELECT user_id, status, job FROM Registrations WHERE channel_id=?',
            [channel_id]).fetchall()
        for row in result:
            registrations.append(
                Registration(row[0], row[1], row[2]))

        # Create the event
        stored_event = Event(channel_id, event_type, name, description, organiser_id,
                             utc_start, utc_end, guild_id, reminder, registrations, scheduled_event_id)

        # Cache event for future reference
        if self.cache is not None and cached_event is None:
            self.cache.cache_event(stored_event)

        return stored_event

    def get_past_events(self) -> list[tuple[int, int, int]]:
        """Retrieve all channel IDs from events that have ended

        Returns:
            list[tuple[int, int, int]]: A list of tuples consisting of channel_id,
                scheduled_event_id and guild_id of past events
        """
        end = round(datetime.now().timestamp())
        result = self.conn.execute(
            'SELECT channel_id, scheduled_event_id, guild_id FROM Events WHERE utc_end<=?', [end])
        return [(row[0], row[1], row[2]) for row in result.fetchall()]

    def get_active_reminders(self) -> list[int]:
        """Retrieve all channel IDs for events that can have their reminder be sent out"""
        now = round(datetime.now().timestamp())
        results = self.conn.execute(
            'SELECT channel_id FROM Events WHERE utc_start>? AND reminder<?', [now, now]).fetchall()
        return [result[0] for result in results]

    def get_event_from_scheduled_event_id(self, scheduled_event_id: int) -> Event | None:
        """Return whether the scheduled event is associated with a stored event"""
        result = self.conn.execute('SELECT channel_id FROM Events WHERE scheduled_event_id=?',
                                   [scheduled_event_id]).fetchone()
        if result is None:
            return None
        return self.get_event(result[0])

    def update_timezone(self, user_id: int, user_timezone: str):
        """Set a users timezone"""
        self.conn.execute(
            self.scripts[NecessaryScripts.SET_TIMEZONE], [user_id, user_timezone])
        self.conn.commit()

    def register(self, channel_id: int, registration: Registration):
        """Store a new registration"""
        self.conn.execute(self.scripts[NecessaryScripts.REGISTER_USER],
                          [channel_id, registration.user_id, registration.job,
                           str(registration.status)])
        self.conn.commit()
        self.cache.register(channel_id, registration)

    def unregister(self, channel_id: int, user_id: int):
        """Remove a registration from storage"""
        self.conn.execute(
            'DELETE FROM Registrations WHERE channel_id=? AND user_id=?', [channel_id, user_id])
        self.conn.commit()
        self.cache.unregister(channel_id, user_id)

    def get_registered_event_ids(self, user_id: int) -> list[int]:
        """Fetch the ID of all events where the user is registered to"""
        result = self.conn.execute('SELECT channel_id FROM Registrations WHERE user_id=?',
                                   [user_id])
        return [row[0] for row in result.fetchall()]

    def _modernize(self):
        """Old versions of this bot used differing event_type names, ensure they're modernized"""
        self.conn.execute('UPDATE Events SET event_type=? WHERE event_type=?',
                          [EventType.FF14, 'FF14Event'])
        self.conn.execute('UPDATE Events SET event_type=? WHERE event_type=?',
                          [EventType.FASHION, 'FashionShow'])
        self.conn.execute('UPDATE Events SET event_type=? WHERE event_type=?',
                          [EventType.CAMPFIRE, 'CampfireEvent'])
        self.conn.commit()
