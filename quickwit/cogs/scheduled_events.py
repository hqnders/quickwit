"""Contains the cog for handling scheduled event hooks"""
from logging import getLogger
import discord
from discord.ext import commands
from quickwit.models import Status, Registration, Event
from quickwit.utils import grab_by_id
from .storage import Storage


DEFAULT_IMAGE_PATH = 'resources/img/default.png'


class ScheduledEvents(commands.Cog):
    """Cog responsible for hooking into and handling scheduled event events"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, scheduled_event: discord.ScheduledEvent,
                                          user: discord.User):
        """Listens to a user joining a scheduled event"""
        # Ensure the event is associated with an event
        event = self.storage.get_event_from_scheduled_event_id(
            scheduled_event.id)
        if event is None:
            return

        # Ensure the channel exists
        channel = await grab_by_id(event.channel_id, self.bot.get_channel, self.bot.fetch_channel)
        if channel is None:
            return

        # Attempt to get the member display name if they're part of the guild
        member = await grab_by_id(user.id, scheduled_event.guild.get_member,
                                  scheduled_event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name

        # Register user and notify other cogs and members
        await channel.send(f'{name} Registered through the Scheduled Event link')
        registration = Registration(user.id, Status.ATTENDING)
        self.storage.register(event.channel_id, registration)
        self.bot.dispatch('event_altered', event, None)

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, scheduled_event: discord.ScheduledEvent,
                                             user: discord.User):
        """Listens to a user leaving the scheduled event"""
        # Ensure the event is associated with an event
        event = self.storage.get_event_from_scheduled_event_id(
            scheduled_event.id)
        if event is None:
            return

        # Ensure the channel exists
        channel = await grab_by_id(event.channel_id, self.bot.get_channel, self.bot.fetch_channel)
        if channel is None:
            return

        # Attempt to get the member display name if they're part of the guild
        member = await grab_by_id(user.id, scheduled_event.guild.get_member,
                                  scheduled_event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name

        await channel.send(f'{name} Unregistered through the Scheduled Event link')
        self.storage.unregister(event.channel_id, user.id)
        self.bot.dispatch('event_altered', event, None)

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, scheduled_event: discord.ScheduledEvent):
        """Remove the link between event and scheduled event,
            in case the scheduled event gets deleted
        """
        event = self.storage.get_event_from_scheduled_event_id(
            scheduled_event.id)
        if event is None:
            return

        event.scheduled_event_id = None
        self.storage.store_event(event)

    @commands.Cog.listener()
    async def on_event_created(self, event: Event, attachment: discord.Attachment | None):
        """Creates an event associated with the scheduled event"""
        if event.scheduled_event_id is not None:
            return

        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            return

        image_bytes = None
        if attachment is None:
            image_bytes = discord.File(DEFAULT_IMAGE_PATH).fp.read()
        else:
            image_bytes = await attachment.read()

        location = f"<#{event.channel_id}>"
        scheduled_event = await guild.create_scheduled_event(
            name=event.name, start_time=event.utc_start, end_time=event.utc_end,
            description=event.description, privacy_level=discord.PrivacyLevel.guild_only,
            location=location, image=image_bytes, reason='Associated with an event',
            entity_type=discord.EntityType.external
        )
        event.scheduled_event_id = scheduled_event.id
        self.storage.store_event(event)

    @commands.Cog.listener()
    async def on_event_deleted(self, event: Event):
        """When a channel is deleted,
            check whether it was associated to an event and remove it as well
        """
        # No need to remove scheduled event if it was never created
        if event.scheduled_event_id is None:
            return

        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            getLogger(__name__).warning(
                'Could not locate guild %i', event.guild_id)
            return

        scheduled_event = await grab_by_id(
            event.scheduled_event_id, guild.get_scheduled_event, guild.fetch_scheduled_event)
        if scheduled_event is None:
            return

        await scheduled_event.delete(reason='Assocaited event was deleted')

    @commands.Cog.listener()
    async def on_event_altered(self, event: Event, attachment: discord.Attachment | None):
        """Edits the scheduled event when an associated event is altered"""
        if event.scheduled_event_id is None:
            return

        # Ensure we have access to the guild
        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            getLogger(__name__).warning(
                'Could not fetch guild %i', event.guild_id)
            return

        # Ensure the scheduled event exists
        scheduled_event = await grab_by_id(event.scheduled_event_id, guild.get_scheduled_event,
                                           guild.fetch_scheduled_event)
        if scheduled_event is None:
            getLogger(__name__).warning(
                'Could not fetch scheduled event %i from guild %i',
                event.scheduled_event_id, guild.id)
            return
        if scheduled_event.status == discord.EventStatus.ended:
            return

        # Edit the scheduled event
        location = f"<#{event.channel_id}>"
        image_bytes = await scheduled_event.cover_image.read()
        if attachment is not None:
            image_bytes = await attachment.read()

        await scheduled_event.edit(name=event.name, description=event.description,
                                   location=location, start_time=event.utc_start,
                                   end_time=event.utc_end, reason='Event was altered',
                                   image=image_bytes)
