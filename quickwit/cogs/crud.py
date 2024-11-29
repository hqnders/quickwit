"""Cog handling all CRUD operations for Events"""
from datetime import datetime, timedelta, time
from logging import getLogger
from inspect import getmembers, isclass
import discord
import pytz
from discord.ext import commands, tasks
import quickwit.cogs.registration as registration
import quickwit.cogs.storage as storage
from quickwit import events, utils

MAX_EVENT_DURATION_MINUTES = 300
DEFAULT_EVENT_DURATION_MINUTES = 60
DEFAULT_REMINDER_MINUTES = 30
MAX_EVENT_NAME_LENGTH = 25
EVENT_CHANNEL_CATEGORY = 'events'
DefaultEventClass = events.FF14Event


class CRUD(commands.Cog):
    """CRUD Cog to handle all CRUD operations"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.prune_events.start()

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
                await interaction.response.send_message(content='Invalid time format, use (DD-MM[-YYYY] HH:MM)', ephemeral=True)
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

    @discord.app_commands.command(description="Create an event")
    @discord.app_commands.choices(event_type=[
        discord.app_commands.Choice(
            name=events.Event.REPRESENTATION[0], value=events.Event.REPRESENTATION[0]),
        discord.app_commands.Choice(
            name=events.FF14Event.REPRESENTATION[0], value=events.FF14Event.REPRESENTATION[0]),
        discord.app_commands.Choice(
            name=events.FashionShow.REPRESENTATION[0], value=events.FashionShow.REPRESENTATION[0]),
        discord.app_commands.Choice(name=events.CampfireEvent.REPRESENTATION[0], value=events.CampfireEvent.REPRESENTATION[0])])
    @discord.app_commands.describe(name='The name of the event',
                                   description='The description of the event',
                                   start='The start of the event (DD-MM[-YYYY] HH:MM)',
                                   duration='The duration of the event in minutes',
                                   event_type='The type of event',
                                   image='The cover image of the event',
                                   reminder='Amount of minutes before start to send out a reminder at')
    async def create(self, interaction: discord.Interaction, name: str, description:
                     str, start: str, duration: int = DEFAULT_EVENT_DURATION_MINUTES,
                     event_type: discord.app_commands.Choice[str] = None,
                     image: discord.Attachment = None, reminder: int = DEFAULT_REMINDER_MINUTES):
        """Creates an event, see command description for further instruction"""
        # Get necessary cogs and validate input
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        if await self._inputs_valid(interaction, name, start, duration, image, reminder) is False:
            return

        # Correct the start time to UTC based on user timezone
        user_tz = pytz.timezone(storage_cog.get_timezone(interaction.user.id))
        utc_start = self._get_utc_start(start, user_tz)

        # Get the event channel category, or create if necessary
        event_channel_category = discord.utils.get(
            interaction.guild.categories, name=EVENT_CHANNEL_CATEGORY)
        if event_channel_category is None:
            event_channel_category = await interaction.guild.create_category(
                name=EVENT_CHANNEL_CATEGORY,
                reason='Required to create events')

        event_channel = await interaction.guild.create_text_channel(
            name=name, category=event_channel_category, reason='Hosting an event')
        await interaction.response.send_message(
            content=f'Event {name} created! <#{event_channel.id}>', ephemeral=True)

        # Handle attached image
        file = storage_cog.get_default_image()
        scheduled_event_file = storage_cog.get_default_image()
        if image is not None:
            file = await image.to_file()
            scheduled_event_file = await image.to_file()

        # Create the scheduled event
        end_time = utc_start + timedelta(minutes=duration)
        location = f"<#{event_channel.id}>"
        scheduled_event = await interaction.guild.create_scheduled_event(
            name=name, start_time=utc_start, end_time=end_time,
            description=description, privacy_level=discord.PrivacyLevel.guild_only, location=location, image=scheduled_event_file.fp.read(), reason='Associated with an event'
        )

        # Fetch the right event class
        event_class = DefaultEventClass
        if event_type is not None:
            for _, _event_class in getmembers(events, lambda x: isclass(x) and issubclass(x, events.Event)):
                if _event_class.REPRESENTATION[0] == event_type.value:
                    event_class = _event_class
                    break

        # Fetch the right view
        event_view = registration.EventView()
        relevant_views = [
            view for view in self.bot.persistent_views if isinstance(view, registration.EventView)]
        for view in relevant_views:
            if view.registration_type == event_class.Registration:
                event_view = view
                break

        # Create and store the event
        event = event_class(name=scheduled_event.name, description=scheduled_event.description,
                            start=scheduled_event.start_time, duration=duration, organiser_id=interaction.user.id)  # type: events.Event # noqa
        reminder_time = utc_start - timedelta(minutes=reminder)
        storage_cog.store_event(storage.StoredEvent(
            event, event_channel.id, scheduled_event.id, interaction.guild_id, reminder_time))

        # Send the pinned event overview message with associated UI
        header_message = await event_channel.send(content=event.header_message(), file=file)
        await event_channel.send(content=event.message(), view=event_view)
        await header_message.pin()
        getLogger(__name__).info(f'Created event \"{event.name}\" (channel {event_channel.id}, scheduled {scheduled_event.id})')  # noqa

    @discord.app_commands.command(description='Edit this channel\'s event')
    async def edit(self, interaction: discord.Interaction, name: str = None,
                   start: str = None, description: str = None,
                   duration: int = None, image: discord.Attachment = None, reminder: int = None):
        """Command for editing an existing event, see create command description for further details"""
        # Get necessary cogs, fetch corresponding event, event message and scheduled event and validate input
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        stored_event = storage_cog.get_event(interaction.channel_id)
        if stored_event is None:
            await interaction.response.send_message(
                content='Failed to get event out of storage.', ephemeral=True)
            return
        event = stored_event.event

        messages = [message async for message in interaction.channel.history(limit=2, oldest_first=True)]  # type: list[discord.Message] # noqa
        if len(messages) == 0:
            await interaction.response.send_message(
                content='Could not locate event creation message in this channel.', ephemeral=True)
        header_message = messages[0]
        registration_message = messages[1]

        scheduled_event = await utils.grab_by_id(
            stored_event.scheduled_event_id, interaction.guild.get_scheduled_event, interaction.guild.fetch_scheduled_event)  # type: discord.ScheduledEvent # noqa
        if scheduled_event is None:
            await interaction.response.send_message(
                content='Failed to fetch the associated scheduled event', ephemeral=True)
            return

        if await self._inputs_valid(interaction, name, start, duration, image, reminder) is False:
            return

        if (interaction.user.id != event.organiser_id):
            await interaction.response.send_message(content='Only the event organiser may update this event')
            return

        await interaction.response.send_message(content="Event will be updated!", ephemeral=True)

        # edit event information
        if name is not None:
            event.name = name
        if description is not None:
            event.description = description
        if duration is not None:
            event.duration = duration

        # Handle attached image
        scheduled_event_image = scheduled_event.cover_image
        if image is not None:
            await header_message.edit(attachments=[await image.to_file()])
            scheduled_event_image = (await image.to_file()).fp.read()

        if start is not None:
            current_reminder = (
                event.start - stored_event.reminder).total_seconds() / 60
            user_tz = pytz.timezone(
                storage_cog.get_timezone(interaction.user.id))
            event.start = self._get_utc_start(start, user_tz)
            stored_event.reminder = event.start - \
                timedelta(minutes=current_reminder)

        if reminder is not None:
            stored_event.reminder = event.start - timedelta(minutes=reminder)

        end_time = event.start + timedelta(minutes=event.duration)
        storage_cog.store_event(stored_event)
        await scheduled_event.edit(name=event.name, description=event.description,
                                   channel=scheduled_event.channel, start_time=event.start,
                                   end_time=end_time, privacy_level=discord.PrivacyLevel.guild_only,
                                   entity_type=scheduled_event.entity_type, status=scheduled_event.status, image=scheduled_event_image,
                                   location=scheduled_event.location)
        await interaction.channel.edit(name=event.name)
        await header_message.edit(content=event.header_message())
        await registration_message.edit(content=event.message())
        getLogger(__name__).info(f'{interaction.user.id} edited event {event.name}')  # noqa

    @tasks.loop(time=time(0, 0, 0))
    async def prune_events(self):
        """Cleanup all events that have ended"""
        getLogger(__name__).info('Pruning events')
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        past_events = storage_cog.get_past_events()

        # Delete the channels
        for event_info in past_events:
            storage_cog.delete_event(event_info[0])
            await self._clean_guild(event_info[0], event_info[1], event_info[2])
        getLogger(__name__).info('Done pruning events')

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
        channel = await utils.grab_by_id(
            channel_id, self.bot.get_channel, self.bot.fetch_channel)  # type: discord.TextChannel
        if channel is not None:
            await channel.delete('Event has ended')

        # Delete associated scheduled event
        guild = await utils.grab_by_id(
            guild_id, self.bot.get_guild, self.bot.fetch_guild)  # type: discord.Guild
        if guild is not None:
            scheduled_event = await utils.grab_by_id(
                scheduled_event_id, guild.get_scheduled_event, guild.fetch_scheduled_event)  # type: discord.ScheduledEvent # noqa
            if scheduled_event is not None:
                await scheduled_event.delete('Event has ended')
