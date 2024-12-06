"""Cog to manage persistent storage"""
from dataclasses import dataclass
from logging import getLogger
from datetime import timedelta, datetime
from discord import File
from discord.ext import commands
from quickwit.events import Event


@dataclass
class StoredEvent:
    """Represents an Event saved in storage"""
    event: Event
    channel_id: int
    scheduled_event_id: int
    guild_id: int
    reminder: datetime


class Storage(commands.Cog):
    """Cog for persistent event storage"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._events_cache = {}  # type: dict[int, StoredEvent]
        self._user_timezone_cache = {}  # type: dict[int, str]

    def set_timezone(self, user_id: int, user_timezone: str):
        """Sets the user timezone

        Args:
            user_id (int): The ID of the user
            user_timezone (str): The timezone
        """
        self._user_timezone_cache[user_id] = user_timezone

    def get_timezone(self, user_id: int) -> str:
        """Gets a user timezone, returning UTC by default

        Args:
            user_id (int): The ID of the user

        Returns:
            str: The timezone, UTC by default
        """
        return self._user_timezone_cache.get(user_id, 'UTC')

    def register_user(self, channel_id: int, user_id: int, registration: Event.Registration):
        """Registers a user for an event

        Args:
            channel_id (int): The channel ID of the event
            user_id (int): The user registering for the event
            registration (Event.Registration): The registration information
        """
        if self._events_cache.get(channel_id, None) is None:
            getLogger(__name__).warning(
                'User %i is trying to register for an uncached event in channel %i', user_id, channel_id)
            return
        self._events_cache[channel_id].event.registrations[user_id] = registration

    def unregister_user(self, channel_id: int, user_id: int):
        """Unregister a user for an event

        Args:
            channel_id (int): The channel ID of the event
            user_id (int): The ID of the user
        """
        if self._events_cache.get(channel_id, None) is None:
            getLogger(__name__).warning(
                'User %i is trying to unregister for an uncached event in channel %i', user_id, channel_id)
            return
        self._events_cache[channel_id].event.registrations.pop(
            user_id, None)

    def store_event(self, stored_event: StoredEvent):
        """Stores an event, also used to overwrite an existing event

        Args:
            stored_event (StoredEvent): The event to store
        """
        self._events_cache[stored_event.channel_id] = stored_event

    def delete_event(self, channel_id: int):
        """Delete an existing event

        Args:
            event_id (int): The ID of the channel associated with the event
        """
        self._events_cache.pop(channel_id, None)

    def get_event(self, channel_id: int) -> StoredEvent | None:
        """Fetch an event based on channel ID

        Args:
            channel_id (int): The ID of the event associated channel

        Returns:
            StoredEvent: The event and all it's storage information
        """
        return self._events_cache.get(channel_id, None)

    def get_default_image(self) -> File:
        """Fetch the default image in file format for events

        Returns:
            File: The default image in File form
        """
        return File('resources/img/default.png')

    def get_past_events(self) -> list[StoredEvent]:
        """Fetch the channel ID's of ended events

        Returns:
            list[tuple[int, int, int]]: A list of channel ID's, scheduled event ID's and guild ID's of events that have ended
        """
        channel_ids_of_past_events = []
        for channel_id in list(self._events_cache.keys()):
            event = self._events_cache[channel_id]
            event_end = event.event.start + timedelta(event.event.duration)
            if event_end < datetime.now():
                channel_ids_of_past_events.append(event)
        return channel_ids_of_past_events

    def get_active_reminders(self) -> list[int]:
        """Get all channels for which a reminder can be sent

        Returns:
            list[int]: The list of channel ID's for which event you may send a reminder
        """
        now = datetime.now()
        active_reminders = []
        for stored_event in self._events_cache.values():
            if stored_event.event.start < now and stored_event.reminder > now:
                active_reminders.append(stored_event.channel_id)
