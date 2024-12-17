"""The announcement cog to announce to all registrations"""
from logging import getLogger
from discord import app_commands, Interaction, Thread
from discord.ext import commands, tasks
from quickwit.utils import grab_by_id
from .storage import Storage


class Announce(commands.Cog):
    """Cog to send out announcements"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        self.already_reminded = list[int]()
        self.send_reminders.start()

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @app_commands.command()
    async def announce(self, interaction: Interaction, message: str):
        """Announce something to all registrated people 
        by resending your message with a ping to all registrations

        Args:
            message (str): The announcement to make
        """
        # Get channel_id from parent in case the channel is a thread
        channel_id = interaction.channel_id
        if isinstance(interaction.channel, Thread):
            channel_id = interaction.channel.parent.id

        # Announcements can only be made from an event channel
        event = self.storage.get_event(channel_id)
        if event is None:
            await interaction.response.send_message(
                content="Could not find event associated with this channel",
                ephemeral=True)
            return

        # Prevent just anyone from making an announcement
        if interaction.user.id != event.organiser_id:
            await interaction.response.send_message(
                content="Only the event organiser may make announcements",
                ephemeral=True)
            return

        message += '\n'
        for registration in event.registrations:
            if registration.user_id != event.organiser_id:
                message += f'<@{registration.user_id}>'
        await interaction.response.send_message(message)

    @tasks.loop(minutes=1)
    async def send_reminders(self):
        """Sends out reminders for upcoming events"""
        reminders = self.storage.get_active_reminders()
        for channel_id in reminders:
            if channel_id in self.already_reminded:
                break
            event = self.storage.get_event(channel_id)
            channel = await grab_by_id(channel_id, self.bot.get_channel,
                                       self.bot.fetch_channel)
            if channel is None:
                self.already_reminded.append(channel_id)
                break
            start = round(event.utc_start.timestamp())
            message = f'{
                event.name} by <@{event.organiser_id}> will start <t:{start}:R>\n'
            for registration in event.registrations:
                if registration.user_id != event.organiser_id:
                    message += f'<@{registration.user_id}>'
            await channel.send(message)

            getLogger(__name__).info(
                'Sent reminder for event %s', event.name)
            self.already_reminded.append(event.channel_id)
