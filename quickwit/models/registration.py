"""Contains all models necessary for registrations"""
from dataclasses import dataclass
from enum import StrEnum
from .jobs import JobT


class Status(StrEnum):
    """Represents an attendance status"""
    ATTENDING = 'Attending'
    BENCH = 'Bench'
    TENTATIVE = 'Tentative'
    LATE = 'Late'


@dataclass
class Registration:
    """Represents a registration saved in storage"""
    user_id: int
    status: Status
    job: JobT | None = None
