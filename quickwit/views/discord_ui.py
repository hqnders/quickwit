from typing import Sequence, Callable, Coroutine, Any
import discord
from quickwit.utils import get_emoji_by_name
from quickwit.models import JobType, Status

type ButtonCallback = Callable[[discord.Interaction], Coroutine[Any, Any, Any]]
type StatusSelectCallback = Callable[[
    discord.Interaction, Status], Coroutine[Any, Any, Any]]
type JobSelectCallback = Callable[[
    discord.Interaction, JobType], Coroutine[Any, Any, Any]]


class JoinButton(discord.ui.Button):
    """Button for parsing registration"""

    def __init__(self, custom_id_prefix: str, callback: ButtonCallback):
        super().__init__(label='Join', custom_id=f'{custom_id_prefix}Join',
                         style=discord.ButtonStyle.success, row=4)
        self.callback = callback


class LeaveButton(discord.ui.Button):
    """Button for unregistering from event"""

    def __init__(self, custom_id_prefix: str, callback: ButtonCallback):
        super().__init__(label='Leave', custom_id=f'{custom_id_prefix}Leave',
                         style=discord.ButtonStyle.danger, row=4)
        self.callback = callback


class StatusSelect(discord.ui.Select):
    """Selection field for registration status"""

    def __init__(self, custom_id_prefix: str, callback: StatusSelectCallback, emojis: Sequence[discord.Emoji]):
        super().__init__(
            placeholder='Attendance status...', custom_id=f'{custom_id_prefix}Status', min_values=1,
            max_values=1, options=[discord.SelectOption(
                emoji=get_emoji_by_name(emojis, status), label=status, value=status)
                for status in Status])
        self._true_callback = callback

    async def callback(self, interaction):
        return await self._true_callback(interaction, self.values[0])


class JobSelect(discord.ui.Select):
    """Selection field for jobs"""

    def __init__(self, custom_id_prefix: str, job_type: JobType, callback: JobSelectCallback, emojis: Sequence[discord.Emoji]):
        super().__init__(
            placeholder="Select your job...",
            min_values=1, max_values=1, custom_id=f'{custom_id_prefix}Job',
            options=[discord.SelectOption(
                emoji=get_emoji_by_name(emojis, job), label=job, value=job)
                for job
                in job_type])
        self._true_callback = callback

    async def callback(self, interaction):
        return await self._true_callback(interaction, self.values[0])
