"""Contains the cog for handling registrations, as well as the necessary UI elements"""
from logging import getLogger
import discord
from discord.ext import commands
from quickwit import representations, utils
import quickwit.cogs.storage as storage
from quickwit.representations.views import EventViewBuilder


class Registration(commands.Cog):
    """Registration Cog to handle all Registration operations"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view_builder = EventViewBuilder(self.bot.emojis)

    @commands.Cog.listener()
    async def on_register(self, channel_id: int, user_id: int,
                          registration: representations.EventRepresentation.Registration):
        """Listens to register events thrown by UI components

        Args:
            channel_id (int): The channel ID of the event
            user_id (int): The user who wishes to regiser
            registration (events.Event.Registration): The user's registration
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        try:
            storage_cog.register_user(channel_id, user_id, registration)
            await self._refresh_message(channel_id, storage_cog)
        except ValueError as e:
            getLogger(__name__).error(
                'User tried to register for missing or broken event: %s', e)

    @commands.Cog.listener()
    async def on_unregister(self, channel_id: int, user_id: int):
        """Listens to an unregister event thrown by UI components

        Args:
            channel_id (int): The channel of the event
            user_id (int): The user who wishes to unregister
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        try:
            storage_cog.unregister_user(channel_id, user_id)
            await self._refresh_message(channel_id, storage_cog)
        except ValueError as e:
            getLogger(__name__).error(
                'User %i tried to unregister for missing or broken event: %s', user_id, e)

    async def _refresh_message(self, channel_id: int, storage_cog: storage.Storage):
        channel: discord.TextChannel = await utils.grab_by_id(channel_id, self.bot.get_channel,
                                                              self.bot.fetch_channel)
        if channel is None:
            return None
        message: discord.Message = [message async
                                    for message
                                    in channel.history(limit=2, oldest_first=True)][1]
        event = storage_cog.get_event(channel_id)
        if event is not None:
            await message.edit(content=event.event.message())

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        """Listens to a user joining a scheduled event

        Args:
            event (discord.ScheduledEvent): The event in question
            user (discord.User): The user registering
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        channel_id = int(event.location.split('#')[1].split('>')[0])
        stored_event = storage_cog.get_event(channel_id)
        if stored_event is None:
            return
        registration_type = stored_event.Registration
        registration = registration_type(
            status=registration_type.Status.ATTENDING)
        if isinstance(registration, representations.JobEventRepresentation.Registration):
            for job in registration.Job:
                registration.job = job
                break
        await self.on_register(channel_id, user.id, registration)
        channel = await utils.grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)

        member = await utils.grab_by_id(user.id, event.guild.get_member, event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name
        await channel.send(f'{name} Registered through the Scheduled Event link')

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent,
                                             user: discord.User):
        """Listens to a user leaving the scheduled event

        Args:
            event (discord.ScheduledEvent): The event in question
            user (discord.User): The user unregistering
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        channel_id = int(event.location.split('#')[1].split('>')[0])
        stored_event = storage_cog.get_event(channel_id)
        if stored_event is None:
            return
        await self.on_unregister(channel_id, user.id)
        channel = await utils.grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)

        member = await utils.grab_by_id(user.id, event.guild.get_member, event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name
        await channel.send(f'{name} Unregistered through the Scheduled Event link')
