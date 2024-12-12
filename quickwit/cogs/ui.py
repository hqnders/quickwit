"""Contains the cog for handling registrations, as well as the necessary UI elements"""
from typing import TypeAlias
from logging import getLogger
import discord
from discord.ext import commands
from quickwit.views import JoinButton, LeaveButton, StatusSelect, JobSelect
from quickwit.models import Status, JobType, Registration, Event, EventType, JOB_EVENT_JOB_TYPE_MAP
from quickwit.utils import grab_by_id
from .events import REGISTER_EVENT_NAME, UNREGISTER_EVENT_NAME, BODY_MESSAGE_SENT_EVENT_NAME
from .storage import Storage

RegistrationData: TypeAlias = tuple[Status | None, JobType | None]


class UI(commands.Cog):
    """Cog responsible for handling all things related to UI, mostly input"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        custom_id_prefix = str(bot.user.id)
        self.registration_data = dict[int, dict[int, RegistrationData]]()
        self.event_type_view_map = dict[EventType, discord.ui.View]()

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

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    async def _join_callback(self, interaction: discord.Interaction):
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)

        if registration[0] is None:
            await interaction.response.send_message(content='No Attendance status found',
                                                    ephemeral=True)
            return
        await interaction.response.defer()

        registration = Registration(
            interaction.user.id, registration[0], registration[1])
        self.bot.dispatch(REGISTER_EVENT_NAME,
                          interaction.channel_id, registration)
        self.registration_data[interaction.user.id].pop(interaction.channel_id)

    async def _leave_callback(self, interaction: discord.Interaction):
        self.bot.dispatch(
            UNREGISTER_EVENT_NAME, interaction.channel_id, interaction.user.id)
        interaction.response.defer()

    async def _status_callback(self, interaction: discord.Interaction, status: Status):
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)
        registration[0] = status
        interaction.response.defer()

    async def _job_callback(self, interaction: discord.Interaction, job: JobType):
        registration = self._ensure_existing_registration(
            interaction.user.id, interaction.channel_id)
        registration[1] = job
        interaction.response.defer()

    def _ensure_existing_registration(self, user_id: int, channel_id: int) -> RegistrationData:
        if self.registration_data.get(user_id, None) is None:
            self.registration_data[user_id] = {}

        if self.registration_data[user_id].get(channel_id, None) is None:
            self.registration_data[user_id][channel_id] = (None, None)
        return self.registration_data[user_id][channel_id]

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, scheduled_event: discord.ScheduledEvent, user: discord.User):
        """Listens to a user joining a scheduled event

        Args:
            scheduled_event (discord.ScheduledEvent): The event in question
            user (discord.User): The user registering
        """
        # Ensure the event is associated with an event
        if not self.storage.is_associated_with_event(scheduled_event.id):
            return

        channel_id = int(scheduled_event.location.split('#')[1].split('>')[0])
        channel = await grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
        if channel is None:
            return

        member = await grab_by_id(user.id, scheduled_event.guild.get_member, scheduled_event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name

        await channel.send(f'{name} Registered through the Scheduled Event link')
        self.bot.dispatch(REGISTER_EVENT_NAME, channel_id,
                          Registration(user.id, Status.ATTENDING))

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, scheduled_event: discord.ScheduledEvent,
                                             user: discord.User):
        """Listens to a user leaving the scheduled event

        Args:
            scheduled_event (discord.ScheduledEvent): The event in question
            user (discord.User): The user unregistering
        """
        # Ensure the event is associated with an event
        if not self.storage.is_associated_with_event(scheduled_event.id):
            return

        channel_id = int(scheduled_event.location.split('#')[1].split('>')[0])
        channel = await grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
        if channel is None:
            return

        member = await grab_by_id(user.id, scheduled_event.guild.get_member, scheduled_event.guild.fetch_member)
        name = user.display_name
        if member is not None:
            name = member.display_name

        await channel.send(f'{name} Unregistered through the Scheduled Event link')
        self.bot.dispatch(UNREGISTER_EVENT_NAME, channel_id, user.id)

    @commands.Cog.listener(name=BODY_MESSAGE_SENT_EVENT_NAME)
    async def on_body_message_sent(self, message: discord.Message, event: Event):
        """Inserts the correct view into the body message of an event when sent"""
        view = self.event_type_view_map.get(event.event_type, None)
        if view is None:
            getLogger(__name__).warning(
                'Could not find view for %s', event.event_type)
            return
        await message.edit(view=view)
