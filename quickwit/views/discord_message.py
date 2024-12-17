"""Contains all necessary classes for representing an event"""
from typing import Sequence
import discord
from quickwit.utils import get_emoji_by_name
from quickwit.models import Event, Registration, Status

DEFAULT_DURATION_MINUTES = 60
START_EMOJI_NAME = 'Start'
DURATION_EMOJI_NAME = 'Duration'
ORGANISER_EMOJI_NAME = 'Organiser'
PEOPLE_EMOJI_NAME = 'People'


class RegistrationMessage:
    """Represents an event registration"""

    def __init__(self, registration: Registration, emojis: Sequence[discord.Emoji]):
        self.registration = registration
        self.emojis = emojis

    def __str__(self):
        status_emoji = get_emoji_by_name(
            self.emojis, self.registration.status)
        if status_emoji == '❓':
            status_emoji = f'{self.registration.status} '

        if self.registration.job is not None:
            job_emoji = get_emoji_by_name(
                self.emojis, self.registration.job)
            if job_emoji == '❓':
                job_emoji = self.registration.job

            return f'{job_emoji} <@{self.registration.user_id}>'
        return f'<@{self.registration.user_id}>'


class EventMessage:
    """Represents an event and it's associated message in Discord"""

    def __init__(self, event: Event, emojis: Sequence[discord.Emoji], event_role: discord.Role):
        self.event_role = event_role
        self.emojis = emojis
        self.event = event

    def header_message(self) -> str:
        """Generates a Discord message representing the event header"""
        return f'# {get_emoji_by_name(self.emojis, self.event.event_type)} {self.event.name}\n{self.event_role.mention}'  # noqa

    def body_message(self) -> str:
        """Generates a Discord formatted string representing the event body"""
        # Split the registrations by status in order to count and sort attendees
        split_registrations = self._split_registrations_by_status(
            self.event.registrations)
        guaranteed_attendees = len(split_registrations[Status.ATTENDING]) + len(
            split_registrations[Status.BENCH])
        maximum_attendees = guaranteed_attendees + \
            len(split_registrations[Status.TENTATIVE]
                ) + len(split_registrations[Status.LATE])

        # Get the emojis ready
        start_emoji = get_emoji_by_name(self.emojis, START_EMOJI_NAME)
        organiser_emoji = get_emoji_by_name(self.emojis, ORGANISER_EMOJI_NAME)
        people_emoji = get_emoji_by_name(self.emojis, PEOPLE_EMOJI_NAME)

        # Generate the message
        start = int(self.event.utc_start.timestamp())
        message = f'{start_emoji} <t:{start}:F>\n{organiser_emoji} <@{self.event.organiser_id}>'  # noqa

        # Forego mentioning a duration if it's a default duration
        duration_minutes = round((self.event.utc_end -
                            self.event.utc_start).total_seconds() / 60)
        if duration_minutes != DEFAULT_DURATION_MINUTES:
            duration_emoji = get_emoji_by_name(
                self.emojis, DURATION_EMOJI_NAME)
            message += f'\t{duration_emoji} {duration_minutes} minutes'

        # Finish with representing attendeeds
        message += f'\n\n{self.event.description}\n\n{people_emoji} {guaranteed_attendees} - {maximum_attendees} Attendees:'  # noqa

        for status, registrations in split_registrations.items():
            if len(registrations) == 0:
                continue
            status_emoji = get_emoji_by_name(self.emojis, status)
            message += f'\n{status_emoji} {status}:'
            for registration in registrations:
                message += f'\n{str(RegistrationMessage(registration, self.emojis))}'
            message += '\n'

        return message

    def __str__(self):
        return f'{self.header_message()}\n{self.body_message()}'

    def _split_registrations_by_status(self, registrations: list[Registration]) \
            -> dict[Status, list[Registration]]:
        split_registrations = dict[Status, list[Registration]]()
        for status in Status:
            split_registrations[status] = [
                registration
                for registration
                in registrations
                if registration.status == status.value]
        return split_registrations
