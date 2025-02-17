"""Cog handling all CRUD operations for Events"""
from datetime import timedelta, time, datetime
from logging import getLogger
import discord
import pytz
from discord.ext import commands, tasks
from quickwit.models import EventType, Event
from quickwit.utils import grab_by_id, get_timezone_aware_datetime_from_supported_formats, \
    get_datetime_from_supported_formats
from .storage import Storage

MAX_EVENT_DURATION_MINUTES = 300
DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_REMINDER_MINUTES = 30
MAX_EVENT_NAME_LENGTH = 25
MAX_EVENT_DESCRIPTION_LENGTH = 1000
EVENT_CHANNEL_CATEGORY = 'events'
DEFAULT_EVENT_TYPE = EventType.FF14


def validate_inputs(name: str | None, start: str | None, duration: int | None,
                    image: discord.Attachment | None, reminder: int | None,
                    description: str | None):
    """Predicate for checking whether create and edit options are valid

    Raises:
        ValueError: Raised with information on an invalid input
    """
    if name is not None:
        if len(name) > MAX_EVENT_NAME_LENGTH:
            raise ValueError(f'The event name must be {
                MAX_EVENT_NAME_LENGTH} characters or fewer.')

    if start is not None:
        get_datetime_from_supported_formats(start)

    if duration is not None:
        if duration > MAX_EVENT_DURATION_MINUTES or duration < 1:
            raise ValueError(f'Duration must be between 1 and {
                MAX_EVENT_DURATION_MINUTES}')

    if image is not None:
        if not image.content_type.startswith('image/'):
            raise ValueError('Attachment must be an image')

    if reminder is not None:
        if reminder < 0:
            raise ValueError('Reminder must be a positive number')

    if description is not None and len(description) > MAX_EVENT_DESCRIPTION_LENGTH:
        raise ValueError('Description cannot be more than 1000 characters')


