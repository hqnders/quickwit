"""Cog to manage persistent storage"""
from discord.ext import commands
from quickwit.models import Registration, Event
from .events import REGISTER_EVENT_NAME, UNREGISTER_EVENT_NAME


class Cache(commands.Cog):
    """Cog for caching event storage"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
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

    @commands.Cog.listener(name=REGISTER_EVENT_NAME)
    async def on_register(self, channel_id: int, registration: Registration):
        """Ensures new registrations are added to cache"""
        if channel_id not in self._events_cache.keys():
            return

        for existing_registration in self._events_cache[channel_id].registrations:
            if existing_registration.user_id == registration.user_id:
                existing_registration = registration
                return
        self._events_cache[channel_id].registrations.append(registration)

    @commands.Cog.listener(name=UNREGISTER_EVENT_NAME)
    async def on_unregister(self, channel_id: int, user_id: int):
        """Ensures registrations are removed from cache"""
        if channel_id not in self._events_cache.keys():
            return
        for existing_registration in self._events_cache[channel_id].registrations:
            if existing_registration.user_id == user_id:
                del existing_registration
                return
