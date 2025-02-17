"""Contains the cog for handling registrations, as well as the necessary UI elements"""
from typing import TypeAlias
from logging import getLogger
import discord
from discord.ext import commands
from quickwit.utils import get_event_role, grab_by_id
from quickwit.views import JoinButton, LeaveButton, StatusSelect, JobSelect, EventMessage
from quickwit.models import Status, JobType, Registration, Event, EventType, JOB_EVENT_JOB_TYPE_MAP
from .storage import Storage

RegistrationData: TypeAlias = tuple[Status | None, JobType | None]
DEFAULT_IMAGE_PATH = 'resources/img/default.png'


class UI(commands.Cog):
    """Cog responsible for handling all things related to UI, mostly input"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        self.registration_data = dict[int, dict[int, RegistrationData]]()
        self.event_type_view_map = dict[EventType, discord.ui.View]()

        # Right now we're taking the bot's ID as the prefix to persistent UI elements
        custom_id_prefix = str(bot.user.id)

        # Generate the views for every event type and add them to the bot
        for event_type in EventType:
            view = discord.ui.View(timeout=None)
            view.add_item(JoinButton(custom_id_prefix, self._join_callback))
            view.add_item(LeaveButton(custom_id_prefix, self._leave_callback))
            view.add_item(StatusSelect(custom_id_prefix,
                          self._status_callback, self.bot.emojis))
            if event_type in JOB_EVENT_JOB_TYPE_MAP:
                view.add_item(JobSelect(custom_id_prefix, JOB_EVENT_JOB_TYPE_MAP[event_type],
                                        self._job_callback, self.bot.emojis))
            self.event_type_view_map[event_type] = view
            self.bot.add_view(view)

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @commands.Cog.listener()
    async def on_event_created(self, event: Event, attachment: discord.Attachment | None):
        """Sends messages in the newly created event channel to represent the event and it's UI"""
        # Ensure the guild exists
        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            getLogger(__name__).warning(
                'Could not find guild %i', event.guild_id)
            return

        # Ensure the channel exists within the guild
        channel = await grab_by_id(event.channel_id, guild.get_channel, guild.fetch_channel)
        if channel is None:
            getLogger(__name__).warning(
                'Could not find channel %i within guild %i', event.channel_id, guild.id)
            return

        # Grab the view corresponding to the event type
        view = self.event_type_view_map.get(event.event_type, None)
        if view is None:
            getLogger(__name__).warning(
                'Could not find view for %s', event.event_type)
            return

        # Send the event creation messages
        event_role = await get_event_role(guild)
        event_representation = EventMessage(
            event, self.bot.emojis, event_role)
        file = None
        if attachment is None:
            file = discord.File(DEFAULT_IMAGE_PATH)
        if attachment is not None:
            file = await attachment.to_file()
        await channel.send(content=event_representation.header_message(), file=file)
        await channel.send(content=event_representation.body_message(), view=view)
        await channel.create_thread(name='Discussion', type=discord.ChannelType.public_thread,
                                    auto_archive_duration=10080)

    @commands.Cog.listener()
    async def on_event_altered(self, event: Event, attachment: discord.Attachment | None):
        """Upates message representations of events on alteration"""
        messages = await self._grab_creation_messages(event.channel_id)
        if messages is None:
            return

        # Ensure the guild exists
        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            return

        # Edit the event creation messages
        event_role = await get_event_role(guild)
        event_message = EventMessage(event, self.bot.emojis, event_role)
        if attachment is not None:
            await messages[0].edit(attachments=[attachment])
        await messages[0].edit(content=event_message.header_message())
        await messages[1].edit(content=event_message.body_message())

    @commands.Cog.listener()
    async def on_registrations_altered(self, event: Event):
        """Updates body message with new registrations"""
        messages = await self._grab_creation_messages(event.channel_id)
        if messages is None:
            return

        # Ensure the guild exists
        guild = await grab_by_id(event.guild_id, self.bot.get_guild, self.bot.fetch_guild)
        if guild is None:
            return

        # Edit the event creation messages
        event_role = await get_event_role(guild)
        event_message = EventMessage(event, self.bot.emojis, event_role).body_message()
        await messages[1].edit(content=event_message)

    @discord.app_commands.command()
    async def refresh_ui(self, interaction: discord.Interaction):
        """Refreshes all UI elements related to this channel's event"""
        event = self.storage.get_event(interaction.channel_id)
        if event is None:
            return

        view = self.event_type_view_map.get(event.event_type, None)
        if view is None:
            return

        messages = await self._grab_creation_messages(event.channel_id)
        if messages is None:
            return
        await interaction.response.send_message(content="Refreshing UI elements", ephemeral=True)
        await messages[1].edit(view=view)

    async def _join_callback(self, interaction: discord.Interaction):
        # Ensure there is registration data to edit
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)

        # Attendance status is required
        if registration[0] is None:
            await interaction.response.send_message(
                content='Could not find your attendance status, '
                'please change your selection and join again',
                ephemeral=True)
            return

        # We can send out the response already while we parse the registration
        await interaction.response.defer()

        # Build the registration
        registration = Registration(
            interaction.user.id, registration[0], registration[1])
        self.storage.register(interaction.channel_id, registration)

        # Make sure event exists
        event = self.storage.get_event(interaction.channel_id)
        if event is None:
            interaction.response.send_message(
                content='UI Element is not associated with any event, how did you get here?!',
                ephemeral=True)
            return

        # Inform the other cogs of the registration
        self.bot.dispatch('registrations_altered', event)

    async def _leave_callback(self, interaction: discord.Interaction):
        # Make sure event exists
        event = self.storage.get_event(interaction.channel_id)
        if event is None:
            interaction.response.send_message(
                content='UI Element is not associated with any event, how did you get here?!',
                ephemeral=True)
            return

        # We can send out the response already while we parse the registration
        await interaction.response.defer()

        # Silently stop further actions if user was not registered in the first place
        registered = False
        for registration in event.registrations:
            if registration.user_id == interaction.user.id:
                registered = True
                break
        if not registered:
            return

        # Unregister from the event
        self.storage.unregister(interaction.channel_id, interaction.user.id)
        for registration in event.registrations:
            if registration.user_id == interaction.user.id:
                event.registrations.remove(registration)
                break

        # Inform other cogs of unregistration
        self.bot.dispatch('registrations_altered', event)

    async def _status_callback(self, interaction: discord.Interaction, status: Status):
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)
        self.registration_data[interaction.user.id][interaction.channel_id] = (
            status, registration[1])
        await interaction.response.defer()

    async def _job_callback(self, interaction: discord.Interaction, job: JobType):
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)
        self.registration_data[interaction.user.id][interaction.channel_id] = (
            registration[0], job)
        await interaction.response.defer()

    def _ensure_existing_registration(self, user_id: int, channel_id: int) -> RegistrationData:
        if self.registration_data.get(user_id, None) is None:
            self.registration_data[user_id] = {}

        if self.registration_data[user_id].get(channel_id, None) is None:
            self.registration_data[user_id][channel_id] = (None, None)
        return self.registration_data[user_id][channel_id]

    async def _grab_creation_messages(self, channel_id: int) \
            -> tuple[discord.Message, discord.Message] | None:
        # Ensure the channel exists
        channel = await grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
        if channel is None:
            return None

        # Ensure event creation messages are present
        messages = [message async for message in channel.history(limit=2, oldest_first=True)]
        if len(messages) != 2:
            return None
        return (messages[0], messages[1])
