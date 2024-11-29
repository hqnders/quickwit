"""The reminder cog for reminding people of events"""
from logging import getLogger
from discord.ext import tasks, commands
from quickwit import utils
import quickwit.cogs.storage as storage

MESSAGE_FORMAT = "{name} by <@{organiser}> will start <t:{start}:R>\n"


class Reminder(commands.Cog):
    """Cog to send out event reminders"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.already_reminded = []
        self.send_reminders.start()

    @tasks.loop(minutes=1)
    async def send_reminders(self):
        """Sends out reminders for upcoming events"""
        storage_cog = self.bot.get_cog('Storage')  # type: storage.Storage
        reminders = storage_cog.get_active_reminders()
        for channel_id in reminders:
            if channel_id in self.already_reminded:
                break
            stored_event = storage_cog.get_event(channel_id)
            channel = await utils.grab_by_id(channel_id, self.bot.get_channel, self.bot.fetch_channel)
            if channel is None:
                self.already_reminded.append(channel_id)
                break
            start = round(stored_event.event.start.timestamp())
            message = MESSAGE_FORMAT.format(
                name=stored_event.event.name, organiser=stored_event.event.organiser_id, start=start)
            for user_id in stored_event.event.registrations.keys():
                if user_id != stored_event.event.organiser_id:
                    message += f'<@{user_id}>'
            await channel.send(message)
            getLogger(__name__).info(
                f'Sent reminder for event {stored_event.event.name}')
            self.already_reminded.append(stored_event.channel_id)
