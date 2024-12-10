"""Cog to manage persistent storage"""
from dataclasses import dataclass
from logging import getLogger
from datetime import datetime
from discord import File
from discord.ext import commands


@dataclass
class Event:
    """Represents an Event saved in storage"""
    @dataclass
    class Registration:
        """Represents a registration saved in storage"""
        user_id: int
        status: str
        job: str = None

    channel_id: int
    event_type: str
    name: str
    description: str
    scheduled_event_id: int
    organiser_id: int
    utc_start: datetime
    utc_end: datetime
    guild_id: int
    reminder: datetime
    registrations = list[Registration]()


class Storage(commands.Cog):
    """Cog for persistent event storage"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._events_cache = dict[int, Event]()
        self._user_timezone_cache = dict[int, str]()
        self._registration_data = dict[int, dict[tuple[str, str]]]

    def set_timezone(self, user_id: int, user_timezone: str):
        """Sets the user timezone"""
        self._user_timezone_cache[user_id] = user_timezone

    def get_timezone(self, user_id: int) -> str:
        """Gets a user timezone

        Returns:
            str: The timezone, UTC by default
        """
        return self._user_timezone_cache.get(user_id, 'UTC')

    def register_user(self, channel_id: int, registration: Event.Registration):
        """Registers a user for an event

        Args:
            channel_id (int): The channel ID of the event
        """
        event = self._events_cache.get(channel_id, None)
        if event is None:
            getLogger(__name__).warning(
                'User %i is trying to register for an uncached event in channel %i',
                registration.user_id, channel_id)
            return
        event.registrations[registration.user_id] = registration

    def unregister_user(self, channel_id: int, user_id: int):
        """Unregister a user for an event

        Args:
            channel_id (int): The channel ID of the event
        """
        event = self._events_cache.get(channel_id, None)
        if event is None:
            getLogger(__name__).warning(
                'User %i is trying to unregister for an uncached event in channel %i',
                user_id, channel_id)
            return
        event.registrations.pop(user_id, None)

    def store_event(self, stored_event: Event):
        """Stores an event, also used to overwrite an existing event"""
        self._events_cache[stored_event.channel_id] = stored_event

    def delete_event(self, channel_id: int):
        """Delete an existing event

        Args:
            event_id (int): The ID of the channel associated with the event
        """
        self._events_cache.pop(channel_id, None)

    def get_event(self, channel_id: int) -> Event | None:
        """Fetch an event based on channel ID

        Returns:
            Event: The event and all it's storage information or None
        """
        return self._events_cache.get(channel_id, None)

    def get_default_image(self) -> File:
        """Fetch the default image in file format for events

        Returns:
            File: The default image in File form
        """
        return File('resources/img/default.png')

    def get_past_events(self) -> list[Event]:
        """Fetch the channel ID's of ended events"""
        now = datetime.now()
        return [event.channel_id for event in self._events_cache.values() if event.utc_end < now]

    def get_active_reminders(self) -> list[int]:
        """Get all channels for which a reminder can be sent

        Returns:
            list[int]: The list of channel ID's for which event you may send a reminder
        """
        now = datetime.now()
        return [event.channel_id for event in self._events_cache.values()
                if event.utc_start < now and event.reminder > now]

    @commands.Cog.listener()
    async def on_job_selected(self, channel_id: int, user_id: int, job: str):
        registration_data = self._registration_data.get(channel_id, {}).get(user_id, (None, None))

    @commands.Cog.listener()
    async def on_user_selected_status(self, channel_id: int, user_id: int, status: str):
        pass
