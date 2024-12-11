"""Contains utility methods used throughout the package"""
from logging import getLogger
from typing import Callable, TypeVar, Coroutine, Sequence
import discord


T = TypeVar('T')
EVENT_ROLE_NAME = 'Events'


async def grab_by_id(a_id: int, get_from_cache: Callable[[int], T],
                     fetch_from_api: Coroutine[None, int, T]) -> T | None:
    """Grabs a Discord resource by ID. First from cache, then from API calls

    Args:
        a_id (int): The ID of the item to grab
        get_from_cache (Callable[[int], T]): The method to get it from cache
        fetch_from_api (Coroutine[None, int, T]): The method to fetch it from API

    Returns:
        T | None: The The resource
    """
    result = get_from_cache(a_id)
    if result is None:
        try:
            getLogger(__name__).info(
                'Using %s to fetch resource with ID: %s', fetch_from_api.__name__, a_id)
            result = await fetch_from_api(a_id)
        except (discord.NotFound, discord.HTTPException) as e:
            getLogger(__name__).error(
                'Encountered error while fetching channel: %s', e)
            return None
    return result


def get_emoji_by_name(emojis: Sequence[discord.Emoji], name: str) -> str:
    """Find an emoji in a sequence by its name, returning a default emoji when not found

    Args:
        emojis (Sequence[discord.Emoji]): The sequence of emojis to search through
        name (str): The name of the emoji to find

    Returns:
        str: The emoji, rendered for Discord
    """
    for e in emojis:
        if e.name.lower() == name.replace(' ', '').lower():
            return str(e)
    return '❓'


async def get_event_role(guild: discord.Guild) -> discord.Role:
    "Retrieves the Event role from a Guild"
    if len(guild.roles) == 0:
        await guild.fetch_roles()

    for role in guild.roles:
        if role.name == EVENT_ROLE_NAME:
            return role
    return guild.default_role
