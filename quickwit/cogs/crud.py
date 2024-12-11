"""Cog handling all CRUD operations for Events"""
from datetime import datetime, timedelta, time
from logging import getLogger
import discord
import pytz
from discord.ext import commands, tasks
from quickwit.models import EventType, Event
from quickwit.views import EventMessage
from quickwit.utils import grab_by_id, get_event_role
from .storage import Storage
from .events import BODY_MESSAGE_SENT_EVENT_NAME

MAX_EVENT_DURATION_MINUTES = 300
DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_REMINDER_MINUTES = 30
MAX_EVENT_NAME_LENGTH = 25
EVENT_CHANNEL_CATEGORY = 'events'


class CRUD(commands.Cog):
    """CRUD Cog to handle all CRUD operations"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        self.prune_events.start()

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @discord.app_commands.command(description="Create an event")
    @discord.app_commands.choices(event_type=[
        discord.app_commands.Choice(
            name=event_type,
            value=event_type) for event_type in EventType])
    async def create(self, interaction: discord.Interaction, name: str, description:
                     str, start: str, duration: int = DEFAULT_EVENT_DURATION_MINUTES,
                     event_type: discord.app_commands.Choice[str] = None,
                     image: discord.Attachment = None, reminder: int = DEFAULT_REMINDER_MINUTES):
        """Creates an event, see command description for further instruction

        Args:
            name (str): The name of the event
            description (str): The description of the event
            start (str): The start of the event (DD-MM[-YYYY] HH:MM)
            duration (int): The duration of the event in minutes
            event_type (discord.app_commands.Choice[str]): The type of event
            image (discord.Attachment): The cover image of the event
            reminder (int): Amount of minutes before start to send out a reminder at
        """
        # Validate input
        if await self._inputs_valid(interaction, name, start, duration, image, reminder) is False:
            return

        # Correct the start time to UTC based on user timezone
        user_tz = pytz.timezone(self.storage.get_timezone(interaction.user.id))
        utc_start = self._get_utc_start(start, user_tz)

        # Get the event channel category, or create if necessary
        event_channel_category = discord.utils.get(
            interaction.guild.categories, name=EVENT_CHANNEL_CATEGORY)
        if event_channel_category is None:
            event_channel_category = await interaction.guild.create_category(
                name=EVENT_CHANNEL_CATEGORY,
                reason='Required to create events')

        # Set event channel permissions
        bot_member = interaction.guild.get_member(self.bot.user.id)
        permission_overwrite = {interaction.guild.default_role:
                                discord.PermissionOverwrite(
                                    send_messages=False, send_messages_in_threads=True),
                                bot_member: discord.PermissionOverwrite(
                                    send_messages=True)
                                }

        # Create event channel
        event_channel = await interaction.guild.create_text_channel(
            name=name, category=event_channel_category, reason='Hosting an event',
            overwrites=permission_overwrite)
        await interaction.response.send_message(
            content=f'Event {name} created! <#{event_channel.id}>', ephemeral=True)

        # Handle attached image
        file = discord.File('resources/img/default.png')
        scheduled_event_file = discord.File('resources/img/default.png')
        if image is not None:
            file = await image.to_file()
            scheduled_event_file = await image.to_file()

        # Create the scheduled event
        end_time = utc_start + timedelta(minutes=duration)
        location = f"<#{event_channel.id}>"
        scheduled_event = await interaction.guild.create_scheduled_event(
            name=name, start_time=utc_start, end_time=end_time, description=description,
            privacy_level=discord.PrivacyLevel.guild_only, location=location,
            image=scheduled_event_file.fp.read(), reason='Associated with an event',
            entity_type=discord.EntityType.external
        )

        # Create and store the event
        reminder_time = utc_start - timedelta(minutes=reminder)
        utc_end = utc_start + timedelta(minutes=duration)
        event = Event(event_channel.id, event_type,
                      name, description, scheduled_event.id, interaction.user.id,
                      utc_start, utc_end, interaction.guild_id, reminder_time)
        self.storage.store_event(event)
        self.bot.dispatch(BODY_MESSAGE_SENT_EVENT_NAME, event)
        getLogger(__name__).info('Created event \"%s\" (channel %i, scheduled %i)',
                                 event.name, event_channel.id, scheduled_event.id)

        # Get the event role of the server
        event_role = await get_event_role(interaction.guild)
        event_representation = EventMessage(
            event, self.bot.emojis, event_role.id)

        # Send the pinned event overview message with associated UI
        await event_channel.send(content=event_representation.header_message(),
                                 file=file)
        body_message = await event_channel.send(content=event_representation.body_message())
        await event_channel.create_thread(name='Discussion', type=discord.ChannelType.public_thread,
                                          auto_archive_duration=10080)
        self.bot.dispatch(BODY_MESSAGE_SENT_EVENT_NAME, body_message, event)

    @discord.app_commands.command(description='Edit this channel\'s event')
    async def edit(self, interaction: discord.Interaction, name: str = None,
                   start: str = None, description: str = None,
                   duration: int = None, image: discord.Attachment = None, reminder: int = None):
        """
        Command for editing an existing event, 
        see create command description for further details
        """
        event = self.storage.get_event(interaction.channel_id)
        if event is None:
            await interaction.response.send_message(
                content='Could not find event in storage, impossible to continue', ephemeral=True)
            return

        if event.channel_id != interaction.channel_id:
            await interaction.response.send_message(
                content="You may only edit an event from its associated channel", ephemeral=True)
            return

        if interaction.user.id != event.organiser_id:
            await interaction.response.send_message(
                content='Only the event organiser may update this event',
                ephemeral=True)
            return

        if await self._inputs_valid(interaction, name, start, duration, image, reminder) is False:
            return

        await interaction.response.send_message(content="Updating event", ephemeral=True)

        scheduled_event: discord.ScheduledEvent = await grab_by_id(
            event.scheduled_event_id,
            interaction.guild.get_scheduled_event,
            interaction.guild.fetch_scheduled_event)
        if scheduled_event is None:
            getLogger(__name__).warning("Could not load scheduled event %i in guild %i",
                                        event.scheduled_event_id, interaction.guild.id)

        await interaction.response.send_message(content="Event will be updated!", ephemeral=True)

        messages: list[discord.Message] = \
            [message async for message in interaction.channel.history(limit=2, oldest_first=True)]
        if len(messages) == 0:
            getLogger(__name__).warning("Could not load scheduled event message in channel %i",
                                        interaction.channel_id)

        # edit event information
        if name is not None:
            event.name = name
        if description is not None:
            event.description = description

        # Handle attached image
        scheduled_event_image = None
        if scheduled_event is not None:
            scheduled_event_image = scheduled_event.cover_image

        if image is not None and len(messages) == 2 and scheduled_event_image is not None:
            await messages[0].edit(attachments=[await image.to_file()])
            scheduled_event_image = (await image.to_file()).fp.read()

        # Set start time
        if start is not None:
            current_reminder = (
                event.utc_start - event.reminder).total_seconds() / 60
            current_duration = (
                event.utc_end - event.utc_start).total_seconds() / 60
            user_tz = pytz.timezone(
                self.storage.get_timezone(interaction.user.id))
            event.utc_start = self._get_utc_start(start, user_tz)
            event.reminder = event.utc_start - \
                timedelta(minutes=current_reminder)
            event.utc_end = event.utc_start + \
                timedelta(minutes=current_duration)

        if reminder is not None:
            event.reminder = event.utc_start - timedelta(minutes=reminder)

        if duration is not None:
            event.utc_end = event.utc_start + timedelta(minutes=duration)

        # update Scheduled Event
        if scheduled_event is not None:
            await scheduled_event.edit(name=event.name, description=event.description,
                                       channel=scheduled_event.channel, start_time=event.start,
                                       end_time=event.utc_end, privacy_level=discord.PrivacyLevel.guild_only,
                                       entity_type=scheduled_event.entity_type,
                                       status=scheduled_event.status, image=scheduled_event_image,
                                       location=scheduled_event.location)
        await interaction.channel.edit(name=event.name)

        # Update event messages
        if len(messages) == 2:
            event_role = await get_event_role(interaction.guild)
            representation = EventMessage(
                event, self.bot.emojis, event_role.id)
            await messages[0].edit(content=representation.header_message())
            await messages[1].edit(content=representation.body_message())

        getLogger(__name__).info('%i edited event %s', interaction.user.id, event.name)  # noqa

    @tasks.loop(time=time(0, 0, 0))
    async def prune_events(self):
        """Cleanup all events that have ended"""
        getLogger(__name__).info('Pruning events')
        past_events = self.storage.get_past_event_channel_ids()

        # Delete the channels
        for channel_id in past_events:
            event = self.storage.get_event(channel_id)
            await self._clean_guild(channel_id, event.scheduled_event_id, event.guild_id)
            self.storage.delete_event(channel_id)
        getLogger(__name__).info('Done pruning events')

    async def _inputs_valid(self, interaction: discord.Interaction, name: str, start: str,
                            duration: int, image: discord.Attachment, reminder: int) -> bool:
        if name is not None and len(name) > MAX_EVENT_NAME_LENGTH:
            await interaction.response.send_message(
                content=f'The event name must be {
                    MAX_EVENT_NAME_LENGTH} characters or fewer.',
                ephemeral=True)
            return False

        if start is not None:
            valid = False
            try:
                datetime.strptime(start, '%d-%m %H:%M')
                valid = True
            except ValueError:
                pass
            try:
                datetime.strptime(start, '%d-%m-%Y %H:%M')
                valid = True
            except ValueError:
                pass
            if not valid:
                await interaction.response.send_message(
                    content='Invalid time format, use (DD-MM[-YYYY] HH:MM)',
                    ephemeral=True)
                return False

        if duration is not None and (duration > MAX_EVENT_DURATION_MINUTES or duration < 1):
            await interaction.response.send_message(
                content=f'Invalid duration, must be between 1 and {
                    MAX_EVENT_DURATION_MINUTES} minutes.',
                ephemeral=True)
            return False

        if image is not None and not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                content='Invalid attachment type. Only images are accepted.',
                ephemeral=True)
            return False
        if reminder is not None and reminder < 0:
            await interaction.response.send_message(
                content='Reminder must be a positive number.',
                ephemeral=True)
            return False
        return True

    def _get_utc_start(self, start: str, timezone: pytz.tzinfo.BaseTzInfo):
        start_dt = datetime.now()
        try:
            start_dt = datetime.strptime(start, '%d-%m %H:%M')
            start_dt = start_dt.replace(year=datetime.now().year)
        except ValueError as _:
            start_dt = datetime.strptime(start, '%d-%m-%Y %H:%M')
        start_dt = timezone.localize(start_dt)
        return start_dt.astimezone(pytz.utc)

    async def _clean_guild(self, channel_id: int, scheduled_event_id: int, guild_id: int):
        # Delete associated channel
        channel: discord.TextChannel = await grab_by_id(channel_id, self.bot.get_channel,
                                                        self.bot.fetch_channel)
        if channel is not None:
            await channel.delete(reason='Event has ended')

        # Delete associated scheduled event
        guild: discord.Guild = await grab_by_id(guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is not None:
            scheduled_event: discord.ScheduledEvent = await grab_by_id(
                scheduled_event_id,
                guild.get_scheduled_event,
                guild.fetch_scheduled_event)
            if scheduled_event is not None:
                await scheduled_event.delete(reason='Event has ended')
