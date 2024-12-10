from typing import Sequence
from inspect import getmembers, isclass
import discord
from quickwit.utils import get_emoji_by_name
from . import events


class EventViewBuilder:
    def __init__(self, emojis: Sequence[discord.Emoji]):
        self.views = dict[str, discord.ui.View]()
        for _, event_type in getmembers(events):
            if isclass(event_type) and issubclass(event_type, events.EventRepresentation):
                self.views[event_type.REPRESENTATION] = self._build_view(
                    event_type, emojis)

    def _build_view(self, event_type: events.EventRepresentation,
                    emojis: Sequence[discord.Emoji]) -> discord.ui.View:
        custom_id_prefix = event_type.__name__
        view = discord.ui.View(timeout=None)
        view.add_item(_JoinButton(f'{custom_id_prefix}Join'))
        view.add_item(_LeaveButton(f'{custom_id_prefix}Leave'))
        view.add_item(_StatusSelect(
            f'{custom_id_prefix}Status', emojis))
        if issubclass(event_type, events.JobEventRepresentation) \
                and event_type != events.JobEventRepresentation:
            view.add_item(_SelectJob(
                f'{custom_id_prefix}Job', emojis, event_type.Job))
        return view


class _JoinButton(discord.ui.Button):
    """Button for parsing registration"""

    def __init__(self, custom_id: str):
        super().__init__(label='Join', custom_id=custom_id,
                         style=discord.ButtonStyle.success, row=4)

    async def callback(self, interaction: discord.Interaction):
        interaction.client.dispatch(
            'register', interaction.channel_id, interaction.user.id)
        await interaction.response.defer()


class _LeaveButton(discord.ui.Button):
    """Button for unregistering from event"""

    def __init__(self, custom_id: str):
        super().__init__(label='Leave', custom_id=custom_id,
                         style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        interaction.client.dispatch(
            'unregister', interaction.channel_id, interaction.user.id)
        await interaction.response.defer()


class _StatusSelect(discord.ui.Select):
    """Selection field for registration status"""

    def __init__(self, custom_id: str, emojis: Sequence[discord.Emoji]):
        super().__init__(
            placeholder='Attendance status...', custom_id=custom_id, min_values=1,
            max_values=1, options=[discord.SelectOption(
                emoji=get_emoji_by_name(emojis, status), label=status, value=status)
                for status in events.EventRepresentation.StatusRepresentation])

    async def callback(self, interaction: discord.Interaction):
        interaction.client.dispatch(
            'user_selected_status', interaction.channel_id, interaction.user.id, self.values[0])
        await interaction.response.defer()


class _SelectJob(discord.ui.Select):
    """Selection field for jobs"""

    def __init__(self, custom_id: str, emojis: Sequence[discord.Emoji],
                 job_type: events.JobEventRepresentation.Job):
        super().__init__(
            placeholder="Select your job...",
            min_values=1, max_values=1, custom_id=custom_id,
            options=[discord.SelectOption(
                emoji=get_emoji_by_name(emojis, job), label=job, value=job)
                for job
                in job_type])

    async def callback(self, interaction: discord.Interaction):
        interaction.client.dispatch(
            'user_selected_job', interaction.channel_id, interaction.user.id, self.values[0])
        await interaction.response.defer()
