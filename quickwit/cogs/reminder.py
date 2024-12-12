"""The reminder cog for reminding people of events"""
from logging import getLogger
from discord.ext import tasks, commands
from quickwit import utils
from .storage import Storage

MESSAGE_FORMAT = "{name} by <@{organiser}> will start <t:{start}:R>\n"


class Reminder(commands.Cog):
    """Cog to send out event reminders"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        self.already_reminded = []
        self.send_reminders.start()

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)

    @tasks.loop(minutes=1)
    async def send_reminders(self):
        """Sends out reminders for upcoming events"""
        reminders = self.storage.get_active_reminders()
        for channel_id in reminders:
            if channel_id in self.already_reminded:
                break
            event = self.storage.get_event(channel_id)
            channel = await utils.grab_by_id(channel_id, self.bot.get_channel,
                                             self.bot.fetch_channel)
            if channel is None:
                self.already_reminded.append(channel_id)
                break
            start = round(event.utc_start.timestamp())
            message = MESSAGE_FORMAT.format(name=event.name,
                                            organiser=event.organiser_id,
                                            start=start)
            for registration in event.registrations:
                if registration.user_id != event.organiser_id:
                    message += f'<@{registration.user_id}>'
            await channel.send(message)

            getLogger(__name__).info(
                'Sent reminder for event %s', event.name)
            self.already_reminded.append(event.channel_id)