class EventCRUD(commands.Cog):
    """CRUD Cog to handle all CRUD operations"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)
        await self.prune_events()
        self.prune_events.start()

    async def cog_app_command_error(self, interaction: discord.Interaction, _):
        message = 'Encountered an error, please contact the admin'
        if interaction.response.is_done():
            await interaction.followup.send(content=message, ephemeral=True)
        else:
            await interaction.response.send_message(
                content=message, ephemeral=True)

    @discord.app_commands.command()
    @discord.app_commands.choices(event_type=[
        discord.app_commands.Choice(
            name=event_type,
            value=event_type) for event_type in EventType])
    async def create(self, interaction: discord.Interaction, name: str, description:
                     str, start: str, duration: int = DEFAULT_EVENT_DURATION_MINUTES,
                     event_type: discord.app_commands.Choice[str] = None,
                     image: discord.Attachment = None, reminder: int = DEFAULT_REMINDER_MINUTES):
        """Creates an event

        Args:
            name (str): The name of the event
            description (str): The description of the event
            start (str): The start of the event ([DD-MM[-YYYY]] HH:MM)
            duration (int): The duration of the event in minutes
            event_type (discord.app_commands.Choice[str]): The type of event
            image (discord.Attachment): The cover image of the event
            reminder (int): Amount of minutes before start to send out a reminder at
        """
        try:
            validate_inputs(name, start, duration, image, reminder, description)
        except ValueError as e:
            await interaction.response.send_message(content=e, ephemeral=True)
            return

        # Correct the start time to UTC based on user timezone
        user_tz = pytz.timezone(self.storage.get_timezone(interaction.user.id))
        utc_start = get_timezone_aware_datetime_from_supported_formats(
            start, user_tz)

        if utc_start < datetime.now():
            await interaction.response.send_message(content="Cannot schedule event in the past",
                                                    ephemeral=True)
            return

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
                                    send_messages=False,
                                    send_messages_in_threads=True),
                                bot_member: discord.PermissionOverwrite(
                                    send_messages=True),
                                interaction.user: discord.PermissionOverwrite(
                                    send_messages=True,
                                    manage_channels=True
                                )
                                }

        # Create event channel
        event_channel = await interaction.guild.create_text_channel(
            name=name, category=event_channel_category, reason='Hosting an event',
            overwrites=permission_overwrite)
        await interaction.response.send_message(
            content=f'Event {name} created! <#{event_channel.id}>', ephemeral=True)

        # Create and store the event
        if event_type is None:
            event_type = DEFAULT_EVENT_TYPE
        else:
            event_type = event_type.value
        reminder_time = utc_start - timedelta(minutes=reminder)
        utc_end = utc_start + timedelta(minutes=duration)
        event = Event(event_channel.id, event_type,
                      name, description, interaction.user.id,
                      utc_start, utc_end, interaction.guild_id, reminder_time, [])
        self.storage.store_event(event)

        getLogger(__name__).info('Created event \"%s\" (channel %i)',
                                 event.name, event_channel.id)
        self.bot.dispatch('event_created', event, image)

    @discord.app_commands.command()
    async def edit(self, interaction: discord.Interaction, name: str = None,
                   start: str = None, description: str = None,
                   duration: int = None, image: discord.Attachment = None, reminder: int = None):
        """Edit an existing command, refer to `create` command description for further details"""
        try:
            validate_inputs(name, start, duration, image, reminder, description)
        except ValueError as e:
            await interaction.response.send_message(content=e, ephemeral=True)
            return

        # Events can only be edited from their respective channel
        event = self.storage.get_event(interaction.channel_id)
        if event is None:
            await interaction.response.send_message(
                content='Could not find any event associated with this channel', ephemeral=True)
            return

        # Prevent anyone other than the event organiser from editing the event
        if interaction.user.id != event.organiser_id:
            await interaction.response.send_message(
                content='Only the event organiser may update this event',
                ephemeral=True)
            return

        await interaction.response.send_message(content="Event will be updated!", ephemeral=True)

        # edit event information
        if name is not None:
            event.name = name
            await interaction.channel.edit(name=event.name)
        if description is not None:
            event.description = description

        # Update start time and shift reminder and end with it
        if start is not None:
            current_reminder = (
                event.utc_start - event.reminder).total_seconds() / 60
            current_duration = (
                event.utc_end - event.utc_start).total_seconds() / 60
            user_tz = pytz.timezone(
                self.storage.get_timezone(interaction.user.id))
            event.utc_start = get_timezone_aware_datetime_from_supported_formats(
                start, user_tz)

            if event.utc_start < datetime.now():
                await interaction.response.send_message(content="Cannot schedule event in the past",
                                                        ephemeral=True)
                return

            event.reminder = event.utc_start - \
                timedelta(minutes=current_reminder)
            event.utc_end = event.utc_start + \
                timedelta(minutes=current_duration)
        if reminder is not None:
            event.reminder = event.utc_start - timedelta(minutes=reminder)
        if duration is not None:
            event.utc_end = event.utc_start + timedelta(minutes=duration)

        self.storage.store_event(event)
        self.bot.dispatch('event_altered', event, image)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Delete the associated event when the channel is deleted"""
        event = self.storage.get_event(channel.id)
        if event is None:
            return

        self.storage.delete_event(event.channel_id)
        self.bot.dispatch('event_deleted', event)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove a member who left the guild from any associated events"""
        channel_ids = self.storage.get_registered_event_ids(member.id)
        for channel_id in channel_ids:
            channel = await grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
            if channel is not None:
                await channel.send(f'{member.display_name} unregistered by leaving the server')

            self.storage.unregister(channel_id, member.id)
            event = self.storage.get_event(channel_id)
            if event is not None:
                self.bot.dispatch('registrations_altered', event, None)

    @tasks.loop(time=time(0, 0, 0))
    async def prune_events(self):
        """Cleanup all events that have ended"""
        getLogger(__name__).info('Pruning events')
        past_events = self.storage.get_past_events()

        # Delete the channels
        for channel_id, _, __ in past_events:
            channel = await grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
            if channel is not None:
                await channel.delete(reason='Event has ended')
        getLogger(__name__).info('Done pruning events')
