"""The roles cog to manage event roles"""
import os
from logging import getLogger
from discord import RawReactionActionEvent
from discord.ext import commands
from quickwit.utils import get_event_role, grab_by_id
from .storage import Storage


class Roles(commands.Cog):
    """Cog to assign roles"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = self.bot.get_cog(Storage.__name__)
        self.already_reminded = list[int]()
        self.roles_message_ids = [int(message_id) for message_id in os.getenv('ROLE_MESSAGE_IDS').split(',')]

    async def cog_load(self):
        if self.storage is None:
            self.storage = Storage(self.bot)
            await self.bot.add_cog(self.storage)
        getLogger(__name__).info('Successfully loaded cog %s', __name__)

    async def _toggle_role(self, guild_id: int, user_id: int):
        guild = await grab_by_id(guild_id, self.bot.get_guild, self.bot.fetch_guild)
        member = await grab_by_id(user_id, guild.get_member, guild.fetch_member)
        role = await get_event_role(guild)
        
        if member.get_role(role.id) is None:
            await member.add_roles(role)
            getLogger(__name__).info('Added event role to %s', member.name)
        else:
            await member.remove_roles(role)
            getLogger(__name__).info('Removed event role from %s', member.name)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.message_id not in self.roles_message_ids:
            return
        await self._toggle_role(payload.guild_id, payload.user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if payload.message_id not in self.roles_message_ids:
            return
        await self._toggle_role(payload.guild_id, payload.user_id)



