"""Provides the quickwit bot"""
import logging
import discord
from discord.ext import commands
from quickwit import cogs


# Setup logger
logger = logging.getLogger('quickwit')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '\x1b[30;1m%(asctime)s\x1b[0m %(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

quickwit = commands.Bot(command_prefix="/", intents=discord.Intents.all())


async def load_extensions():
    """Loads all relevant extensions"""
    await quickwit.add_cog(cogs.PersistentStorage(quickwit))
    await quickwit.add_cog(cogs.CRUD(quickwit))
    await quickwit.add_cog(cogs.Timezone(quickwit))
    await quickwit.add_cog(cogs.Registration(quickwit))
    await quickwit.add_cog(cogs.Reminder(quickwit))
    try:
        synced = await quickwit.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except (discord.HTTPException, discord.app_commands.CommandSyncFailure, discord.Forbidden, discord.app_commands.MissingApplicationID, discord.app_commands.TranslationError) as e:
        logger.info(f"Failed to sync commands: {e}")


@quickwit.event
async def on_ready():
    """Called when quickwit is ready"""
    logger.info(f"Logged in as {quickwit.user}")
    await load_extensions()
