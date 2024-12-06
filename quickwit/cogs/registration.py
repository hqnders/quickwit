"""Contains the cog for handling registrations, as well as the necessary UI elements"""
from inspect import getmembers, isclass
from logging import getLogger
from dataclasses import fields
import discord
from discord.ext import commands
from quickwit import events, utils
import quickwit.cogs.storage as storage


class EventView(discord.ui.View):
    """UI View for event registation"""

    def __init__(self, registration_type: events.Event.Registration = events.Event.Registration, custom_id_prefix: str = 'Event'):
        super().__init__(timeout=None)
        self.registration_type = registration_type
        self.registration_data = {}  # type: dict[int, events.Event.Registration] # noqa
        self.add_item(self._PersistentJoinButton(f'{custom_id_prefix}Join'))
        self.add_item(self._PersistentLeaveButton(f'{custom_id_prefix}Leave'))
        self.add_item(self._PersistentStatusSelect(
            f'{custom_id_prefix}Status'))

    class _PersistentJoinButton(discord.ui.Button):
        """Button for parsing registration"""

        def __init__(self, custom_id: str):
            super().__init__(label='Join', custom_id=custom_id,
                             style=discord.ButtonStyle.success, row=4)

        async def callback(self, interaction: discord.Interaction):
            registration_data = self.view.registration_data.get(interaction.user.id, None)  # type: events.Event.Registration # noqa
            if registration_data is None:
                await interaction.response.send_message("Please fill out your registration informaion", ephemeral=True)
                return

            for field in fields(registration_data):
                if getattr(registration_data, field.name) is None:
                    await interaction.response.send_message(f"Could not find value for {field.name}, please resubmit registration", ephemeral=True)
                    return

            interaction.client.dispatch(
                'register', interaction.channel_id, interaction.user.id, self.view.registration_data[interaction.user.id])
            self.view.registration_data.pop(interaction.user.id)
            await interaction.response.defer()

    class _PersistentLeaveButton(discord.ui.Button):
        """Button for unregistering from event"""

        def __init__(self, custom_id: str):
            super().__init__(label='Leave', custom_id=custom_id,
                             style=discord.ButtonStyle.danger, row=4)

        async def callback(self, interaction: discord.Interaction):
            interaction.client.dispatch(
                'unregister', interaction.channel_id, interaction.user.id)
            await interaction.response.defer()

    class _PersistentStatusSelect(discord.ui.Select):
        """Selection field for registration status"""

        def __init__(self, custom_id:  str):
            super().__init__(placeholder='Attendance status...', custom_id=custom_id, min_values=1, max_values=1, options=[discord.SelectOption(
                emoji=status.value[1], label=status.value[0], value=status.value[0]) for status in events.Event.Registration.Status])

        async def callback(self, interaction: discord.Interaction):
            for status in events.Event.Registration.Status:
                if status.value[0] == self.values[0]:
                    if self.view.registration_data.get(interaction.user.id, None) is None:
                        self.view.registration_data[interaction.user.id] = self.view.registration_type(
                            status=status)
                    else:
                        self.view.registration_data[interaction.user.id].status = status
                    break
            await interaction.response.defer()


class JobEventView(EventView):
    """Alternate registration view that allows for job selection"""

    def __init__(self, registration_type: events.JobEvent.Registration, custom_id_prefix: str):
        super().__init__(registration_type, custom_id_prefix)
        self.add_item(self._SelectJob(
            registration_type.Job, f'{custom_id_prefix}Job'))

    class _SelectJob(discord.ui.Select):
        """Selection field for jobs"""

        def __init__(self, job_type: events.JobEvent.Registration.Job, custom_id: str):
            super().__init__(placeholder="Select your job...",
                             min_values=1, max_values=1, custom_id=custom_id, options=[discord.SelectOption(
                                 emoji=job.value[1], label=job.value[0], value=job.value[0]) for job in job_type])
            self.job_type = job_type

        async def callback(self, interaction: discord.Interaction):
            for job in self.job_type:
                if job.value[0] == self.values[0]:
                    if self.view.registration_data.get(interaction.user.id, None) is None:
                        self.view.registration_data[interaction.user.id] = self.view.registration_type(
                            job=job)
                    else:
                        self.view.registration_data[interaction.user.id].job = job
                    break
            await interaction.response.defer()


class Registration(commands.Cog):
    """Registration Cog to handle all Registration operations"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Populate bot views with registration views
        self.bot.add_view(EventView())
        for name, member in getmembers(events, lambda x: isclass(x) and issubclass(x, events.JobEvent) and x != events.JobEvent):
            self.bot.add_view(JobEventView(member.Registration, name))

    @commands.Cog.listener()
    async def on_register(self, channel_id: int, user_id: int, registration: events.Event.Registration):
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
                f'User tried to register for missing or broken event: {e}')

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
                f'User {user_id} tried to unregister for missing or broken event: {e}')

    async def _refresh_message(self, channel_id: int, storage_cog: storage.Storage):
        channel = await utils.grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)  # type: discord.TextChannel # noqa
        if channel is None:
            return None
        message = [message async for message in channel.history(limit=2, oldest_first=True)][1]  # type: discord.Message # noqa
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
        registration_type = stored_event.event.Registration
        registration = registration_type(
            status=registration_type.Status.ATTENDING)
        if isinstance(registration, events.JobEvent.Registration):
            for job in registration.Job:
                registration.job = job
                break
        await self.on_register(channel_id, user.id, registration)
        channel = await utils.grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
        await channel.send(f'{user.name} Registered through the Scheduled Event link')

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
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
        await channel.send(f'{user.name} Unregistered through the Scheduled Event link')
