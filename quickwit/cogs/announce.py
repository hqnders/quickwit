"""The announcement cog to announce to all registrations"""
from discord import app_commands, Interaction
from discord.ext import commands
from .storage import Storage

MESSAGE_FORMAT = "**Message by <@{organiser}> to all registrated people:**\n{message}\n"


class Announce(commands.Cog):
    """Cog to send out announcements"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.already_reminded = []

    @app_commands.command()
    async def announce(self, interaction: Interaction, message: str):
        """Announce something to all registrated people 
        by resending your message with a ping to all registrations

        Args:
            message (str): The announcement to make
        """
        storage_cog: Storage = self.bot.get_cog('Storage')

        event = storage_cog.get_event(interaction.channel_id)
        if event is None:
            await interaction.response.send_message(
                content="Could not find event associated with this channel",
                ephemeral=True)
            return

        if interaction.user.id != event.event.organiser_id:
            await interaction.response.send_message(
                content="Only the event organiser may make announcements",
                ephemeral=True)
            return

        message = MESSAGE_FORMAT.format(
            organiser=event.organiser_id, message=message)
        for registration in event.registrations:
            if registration.user_id != event.organiser_id:
                message += f'<@{registration.user_id}>'
        await interaction.channel.send(message)
        await interaction.response.send_message(content="Announcement has been made",
                                                ephemeral=True)
