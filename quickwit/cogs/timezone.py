"""The timezone cog for user timezone tracking"""
from logging import getLogger
import pytz
import discord
from discord.ext import commands
import quickwit.cogs.storage as storage


class Timezone(commands.Cog):
    """Cog to provide timezone tracking functionalities"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(description='Set your timezone to \'Continent/City\'')
    async def timezone(self, interaction: discord.Interaction, timezone: str):
        """Sets a user's timezone

        Args:
            interaction (discord.Interaction): _description_
            timezone (str): _description_
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        if timezone not in pytz.all_timezones:
            await interaction.response.send_message(content='Invalid timezone! Please use a valid timezone (e.g., \'America/New_York\')', ephemeral=True)
            return
        storage_cog.set_timezone(interaction.user.id, timezone)
        getLogger(__name__).info(f'User {interaction.user.id} set timezone to {timezone}')
        await interaction.response.send_message(content=f'Your timezone has been set to {timezone}', ephemeral=True)
