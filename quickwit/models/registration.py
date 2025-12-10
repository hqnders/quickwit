"""Contains all models necessary for registrations"""
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Union
from .jobs import JobT

class Status(StrEnum):
    """Represents an attendance status"""
    ATTENDING = 'Attending'
    BACKUP = 'Backup'
    MAYBE = 'Maybe'
    LATE = 'Late'

@dataclass
class Registration:
    """Represents a registration saved in storage"""
    user_id: int
    status: Status
    job: Optional[JobT] = None
