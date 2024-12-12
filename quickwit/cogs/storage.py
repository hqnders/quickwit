"""Cog to manage persistent storage"""
import sqlite3
import os
from enum import StrEnum
from logging import getLogger
from datetime import datetime, timezone
from discord.ext import commands
from quickwit.models import Event, Registration
from .cache import Cache
from .events import REGISTER_EVENT_NAME, UNREGISTER_EVENT_NAME, \
    USER_TIMEZONE_REGISTRATION_EVENT_NAME

DATA_FOLDER_NAME = 'data'
DATABASE_NAME = 'events.db'
SCRIPTS_PATH = 'resources/sql'


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
        self.cache = self.bot.get_cog(Cache.__name__)
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

    async def cog_load(self):
        # Ensure there is always a cache available
        if self.cache is None:
            self.cache = Cache(self.bot)
            await self.bot.add_cog(self.cache)

    def get_timezone(self, user_id: int) -> str:
        """Fetch the timezone of a user, returning UTC on default"""
        result = self.conn.execute(
            'SELECT timezone FROM UserTimezones WHERE user_id=?', [user_id]).fetchone()
        if result is not None:
            result = result[0]
        return result

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

        # Create the event
        stored_event = Event(channel_id, event_type, name, description,
                             scheduled_event_id, organiser_id, utc_start,
                             utc_end, guild_id, reminder)

        # Fetch registrations
        result = self.conn.execute(
            'SELECT user_id, status, job FROM Registrations WHERE channel_id=?',
            [channel_id]).fetchall()
        for row in result:
            stored_event.registrations.append(
                Registration(row[0], row[1], row[2]))

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

    def is_associated_with_event(self, scheduled_event_id: int) -> bool:
        """Return whether the scheduled event is associated with a stored event"""
        result = self.conn.execute('SELECT channel_id FROM Events WHERE scheduled_event_id=?',
                                   [scheduled_event_id])
        return result.arraysize > 0

    @commands.Cog.listener(name=USER_TIMEZONE_REGISTRATION_EVENT_NAME)
    async def on_timezone_registration(self, user_id: int, user_timezone: str):
        """Set a users timezone"""
        self.conn.execute(
            self.scripts[NecessaryScripts.SET_TIMEZONE], [user_id, user_timezone])
        self.conn.commit()

    @commands.Cog.listener(name=REGISTER_EVENT_NAME)
    async def on_register(self, channel_id: int, registration: Registration):
        """Store a new registration"""
        self.conn.execute(self.scripts[NecessaryScripts.REGISTER_USER],
                          [channel_id, registration.user_id, registration.job,
                           str(registration.status)])
        self.conn.commit()

    @commands.Cog.listener(name=UNREGISTER_EVENT_NAME)
    async def on_unregister(self, channel_id: int, user_id: int):
        """Remove a registration from storage"""
        self.conn.execute(
            'DELETE FROM Registrations WHERE channel_id=? AND user_id=?', [channel_id, user_id])
        self.conn.commit()
