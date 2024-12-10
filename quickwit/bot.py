"""Provides the quickwit bot"""
import logging
import sys
import discord
from discord.ext import commands
from quickwit import cogs, utils


class QuickWit(commands.Bot):
    """Wrapper around a commands.Bot to provide QuickWit functionalities"""

    def __init__(self, admin_user_id: int):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix='/', intents=intents)

        self._admin_user_id = admin_user_id

        # Setup logger
        logger = logging.getLogger('quickwit')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '\x1b[30;1m%(asctime)s\x1b[0m %(levelname)-8s\x1b\
                [0m \x1b[35m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    async def setup_hook(self):
        self.add_listener(self.on_ready, 'on_ready')
        self.add_listener(self.on_error, 'on_error')

    async def on_ready(self):
        """Called when quickwit is ready"""
        logging.getLogger(__name__).info("Logged in as %s", self.user)
        await self._load_extensions()

    async def on_error(self, event_method: str, /, *_, **__):
        owner = await utils.grab_by_id(self.owner_id, self.get_user, self.fetch_user)
        await owner.send(
            content=f'An error occured during execution of {event_method}:\n{sys.exception()}')

    async def _load_extensions(self):
        """Loads all relevant extensions"""
        await self.add_cog(cogs.Storage(self))
        await self.add_cog(cogs.CRUD(self))
        await self.add_cog(cogs.Timezone(self))
        await self.add_cog(cogs.Registration(self))
        # await self.add_cog(cogs.Reminder(self))
        # await self.add_cog(cogs.Announce(self))
        # await self.add_cog(cogs.Overview(self))
        try:
            synced = await self.tree.sync()
            logging.getLogger(__name__).info("Synced %i commands", len(synced))
        except (discord.HTTPException,
                discord.app_commands.CommandSyncFailure,
                discord.Forbidden,
                discord.app_commands.MissingApplicationID,
                discord.app_commands.TranslationError) as e:
            logging.getLogger(__name__).info("Failed to sync commands: %s", e)
