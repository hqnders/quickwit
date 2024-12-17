"""Contains all models necessary for Events"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from .registration import Registration
from .jobs import FF14Job, FashionShowJob, CampfireEventJob


class EventType(StrEnum):
    EVENT = 'Event'
    FF14 = 'Final Fantasy XIV'
    FASHION = 'Fashion Show'
    CAMPFIRE = 'Campfire Event'


JOB_EVENT_JOB_TYPE_MAP = {
    EventType.FF14: FF14Job,
    EventType.FASHION: FashionShowJob,
    EventType.CAMPFIRE: CampfireEventJob
}


@dataclass
class Event:
    """Represents an Event saved in storage"""
    channel_id: int
    event_type: EventType
    name: str
    description: str
    organiser_id: int
    utc_start: datetime
    utc_end: datetime
    guild_id: int
    reminder: datetime
    registrations: list[Registration]
    scheduled_event_id: int | None = None
