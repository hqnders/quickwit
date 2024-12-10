"""Contains all necessary classes for representing an event"""
from enum import StrEnum
from typing import Sequence
import discord
from quickwit.cogs.storage import Event
from quickwit.utils import get_emoji_by_name


class RegistrationRepresentation:
    """Represents an event registration"""

    def __init__(self, registration: Event.Registration, emojis: Sequence[discord.Emoji]):
        self.registration = registration
        self.emojis = emojis

    def __str__(self):
        status_emoji = get_emoji_by_name(
            self.emojis, self.registration.status)
        if self.registration.job is not None:
            job_emoji = get_emoji_by_name(
                self.emojis, self.registration.job)
            return f'{status_emoji}{job_emoji} {self.registration.status} \
                <@{self.registration.user_id}>'
        return f'{status_emoji} {self.registration.status} <@{self.registration.user_id}>'


class EventRepresentation:
    """Represents an event and it's associated message in Discord"""
    class StatusRepresentation(StrEnum):
        """Represents an attendance status"""
        ATTENDING = 'Attending'
        BENCH = 'Bench'
        TENTATIVE = 'Tentative'
        LATE = 'Late'

    DEFAULT_DURATION_MINUTES = 60
    START_EMOJI_NAME = 'Start'
    DURATION_EMOJI_NAME = 'Duration'
    ORGANISER_EMOJI_NAME = 'Organiser'
    PEOPLE_EMOJI_NAME = 'People'

    # Must be unique across all subclasses
    REPRESENTATION = 'Event'

    def __init__(self, emojis: Sequence[discord.Emoji], event_role_id: int):
        self.event_role_id = event_role_id
        self.emojis = emojis

    def header_message(self, event: Event) -> str:
        """Generates a Discord message representing the event header"""
        return f'# {get_emoji_by_name(self.emojis, self.REPRESENTATION)} {event.name}'

    def body_message(self, event: Event) -> str:
        """Generates a Discord formatted string representing the event body"""
        # Split the registrations by status in order to count and sort attendees
        split_registrations = self._split_registrations_by_status(
            event.registrations)
        guaranteed_attendees = len(split_registrations[self.StatusRepresentation.ATTENDING]) + len(
            split_registrations[self.StatusRepresentation.BENCH])
        maximum_attendees = guaranteed_attendees + \
            len(split_registrations[self.StatusRepresentation.TENTATIVE]
                ) + len(split_registrations[self.StatusRepresentation.LATE])

        # Get the emojis ready
        start_emoji = get_emoji_by_name(self.emojis, self.START_EMOJI_NAME)
        organiser_emoji = get_emoji_by_name(self.emojis, self.START_EMOJI_NAME)
        people_emoji = get_emoji_by_name(self.emojis, self.PEOPLE_EMOJI_NAME)

        # Generate the message
        start = int(event.utc_start.timestamp())
        message = f'<@&{self.event_role_id}>\n{start_emoji} <t:{start}:F>\n{organiser_emoji} \
            <@{event.organiser_id}>'

        # Forego mentioning a duration if it's a default duration
        duration_minutes = (event.utc_end -
                            event.utc_start).total_seconds() / 60
        if duration_minutes != self.DEFAULT_DURATION_MINUTES:
            duration_emoji = get_emoji_by_name(
                self.emojis, self.DURATION_EMOJI_NAME)
            message += f'\t{duration_emoji} {duration_minutes} minutes'

        # Finish with representing attendeeds
        message += f'\n\n{event.description}\n\n{people_emoji} \
            {guaranteed_attendees} - {maximum_attendees} Attendees:\n'

        for registrations_for_status in split_registrations.values():
            for registration in registrations_for_status:
                message += f'\n{str(RegistrationRepresentation(registration, self.emojis))}'

        return message

    def _split_registrations_by_status(self, registrations: list[Event.Registration]) \
            -> dict[StatusRepresentation, list[RegistrationRepresentation]]:
        split_registrations = dict[self.StatusRepresentation,
                                   list[Event.Registration]]()
        for status in self.StatusRepresentation:
            split_registrations[status] = [
                registration
                for registration
                in registrations
                if registration.status == status.value]
        return split_registrations


class JobEventRepresentation(EventRepresentation):
    """Reprentation for an event where registrations have jobs"""
    class Job(StrEnum):
        """Default placeholder job"""
        JOBLESS = 'Jobless'
    REPRESENTATION = "Job Event"


class FF14EventRepresentation(JobEventRepresentation):
    """Represents a job event with FF14 jobs"""
    class Job(StrEnum):
        """Represents FF14 jobs and their Discord emoji"""
        ALL_ROUNDER = 'Allrounder'
        WAR = 'Warrior'
        PLD = 'Paladin'
        DRK = 'Dark Knight'
        GNB = 'Gunbreaker'
        WHM = 'White Mage'
        SCH = 'Scholar'
        AST = 'Astrologian'
        SGE = 'Sage'
        MNK = 'Monk'
        DRG = 'Dragoon'
        NIN = 'Ninja'
        SAM = 'Samurai'
        VPR = 'Viper'
        RPR = 'Reaper'
        BRD = 'Bard'
        MCH = 'Machinist'
        DNC = 'Dancer',
        BLM = 'Black Mage'
        SMN = 'Summoner'
        RDM = 'Red Mage'
        PCT = 'Pictomancer'
        BLU = 'Blue Mage'
    REPRESENTATION = 'Final Fantasy XIV'


class FashionShowRepresentation(JobEventRepresentation):
    """Represents a job event with fashion show jobs"""
    class Job(StrEnum):
        """Represents fashion show jobs and their Discord emoji"""
        CROWD = 'Crowd'
        MODEL = 'Model'
        JUDGE = 'Judge'
    REPRESENTATION = 'Fashion Show'


class CampfireEventRepresentation(JobEventRepresentation):
    """Represents a job event with campfire event jobs"""
    class Job(StrEnum):
        """Represents campfire event jobs and their Discord emoji"""
        CROWD = 'Crowd'
        SPEAKER = 'Speaker'
    REPRESENTATION = 'Campfire Event'
