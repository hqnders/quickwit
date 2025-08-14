"""Contains utility methods used throughout the package"""
from logging import getLogger
from typing import Callable, TypeVar, Coroutine, Sequence
from datetime import datetime
import pytz
import discord


T = TypeVar('T')

EVENT_ROLE_NAME = 'Events'

EMOJIS = [
    ('Tank', '<:Tank:1318563147971563541>'),
    ('Healer', '<:Healer:1318563129172426782>'),
    ('DPS', '<:DPS:1318563106313732106>'),
    ('CampfireEvent','<:Campfire:1303500098306572388>'),
    ('FashionShow','<:FashionShow:1303500090710687785>'),
    ('Judge','<:Judge:1303499086363758732>'),
    ('Speaker','<:Speaker:1303499095217930250>'),
    ('Crowd','<:Crowd:1303499075865415731>'),
    ('Model','<:Model:1303499055434960937>'),
    ('Duration','<:Duration:1303485160934604872>'),
    ('FinalFantasyXIV','<:FF14:1302571147258236949>'),
    ('Event','<:Event:1302570929024536626>'),
    ('Attending','<:Attending:1302340634933334137>'),
    ('Organiser','<:Organiser:1302339823813787778>'),
    ('People','<:People:1302339799436234802>'),
    ('Start','<:Start:1302339755224338432>'),
    ('Tentative','<:Tentative:1302339734802272267>'),
    ('Late','<:Late:1302339715063877793>'),
    ('Bench','<:Bench:1302339692355784845>'),
    ('Allrounder','<:Allrounder:1302305556966539346>'),
    ('Pictomancer','<:Pictomancer:1302304017107652782>'),
    ('BlueMage','<:BlueMage:1302300345069994004>'),
    ('Samurai','<:Samurai:1302300299729305652>'),
    ('Reaper','<:Reaper:1302300288585044139>'),
    ('Ninja','<:Ninja:1302300281907970049>'),
    ('Monk','<:Monk:1302300274488246322>'),
    ('Machinist','<:Machinist:1302300267680890981>'),
    ('Dragoon','<:Dragoon:1302300259631894568>'),
    ('Dancer','<:Dancer:1302300251679494235>'),
    ('Summoner','<:Summoner:1302300220490776656>'),
    ('RedMage','<:RedMage:1302300210923569183>'),
    ('BlackMage','<:BlackMage:1302300194045694023>'),
    ('Bard','<:Bard:1302300185543708733>'),
    ('WhiteMage','<:WhiteMage:1302300161271267388>'),
    ('Scholar','<:Scholar:1302300155097387118>'),
    ('Sage','<:Sage:1302300147753160714>'),
    ('Astrologian','<:Astrologian:1302300139624595486>'),
    ('Warrior','<:Warrior:1302300106103455835>'),
    ('Paladin','<:Paladin:1302300099103166565>'),
    ('GunBreaker','<:Gunbreaker:1302300089292951593>'),
    ('DarkKnight','<:DarkKnight:1302300076600725616>'),
    ('Viper', '<:Viper:1302303987671765114>')
]


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
    for e in EMOJIS:
        if e[0].lower() == name.replace(' ', '').lower():
            return e[1]
    return '❓'


async def get_event_role(guild: discord.Guild) -> discord.Role:
    "Retrieves the Event role from a Guild, defaulting to guild's default role"
    if len(guild.roles) == 0:
        await guild.fetch_roles()

    for role in guild.roles:
        if role.name == EVENT_ROLE_NAME:
            return role
    return guild.default_role


def strptime_no_exception(datetime_str: str, format_str) -> datetime | None:
    """Executes datetime.strptime without throwing an exception"""
    try:
        return datetime.strptime(datetime_str, format_str)
    except ValueError:
        pass
    return None


def get_datetime_from_supported_formats(datetime_str: str) -> datetime:
    """Returns a datetime object parsed from any supported format

    Raises:
        ValueError: Raised when no supported pattern matches
    """
    dt = strptime_no_exception(datetime_str, '%d-%m-%Y %H:%M')
    now = datetime.now()
    if dt is None:
        dt = strptime_no_exception(datetime_str, '%d/%m/%Y %H:%M')
    if dt is None:
        dt = strptime_no_exception(datetime_str, '%d-%m %H:%M')
        if dt is not None:
            dt = dt.replace(year=now.year)
    if dt is None:
        dt = strptime_no_exception(datetime_str, '%d/%m %H:%M')
        if dt is not None:
            dt = dt.replace(year=now.year)
    if dt is None:
        dt = strptime_no_exception(datetime_str, '%H:%M')
        if dt is not None:
            dt = dt.replace(year=now.year, month=now.month, day=now.day)
    if dt is None:
        raise ValueError(
            f'Could not match {datetime_str} to any supported format')
    return dt


def get_timezone_aware_datetime_from_supported_formats(
        datetime_str: str,
        timezone: pytz.tzinfo.BaseTzInfo) -> datetime:
    """Generate a timezone aware datetime object from string

    Raises:
        ValueError: Raised when no supported pattern matches
    """
    dt = get_datetime_from_supported_formats(datetime_str)
    dt = timezone.localize(dt)
    return dt.astimezone(pytz.utc)
