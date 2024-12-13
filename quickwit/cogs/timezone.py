"""The timezone cog for user timezone tracking"""
from logging import getLogger
import pytz
import discord
from discord.ext import commands
from .storage import Storage


class Timezone(commands.Cog):
    """Cog to provide timezone tracking functionalities"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @discord.app_commands.command(description='Set your timezone to \'Continent/City\'')
    async def timezone(self, interaction: discord.Interaction, timezone: str):
        """Sets a user's timezone

        Args:
            interaction (discord.Interaction): The Discord interaction relating to the command call
            timezone (str): The timezone to apply, e.g. \'Europe/Amsterdam\'
        """
        for possible_timezone in pytz.all_timezones:
            if possible_timezone.lower() == timezone.lower().strip():
                self.storage.update_timezone(
                    interaction.user.id, possible_timezone)
                getLogger(__name__).info('User %i set timezone to %s',
                                         interaction.user.id, possible_timezone)
                await interaction.response.send_message(
                    content=f'Your timezone has been set to {
                        possible_timezone}',
                    ephemeral=True)
                return

        await interaction.response.send_message(
            content='Invalid timezone! Please use a valid timezone (e.g., \'America/New_York\')',
            ephemeral=True)

    @discord.app_commands.command()
    async def list_timezones(self, interaction: discord.Interaction, country_code: str):
        """Returns a list of all supported timezones

        Args:
            country_code: ISO 3166 country code (e.g. nl, de, fr, en)
        """
        country_code = country_code.upper()
        if country_code not in pytz.country_timezones.keys():
            await interaction.response.send_message(
                content='Invalid country code, please use a ISO 3166 country code', ephemeral=True)
            return

        message = ''
        for timezone in pytz.country_timezones[country_code]:
            message += f"{timezone}\n"

        await interaction.response.send_message(
            content=f'The following timezones are supported for your country:\n{
                message}',
            ephemeral=True)
