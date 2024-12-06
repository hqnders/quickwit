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
            interaction (discord.Interaction): The Discord interaction relating to the command call
            timezone (str): The timezone to apply, e.g. \'Europe/Amsterdam\'
        """
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        if timezone not in pytz.all_timezones:
            await interaction.response.send_message(content='Invalid timezone! Please use a valid timezone (e.g., \'America/New_York\')', ephemeral=True)
            return
        storage_cog.set_timezone(interaction.user.id, timezone)
        getLogger(__name__).info(
            'User %i set timezone to %s', interaction.user.id, timezone)
        await interaction.response.send_message(content=f'Your timezone has been set to {timezone}', ephemeral=True)

    @discord.app_commands.command()
    async def list_timezones(self, interaction: discord.Interaction, country_code: str):
        """Returns a list of all supported timezones

        Args:
            country_code: ISO 3166 country code (e.g. nl, de, fr, en)
        """
        country_code = country_code.upper()
        if country_code not in pytz.country_timezones.keys():
            await interaction.response.send_message(content='Invalid country code, please use a ISO 3166 country code', ephemeral=True)
            return

        message = ''
        for timezone in pytz.country_timezones[country_code]:
            message += f"{timezone}\n"

        await interaction.response.send_message(content=f'The following timezones are supported for your country:\n{message}', ephemeral=True)
